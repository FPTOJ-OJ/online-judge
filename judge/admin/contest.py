from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Q, TextField
from django.forms import ModelForm, ModelMultipleChoiceField
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.decorators.http import require_POST
from reversion.admin import VersionAdmin

from judge.models import Class, Contest, ContestProblem, ContestSubmission, Profile, Rating, Submission, ThemisExtensionMapping
from judge.ratings import rate_contest
from judge.utils.views import NoBatchDeleteMixin
from judge.widgets import AdminAceWidget, AdminHeavySelect2MultipleWidget, AdminHeavySelect2Widget, \
    AdminMartorWidget, AdminSelect2MultipleWidget, AdminSelect2Widget


class ThemisExtensionMappingAdmin(admin.ModelAdmin):
    list_display = ('extension', 'language')
    search_fields = ('extension', 'language__name')


class AdminHeavySelect2Widget(AdminHeavySelect2Widget):
    @property
    def is_hidden(self):
        return False


class ContestTagForm(ModelForm):
    contests = ModelMultipleChoiceField(
        label=_('Included contests'),
        queryset=Contest.objects.all(),
        required=False,
        widget=AdminHeavySelect2MultipleWidget(data_view='contest_select2'))


class ContestTagAdmin(admin.ModelAdmin):
    fields = ('name', 'color', 'description', 'contests')
    list_display = ('name', 'color')
    actions_on_top = True
    actions_on_bottom = True
    form = ContestTagForm
    formfield_overrides = {
        TextField: {'widget': AdminMartorWidget},
    }

    def save_model(self, request, obj, form, change):
        super(ContestTagAdmin, self).save_model(request, obj, form, change)
        obj.contests.set(form.cleaned_data['contests'])

    def get_form(self, request, obj=None, **kwargs):
        form = super(ContestTagAdmin, self).get_form(request, obj, **kwargs)
        if obj is not None:
            form.base_fields['contests'].initial = obj.contests.all()
        return form


class ContestProblemInlineForm(ModelForm):
    class Meta:
        widgets = {'problem': AdminHeavySelect2Widget(data_view='problem_select2')}


class ContestProblemInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ContestProblem
    verbose_name = _('Problem')
    verbose_name_plural = _('Problems')
    fields = ('problem', 'points', 'partial', 'is_pretested', 'max_submissions', 'output_prefix_override', 'order',
              'rejudge_column')
    readonly_fields = ('rejudge_column',)
    form = ContestProblemInlineForm

    @admin.display(description='')
    def rejudge_column(self, obj):
        if obj.id is None:
            return ''
        return format_html('<a class="button rejudge-link action-link" href="{0}">{1}</a>',
                           reverse('admin:judge_contest_rejudge', args=(obj.contest.id, obj.id)), _('Rejudge'))


from django import forms

