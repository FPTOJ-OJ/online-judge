"""
Full CLI for Problem Management.
Powered by Django management command.

Usage:
  python manage.py problem_cli list [--public] [--private] [--org] [--search SEARCH]
  python manage.py problem_cli detail <problem_code>
  python manage.py problem_cli create <code> <name> --description DESC --type TYPE --group GROUP [--points PTS] [--time-limit SEC] [--memory-limit KB] [--public]
  python manage.py problem_cli update <problem_code> [--name NAME] [--description DESC] [--public/--private] [--points PTS] ...
  python manage.py problem_cli delete <problem_code>
  python manage.py problem_cli testcase list <problem_code>
  python manage.py problem_cli testcase add <problem_code> --input INPUT --output OUTPUT --points PTS [--generator-args ARGS] [--order N] [--pretest] [--checker CHECKER]
  python manage.py problem_cli testcase delete <problem_code> <testcase_id>
  python manage.py problem_cli data show <problem_code>
  python manage.py problem_cli data upload-zip <problem_code> <zip_path>
  python manage.py problem_cli data upload-generator <problem_code> <generator_path>
  python manage.py problem_cli data compile <problem_code>
  python manage.py problem_cli type list
  python manage.py problem_cli type add <name> <full_name>
  python manage.py problem_cli group list
  python manage.py problem_cli group add <name> <full_name>
  python manage.py problem_cli author add <problem_code> <username>
  python manage.py problem_cli author remove <problem_code> <username>
"""

import os
import subprocess
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
import json
import zipfile
from io import StringIO

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction

from django.db import models
from judge.models import Problem, ProblemGroup, ProblemType, ProblemData, ProblemTestCase, Profile
from judge.utils.problem_data import ProblemDataCompiler, ProblemDataStorage


problem_data_storage = ProblemDataStorage()


