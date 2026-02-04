from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, gettext_lazy

from judge.contest_format.base import BaseContestFormat
from judge.contest_format.registry import register_contest_format


@register_contest_format('themis')
class ThemisContestFormat(BaseContestFormat):
    name = gettext_lazy('Themis Style')

    @classmethod
    def validate(cls, config):
        if config is None:
            return
        if not isinstance(config, dict):
            raise ValidationError('Themis contest config must be a dict')
        
        mapping = config.get('mapping')
        if mapping:
            if not isinstance(mapping, dict):
                raise ValidationError('Themis contest "mapping" must be a dict')

        rate_limit = config.get('rate_limit')
        if rate_limit:
            if not isinstance(rate_limit, dict):
                raise ValidationError('Themis contest "rate_limit" must be a dict')
            if 'count' not in rate_limit or 'window' not in rate_limit:
                raise ValidationError('Themis contest "rate_limit" must contain "count" and "window"')
            try:
                int(rate_limit['count'])
                int(rate_limit['window'])
            except ValueError:
                raise ValidationError('"count" and "window" in "rate_limit" must be integers')

    def __init__(self, contest, config):
        super(ThemisContestFormat, self).__init__(contest, config)
        self.config = config or {}

    def update_participation(self, participation):
        cumtime = 0
        points = 0
        format_data = {}

        running_probs = set(participation.submissions.filter(
            submission__status__in=['QU', 'P', 'G']
        ).values_list('problem_id', flat=True))

        for result in participation.submissions.values('problem_id').annotate(
                time=Max('submission__date'), points=Max('points'),
        ):
            dt = (result['time'] - participation.start).total_seconds()
            pid = result['problem_id']
            format_data[str(pid)] = {
                'time': dt, 
                'points': result['points'],
                'is_running': pid in running_probs
            }
            points += result['points']
            # We track max time for tie-breaking if needed, but primary is points
            cumtime = max(cumtime, dt)

        participation.cumtime = cumtime
        participation.score = round(points, self.contest.points_precision)
        participation.tiebreaker = 0
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            param = {
                'state': (('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                       self.best_solution_state(format_data['points'], contest_problem.points)),
                'url': reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                'points': floatformat(format_data['points']),
            }
            if format_data.get('is_running'):
                return format_html(
                    '<td class="{state}"><a href="{url}">{points} <i class="fa fa-spinner fa-spin"></i></a></td>',
                    **param
                )
            return format_html(
                '<td class="{state}"><a href="{url}">{points}</a></td>',
                **param
            )
        else:
            return mark_safe('<td></td>')

    def display_participation_result(self, participation):
        return format_html(
            '<td class="user-points"><a href="{url}">{points}</a></td>',
            url=reverse('contest_all_user_submissions',
                        args=[self.contest.key, participation.user.user.username]),
            points=floatformat(participation.score, -self.contest.points_precision),
        )

    def get_problem_breakdown(self, participation, contest_problems):
        return [(participation.format_data or {}).get(str(contest_problem.id)) for contest_problem in contest_problems]

    def get_label_for_problem(self, index):
        return str(index + 1)

    def get_short_form_display(self):
        yield _('Themis Style Contest: Upload your files and get graded immediately.')