class ContestForm(ModelForm):
    is_infinite = forms.BooleanField(label=_('Infinite'), required=False, help_text=_('Check to make the contest last forever.'))
    is_lock_infinite = forms.BooleanField(label=_('Infinite Lock'), required=False, help_text=_('Check to make the contest lock date infinite (will be set to 3099-12-31).'))
    one_submission_only = forms.BooleanField(label=_('One-time Submission Only'), required=False, help_text=_('Check to allow only one ZIP/bulk upload per student (Themis Style).'))
    hide_scores_from_students = forms.BooleanField(label=_('Hide Scores from Students'), required=False, help_text=_('Check to hide scores and details from students, behaving like a real exam (Themis Style).'))

    def __init__(self, *args, **kwargs):
        # Replace far-future dates (year >= 2999) with None to prevent pytz overflow
        instance = kwargs.get('instance')
        if instance and instance.pk:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            if instance.end_time and instance.end_time.year >= 2999:
                kwargs['initial']['end_time'] = None
                kwargs['initial']['is_infinite'] = True
            if instance.locked_after and instance.locked_after.year >= 2999:
                kwargs['initial']['locked_after'] = None
                kwargs['initial']['is_lock_infinite'] = True
        super(ContestForm, self).__init__(*args, **kwargs)
        if 'rate_exclude' in self.fields:
            if self.instance and self.instance.id:
                self.fields['rate_exclude'].queryset = \
                    Profile.objects.filter(contest_history__contest=self.instance).distinct()
            else:
                self.fields['rate_exclude'].queryset = Profile.objects.none()
        self.fields['banned_users'].widget.can_add_related = False
        self.fields['view_contest_scoreboard'].widget.can_add_related = False
        if 'end_time' in self.fields:
            self.fields['end_time'].required = False
            self.fields['end_time'].help_text = _('Leave blank for infinite contest (will be set to 3099-12-31).')
        if 'locked_after' in self.fields:
            self.fields['locked_after'].required = False
            self.fields['locked_after'].help_text = _('Leave blank or check infinite to never lock.')
        
        if self.instance and self.instance.pk:
            if self.instance.end_time and self.instance.end_time.year >= 2999:
                self.fields['is_infinite'].initial = True
                self.initial['end_time'] = None
            if self.instance.locked_after and self.instance.locked_after.year >= 2999:
                self.fields['is_lock_infinite'].initial = True
                self.initial['locked_after'] = None
            config = self.instance.format_config or {}
            self.fields['one_submission_only'].initial = config.get('one_submission_only', False)
            self.fields['hide_scores_from_students'].initial = config.get('hide_scores_from_students', False)
            # Strip admin-only keys from format_config widget display
            if isinstance(self.initial.get('format_config'), dict):
                self.initial['format_config'] = {
                    k: v for k, v in self.initial['format_config'].items()
                    if k not in ('one_submission_only', 'hide_scores_from_students')
                }

    def clean_end_time(self):
        end_time = self.cleaned_data.get('end_time')
        if not end_time:
            import datetime
            return datetime.datetime(3099, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        return end_time

    def clean_locked_after(self):
        locked_after = self.cleaned_data.get('locked_after')
        if not locked_after and self.cleaned_data.get('is_lock_infinite'):
            import datetime
            return datetime.datetime(3099, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        return locked_after

    def clean(self):
        cleaned_data = super(ContestForm, self).clean()
        if cleaned_data.get('is_infinite'):
            import datetime
            cleaned_data['end_time'] = datetime.datetime(3099, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        if cleaned_data.get('is_lock_infinite'):
            import datetime
            cleaned_data['locked_after'] = datetime.datetime(3099, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        
        # Merge themis format settings into format_config
        one_sub = cleaned_data.get('one_submission_only', False)
        hide_scores = cleaned_data.get('hide_scores_from_students', False)
        
        format_config = cleaned_data.get('format_config') or {}
        if isinstance(format_config, dict):
            format_config['one_submission_only'] = one_sub
            format_config['hide_scores_from_students'] = hide_scores
            cleaned_data['format_config'] = format_config
            
        cleaned_data['banned_users'].filter(current_contest__contest=self.instance).update(current_contest=None)
        return cleaned_data

    class Meta:
        widgets = {
            'authors': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'curators': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'testers': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'spectators': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'private_contestants': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'organizations': AdminHeavySelect2MultipleWidget(data_view='organization_select2'),
            'classes': AdminHeavySelect2MultipleWidget(data_view='class_select2'),
            'join_organizations': AdminHeavySelect2MultipleWidget(data_view='organization_select2'),
            'tags': AdminSelect2MultipleWidget,
            'banned_users': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'view_contest_scoreboard': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'view_contest_submissions': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'description': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('contest_preview')}),
        }


class ContestAdmin(SortableAdminBase, VersionAdmin):
    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        
        # Add related Themis problems to the list so they show up in "Are you sure?"
        from django.utils.text import capfirst
        from django.utils.html import format_html
        from judge.models import Problem
        
        additional_problems = []
        for obj in objs:
            if obj.format_name == 'themis':
                prefix = f"{obj.key}_".upper()
                problems = Problem.objects.filter(code__startswith=prefix)
                for p in problems:
                    opts = p._meta
                    additional_problems.append(
                        format_html('%s: <a href="%s">%s</a>' % (
                            capfirst(opts.verbose_name),
                            reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name), args=(p.pk,)),
                            p
                        ))
                    )
                    # Update model_count
                    model_name = str(opts.verbose_name_plural)
                    model_count[model_name] = model_count.get(model_name, 0) + 1
        
        if additional_problems:
            deleted_objects.extend(additional_problems)
            
        return deleted_objects, model_count, perms_needed, protected

    fieldsets = (
        (None, {'fields': ('key', 'name', 'authors', 'curators', 'testers', 'tester_see_submissions',
                           'tester_see_scoreboard', 'spectators')}),
        (_('Settings'), {'fields': ('is_visible', 'use_clarifications', 'hide_problem_tags', 'hide_problem_authors',
                                    'show_short_display', 'run_pretests_only', 'locked_after', 'is_lock_infinite', 'scoreboard_visibility',
                                    'points_precision')}),
        (_('Scheduling'), {'fields': ('start_time', 'end_time', 'is_infinite', 'time_limit')}),
        (_('Details'), {'fields': ('description', 'og_image', 'logo_override_image', 'tags', 'summary')}),
        (_('Format'), {'fields': ('format_name', 'one_submission_only', 'hide_scores_from_students', 'format_config', 'problem_label_script')}),
        (_('Rating'), {'fields': ('is_rated', 'rate_all', 'rating_floor', 'rating_ceiling', 'rate_exclude')}),
        (_('Access'), {'fields': ('access_code', 'private_contestants', 'organizations', 'classes',
                                  'join_organizations', 'view_contest_scoreboard', 'view_contest_submissions')}),
        (_('Justice'), {'fields': ('banned_users',)}),
    )
    list_display = ('key', 'name', 'is_visible', 'is_rated', 'locked_after', 'start_time', 'end_time', 'time_limit',
                    'user_count')
    search_fields = ('key', 'name')
    inlines = [ContestProblemInline]
    actions_on_top = True
    actions_on_bottom = True
    form = ContestForm
    change_list_template = 'admin/judge/contest/change_list.html'
    filter_horizontal = ['rate_exclude']
    date_hierarchy = 'start_time'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['themis_create_url'] = reverse('admin:judge_contest_themis_create')
        return super().changelist_view(request, extra_context=extra_context)

    def get_actions(self, request):
        actions = super(ContestAdmin, self).get_actions(request)

        if request.user.has_perm('judge.change_contest_visibility') or \
                request.user.has_perm('judge.create_private_contest'):
            for action in ('make_visible', 'make_hidden'):
                actions[action] = self.get_action(action)

        if request.user.has_perm('judge.lock_contest'):
            for action in ('set_locked', 'set_unlocked'):
                actions[action] = self.get_action(action)

        return actions

    def get_queryset(self, request):
        queryset = Contest.objects.all()
        if request.user.has_perm('judge.edit_all_contest'):
            return queryset
        else:
            return queryset.filter(Q(authors=request.profile) | Q(curators=request.profile)).distinct()

    def get_readonly_fields(self, request, obj=None):
        readonly = []
        if not request.user.has_perm('judge.contest_rating'):
            readonly += ['is_rated', 'rate_all', 'rate_exclude']
        if not request.user.has_perm('judge.lock_contest'):
            readonly += ['locked_after', 'is_lock_infinite']
        if not request.user.has_perm('judge.contest_access_code'):
            readonly += ['access_code']
        if not request.user.has_perm('judge.create_private_contest'):
            readonly += ['private_contestants', 'organizations']
            if not request.user.has_perm('judge.change_contest_visibility'):
                readonly += ['is_visible']
        if not request.user.has_perm('judge.contest_problem_label'):
            readonly += ['problem_label_script']
        return readonly

    def save_model(self, request, obj, form, change):
        # `private_contestants` and `organizations` will not appear in `cleaned_data` if user cannot edit it
        if form.changed_data:
            if 'private_contestants' in form.changed_data:
                obj.is_private = bool(form.cleaned_data['private_contestants'])
            if 'organizations' in form.changed_data or 'classes' in form.changed_data:
                obj.is_organization_private = bool(form.cleaned_data['organizations'] or form.cleaned_data['classes'])
            if 'join_organizations' in form.cleaned_data:
                obj.limit_join_organizations = bool(form.cleaned_data['join_organizations'])

        # `is_visible` will not appear in `cleaned_data` if user cannot edit it
        if form.cleaned_data.get('is_visible') and not request.user.has_perm('judge.change_contest_visibility'):
            if not obj.is_private and not obj.is_organization_private:
                raise PermissionDenied
            if not request.user.has_perm('judge.create_private_contest'):
                raise PermissionDenied

        super().save_model(request, obj, form, change)
        # We need this flag because `save_related` deals with the inlines, but does not know if we have already rescored
        self._rescored = False
        if form.changed_data and any(f in form.changed_data for f in ('format_config', 'format_name')):
            self._rescore(obj.key)
            self._rescored = True

        if form.changed_data and 'locked_after' in form.changed_data:
            self.set_locked_after(obj, form.cleaned_data['locked_after'])

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Only rescored if we did not already do so in `save_model`
        if not self._rescored and any(formset.has_changed() for formset in formsets):
            self._rescore(form.cleaned_data['key'])

    def delete_model(self, request, obj):
        if obj.format_name == 'themis':
            from judge.models import Problem
            prefix = f"{obj.key}_".upper()
            Problem.objects.filter(code__startswith=prefix).delete()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.format_name == 'themis':
                from judge.models import Problem
                prefix = f"{obj.key}_".upper()
                Problem.objects.filter(code__startswith=prefix).delete()
        super().delete_queryset(request, queryset)

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_contest'):
            return False
        if obj is None:
            return True
        return obj.is_editable_by(request.user)

    def _rescore(self, contest_key):
        from judge.tasks import rescore_contest
        transaction.on_commit(rescore_contest.s(contest_key).delay)

    @admin.display(description=_('Mark contests as visible'))
    def make_visible(self, request, queryset):
        if not request.user.has_perm('judge.change_contest_visibility'):
            queryset = queryset.filter(Q(is_private=True) | Q(is_organization_private=True))
        count = queryset.update(is_visible=True)
        self.message_user(request, ngettext('%d contest successfully marked as visible.',
                                            '%d contests successfully marked as visible.',
                                            count) % count)

    @admin.display(description=_('Mark contests as hidden'))
    def make_hidden(self, request, queryset):
        if not request.user.has_perm('judge.change_contest_visibility'):
            queryset = queryset.filter(Q(is_private=True) | Q(is_organization_private=True))
        count = queryset.update(is_visible=False)
        self.message_user(request, ngettext('%d contest successfully marked as hidden.',
                                            '%d contests successfully marked as hidden.',
                                            count) % count)

    @admin.display(description=_('Lock contest submissions'))
    def set_locked(self, request, queryset):
        for row in queryset:
            self.set_locked_after(row, timezone.now())
        count = queryset.count()
        self.message_user(request, ngettext('%d contest successfully locked.',
                                            '%d contests successfully locked.',
                                            count) % count)

    @admin.display(description=_('Unlock contest submissions'))
    def set_unlocked(self, request, queryset):
        for row in queryset:
            self.set_locked_after(row, None)
        count = queryset.count()
        self.message_user(request, ngettext('%d contest successfully unlocked.',
                                            '%d contests successfully unlocked.',
                                            count) % count)

    def set_locked_after(self, contest, locked_after):
        with transaction.atomic():
            contest.locked_after = locked_after
            contest.save()
            Submission.objects.filter(contest_object=contest,
                                      contest__participation__virtual=0).update(locked_after=locked_after)

    def get_urls(self):
        from judge.views.themis_creation import ThemisCreateView
        return [
            path('rate/all/', self.rate_all_view, name='judge_contest_rate_all'),
            path('<int:id>/rate/', self.rate_view, name='judge_contest_rate'),
            path('<int:contest_id>/judge/<int:problem_id>/', self.rejudge_view, name='judge_contest_rejudge'),
            path('themis/create/', self.admin_site.admin_view(ThemisCreateView.as_view()), name='judge_contest_themis_create'),
        ] + super(ContestAdmin, self).get_urls()

    @method_decorator(require_POST)
    def rejudge_view(self, request, contest_id, problem_id):
        contest = get_object_or_404(Contest, id=contest_id)
        if not self.has_change_permission(request, contest):
            raise PermissionDenied()
        queryset = ContestSubmission.objects.filter(problem_id=problem_id).select_related('submission')
        for model in queryset:
            model.submission.judge(rejudge=True, rejudge_user=request.user)

        self.message_user(request, ngettext('%d submission was successfully scheduled for rejudging.',
                                            '%d submissions were successfully scheduled for rejudging.',
                                            len(queryset)) % len(queryset))
        return HttpResponseRedirect(reverse('admin:judge_contest_change', args=(contest_id,)))

    @method_decorator(require_POST)
    def rate_all_view(self, request):
        if not request.user.has_perm('judge.contest_rating'):
            raise PermissionDenied()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('TRUNCATE TABLE `%s`' % Rating._meta.db_table)
            Profile.objects.update(rating=None)
            for contest in Contest.objects.filter(is_rated=True, end_time__lte=timezone.now()).order_by('end_time'):
                rate_contest(contest)
        return HttpResponseRedirect(reverse('admin:judge_contest_changelist'))

    @method_decorator(require_POST)
    def rate_view(self, request, id):
        if not request.user.has_perm('judge.contest_rating'):
            raise PermissionDenied()
        contest = get_object_or_404(Contest, id=id)
        if not contest.is_rated or not contest.ended:
            raise Http404()
        with transaction.atomic():
            contest.rate()
        return HttpResponseRedirect(request.headers.get('referer', reverse('admin:judge_contest_changelist')))

    def get_form(self, request, obj=None, **kwargs):
        form = super(ContestAdmin, self).get_form(request, obj, **kwargs)
        if 'problem_label_script' in form.base_fields:
            # form.base_fields['problem_label_script'] does not exist when the user has only view permission
            # on the model.
            form.base_fields['problem_label_script'].widget = AdminAceWidget(
                mode='lua', theme=request.profile.resolved_ace_theme,
            )

        perms = ('edit_own_contest', 'edit_all_contest')
        form.base_fields['curators'].queryset = Profile.objects.filter(
            Q(user__is_superuser=True) |
            Q(user__groups__permissions__codename__in=perms) |
            Q(user__user_permissions__codename__in=perms),
        ).distinct()
        form.base_fields['classes'].queryset = Class.get_visible_classes(request.user)
        return form