class Command(BaseCommand):
    help = 'Full CLI for problem management'

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='subcommand', required=True)

        # list
        p_list = sub.add_parser('list', help='List problems')
        p_list.add_argument('--public', action='store_true', help='Show only public')
        p_list.add_argument('--private', action='store_true', help='Show only private')
        p_list.add_argument('--org', type=str, help='Filter by organization slug')
        p_list.add_argument('--search', type=str, help='Search in code/name')
        p_list.add_argument('--type', type=str, dest='ptype', help='Filter by type name')
        p_list.add_argument('--group', type=str, help='Filter by group name')
        p_list.add_argument('--json', action='store_true', help='Output as JSON')

        # detail
        p_detail = sub.add_parser('detail', help='Show problem details')
        p_detail.add_argument('code', help='Problem code')
        p_detail.add_argument('--json', action='store_true', help='JSON output')

        # create
        p_create = sub.add_parser('create', help='Create a new problem')
        p_create.add_argument('code', help='Problem code (unique)')
        p_create.add_argument('name', help='Problem name')
        p_create.add_argument('--description', '-d', default='', help='Problem statement')
        p_create.add_argument('--type', required=True, help='Problem type name')
        p_create.add_argument('--group', required=True, help='Problem group name')
        p_create.add_argument('--points', type=float, default=1.0, help='Points')
        p_create.add_argument('--time-limit', type=float, default=1.0, help='Time limit in seconds')
        p_create.add_argument('--memory-limit', type=int, default=65536, help='Memory limit in KB')
        p_create.add_argument('--public', action='store_true', help='Make public')
        p_create.add_argument('--org-private', action='store_true', default=False, help='Restrict to organization members')
        p_create.add_argument('--author', type=str, help='Author username')
        p_create.add_argument('--editorial', default='', help='Editorial content in Markdown')
        p_create.add_argument('--description-file', type=str, help='Read description from file (avoids bash escaping issues)')
        p_create.add_argument('--editorial-file', type=str, help='Read editorial from file (avoids bash escaping issues)')

        # update
        p_update = sub.add_parser('update', help='Update problem fields')
        p_update.add_argument('code', help='Problem code')
        p_update.add_argument('--name', type=str)
        p_update.add_argument('--description', '-d', type=str)
        p_update.add_argument('--type', type=str)
        p_update.add_argument('--group', type=str)
        p_update.add_argument('--points', type=float)
        p_update.add_argument('--time-limit', type=float)
        p_update.add_argument('--memory-limit', type=int)
        p_update.add_argument('--public', action='store_true', dest='make_public', default=None)
        p_update.add_argument('--private', action='store_true', dest='make_private', default=None)
        p_update.add_argument('--org-private', type=str, choices=['y', 'n', 'yes', 'no', 'true', 'false'], default=None)
        p_update.add_argument('--summary', type=str)
        p_update.add_argument('--editorial', type=str, help='Editorial content in Markdown')
        p_update.add_argument('--description-file', type=str, help='Read description from file')
        p_update.add_argument('--editorial-file', type=str, help='Read editorial from file')

        # delete
        p_delete = sub.add_parser('delete', help='Delete a problem')
        p_delete.add_argument('code', help='Problem code')
        p_delete.add_argument('--force', action='store_true', help='Skip confirmation')

        # ---- testcase ----
        tc = sub.add_parser('testcase', help='Manage testcases')
        tc_sub = tc.add_subparsers(dest='tc_action', required=True)

        tc_list = tc_sub.add_parser('list', help='List testcases')
        tc_list.add_argument('code', help='Problem code')
        tc_list.add_argument('--json', action='store_true')

        tc_add = tc_sub.add_parser('add', help='Add a testcase')
        tc_add.add_argument('code', help='Problem code')
        tc_add.add_argument('--input', type=str, default='', help='Input filename')
        tc_add.add_argument('--output', type=str, default='', help='Output filename')
        tc_add.add_argument('--points', type=int, help='Point value')
        tc_add.add_argument('--generator-args', type=str, default='', help='Generator arguments')
        tc_add.add_argument('--order', type=int, default=None, help='Case position (default: append)')
        tc_add.add_argument('--pretest', action='store_true', help='Mark as pretest')
        tc_add.add_argument('--checker', type=str, default='', help='Checker name')
        tc_add.add_argument('--checker-args', type=str, default='', help='Checker arguments')
        tc_add.add_argument('--batch-dependencies', type=str, default='', help='Comma-separated batch dependencies (for type=S)')
        tc_add.add_argument('--type', type=str, default='C', choices=['C', 'S', 'E'], help='Case type')
        tc_add.add_argument('--output-prefix', type=int, help='Output prefix length')
        tc_add.add_argument('--output-limit', type=int, help='Output limit length')

        tc_del = tc_sub.add_parser('delete', help='Delete a testcase')
        tc_del.add_argument('code', help='Problem code')
        tc_del.add_argument('tc_id', type=int, help='Testcase ID')

        # ---- data ----
        data = sub.add_parser('data', help='Manage problem data files')
        data_sub = data.add_subparsers(dest='data_action', required=True)

        data_show = data_sub.add_parser('show', help='Show problem data info')
        data_show.add_argument('code', help='Problem code')

        data_zip = data_sub.add_parser('upload-zip', help='Upload data zip file')
        data_zip.add_argument('code', help='Problem code')
        data_zip.add_argument('zip_path', type=str, help='Path to zip file')

        data_gen = data_sub.add_parser('upload-generator', help='Upload generator file')
        data_gen.add_argument('code', help='Problem code')
        data_gen.add_argument('gen_path', type=str, help='Path to generator file')

        data_compile = data_sub.add_parser('compile', help='Compile init.yml')
        data_compile.add_argument('code', help='Problem code')

        # ---- type ----
        ptype = sub.add_parser('type', help='Manage problem types')
        ptype_sub = ptype.add_subparsers(dest='type_action', required=True)

        ptype_list = ptype_sub.add_parser('list', help='List types')
        ptype_list.add_argument('--json', action='store_true')

        ptype_add = ptype_sub.add_parser('add', help='Add a type')
        ptype_add.add_argument('name', help='Type ID (e.g. "dp")')
        ptype_add.add_argument('full_name', help='Display name (e.g. "Dynamic Programming")')

        # ---- group ----
        pgroup = sub.add_parser('group', help='Manage problem groups')
        pgroup_sub = pgroup.add_subparsers(dest='group_action', required=True)

        pgroup_list = pgroup_sub.add_parser('list', help='List groups')
        pgroup_list.add_argument('--json', action='store_true')

        pgroup_add = pgroup_sub.add_parser('add', help='Add a group')
        pgroup_add.add_argument('name', help='Group ID (e.g. "usaco")')
        pgroup_add.add_argument('full_name', help='Display name (e.g. "USACO")')

        pgroup_delete = pgroup_sub.add_parser('delete', help='Delete a group')
        pgroup_delete.add_argument('name', help='Group ID to delete')

        # ---- bulk ----
        p_bulk = sub.add_parser('bulk', help='Bulk import problems from JSON file')
        p_bulk.add_argument('json_file', type=str, help='Path to JSON file describing problems')
        p_bulk.add_argument('--dry-run', action='store_true', help='Validate only, do not create')
        p_bulk.add_argument('--json', action='store_true', dest='bulk_json_out', help='Output result as JSON')

        # ---- author ----
        pauthor = sub.add_parser('author', help='Manage problem authors')
        pauthor_sub = pauthor.add_subparsers(dest='author_action', required=True)

        pauthor_add = pauthor_sub.add_parser('add', help='Add author')
        pauthor_add.add_argument('code', help='Problem code')
        pauthor_add.add_argument('username', help='Author username')

        pauthor_remove = pauthor_sub.add_parser('remove', help='Remove author')
        pauthor_remove.add_argument('code', help='Problem code')
        pauthor_remove.add_argument('username', help='Author username')

    def handle(self, *args, **options):
        sub = options['subcommand']
        if sub == 'list':
            self.handle_list(options)
        elif sub == 'detail':
            self.handle_detail(options)
        elif sub == 'create':
            self.handle_create(options)
        elif sub == 'update':
            self.handle_update(options)
        elif sub == 'delete':
            self.handle_delete(options)
        elif sub == 'testcase':
            self.handle_testcase(options)
        elif sub == 'data':
            self.handle_data(options)
        elif sub == 'type':
            self.handle_type(options)
        elif sub == 'group':
            self.handle_group(options)
        elif sub == 'author':
            self.handle_author(options)
        elif sub == 'bulk':
            self.handle_bulk(options)

    # ───────────────────────── L I S T ─────────────────────────

    def handle_list(self, opts):
        qs = Problem.objects.all().select_related('group')
        if opts.get('ptype'):
            qs = qs.filter(types__name=opts['ptype'])
        if opts.get('group'):
            qs = qs.filter(group__name=opts['group'])
        if opts.get('search'):
            q = opts['search']
            qs = qs.filter(models.Q(code__icontains=q) | models.Q(name__icontains=q))
        if opts.get('public'):
            qs = qs.filter(is_public=True)
        if opts.get('private'):
            qs = qs.filter(is_public=False)
        if opts.get('org'):
            from judge.models import Organization
            org = Organization.objects.filter(slug=opts['org']).first()
            if org:
                qs = qs.filter(organizations=org)

        qs = qs.order_by('code')
        if opts.get('json'):
            data = [{'code': p.code, 'name': p.name, 'group': str(p.group),
                     'public': p.is_public, 'org_private': p.is_organization_private,
                     'points': p.points, 'time_limit': p.time_limit, 'memory_limit': p.memory_limit}
                    for p in qs]
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'Problems ({qs.count()}):')
        self.stdout.write('─' * 80)
        self.stdout.write(f'{"Code":20s} {"Name":40s} {"Public":8s} {"Group":20s} Points')
        self.stdout.write('─' * 80)
        for p in qs:
            pub = '✓' if p.is_public else '✗'
            self.stdout.write(f'{p.code:20s} {p.name[:38]:40s} {pub:8s} {str(p.group):20s} {p.points}')

    # ─────────────────────── D E T A I L ───────────────────────

    def handle_detail(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        types = ', '.join(t.full_name for t in p.types.all())
        authors = ', '.join(u.user.username for u in p.authors.all()) or '(none)'
        orgs = ', '.join(o.name for o in p.organizations.all()) or '(none)'

        if opts.get('json'):
            cases = ProblemTestCase.objects.filter(dataset=p).order_by('order')
            cases_data = [{'order': c.order, 'type': c.type, 'input_file': c.input_file,
                           'output_file': c.output_file, 'generator_args': c.generator_args,
                           'points': c.points, 'is_pretest': c.is_pretest,
                           'checker': c.checker, 'checker_args': c.checker_args,
                           'batch_dependencies': c.batch_dependencies}
                          for c in cases]
            data_files = {}
            try:
                pd = ProblemData.objects.get(problem=p)
                data_files = {
                    'zipfile': pd.zipfile.name if pd.zipfile else None,
                    'generator': pd.generator.name if pd.generator else None,
                    'checker': pd.checker or None,
                    'io_mode': pd.io_mode,
                    'has_init_yml': pd.has_yml(),
                    'feedback': pd.feedback or None,
                }
            except ProblemData.DoesNotExist:
                pass
            out = {
                'code': p.code, 'name': p.name, 'group': str(p.group),
                'types': types, 'public': p.is_public,
                'org_private': p.is_organization_private, 'organizations': orgs,
                'points': p.points, 'time_limit': p.time_limit, 'memory_limit': p.memory_limit,
                'authors': authors, 'user_count': p.user_count, 'ac_rate': p.ac_rate,
                'summary': p.summary or None,
                'testcases': cases_data, 'data_files': data_files,
            }
            self.stdout.write(json.dumps(out, indent=2, ensure_ascii=False))
            return

        lines = [
            ('code', p.code),
            ('name', p.name),
            ('group', str(p.group)),
            ('types', types),
            ('public', str(p.is_public)),
            ('org_private', str(p.is_organization_private)),
            ('organizations', orgs),
            ('points', str(p.points)),
            ('partial', str(p.partial)),
            ('time_limit (s)', str(p.time_limit)),
            ('memory_limit (KB)', str(p.memory_limit)),
            ('short_circuit', str(p.short_circuit)),
            ('authors', authors),
            ('user_count', str(p.user_count)),
            ('ac_rate', f'{p.ac_rate:.2%}'),
            ('summary', (p.summary or '')[:80]),
            ('date', str(p.date or '')),
            ('license', str(p.license or '')),
            ('is_full_markup', str(p.is_full_markup)),
            ('manually_managed', str(p.is_manually_managed)),
            ('submission_source_visibility', self._get_ssv_display(p.submission_source_visibility_mode)),
        ]

        self.stdout.write(f'\nProblem: {p.code}')
        self.stdout.write('═' * 60)
        for key, val in lines:
            self.stdout.write(f'  {key:35s} {val}')

        # testcases
        cases = ProblemTestCase.objects.filter(dataset=p).order_by('order')
        self.stdout.write(f'\nTestcases ({cases.count()}):')
        self.stdout.write('─' * 80)
        for c in cases:
            gen = f' [generator: {c.generator_args[:30]}]' if c.generator_args else ''
            pts = str(c.points) if c.points is not None else 'default'
            check = f' checker={c.checker}' if c.checker else ''
            batch = f' batch_deps={c.batch_dependencies}' if c.batch_dependencies else ''
            self.stdout.write(f'  #{c.order:3d} type={c.type} input={c.input_file or "-":18s} '
                              f'output={c.output_file or "-":18s} points={pts:>8s}{gen}{check}{batch}')

        # data files
        try:
            pd = ProblemData.objects.get(problem=p)
            self.stdout.write(f'\nData files:')
            self.stdout.write(f'  zipfile:      {pd.zipfile.name if pd.zipfile else "(none)"}')
            self.stdout.write(f'  generator:    {pd.generator.name if pd.generator else "(none)"}')
            self.stdout.write(f'  checker:      {pd.checker or "(default)"}')
            self.stdout.write(f'  io_mode:      {pd.io_mode}')
            self.stdout.write(f'  has init.yml: {pd.has_yml()}')
        except ProblemData.DoesNotExist:
            self.stdout.write('\nData files: (none)')

    # ───────────────────── C R E A T E ─────────────────────

    @transaction.atomic
    def handle_create(self, opts):
        if Problem.objects.filter(code=opts['code']).exists():
            raise CommandError(f'Problem code "{opts["code"]}" already exists.')

        ptype = get_object_or_404(ProblemType, name=opts['type'])
        pgroup = get_object_or_404(ProblemGroup, name=opts['group'])

        description = opts['description']
        if opts.get('description_file'):
            if description:
                raise CommandError('Cannot use both --description and --description-file.')
            description = self._read_file(opts['description_file'])

        p = Problem(
            code=opts['code'],
            name=opts['name'],
            description=description,
            group=pgroup,
            points=opts['points'],
            time_limit=opts['time_limit'],
            memory_limit=opts['memory_limit'],
            is_public=opts['public'],
            is_organization_private=opts['org_private'],
        )
        p.save()
        p.types.add(ptype)
        from judge.models import Language
        p.allowed_languages.add(*Language.objects.all())

        if opts.get('author'):
            profile = self._resolve_profile(opts['author'])
            p.authors.add(profile)

        editorial_content = opts.get('editorial', '')
        if opts.get('editorial_file'):
            if editorial_content:
                raise CommandError('Cannot use both --editorial and --editorial-file.')
            editorial_content = self._read_file(opts['editorial_file'])

        if editorial_content:
            from judge.models import Solution
            from django.utils import timezone
            import datetime
            sol = Solution.objects.create(
                problem=p,
                is_public=True,
                publish_on=timezone.now() - datetime.timedelta(days=1),
                content=editorial_content
            )
            if opts.get('author'):
                sol.authors.add(profile)

        self.stdout.write(self.style.SUCCESS(f'Problem "{p.code}" created.'))
        self.handle_detail({'code': p.code})

    # ───────────────────── U P D A T E ─────────────────────

    @transaction.atomic
    def handle_update(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        changed = []

        for field, opt_key in [
            ('name', 'name'), ('points', 'points'),
            ('time_limit', 'time_limit'), ('memory_limit', 'memory_limit'),
            ('summary', 'summary'),
        ]:
            val = opts.get(opt_key)
            if val is not None:
                setattr(p, field, val)
                changed.append(field)

        # Handle description (inline or file)
        if opts.get('description_file'):
            if opts.get('description'):
                raise CommandError('Cannot use both --description and --description-file.')
            p.description = self._read_file(opts['description_file'])
            changed.append('description')
        elif opts.get('description') is not None:
            p.description = opts['description']
            changed.append('description')

        if opts.get('type'):
            ptype = get_object_or_404(ProblemType, name=opts['type'])
            p.types.set([ptype])
            changed.append('types')

        if opts.get('group'):
            pgroup = get_object_or_404(ProblemGroup, name=opts['group'])
            p.group = pgroup
            changed.append('group')

        if opts.get('make_public') and not opts.get('make_private'):
            p.is_public = True
            changed.append('is_public')
        if opts.get('make_private') and not opts.get('make_public'):
            p.is_public = False
            changed.append('is_public')

        raw_org_private = opts.get('org_private')
        if raw_org_private is not None:
            p.is_organization_private = raw_org_private.lower() in ('y', 'yes', 'true')
            changed.append('is_organization_private')

        p.save()
        editorial_content = opts.get('editorial')
        if opts.get('editorial_file'):
            if editorial_content is not None:
                raise CommandError('Cannot use both --editorial and --editorial-file.')
            editorial_content = self._read_file(opts['editorial_file'])

        if editorial_content is not None:
            from judge.models import Solution
            from django.utils import timezone
            import datetime
            sol, created = Solution.objects.get_or_create(
                problem=p,
                defaults={
                    'is_public': True,
                    'publish_on': timezone.now() - datetime.timedelta(days=1),
                    'content': editorial_content
                }
            )
            if not created:
                sol.content = editorial_content
                sol.save()
            changed.append('editorial')
        self.stdout.write(self.style.SUCCESS(f'Updated: {", ".join(changed)}'))

    # ───────────────────── D E L E T E ─────────────────────

    @transaction.atomic
    def handle_delete(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        if not opts.get('force'):
            self.stdout.write(f'Are you sure you want to delete problem "{p.code} - {p.name}"?')
            self.stdout.write(f'This will also delete {p.cases.count()} testcases, all submissions, etc.')
            confirm = input('Type "yes" to confirm: ')
            if confirm != 'yes':
                raise CommandError('Aborted.')
        p.delete()
        self.stdout.write(self.style.SUCCESS(f'Problem "{opts["code"]}" deleted.'))

    # ─────────────────── T E S T C A S E ───────────────────

    def handle_testcase(self, opts):
        action = opts['tc_action']
        if action == 'list':
            self._testcase_list(opts)
        elif action == 'add':
            self._testcase_add(opts)
        elif action == 'delete':
            self._testcase_delete(opts)

    def _testcase_list(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        cases = ProblemTestCase.objects.filter(dataset=p).order_by('order')

        if opts.get('json'):
            data = [{'order': c.order, 'type': c.type, 'input_file': c.input_file,
                     'output_file': c.output_file, 'generator_args': c.generator_args,
                     'points': c.points, 'is_pretest': c.is_pretest, 'checker': c.checker,
                     'checker_args': c.checker_args, 'output_prefix': c.output_prefix,
                     'output_limit': c.output_limit, 'batch_dependencies': c.batch_dependencies}
                    for c in cases]
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'\nTestcases for {p.code}:')
        self.stdout.write('─' * 120)
        hdr = f'{"ID":5s} {"Ord":4s} {"Type":5s} {"Input":22s} {"Output":22s} {"Points":8s} {"Gen":5s} {"Pre":5s} {"Checker":12s} {"Batch":8s}'
        self.stdout.write(hdr)
        self.stdout.write('─' * 120)
        for c in cases:
            gen = '✓' if c.generator_args else '✗'
            pretest = '✓' if c.is_pretest else '✗'
            pts = str(c.points) if c.points else '(default)'
            check = c.checker or '(default)'
            batch = c.batch_dependencies or ''
            self.stdout.write(f'{c.id:5d} {c.order:4d} {c.type:5s} {c.input_file or "-":22s} '
                              f'{c.output_file or "-":22s} {pts:8s} {gen:5s} {pretest:5s} '
                              f'{check:12s} {batch:8s}')

    @transaction.atomic
    def _testcase_add(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        order = opts['order']
        if order is None:
            last = ProblemTestCase.objects.filter(dataset=p).order_by('order').last()
            order = (last.order + 1) if last else 0

        tc = ProblemTestCase(
            dataset=p,
            order=order,
            type=opts['type'],
            input_file=opts['input'],
            output_file=opts['output'],
            generator_args=opts['generator_args'],
            points=opts['points'],
            is_pretest=opts['pretest'],
            checker=opts['checker'],
            checker_args=opts['checker_args'],
            output_prefix=opts['output_prefix'],
            output_limit=opts['output_limit'],
        )
        if opts['batch_dependencies']:
            tc.batch_dependencies = opts['batch_dependencies']
        tc.save()
        self.stdout.write(self.style.SUCCESS(
            f'Testcase #{tc.id} added (order={order}, '
            f'input="{opts["input"] or "-"}", output="{opts["output"] or "-"}").'))

    @transaction.atomic
    def _testcase_delete(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        tc = get_object_or_404(ProblemTestCase, id=opts['tc_id'], dataset=p)
        tc.delete()
        self.stdout.write(self.style.SUCCESS(f'Testcase #{opts["tc_id"]} deleted.'))

    # ───────────────────── D A T A ─────────────────────

    def handle_data(self, opts):
        action = opts['data_action']
        if action == 'show':
            self._data_show(opts)
        elif action == 'upload-zip':
            self._data_upload_zip(opts)
        elif action == 'upload-generator':
            self._data_upload_generator(opts)
        elif action == 'compile':
            self._data_compile(opts)

    def _data_show(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        try:
            pd = ProblemData.objects.get(problem=p)
            self.stdout.write(f'Problem Data for {p.code}:')
            self.stdout.write(f'  zipfile:      {pd.zipfile.name if pd.zipfile else "(none)"}')
            self.stdout.write(f'  generator:    {pd.generator.name if pd.generator else "(none)"}')
            self.stdout.write(f'  checker:      {pd.checker or "(default)"}')
            self.stdout.write(f'  io_mode:      {pd.io_mode}')
            self.stdout.write(f'  input_file:   {pd.input_filename or "(none)"}')
            self.stdout.write(f'  output_file:  {pd.output_filename or "(none)"}')
            self.stdout.write(f'  has init.yml: {pd.has_yml()}')
            self.stdout.write(f'  feedback:     {pd.feedback[:200] if pd.feedback else "(none)"}')
        except ProblemData.DoesNotExist:
            self.stdout.write(f'No ProblemData record for "{opts["code"]}".')

    def _data_upload_zip(self, opts):
        path = opts['zip_path']
        if not os.path.isfile(path):
            raise CommandError(f'File not found: {path}')
        p = get_object_or_404(Problem, code=opts['code'])
        pd, _ = ProblemData.objects.get_or_create(problem=p)
        with open(path, 'rb') as f:
            pd.zipfile.save(os.path.basename(path), f)
        self.stdout.write(self.style.SUCCESS(f'Zip uploaded to problem "{p.code}".'))

    def _data_upload_generator(self, opts):
        path = opts['gen_path']
        if not os.path.isfile(path):
            raise CommandError(f'File not found: {path}')

        # Auto-compile check for .cpp files
        if path.lower().endswith('.cpp'):
            self._check_generator_compiles(path)

        p = get_object_or_404(Problem, code=opts['code'])
        pd, _ = ProblemData.objects.get_or_create(problem=p)
        with open(path, 'rb') as f:
            pd.generator.save(os.path.basename(path), f)
        self.stdout.write(self.style.SUCCESS(f'Generator uploaded to problem "{p.code}".'))

    @staticmethod
    def _check_generator_compiles(path):
        """Compile a .cpp file with g++ to verify it compiles before uploading."""
        try:
            result = subprocess.run(
                ['g++', '-std=c++17', '-O2', '-o', '/dev/null', '-x', 'c++', path],
                capture_output=True, text=True, timeout=30
            )
        except FileNotFoundError:
            # g++ not installed, skip check
            return
        except subprocess.TimeoutExpired:
            raise CommandError(f'Compilation timed out for: {path}')
        if result.returncode != 0:
            msg = result.stderr.strip() or 'Unknown compilation error'
            raise CommandError(
                f'Generator compilation FAILED for: {path}\n'
                f'Fix the C++ errors and try again:\n{msg}'
            )

    def _data_compile(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        try:
            pd = ProblemData.objects.get(problem=p)
        except ProblemData.DoesNotExist:
            raise CommandError(f'No ProblemData for "{opts["code"]}". Create one and upload zip/generator first.')

        cases = ProblemTestCase.objects.filter(dataset=p).order_by('order')
        files = []
        if pd.zipfile:
            try:
                with zipfile.ZipFile(pd.zipfile.path, 'r') as zf:
                    files = zf.namelist()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not read zip contents: {e}'))

        compiler = ProblemDataCompiler(p, pd, cases, files)
        compiler.compile()
        pd.refresh_from_db()

        if pd.feedback:
            self.stdout.write(self.style.ERROR(f'Compilation failed for "{p.code}":'))
            self.stdout.write(pd.feedback)
        else:
            self.stdout.write(self.style.SUCCESS(f'init.yml compiled for "{p.code}".'))

    # ───────────────────── T Y P E ─────────────────────

    def handle_type(self, opts):
        if opts['type_action'] == 'list':
            types = ProblemType.objects.all().order_by('full_name')
            if opts.get('json'):
                data = [{'name': t.name, 'full_name': t.full_name} for t in types]
                self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
                return
            self.stdout.write('Problem Types:')
            self.stdout.write('  {:<20} {:<40}'.format('Name', 'Full Name'))
            self.stdout.write('  {} {}'.format('─' * 20, '─' * 40))
            for t in types:
                self.stdout.write(f'  {t.name:20s} {t.full_name:40s}')
        elif opts['type_action'] == 'add':
            if ProblemType.objects.filter(name=opts['name']).exists():
                raise CommandError(f'Type "{opts["name"]}" already exists.')
            t = ProblemType(name=opts['name'], full_name=opts['full_name'])
            t.save()
            self.stdout.write(self.style.SUCCESS(f'Type "{opts["name"]}" created.'))

    # ───────────────────── G R O U P ─────────────────────

    def handle_group(self, opts):
        if opts['group_action'] == 'list':
            groups = ProblemGroup.objects.all().order_by('full_name')
            if opts.get('json'):
                data = [{'name': g.name, 'full_name': g.full_name} for g in groups]
                self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
                return
            self.stdout.write('Problem Groups:')
            self.stdout.write('  {:<20} {:<40}'.format('Name', 'Full Name'))
            self.stdout.write('  {} {}'.format('─' * 20, '─' * 40))
            for g in groups:
                self.stdout.write(f'  {g.name:20s} {g.full_name:40s}')
        elif opts['group_action'] == 'add':
            if ProblemGroup.objects.filter(name=opts['name']).exists():
                raise CommandError(f'Group "{opts["name"]}" already exists.')
            g = ProblemGroup(name=opts['name'], full_name=opts['full_name'])
            g.save()
            self.stdout.write(self.style.SUCCESS(f'Group "{opts["name"]}" created.'))
        elif opts['group_action'] == 'delete':
            g = ProblemGroup.objects.filter(name=opts['name']).first()
            if not g:
                raise CommandError(f'Group "{opts["name"]}" not found.')
            if g.problem_set.exists():
                raise CommandError(f'Group "{opts["name"]}" has {g.problem_set.count()} problems. Reassign them first.')
            g.delete()
            self.stdout.write(self.style.SUCCESS(f'Group "{opts["name"]}" deleted.'))

    # ───────────────────── A U T H O R ─────────────────────

    def handle_author(self, opts):
        p = get_object_or_404(Problem, code=opts['code'])
        profile = self._resolve_profile(opts['username'])

        if opts['author_action'] == 'add':
            p.authors.add(profile)
            self.stdout.write(self.style.SUCCESS(f'User "{opts["username"]}" added as author of "{p.code}".'))
        elif opts['author_action'] == 'remove':
            p.authors.remove(profile)
            self.stdout.write(self.style.SUCCESS(f'User "{opts["username"]}" removed from authors of "{p.code}".'))

    # ───────────────────── B U L K ─────────────────────

    @transaction.atomic
    def handle_bulk(self, opts):
        path = opts['json_file']
        if not os.path.isfile(path):
            raise CommandError(f'File not found: {path}')
        with open(path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise CommandError(f'Invalid JSON: {e}')

        if 'problems' not in data or not isinstance(data['problems'], list):
            raise CommandError('JSON must contain a "problems" array.')

        results = []
        for i, item in enumerate(data['problems']):
            code = item.get('code', '')
            name = item.get('name', '')
            result = {'index': i, 'code': code, 'name': name, 'status': 'ok', 'messages': []}
            try:
                if not code or not name:
                    raise CommandError('Each problem must have "code" and "name".')
                if Problem.objects.filter(code=code).exists():
                    raise CommandError(f'Problem code "{code}" already exists.')

                ptype = get_object_or_404(ProblemType, name=item.get('type', ''))
                pgroup = get_object_or_404(ProblemGroup, name=item.get('group', ''))

                # Early validation: resolve author and check file paths before creating
                author_profile = None
                if item.get('author'):
                    author_profile = self._resolve_profile(item['author'])

                gen_path = item.get('generator')
                if gen_path and not os.path.isfile(gen_path):
                    raise CommandError(f'Generator file not found: {gen_path}')

                zip_path = item.get('zip')
                if zip_path and not os.path.isfile(zip_path):
                    raise CommandError(f'Zip file not found: {zip_path}')

                if not opts.get('dry_run'):
                    p = Problem(
                        code=code,
                        name=name,
                        description=item.get('description', ''),
                        group=pgroup,
                        points=item.get('points', 1.0),
                        time_limit=item.get('time_limit', 1.0),
                        memory_limit=item.get('memory_limit', 65536),
                        is_public=item.get('public', False),
                    )
                    p.save()
                    p.types.add(ptype)
                    from judge.models import Language
                    p.allowed_languages.add(*Language.objects.all())
                    result['messages'].append(f'Problem "{code}" created.')

                    if author_profile:
                        p.authors.add(author_profile)

                    if gen_path:
                        if gen_path.lower().endswith('.cpp'):
                            self._check_generator_compiles(gen_path)
                        pd, _ = ProblemData.objects.get_or_create(problem=p)
                        with open(gen_path, 'rb') as gf:
                            pd.generator.save(os.path.basename(gen_path), gf)
                        result['messages'].append(f'Generator uploaded from {gen_path}.')

                    if zip_path:
                        pd, _ = ProblemData.objects.get_or_create(problem=p)
                        with open(zip_path, 'rb') as zf:
                            pd.zipfile.save(os.path.basename(zip_path), zf)
                        result['messages'].append(f'Zip uploaded from {zip_path}.')

                    # Add testcases
                    testcases = item.get('testcases', [])
                    for tc_idx, tc in enumerate(testcases):
                        tc_order = tc.get('order', tc_idx)
                        tc_type = tc.get('type', 'C')
                        tc_obj = ProblemTestCase(
                            dataset=p,
                            order=tc_order,
                            type=tc_type,
                            input_file=tc.get('input', ''),
                            output_file=tc.get('output', ''),
                            generator_args=tc.get('generator_args', ''),
                            points=tc.get('points'),
                            is_pretest=tc.get('pretest', False),
                            checker=tc.get('checker', ''),
                            checker_args=tc.get('checker_args', ''),
                            output_prefix=tc.get('output_prefix'),
                            output_limit=tc.get('output_limit'),
                        )
                        if tc.get('batch_dependencies'):
                            tc_obj.batch_dependencies = tc['batch_dependencies']
                        tc_obj.save()
                        result['messages'].append(
                            f'  Testcase #{tc_idx + 1} added '
                            f'({"generator: " + tc.get("generator_args", "") if tc.get("generator_args") else "file: " + tc.get("input", "")}).')

                    # Compile init.yml
                    if testcases and (gen_path or zip_path or item.get('auto_compile', True)):
                        pd, _ = ProblemData.objects.get_or_create(problem=p)
                        cases_qs = ProblemTestCase.objects.filter(dataset=p).order_by('order')
                        files = []
                        if pd.zipfile:
                            try:
                                with zipfile.ZipFile(pd.zipfile.path, 'r') as zf:
                                    files = zf.namelist()
                            except Exception:
                                pass
                        compiler = ProblemDataCompiler(p, pd, cases_qs, files)
                        compiler.compile()
                        pd.refresh_from_db()
                        if pd.feedback:
                            result['messages'].append(f'  Compile WARNING: {pd.feedback[:100]}')
                        else:
                            result['messages'].append(f'  init.yml compiled.')

            except CommandError as e:
                result['status'] = 'error'
                result['messages'].append(str(e))
            except Exception as e:
                result['status'] = 'error'
                result['messages'].append(f'Unexpected error: {e}')

            results.append(result)

        # Summary
        ok_count = sum(1 for r in results if r['status'] == 'ok')
        err_count = sum(1 for r in results if r['status'] == 'error')

        if opts.get('bulk_json_out'):
            self.stdout.write(json.dumps({'results': results, 'ok': ok_count, 'errors': err_count},
                                         indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'\nBulk import: {ok_count} OK, {err_count} errors')
        for r in results:
            prefix = '✓' if r['status'] == 'ok' else '✗'
            self.stdout.write(f'\n{prefix} [{r["index"]}] {r["code"]}: {r["name"]}')
            for msg in r['messages']:
                self.stdout.write(f'    {msg}')

    # ─────────────────── H E L P E R S ───────────────────

    def _read_file(self, path):
        if not os.path.isfile(path):
            raise CommandError(f'File not found: {path}')
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _resolve_profile(self, username):
        user = User.objects.filter(username=username).first()
        if not user:
            raise CommandError(f'User "{username}" not found.')
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def _get_ssv_display(mode):
        return {'F': 'Follow global', 'A': 'Always visible',
                'S': 'Visible if solved', 'O': 'Only own submissions'}.get(mode, mode)


def get_object_or_404(qs_or_model, **kwargs):
    """Simplified get_object_or_404 for management commands."""
    from django.shortcuts import _get_queryset
    qs = _get_queryset(qs_or_model)
    try:
        return qs.get(**kwargs)
    except qs.model.DoesNotExist:
        raise CommandError(f'{qs.model.__name__} not found: {kwargs}')
    except qs.model.MultipleObjectsReturned:
        raise CommandError(f'Multiple {qs.model.__name__} found: {kwargs}')
