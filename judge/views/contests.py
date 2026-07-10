import json
import csv
import re
from calendar import Calendar, SUNDAY
from collections import defaultdict, namedtuple
from datetime import date, datetime, time, timedelta
from functools import partial
from itertools import chain
from operator import attrgetter, itemgetter

from django import forms
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import BooleanField, Case, Count, F, FloatField, IntegerField, Max, Min, Q, Sum, Value, When
from django.db.models.expressions import CombinedExpression, Exists, OuterRef
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _, gettext_lazy
from django.views.generic import ListView, TemplateView, View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.list import BaseListView
from icalendar import Calendar as ICalendar, Event
from reversion import revisions

from judge import event_poster as event
from judge.comments import CommentedDetailView
from judge.forms import ContestCloneForm, ThemisUploadForm
from judge.models import Contest, ContestMoss, ContestParticipation, ContestProblem, ContestTag, \
    Problem, Profile, Submission, Language, ContestSubmission, SubmissionSource, ThemisExtensionMapping, \
    ProblemData
from judge.models.problem_data import IO_MODES
from judge.tasks import run_moss
from judge.utils.celery import redirect_to_task_status
from judge.utils.opengraph import generate_opengraph
from judge.utils.problems import _get_result_data
from judge.utils.ranker import ranker
from judge.utils.stats import get_bar_chart, get_pie_chart
from judge.utils.views import DiggPaginatorMixin, QueryStringSortMixin, SingleObjectFormView, TitleMixin, \
    generic_message

__all__ = ['ContestList', 'ContestDetail', 'ContestRanking', 'ContestJoin', 'ContestLeave', 'ContestCalendar',
           'ContestClone', 'ContestStats', 'ContestMossView', 'ContestMossDelete', 'contest_ranking_ajax',
           'ContestParticipationList', 'ContestParticipationDisqualify', 'get_contest_ranking_list',
           'base_contest_ranking_list', 'ContestThemisUpload', 'ContestQuickEdit']


def _find_contest(request, key, private_check=True):
    try:
        contest = Contest.objects.get(key=key)
        if private_check and not contest.is_accessible_by(request.user):
            raise ObjectDoesNotExist()
    except ObjectDoesNotExist:
        return generic_message(request, _('No such contest'),
                               _('Could not find a contest with the key "%s".') % key, status=404), False
    return contest, True


class ContestListMixin(object):
    def get_queryset(self):
        return Contest.get_visible_contests(self.request.user)


class ContestList(QueryStringSortMixin, DiggPaginatorMixin, TitleMixin, ContestListMixin, ListView):
    model = Contest
    paginate_by = 20
    template_name = 'contest/list.html'
    title = gettext_lazy('Contests')
    context_object_name = 'past_contests'
    all_sorts = frozenset(('name', 'user_count', 'start_time'))
    default_desc = frozenset(('name', 'user_count'))
    default_sort = '-start_time'

    @cached_property
    def _now(self):
        return timezone.now()

    def _get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            'tags',
            'organizations',
            'authors',
            'curators',
            'testers',
            'spectators',
            'classes',
        )

        profile = self.request.profile
        if not profile:
            return queryset

        return queryset.annotate(
            editor_or_tester=Exists(Contest.authors.through.objects.filter(contest=OuterRef('pk'), profile=profile)) |
            Exists(Contest.curators.through.objects.filter(contest=OuterRef('pk'), profile=profile)) |
            Exists(Contest.testers.through.objects.filter(contest=OuterRef('pk'), profile=profile)),
            completed_contest=Exists(ContestParticipation.objects.filter(contest=OuterRef('pk'), user=profile,
                                                                         virtual=ContestParticipation.LIVE)),
        )

    def get_queryset(self):
        self.search_query = None
        queryset = self._get_queryset().order_by(self.order, 'key').filter(end_time__lt=self._now)
        if 'search' in self.request.GET:
            self.search_query = search_query = ' '.join(self.request.GET.getlist('search')).strip()
            if search_query:
                queryset = queryset.filter(Q(key__icontains=search_query) | Q(name__icontains=search_query))
        return queryset

    def get_paginator(self, queryset, per_page, orphans=0, allow_empty_first_page=True, **kwargs):
        return super().get_paginator(queryset, per_page, orphans, allow_empty_first_page,
                                     count=self.get_queryset().values('id').count(), **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ContestList, self).get_context_data(**kwargs)
        present, active, future = [], [], []
        finished = set()
        for contest in self._get_queryset().exclude(end_time__lt=self._now):
            if contest.start_time > self._now:
                future.append(contest)
            else:
                present.append(contest)

        if self.request.user.is_authenticated:
            for participation in (
                ContestParticipation.objects.filter(virtual=0, user=self.request.profile, contest_id__in=present)
                .select_related('contest')
                .prefetch_related('contest__authors', 'contest__curators', 'contest__testers', 'contest__spectators')
                .annotate(key=F('contest__key'))
            ):
                if participation.ended:
                    finished.add(participation.contest.key)
                else:
                    active.append(participation)
                    present.remove(participation.contest)

        active.sort(key=attrgetter('end_time', 'key'))
        present.sort(key=attrgetter('end_time', 'key'))
        future.sort(key=attrgetter('start_time'))
        context['active_participations'] = active
        context['current_contests'] = present
        context['future_contests'] = future
        context['finished_contests'] = finished
        context['now'] = self._now
        context['first_page_href'] = '.'
        context['page_suffix'] = '#past-contests'
        context['search_query'] = self.search_query
        context.update(self.get_sort_context())
        context.update(self.get_sort_paginate_context())
        return context