class ContestParticipationForm(ModelForm):
    class Meta:
        widgets = {
            'contest': AdminSelect2Widget(),
            'user': AdminHeavySelect2Widget(data_view='profile_select2'),
        }


class ContestParticipationAdmin(admin.ModelAdmin):
    fields = ('contest', 'user', 'real_start', 'virtual', 'is_disqualified')
    list_display = ('contest', 'username', 'show_virtual', 'real_start', 'score', 'cumtime', 'tiebreaker')
    actions = ['recalculate_results']
    actions_on_bottom = actions_on_top = True
    search_fields = ('contest__key', 'contest__name', 'user__user__username')
    form = ContestParticipationForm
    date_hierarchy = 'real_start'

    def get_queryset(self, request):
        return super(ContestParticipationAdmin, self).get_queryset(request).only(
            'contest__name', 'contest__format_name', 'contest__format_config',
            'user__user__username', 'real_start', 'score', 'cumtime', 'tiebreaker', 'virtual',
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.changed_data and 'is_disqualified' in form.changed_data:
            obj.set_disqualified(obj.is_disqualified)

    @admin.display(description=_('Recalculate results'))
    def recalculate_results(self, request, queryset):
        count = 0
        for participation in queryset:
            participation.recompute_results()
            count += 1
        self.message_user(request, ngettext('%d participation recalculated.',
                                            '%d participations recalculated.',
                                            count) % count)

    @admin.display(description=_('username'), ordering='user__user__username')
    def username(self, obj):
        return obj.user.username

    @admin.display(description=_('virtual'), ordering='virtual')
    def show_virtual(self, obj):
        return obj.virtual or '-'