class PrivateContestError(Exception):
    def __init__(self, name, is_private, is_organization_private, orgs, classes):
        self.name = name
        self.is_private = is_private
        self.is_organization_private = is_organization_private
        self.orgs = orgs
        self.classes = classes


class ContestMixin(object):
    context_object_name = 'contest'
    model = Contest
    slug_field = 'key'
    slug_url_kwarg = 'contest'

    @cached_property
    def is_editor(self):
        if not self.request.user.is_authenticated:
            return False
        return self.request.profile.id in self.object.editor_ids

    @cached_property
    def is_tester(self):
        if not self.request.user.is_authenticated:
            return False
        return self.request.profile.id in self.object.tester_ids

    @cached_property
    def is_spectator(self):
        if not self.request.user.is_authenticated:
            return False
        return self.request.profile.id in self.object.spectator_ids

    @cached_property
    def can_edit(self):
        return self.object.is_editable_by(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            try:
                context['live_participation'] = (
                    self.request.profile.contest_history.get(
                        contest=self.object,
                        virtual=ContestParticipation.LIVE,
                    )
                )
            except ContestParticipation.DoesNotExist:
                context['live_participation'] = None
                context['has_joined'] = False
            else:
                context['has_joined'] = True
        else:
            context['live_participation'] = None
            context['has_joined'] = False

        context['now'] = timezone.now()
        context['is_editor'] = self.is_editor
        context['is_tester'] = self.is_tester
        context['is_spectator'] = self.is_spectator
        context['can_edit'] = self.can_edit

        if not self.object.og_image or not self.object.summary:
            metadata = generate_opengraph('generated-meta-contest:%d' % self.object.id,
                                          self.object.description, 'contest')
        context['meta_description'] = self.object.summary or metadata[0]
        context['og_image'] = self.object.og_image or metadata[1]
        context['has_moss_api_key'] = settings.MOSS_API_KEY is not None
        context['logo_override_image'] = self.object.logo_override_image
        if not context['logo_override_image'] and self.object.organizations.count() == 1:
            context['logo_override_image'] = self.object.organizations.first().logo_override_image

        return context

    def get_object(self, queryset=None):
        contest = super().get_object(queryset)

        profile = self.request.profile
        if (profile is not None and
                ContestParticipation.objects.filter(id=profile.current_contest_id, contest_id=contest.id).exists()):
            return contest

        try:
            contest.access_check(self.request.user)
        except Contest.PrivateContest:
            raise PrivateContestError(contest.name, contest.is_private, contest.is_organization_private,
                                      contest.organizations.all(), contest.classes.all())
        except Contest.Inaccessible:
            raise Http404()
        else:
            return contest

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            if key:
                return generic_message(request, _('No such contest'),
                                       _('Could not find a contest with the key "%s".') % key)
            else:
                return generic_message(request, _('No such contest'),
                                       _('Could not find such contest.'))
        except PrivateContestError as e:
            return render(request, 'contest/private.html', {
                'error': e, 'title': _('Access to contest "%s" denied') % e.name,
            }, status=403)


class ContestDetail(ContestMixin, TitleMixin, CommentedDetailView):
    template_name = 'contest/contest.html'

    def get_comment_page(self):
        return 'c:%s' % self.object.key

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super(ContestDetail, self).get_context_data(**kwargs)

        participation = None
        participation_data = {}
        completed_problem_ids = set()
        attempted_problems = set()

        if self.request.user.is_authenticated:
            from judge.utils.problems import user_completed_ids, user_attempted_ids
            completed_problem_ids = user_completed_ids(self.request.profile)
            attempted_problems = user_attempted_ids(self.request.profile)

            if self.request.profile.current_contest_id:
                try:
                    participation = ContestParticipation.objects.get(
                        id=self.request.profile.current_contest_id,
                        contest=self.object,
                    )
                except ContestParticipation.DoesNotExist:
                    pass

            if participation is None:
                participation = ContestParticipation.objects.filter(
                    contest=self.object,
                    user=self.request.profile,
                ).order_by('-id').first()

            if participation:
                participation_data = participation.format_data or {}

        context['participation'] = participation
        context['participation_data'] = participation_data
        context['completed_problem_ids'] = completed_problem_ids
        context['attempted_problems'] = attempted_problems

        context['contest_problems'] = Problem.objects.filter(contests__contest=self.object) \
            .order_by('contests__order').defer('description') \
            .annotate(
                contest_problem_id=F('contests__id'),
                contest_problem_points=F('contests__points'),
                has_public_editorial=Case(
                    When(solution__is_public=True, solution__publish_on__lte=timezone.now(), then=True),
                    default=False,
                    output_field=BooleanField(),
                )
            ) \
            .add_i18n_name(self.request.LANGUAGE_CODE)
        context['metadata'] = {
            'has_public_editorials': any(
                problem.is_public and problem.has_public_editorial for problem in context['contest_problems']
            ),
        }
        context['metadata'].update(
            **self.object.contest_problems
            .annotate(
                partials_enabled=Case(
                    When(partial=True, problem__partial=True, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                pretests_enabled=Case(
                    When(is_pretested=True, contest__run_pretests_only=True, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .aggregate(
                has_partials=Sum('partials_enabled'),
                has_pretests=Sum('pretests_enabled'),
                has_submission_cap=Sum('max_submissions'),
                problem_count=Count('id'),
            ),
        )
        context['enable_comments'] = settings.DMOJ_ENABLE_COMMENTS
        context['enable_social'] = settings.DMOJ_ENABLE_SOCIAL
        from judge.utils.pdfoid import PDF_RENDERING_ENABLED
        context['has_pdf_render'] = PDF_RENDERING_ENABLED
        return context


class ContestClone(ContestMixin, PermissionRequiredMixin, TitleMixin, SingleObjectFormView):
    title = gettext_lazy('Clone Contest')
    template_name = 'contest/clone.html'
    form_class = ContestCloneForm
    permission_required = 'judge.clone_contest'

    def form_valid(self, form):
        contest = self.object

        tags = contest.tags.all()
        organizations = contest.organizations.all()
        private_contestants = contest.private_contestants.all()
        view_contest_scoreboard = contest.view_contest_scoreboard.all()
        contest_problems = contest.contest_problems.all()
        old_key = contest.key

        contest.pk = None
        contest.is_visible = False
        contest.user_count = 0
        contest.locked_after = None
        contest.key = form.cleaned_data['key']
        with revisions.create_revision(atomic=True):
            contest.save()
            contest.tags.set(tags)
            contest.organizations.set(organizations)
            contest.private_contestants.set(private_contestants)
            contest.view_contest_scoreboard.set(view_contest_scoreboard)
            contest.authors.add(self.request.profile)

            for problem in contest_problems:
                problem.contest = contest
                problem.pk = None
            ContestProblem.objects.bulk_create(contest_problems)

            revisions.set_user(self.request.user)
            revisions.set_comment(_('Cloned contest from %s') % old_key)

        return HttpResponseRedirect(reverse('admin:judge_contest_change', args=(contest.id,)))


class ContestAccessDenied(Exception):
    pass


class ContestAccessCodeForm(forms.Form):
    access_code = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super(ContestAccessCodeForm, self).__init__(*args, **kwargs)
        self.fields['access_code'].widget.attrs.update({'autocomplete': 'off'})


class ContestJoin(LoginRequiredMixin, ContestMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.ask_for_access_code()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return self.join_contest(request)
        except ContestAccessDenied:
            if request.POST.get('access_code'):
                return self.ask_for_access_code(ContestAccessCodeForm(request.POST))
            else:
                return HttpResponseRedirect(request.path)

    def join_contest(self, request, access_code=None):
        contest = self.object

        if not contest.started and not (self.is_editor or self.is_tester):
            return generic_message(request, _('Contest not ongoing'),
                                   _('"%s" is not currently ongoing.') % contest.name)

        profile = request.profile

        if not request.user.is_superuser and contest.banned_users.filter(id=profile.id).exists():
            return generic_message(request, _('Banned from joining'),
                                   _('You have been declared persona non grata for this contest. '
                                     'You are permanently barred from joining this contest.'))

        requires_access_code = (not self.can_edit and contest.access_code and access_code != contest.access_code)
        if contest.ended:
            if requires_access_code:
                raise ContestAccessDenied()

            while True:
                virtual_id = max((ContestParticipation.objects.filter(contest=contest, user=profile)
                                  .aggregate(virtual_id=Max('virtual'))['virtual_id'] or 0) + 1, 1)
                try:
                    participation = ContestParticipation.objects.create(
                        contest=contest, user=profile, virtual=virtual_id,
                        real_start=timezone.now(),
                    )
                # There is obviously a race condition here, so we keep trying until we win the race.
                except IntegrityError:
                    pass
                else:
                    break
        else:
            SPECTATE = ContestParticipation.SPECTATE
            LIVE = ContestParticipation.LIVE

            if contest.is_live_joinable_by(request.user):
                participation_type = LIVE
            elif contest.is_spectatable_by(request.user):
                participation_type = SPECTATE
            else:
                return generic_message(request, _('Cannot enter'),
                                       _('You are not able to join this contest.'))
            try:
                participation = ContestParticipation.objects.get(
                    contest=contest, user=profile, virtual=participation_type,
                )
            except ContestParticipation.DoesNotExist:
                if requires_access_code:
                    raise ContestAccessDenied()

                participation = ContestParticipation.objects.create(
                    contest=contest, user=profile, virtual=participation_type,
                    real_start=timezone.now(),
                )
            else:
                if participation.ended:
                    participation = ContestParticipation.objects.get_or_create(
                        contest=contest, user=profile, virtual=SPECTATE,
                        defaults={'real_start': timezone.now()},
                    )[0]

        profile.current_contest = participation
        profile.save()
        
        # Ensure points are computed for virtual join
        participation.recompute_results()
        
        contest._updating_stats_only = True
        contest.update_user_count()
        return HttpResponseRedirect(reverse('problem_list'))

    def ask_for_access_code(self, form=None):
        contest = self.object
        wrong_code = False
        if form:
            if form.is_valid():
                if form.cleaned_data['access_code'] == contest.access_code:
                    return self.join_contest(self.request, form.cleaned_data['access_code'])
                wrong_code = True
        else:
            form = ContestAccessCodeForm()
        return render(self.request, 'contest/access_code.html', {
            'form': form, 'wrong_code': wrong_code,
            'title': _('Enter access code for "%s"') % contest.name,
        })


class ContestLeave(LoginRequiredMixin, ContestMixin, SingleObjectMixin, View):
    def post(self, request, *args, **kwargs):
        contest = self.get_object()

        profile = request.profile
        if profile.current_contest is None or profile.current_contest.contest_id != contest.id:
            return generic_message(request, _('No such contest'),
                                   _('You are not in contest "%s".') % contest.key, 404)

        profile.remove_contest()
        return HttpResponseRedirect(reverse('contest_view', args=(contest.key,)))


ContestDay = namedtuple('ContestDay', 'date is_pad is_today starts ends oneday')


class ContestCalendar(TitleMixin, ContestListMixin, TemplateView):
    firstweekday = SUNDAY
    template_name = 'contest/calendar.html'

    def get(self, request, *args, **kwargs):
        try:
            self.year = int(kwargs['year'])
            self.month = int(kwargs['month'])
        except (KeyError, ValueError):
            raise ImproperlyConfigured('ContestCalendar requires integer year and month')
        self.today = timezone.now().date()
        return self.render()

    def render(self):
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_contest_data(self, start, end):
        end += timedelta(days=1)
        contests = self.get_queryset().filter(Q(start_time__gte=start, start_time__lt=end) |
                                              Q(end_time__gte=start, end_time__lt=end))
        starts, ends, oneday = (defaultdict(list) for i in range(3))
        for contest in contests:
            start_date = timezone.localtime(contest.start_time).date()
            end_date = timezone.localtime(contest.end_time - timedelta(seconds=1)).date()
            if start_date == end_date:
                oneday[start_date].append(contest)
            else:
                starts[start_date].append(contest)
                ends[end_date].append(contest)
        return starts, ends, oneday

    def get_table(self):
        calendar = Calendar(self.firstweekday).monthdatescalendar(self.year, self.month)
        starts, ends, oneday = self.get_contest_data(make_aware(datetime.combine(calendar[0][0], time.min)),
                                                     make_aware(datetime.combine(calendar[-1][-1], time.min)))
        return [[ContestDay(
            date=date, is_pad=date.month != self.month,
            is_today=date == self.today, starts=starts[date], ends=ends[date], oneday=oneday[date],
        ) for date in week] for week in calendar]

    def get_context_data(self, **kwargs):
        context = super(ContestCalendar, self).get_context_data(**kwargs)

        try:
            month = date(self.year, self.month, 1)
        except ValueError:
            raise Http404()
        else:
            context['title'] = _('Contests in %(month)s') % {'month': date_filter(month, _('F Y'))}

        dates = Contest.objects.aggregate(min=Min('start_time'), max=Max('end_time'))
        min_month = (self.today.year, self.today.month)
        if dates['min'] is not None:
            min_month = dates['min'].year, dates['min'].month
        max_month = (self.today.year, self.today.month)
        if dates['max'] is not None:
            max_month = max((dates['max'].year, dates['max'].month), (self.today.year, self.today.month))

        month = (self.year, self.month)
        if month < min_month or month > max_month:
            # 404 is valid because it merely declares the lack of existence, without any reason
            raise Http404()

        context['now'] = timezone.now()
        context['calendar'] = self.get_table()
        context['curr_month'] = date(self.year, self.month, 1)

        if month > min_month:
            context['prev_month'] = date(self.year - (self.month == 1), 12 if self.month == 1 else self.month - 1, 1)
        else:
            context['prev_month'] = None

        if month < max_month:
            context['next_month'] = date(self.year + (self.month == 12), 1 if self.month == 12 else self.month + 1, 1)
        else:
            context['next_month'] = None
        return context


class ContestICal(TitleMixin, ContestListMixin, BaseListView):
    def generate_ical(self):
        cal = ICalendar()
        cal.add('prodid', '-//DMOJ//NONSGML Contests Calendar//')
        cal.add('version', '2.0')

        now = timezone.now().astimezone(timezone.utc)
        domain = self.request.get_host()
        for contest in self.get_queryset():
            event = Event()
            event.add('uid', f'contest-{contest.key}@{domain}')
            event.add('summary', contest.name)
            event.add('location', self.request.build_absolute_uri(contest.get_absolute_url()))
            event.add('dtstart', contest.start_time.astimezone(timezone.utc))
            event.add('dtend', contest.end_time.astimezone(timezone.utc))
            event.add('dtstamp', now)
            cal.add_component(event)
        return cal.to_ical()

    def render_to_response(self, context, **kwargs):
        return HttpResponse(self.generate_ical(), content_type='text/calendar')


class ContestStats(TitleMixin, ContestMixin, DetailView):
    template_name = 'contest/stats.html'

    def get_title(self):
        return _('%s Statistics') % self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not (self.object.ended or self.can_edit):
            raise Http404()

        queryset = Submission.objects.filter(contest_object=self.object)

        ac_count = Count(Case(When(result='AC', then=Value(1)), output_field=IntegerField()))
        ac_rate = CombinedExpression(ac_count / Count('problem'), '*', Value(100.0), output_field=FloatField())

        status_count_queryset = list(
            queryset.values('problem__code', 'result').annotate(count=Count('result'))
                    .values_list('problem__code', 'result', 'count'),
        )
        labels, codes = [], []
        contest_problems = self.object.contest_problems.order_by('order').values_list('problem__name', 'problem__code')
        if contest_problems:
            labels, codes = zip(*contest_problems)
        num_problems = len(labels)
        status_counts = [[] for i in range(num_problems)]
        for problem_code, result, count in status_count_queryset:
            if problem_code in codes:
                status_counts[codes.index(problem_code)].append((result, count))

        result_data = defaultdict(partial(list, [0] * num_problems))
        for i in range(num_problems):
            for category in _get_result_data(defaultdict(int, status_counts[i]))['categories']:
                result_data[category['code']][i] = category['count']

        stats = {
            'problem_status_count': {
                'labels': labels,
                'datasets': [
                    {
                        'label': name,
                        'backgroundColor': settings.DMOJ_STATS_SUBMISSION_RESULT_COLORS[name],
                        'data': data,
                    }
                    for name, data in result_data.items()
                ],
            },
            'problem_ac_rate': get_bar_chart(
                queryset.values('contest__problem__order', 'problem__name').annotate(ac_rate=ac_rate)
                        .order_by('contest__problem__order').values_list('problem__name', 'ac_rate'),
            ),
            'language_count': get_pie_chart(
                queryset.values('language__name').annotate(count=Count('language__name'))
                        .filter(count__gt=0).order_by('-count').values_list('language__name', 'count'),
            ),
            'language_ac_rate': get_bar_chart(
                queryset.values('language__name').annotate(ac_rate=ac_rate)
                        .filter(ac_rate__gt=0).values_list('language__name', 'ac_rate'),
            ),
        }

        context['stats'] = mark_safe(json.dumps(stats))

        return context


ContestRankingProfile = namedtuple(
    'ContestRankingProfile',
    'id user css_class username points cumtime tiebreaker organization participation '
    'participation_rating problem_cells result_cell display_name',
)

BestSolutionData = namedtuple('BestSolutionData', 'code points time state is_pretested')


def make_contest_ranking_profile(contest, participation, contest_problems):
    def display_user_problem(contest_problem):
        # When the contest format is changed, `format_data` might be invalid.
        # This will cause `display_user_problem` to error, so we display '???' instead.
        try:
            return contest.format.display_user_problem(participation, contest_problem)
        except (KeyError, TypeError, ValueError):
            return mark_safe('<td>???</td>')

    user = participation.user
    return ContestRankingProfile(
        id=user.id,
        user=user.user,
        css_class=user.css_class,
        username=user.username,
        points=participation.score,
        cumtime=participation.cumtime,
        tiebreaker=participation.tiebreaker,
        organization=user.organization,
        participation_rating=participation.rating.rating if hasattr(participation, 'rating') else None,
        problem_cells=[display_user_problem(contest_problem) for contest_problem in contest_problems],
        result_cell=contest.format.display_participation_result(participation),
        participation=participation,
        display_name=user.display_name,
    )


def base_contest_ranking_list(contest, problems, queryset):
    return [make_contest_ranking_profile(contest, participation, problems) for participation in
            queryset.select_related('user__user', 'rating').defer('user__about', 'user__organizations__about')]


def contest_ranking_list(contest, problems):
    return base_contest_ranking_list(contest, problems, contest.users.filter(virtual=0)
                                     .prefetch_related('user__organizations')
                                     .annotate(submission_cnt=Count('submission'))
                                     .order_by('is_disqualified', '-score', 'cumtime', 'tiebreaker', '-submission_cnt'))


def get_contest_ranking_list(request, contest, participation=None, ranking_list=contest_ranking_list,
                             show_current_virtual=True, ranker=ranker):
    problems = list(contest.contest_problems.select_related('problem').defer('problem__description').order_by('order'))

    users = ranker(ranking_list(contest, problems), key=attrgetter('points', 'cumtime', 'tiebreaker'))

    if show_current_virtual:
        if participation is None and request.user.is_authenticated:
            participation = request.profile.current_contest
            if participation is None or participation.contest_id != contest.id:
                participation = None
        if participation is not None and participation.virtual:
            users = chain([('-', make_contest_ranking_profile(contest, participation, problems))], users)
    return users, problems


def contest_ranking_ajax(request, contest, participation=None):
    contest, exists = _find_contest(request, contest)
    if not exists:
        return HttpResponseBadRequest('Invalid contest', content_type='text/plain')

    if not contest.can_see_full_scoreboard(request.user):
        raise Http404()

    users, problems = get_contest_ranking_list(request, contest, participation)
    return render(request, 'contest/ranking-table.html', {
        'users': users,
        'problems': problems,
        'contest': contest,
        'has_rating': contest.ratings.exists(),
    })


class ContestRankingBase(ContestMixin, TitleMixin, DetailView):
    template_name = 'contest/ranking.html'
    tab = None

    def get_title(self):
        raise NotImplementedError()

    def get_content_title(self):
        return self.object.name

    def get_ranking_list(self):
        raise NotImplementedError()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.object.can_see_own_scoreboard(self.request.user):
            raise Http404()

        users, problems = self.get_ranking_list()
        context['users'] = users
        context['problems'] = problems
        context['last_msg'] = event.last()
        context['tab'] = self.tab
        return context


class ContestRanking(ContestRankingBase):
    tab = 'ranking'

    def get_title(self):
        return _('%s Rankings') % self.object.name

    def get_ranking_list(self):
        if not self.object.can_see_full_scoreboard(self.request.user):
            # If they can only see their own score, still try to show their virtual participation if applicable
            queryset = self.object.users.filter(user=self.request.profile, virtual=ContestParticipation.LIVE)
            return get_contest_ranking_list(
                self.request, self.object,
                ranking_list=partial(base_contest_ranking_list, queryset=queryset),
                ranker=lambda users, key: ((_('???'), user) for user in users),
                show_current_virtual=True,
            )

        return get_contest_ranking_list(self.request, self.object, show_current_virtual=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_rating'] = self.object.ratings.exists()
        from judge.utils.pdfoid import PDF_RENDERING_ENABLED
        context['has_pdf_render'] = PDF_RENDERING_ENABLED
        return context


class ContestRankingCSV(ContestRanking):
    def get_ranking_list(self):
        # Exclude virtual participants from CSV export
        return get_contest_ranking_list(self.request, self.object, show_current_virtual=False)

    def render_to_response(self, context, **response_kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % self.object.key
        writer = csv.writer(response)

        hide_scores = self.object.format_config and self.object.format_config.get('hide_scores_from_students') \
            and not (self.request.user.is_staff or self.request.user.is_superuser)

        if hide_scores:
            writer.writerow([_('Scores are hidden for this contest.')])
            return response

        users = context['users']
        problems = context['problems']

        header = ['User'] + [p.problem.code for p in problems] + ['Total', 'Time']
        writer.writerow(header)

        for item in users:
            if isinstance(item, tuple):
                 profile = item[1]
            else:
                 profile = item

            if not hasattr(profile, 'participation'):
                continue

            p = profile.participation
            row = [profile.username]

            for problem in problems:
                data = (p.format_data or {}).get(str(problem.id))
                if data:
                    row.append(data.get('points', 0))
                else:
                    row.append(0)

            row.append(profile.points)
            row.append(profile.cumtime)
            writer.writerow(row)

        return response


class ContestParticipationList(LoginRequiredMixin, ContestRankingBase):
    tab = 'participation'

    def get_title(self):
        if self.profile == self.request.profile:
            return _('Your participation in %(contest)s') % {'contest': self.object.name}
        return _("%(user)s's participation in %(contest)s") % {
            'user': self.profile.username, 'contest': self.object.name,
        }

    def get_ranking_list(self):
        if not self.object.can_see_full_scoreboard(self.request.user) and self.profile != self.request.profile:
            raise Http404()

        queryset = self.object.users.filter(user=self.profile, virtual__gte=0).order_by('-virtual')
        live_link = format_html('<a href="{2}#!{1}">{0}</a>', _('Live'), self.profile.username,
                                reverse('contest_ranking', args=[self.object.key]))

        return get_contest_ranking_list(
            self.request, self.object, show_current_virtual=False,
            ranking_list=partial(base_contest_ranking_list, queryset=queryset),
            ranker=lambda users, key: ((user.participation.virtual or live_link, user) for user in users))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_rating'] = False
        context['now'] = timezone.now()
        context['rank_header'] = _('Participation')
        return context

    def get(self, request, *args, **kwargs):
        if 'user' in kwargs:
            self.profile = get_object_or_404(Profile, user__username=kwargs['user'])
        else:
            self.profile = self.request.profile
        return super().get(request, *args, **kwargs)


class ContestParticipationDisqualify(ContestMixin, SingleObjectMixin, View):
    def get_object(self, queryset=None):
        contest = super().get_object(queryset)
        if not contest.is_editable_by(self.request.user):
            raise Http404()
        return contest

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        try:
            participation = self.object.users.get(pk=request.POST.get('participation'))
        except ObjectDoesNotExist:
            pass
        else:
            participation.set_disqualified(not participation.is_disqualified)
        return HttpResponseRedirect(reverse('contest_ranking', args=(self.object.key,)))


class ContestMossMixin(ContestMixin, PermissionRequiredMixin):
    permission_required = 'judge.moss_contest'

    def get_object(self, queryset=None):
        contest = super().get_object(queryset)
        if settings.MOSS_API_KEY is None or not contest.is_editable_by(self.request.user):
            raise Http404()
        return contest


class ContestMossView(ContestMossMixin, TitleMixin, DetailView):
    template_name = 'contest/moss.html'

    def get_title(self):
        return _('%s MOSS Results') % self.object.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        problems = list(map(attrgetter('problem'), self.object.contest_problems.order_by('order')
                                                              .select_related('problem')))
        languages = list(map(itemgetter(0), ContestMoss.LANG_MAPPING))

        results = ContestMoss.objects.filter(contest=self.object)
        moss_results = defaultdict(list)
        for result in results:
            moss_results[result.problem].append(result)

        for result_list in moss_results.values():
            result_list.sort(key=lambda x: languages.index(x.language))

        context['languages'] = languages
        context['has_results'] = results.exists()
        context['moss_results'] = [(problem, moss_results[problem]) for problem in problems]

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        status = run_moss.delay(self.object.key)
        return redirect_to_task_status(
            status, message=_('Running MOSS for %s...') % (self.object.name,),
            redirect=reverse('contest_moss', args=(self.object.key,)),
        )


class ContestMossDelete(ContestMossMixin, SingleObjectMixin, View):
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        ContestMoss.objects.filter(contest=self.object).delete()
        return HttpResponseRedirect(reverse('contest_moss', args=(self.object.key,)))


class ContestTagDetailAjax(DetailView):
    model = ContestTag
    slug_field = slug_url_kwarg = 'name'
    context_object_name = 'tag'
    template_name = 'contest/tag-ajax.html'


class ContestTagDetail(TitleMixin, ContestTagDetailAjax):
    template_name = 'contest/tag.html'

    def get_title(self):
        return _('Contest tag: %s') % self.object.name


class ContestPDF(ContestMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        from judge.utils.pdfoid import PDF_RENDERING_ENABLED, render_pdf
        if not PDF_RENDERING_ENABLED:
            raise Http404()

        self.object = self.get_object()
        problems = self.object.contest_problems.select_related('problem').order_by('order')
        
        full_html = ""
        for cp in problems:
            problem = cp.problem
            # Basic markdown to HTML for problems that aren't using complex templates
            # DMOJ usually has a more complex rendering pipeline, but for this bulk 
            # export we'll use a simplified version or rely on the fact that 
            # themis problems often use simple markdown/text.
            
            # Use the raw template from problem view
            from django.template.loader import get_template
            full_html += get_template('problem/raw.html').render({
                'problem': problem,
                'problem_name': problem.name,
                'description': problem.description,
                'url': request.build_absolute_uri(problem.get_absolute_url()),
            })
            # Add page break
            full_html += '<div style="page-break-after: always;"></div>'

        pdf_basename = f'{self.object.key}.pdf'
        pdf_content = render_pdf(
            html=full_html.replace('"//', '"https://').replace("'//", "'https://"),
            title=self.object.name,
        )

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename={pdf_basename}'
        return response


class ContestThemisUpload(ContestMixin, LoginRequiredMixin, TitleMixin, SingleObjectMixin, TemplateView):
    model = Contest
    slug_field = 'key'
    slug_url_kwarg = 'contest'
    template_name = 'contest/themis_upload.html'

    def get_title(self):
        return _('Bulk Upload - %s') % self.object.name

    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            if self.object.format_name != 'themis':
                raise Http404()
            if not self.object.is_in_contest(request.user):
                 return redirect(reverse('contest_view', args=[self.object.key]))
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            if request.method == 'POST':
                import traceback
                return JsonResponse({'success': False, 'error': f"Dispatch Error: {str(e)}", 'trace': traceback.format_exc()})
            raise

    def get_context_data(self, **kwargs):
        if 'contest' in kwargs:
            del kwargs['contest']
        context = super().get_context_data(**kwargs)
        problems_data = {}
        ordered_problems = []
        for cp in self.object.contest_problems.select_related('problem').order_by('order'):
            p = cp.problem
            problems_data[p.code.upper()] = p.code
            problems_data[p.name.upper()] = p.code
            problems_data[f"BAI{cp.order + 1}"] = p.code
            ordered_problems.append({'code': p.code, 'name': p.name})
        
        languages_data = []
        for lang in Language.objects.filter(judges__online=True).distinct():
            languages_data.append({'id': lang.key, 'name': lang.name, 'common_name': lang.common_name})
        
        context['problems_json'] = json.dumps(problems_data)
        context['ordered_problems_json'] = json.dumps(ordered_problems)
        context['languages_json'] = json.dumps(languages_data)
        # Ensure default mappings exist in DB if table is empty
        if not ThemisExtensionMapping.objects.exists():
            default_map = {
                '.cpp': 'CPP17', '.cc': 'CPP17', '.c': 'C11',
                '.py': 'PY3', '.pas': 'PAS', '.java': 'JAVA'
            }
            for ext, lang_key in default_map.items():
                try:
                    lang = Language.objects.get(key=lang_key)
                    ThemisExtensionMapping.objects.get_or_create(extension=ext, language=lang)
                except Language.DoesNotExist:
                    pass

        mappings = {}
        extensions = []
        for m in ThemisExtensionMapping.objects.all().select_related('language'):
            mappings[m.extension.lower()] = m.language.key
            extensions.append(m.extension.lower())
        
        context['mappings_json'] = json.dumps(mappings)
        context['all_extensions'] = ','.join(extensions) or '.cpp,.py,.pas,.java,.c'
        return context

    def post(self, request, *args, **kwargs):
        if 'zip_file' in request.FILES:
            if not request.user.is_superuser and not self.object.is_editable_by(request.user):
                return HttpResponseForbidden("Only admins can perform bulk zip upload.")
            
            zip_file = request.FILES['zip_file']
            problems_map = {}
            for cp in self.object.contest_problems.select_related('problem'):
                p = cp.problem
                problems_map[p.code.upper()] = p.code
                problems_map[p.name.upper()] = p.code
                problems_map[f"BAI{cp.order + 1}"] = p.code
            
            from judge.utils.themis_zip import process_themis_zip
            data = process_themis_zip(zip_file, self.object, problems_map, request.profile)
            return JsonResponse({
                'success': True, 
                'results': data['results'], 
                'errors': data['errors']
            })

        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return HttpResponseBadRequest("Invalid JSON")
            
            profile = request.profile
            username = data.get('username')
            is_admin_upload = request.user.is_superuser or self.object.is_editable_by(request.user)
            user_not_found = False
            if username and is_admin_upload:
                from judge.models import Profile
                target_profile = Profile.objects.filter(user__username=username).first()
                if not target_profile:
                    target_profile = Profile.objects.filter(display_name=username).first()
                if target_profile:
                    profile = target_profile
                else:
                    user_not_found = True

            participation = None
            if profile.current_contest and profile.current_contest.contest_id == self.object.id:
                participation = profile.current_contest
            else:
                participation = profile.contest_history.filter(contest=self.object).order_by('-start').first()
            
            if not participation:
                if is_admin_upload:
                    from judge.models import ContestParticipation
                    participation = ContestParticipation.objects.create(
                        contest=self.object,
                        user=profile,
                    )
                else:
                    return JsonResponse({'success': False, 'error': _('You are not participating in this contest.')})

            # Check one submission only limit for students
            if not is_admin_upload and self.object.format_config and self.object.format_config.get('one_submission_only'):
                oldest_sub = Submission.objects.filter(user=request.profile, contest_object=self.object).order_by('date').first()
                if oldest_sub:
                    from django.utils import timezone
                    if (timezone.now() - oldest_sub.date).total_seconds() > 120:
                        return JsonResponse({'success': False, 'error': _('You can only submit once in this contest.')})
            
            problem_code = data.get('problem')
            lang_key = data.get('language')
            source_code = data.get('source')
            if not problem_code or not lang_key or not source_code:
                return JsonResponse({'success': False, 'error': _('Missing required fields.')})
            try:
                contest_problem = self.object.contest_problems.get(problem__code=problem_code)
                problem = contest_problem.problem
            except ContestProblem.DoesNotExist:
                 return JsonResponse({'success': False, 'error': _('Problem not found in contest.')})

            # Check submission limits
            if contest_problem.max_submissions is not None:
                submissions_count = ContestSubmission.objects.filter(
                    participation=participation, problem=contest_problem
                ).count()
                if submissions_count >= contest_problem.max_submissions:
                    return JsonResponse({'success': False, 'error': _('Submission limit reached for problem %s.') % problem_code})

            try:
                language = Language.objects.get(key=lang_key)
            except Language.DoesNotExist:
                return JsonResponse({'success': False, 'error': _('Language not found: %s') % lang_key})


            sub = Submission.objects.create(user=profile, problem=problem, language=language, contest_object=self.object)
            SubmissionSource.objects.create(submission=sub, source=source_code)
            ContestSubmission.objects.get_or_create(submission=sub, problem=contest_problem, participation=participation)
            sub.judge()
            return JsonResponse({
                'success': True,
                'id': sub.id,
                'status': 'Queued',
                'user_not_found': user_not_found,
                'submitted_as': profile.user.username
            })
        except Exception as e:
            import traceback
            return JsonResponse({'success': False, 'error': f"Server Error: {str(e)}", 'trace': traceback.format_exc()})


class ContestQuickEdit(ContestMixin, LoginRequiredMixin, TitleMixin, SingleObjectMixin, TemplateView):
    template_name = 'contest/quick_edit.html'

    def get_title(self):
        return _('Quick Edit - %s') % self.object.name

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.can_edit:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        if 'contest' in kwargs:
            del kwargs['contest']
        context = super().get_context_data(**kwargs)
        problems = []
        from judge.widgets import AdminMartorWidget
        for cp in self.object.contest_problems.select_related('problem', 'problem__data_files').order_by('order'):
            p = cp.problem
            p.contest_points = cp.points
            p.contest_max_submissions = cp.max_submissions
            field_name = f'p_{p.id}_description'
            widget = AdminMartorWidget(attrs={'data-markdownfy-url': reverse('problem_preview')})
            p.martor_html = widget.render(field_name, p.description, attrs={'id': f'id_{field_name}'})
            problems.append(p)
        context['problems'] = problems
        context['io_modes'] = IO_MODES
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.can_edit:
             return HttpResponseBadRequest("Unauthorized")
        
        data = request.POST
        for cp in self.object.contest_problems.select_related('problem', 'problem__data_files'):
            p = cp.problem
            prefix = f'p_{p.id}_'
            changed = False
            cp_changed = False

            if f'{prefix}description' in data:
                new_desc = data[f'{prefix}description']
                if p.description != new_desc:
                    p.description = new_desc
                    changed = True
            
            if f'{prefix}time_limit' in data:
                try:
                    new_tl = float(data[f'{prefix}time_limit'])
                    if p.time_limit != new_tl:
                        p.time_limit = new_tl
                        changed = True
                except ValueError:
                    pass

            if f'{prefix}memory_limit' in data:
                try:
                    new_ml = int(data[f'{prefix}memory_limit'])
                    if p.memory_limit != new_ml:
                        p.memory_limit = new_ml
                        changed = True
                except ValueError:
                    pass

            if f'{prefix}points' in data:
                try:
                    new_pts = float(data[f'{prefix}points'])
                    if cp.points != new_pts:
                        cp.points = new_pts
                        cp_changed = True
                except ValueError:
                    pass

            if f'{prefix}max_submissions' in data:
                try:
                    val = data[f'{prefix}max_submissions'].strip()
                    new_ms = int(val) if val else None
                    if cp.max_submissions != new_ms:
                        cp.max_submissions = new_ms
                        cp_changed = True
                except ValueError:
                    pass

            if changed:
                p.save()
            if cp_changed:
                cp.save()
            
            p_data, created = ProblemData.objects.get_or_create(problem=p)
            data_changed = False
            if f'{prefix}io_mode' in data:
                new_io_mode = data[f'{prefix}io_mode']
                if p_data.io_mode != new_io_mode:
                    p_data.io_mode = new_io_mode
                    data_changed = True
            if f'{prefix}input_filename' in data:
                new_input = data[f'{prefix}input_filename'].strip().upper()
                if p_data.input_filename != new_input:
                    p_data.input_filename = new_input
                    data_changed = True
            if f'{prefix}output_filename' in data:
                new_output = data[f'{prefix}output_filename'].strip().upper()
                if p_data.output_filename != new_output:
                    p_data.output_filename = new_output
                    data_changed = True
            if data_changed or created:
                p_data.save()
                
            # Regenerate init.yml to notify judge of configuration changes (e.g., File IO)
            from judge.utils.problem_data import ProblemDataCompiler
            from zipfile import ZipFile
            
            try:
                cases = p.cases.all().order_by('order')
                valid_files = []
                if p_data.zipfile:
                    try:
                        valid_files = ZipFile(p_data.zipfile.path).namelist()
                    except Exception:
                        pass
                
                ProblemDataCompiler.generate(p, p_data, cases, valid_files)
            except Exception:
                pass
            
        return HttpResponseRedirect(request.path)

