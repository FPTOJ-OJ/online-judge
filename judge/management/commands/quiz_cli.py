"""
Full CLI for Quiz/Exam Management.
Django management command for AI agents.

Usage:
  python manage.py quiz_cli exam list [--json]
  python manage.py quiz_cli exam detail <id>
  python manage.py quiz_cli exam create <name> [--duration MIN] [--description DESC] [--visible] [--featured] [--login] [--locked] [--org-only] [--author USER]
  python manage.py quiz_cli exam update <id> [options]
  python manage.py quiz_cli exam delete <id> [--force]
  python manage.py quiz_cli exam question list <exam_id> [--json]
  python manage.py quiz_cli exam question add <exam_id> --content "Question" [--type choice|tf] [--difficulty EASY|MEDIUM|HARD|VERY_HARD] [--explanation "..."]./ [--tag TAG] [--option A:"Text":true B:"Text":false]
  python manage.py quiz_cli exam question remove <exam_id> <question_id>
  python manage.py quiz_cli tag list [--json]
  python manage.py quiz_cli tag add <name> <slug>
  python manage.py quiz_cli tag delete <slug>
"""

import json
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q

from judge.models import QuizSource, QuizQuestion, QuizOption, QuizTag, Profile


def get_object_or_404(qs_or_model, **kwargs):
    from django.shortcuts import _get_queryset
    qs = _get_queryset(qs_or_model)
    try:
        return qs.get(**kwargs)
    except qs.model.DoesNotExist:
        raise CommandError(f'{qs.model.__name__} not found: {kwargs}')
    except qs.model.MultipleObjectsReturned:
        raise CommandError(f'Multiple {qs.model.__name__} found: {kwargs}')


DIFFICULTY_MAP = {
    'easy': 'easy', 'nhận biết': 'easy', 'nhan biet': 'easy',
    'medium': 'medium', 'thông hiểu': 'medium', 'thong hieu': 'medium',
    'hard': 'hard', 'vận dụng': 'hard', 'van dung': 'hard',
    'very_hard': 'very_hard', 'vận dụng cao': 'very_hard', 'van dung cao': 'very_hard',
    'very hard': 'very_hard',
}

QUESTION_TYPE_MAP = {
    'choice': 'choice', 'trắc nghiệm': 'choice', 'trac nghiem': 'choice', 'mc': 'choice',
    'tf': 'tf', 'true/false': 'tf', 'đúng/sai': 'tf', 'dung sai': 'tf',
}


class Command(BaseCommand):
    help = 'Full CLI for quiz/exam management'

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='subcommand', required=True)

        # ── exam ──
        exam = sub.add_parser('exam', help='Manage exams (QuizSource)')
        exam_sub = exam.add_subparsers(dest='exam_action', required=True)

        exam_list = exam_sub.add_parser('list', help='List exams')
        exam_list.add_argument('--visible', action='store_true', default=None, help='Filter by visible')
        exam_list.add_argument('--featured', action='store_true', default=None, help='Filter by featured')
        exam_list.add_argument('--locked', action='store_true', default=None, help='Filter by locked')
        exam_list.add_argument('--search', type=str, help='Search by name')
        exam_list.add_argument('--json', action='store_true', help='JSON output')

        exam_detail = exam_sub.add_parser('detail', help='Show exam details')
        exam_detail.add_argument('id', type=int, help='Exam ID')
        exam_detail.add_argument('--json', action='store_true', help='JSON output')

        exam_create = exam_sub.add_parser('create', help='Create a new exam')
        exam_create.add_argument('name', help='Exam name')
        exam_create.add_argument('--description', '-d', default='', help='Exam description')
        exam_create.add_argument('--duration', type=int, default=45, help='Duration in minutes')
        exam_create.add_argument('--visible', action='store_true', default=False, help='Visible to users')
        exam_create.add_argument('--featured', action='store_true', default=False, help='Mark as featured')
        exam_create.add_argument('--login', action='store_true', default=False, help='Require login')
        exam_create.add_argument('--locked', action='store_true', default=False, help='Lock exam')
        exam_create.add_argument('--org-only', action='store_true', default=False, help='Organization only')
        exam_create.add_argument('--author', type=str, help='Creator username')

        exam_update = exam_sub.add_parser('update', help='Update exam')
        exam_update.add_argument('id', type=int, help='Exam ID')
        exam_update.add_argument('--name', type=str)
        exam_update.add_argument('--description', type=str)
        exam_update.add_argument('--duration', type=int)
        exam_update.add_argument('--visible', type=str, choices=['y', 'n', 'yes', 'no', 'true', 'false'])
        exam_update.add_argument('--featured', type=str, choices=['y', 'n', 'yes', 'no', 'true', 'false'])
        exam_update.add_argument('--login', type=str, choices=['y', 'n', 'yes', 'no', 'true', 'false'])
        exam_update.add_argument('--locked', type=str, choices=['y', 'n', 'yes', 'no', 'true', 'false'])
        exam_update.add_argument('--org-only', type=str, choices=['y', 'n', 'yes', 'no', 'true', 'false'])

        exam_delete = exam_sub.add_parser('delete', help='Delete exam')
        exam_delete.add_argument('id', type=int, help='Exam ID')
        exam_delete.add_argument('--force', action='store_true', help='Skip confirmation')

        # ── exam question ──
        eq = exam_sub.add_parser('question', help='Manage exam questions')
        eq_sub = eq.add_subparsers(dest='eq_action', required=True)

        eq_list = eq_sub.add_parser('list', help='List questions for an exam')
        eq_list.add_argument('exam_id', type=int, help='Exam ID')
        eq_list.add_argument('--json', action='store_true')

        eq_add = eq_sub.add_parser('add', help='Add question to exam')
        eq_add.add_argument('exam_id', type=int, help='Exam ID')
        eq_add.add_argument('--content', required=True, help='Question content (Markdown)')
        eq_add.add_argument('--type', default='choice', choices=['choice', 'tf', 'trắc nghiệm', 'trac nghiem', 'đúng/sai', 'dung sai', 'mc'],
                            help='Question type')
        eq_add.add_argument('--difficulty', default='easy',
                            choices=['easy', 'medium', 'hard', 'very_hard', 'nhận biết', 'nhan biet',
                                     'thông hiểu', 'thong hieu', 'vận dụng', 'van dung', 'vận dụng cao', 'van dung cao'],
                            help='Difficulty level')
        eq_add.add_argument('--explanation', default='', help='Explanation (Markdown)')
        eq_add.add_argument('--tag', type=str, action='append', default=[], help='Tag slug. Repeat for multiple tags.')
        eq_add.add_argument('--option', type=str, action='append', default=[], dest='options',
                            help='Options in format LABEL:"Text":correct. Repeat for each option. E.g. --option A:"Answer A":true --option B:"Answer B":false')

        eq_remove = eq_sub.add_parser('remove', help='Remove question from exam')
        eq_remove.add_argument('exam_id', type=int, help='Exam ID')
        eq_remove.add_argument('question_id', type=int, help='Question ID')

        eq_update_q = eq_sub.add_parser('update', help='Update a question')
        eq_update_q.add_argument('question_id', type=int, help='Question ID')
        eq_update_q.add_argument('--content', type=str)
        eq_update_q.add_argument('--type', type=str)
        eq_update_q.add_argument('--difficulty', type=str)
        eq_update_q.add_argument('--explanation', type=str)
        eq_update_q.add_argument('--tag', type=str, action='append', default=None, help='Tag slug. Repeat for multiple tags.')
        eq_update_q.add_argument('--option', type=str, action='append', default=None, dest='options',
                                 help='Replace options. Repeat for each option. Format: LABEL:"Text":correct')

        eq_del = eq_sub.add_parser('delete', help='Delete a question entirely')
        eq_del.add_argument('question_id', type=int, help='Question ID')
        eq_del.add_argument('--force', action='store_true')

        # ── bulk ──
        p_bulk = sub.add_parser('bulk', help='Bulk import exams from JSON')
        p_bulk.add_argument('json_file', type=str, help='Path to JSON file')
        p_bulk.add_argument('--dry-run', action='store_true', help='Validate only')
        p_bulk.add_argument('--json', action='store_true', dest='bulk_json_out', help='Output result as JSON')

        # ── tag ──
        tag = sub.add_parser('tag', help='Manage quiz tags')
        tag_sub = tag.add_subparsers(dest='tag_action', required=True)

        tag_list = tag_sub.add_parser('list', help='List tags')
        tag_list.add_argument('--json', action='store_true')

        tag_add = tag_sub.add_parser('add', help='Add a tag')
        tag_add.add_argument('name', help='Display name')
        tag_add.add_argument('slug', help='Unique slug')

        tag_del = tag_sub.add_parser('delete', help='Delete a tag')
        tag_del.add_argument('slug', help='Tag slug')

    def handle(self, *args, **options):
        sub = options['subcommand']
        if sub == 'exam':
            self.handle_exam(options)
        elif sub == 'tag':
            self.handle_tag(options)
        elif sub == 'bulk':
            self.handle_bulk(options)

    # ════════════════ E X A M ════════════════

    def handle_exam(self, opts):
        action = opts['exam_action']
        if action == 'list':
            self._exam_list(opts)
        elif action == 'detail':
            self._exam_detail(opts)
        elif action == 'create':
            self._exam_create(opts)
        elif action == 'update':
            self._exam_update(opts)
        elif action == 'delete':
            self._exam_delete(opts)
        elif action == 'question':
            self._exam_question(opts)

    def _exam_list(self, opts):
        qs = QuizSource.objects.annotate(q_count=Count('questions')).order_by('-created_at')

        if opts.get('visible') is not None:
            qs = qs.filter(is_visible=opts['visible'])
        if opts.get('featured') is not None:
            qs = qs.filter(is_featured=opts['featured'])
        if opts.get('locked') is not None:
            qs = qs.filter(is_locked=opts['locked'])
        if opts.get('search'):
            qs = qs.filter(name__icontains=opts['search'])

        if opts.get('json'):
            data = []
            for s in qs:
                data.append({
                    'id': s.id,
                    'name': s.name,
                    'visible': s.is_visible,
                    'featured': s.is_featured,
                    'locked': s.is_locked,
                    'login_required': s.require_login,
                    'org_only': s.is_organization_only,
                    'duration': s.default_duration,
                    'question_count': s.q_count,
                    'created_by': s.created_by.username if s.created_by else None,
                    'created_at': s.created_at.isoformat(),
                })
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'Exams ({qs.count()}):')
        self.stdout.write('─' * 120)
        hdr = f'{"ID":5s} {"Name":45s} {"Visible":8s} {"Featured":9s} {"Locked":7s} {"Login":6s} {"Org":5s} {"Dur":5s} {"Q":4s} {"Author":15s}'
        self.stdout.write(hdr)
        self.stdout.write('─' * 120)
        for s in qs:
            vis = '✓' if s.is_visible else '✗'
            feat = '✓' if s.is_featured else '✗'
            locked = '✓' if s.is_locked else '✗'
            login = '✓' if s.require_login else '✗'
            org = '✓' if s.is_organization_only else '✗'
            author = s.created_by.username if s.created_by else '(none)'
            self.stdout.write(
                f'{s.id:5d} {s.name[:43]:45s} {vis:8s} {feat:9s} {locked:7s} '
                f'{login:6s} {org:5s} {s.default_duration:5d} {s.q_count:4d} {author:15s}')

    def _exam_detail(self, opts):
        s = get_object_or_404(QuizSource, id=opts['id'])
        orgs = ', '.join(o.name for o in s.organizations.all()) or '(none)'
        author = s.created_by.username if s.created_by else '(none)'

        if opts.get('json'):
            qs = QuizQuestion.objects.filter(source=s).prefetch_related('tags', 'options').order_by('id')
            questions = []
            for q in qs:
                opts_data = [{'label': o.label, 'content': o.content, 'is_correct': o.is_correct}
                             for o in q.options.all()]
                questions.append({
                    'id': q.id, 'type': q.type, 'difficulty': q.difficulty,
                    'content': q.content, 'explanation': q.explanation,
                    'tags': [t.slug for t in q.tags.all()],
                    'options': opts_data,
                })
            out = {
                'id': s.id, 'name': s.name, 'visible': s.is_visible,
                'featured': s.is_featured, 'locked': s.is_locked,
                'login_required': s.require_login, 'org_only': s.is_organization_only,
                'organizations': [o.name for o in s.organizations.all()],
                'duration': s.default_duration, 'description': s.description,
                'created_by': author, 'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat(),
                'question_count': len(questions),
                'questions': questions,
            }
            self.stdout.write(json.dumps(out, indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'\nExam: {s.name}')
        self.stdout.write('═' * 60)
        self.stdout.write(f'  {"ID":25s} {s.id}')
        self.stdout.write(f'  {"Name":25s} {s.name}')
        self.stdout.write(f'  {"Visible":25s} {s.is_visible}')
        self.stdout.write(f'  {"Featured":25s} {s.is_featured}')
        self.stdout.write(f'  {"Locked":25s} {s.is_locked}')
        self.stdout.write(f'  {"Login required":25s} {s.require_login}')
        self.stdout.write(f'  {"Org only":25s} {s.is_organization_only}')
        self.stdout.write(f'  {"Organizations":25s} {orgs}')
        self.stdout.write(f'  {"Duration (min)":25s} {s.default_duration}')
        self.stdout.write(f'  {"Created by":25s} {author}')
        self.stdout.write(f'  {"Created at":25s} {s.created_at}')
        self.stdout.write(f'  {"Updated at":25s} {s.updated_at}')
        desc = (s.description or '').strip()
        if desc:
            self.stdout.write(f'  {"Description":25s} {desc[:200]}')

        qs = QuizQuestion.objects.filter(source=s).prefetch_related('tags').order_by('id')
        self.stdout.write(f'\nQuestions ({qs.count()}):')
        self.stdout.write('─' * 80)
        self.stdout.write(f'{"ID":6s} {"Type":10s} {"Difficulty":12s} {"Tags":25s} {"Content preview":30s}')
        self.stdout.write('─' * 80)
        for q in qs:
            tags = ', '.join(t.name for t in q.tags.all()) or '-'
            content_preview = q.content[:50].replace('\n', ' ')
            self.stdout.write(
                f'{q.id:6d} {q.type:10s} {q.difficulty:12s} {tags:25s} {content_preview[:48]:30s}')

    @transaction.atomic
    def _exam_create(self, opts):
        if QuizSource.objects.filter(name=opts['name']).exists():
            raise CommandError(f'Exam "{opts["name"]}" already exists.')

        user = None
        if opts.get('author'):
            user_obj = User.objects.filter(username=opts['author']).first()
            if not user_obj:
                raise CommandError(f'User "{opts["author"]}" not found.')
            user = user_obj

        s = QuizSource(
            name=opts['name'],
            description=opts['description'],
            default_duration=opts['duration'],
            is_visible=opts['visible'],
            is_featured=opts['featured'],
            require_login=opts['login'],
            is_locked=opts['locked'],
            is_organization_only=opts['org_only'],
            created_by=user,
        )
        s.save()
        self.stdout.write(self.style.SUCCESS(f'Exam #{s.id} "{s.name}" created.'))

    @transaction.atomic
    def _exam_update(self, opts):
        s = get_object_or_404(QuizSource, id=opts['id'])
        changed = []

        str_fields = [('name', 'name'), ('description', 'description')]
        int_fields = [('default_duration', 'duration')]
        bool_fields = [
            ('is_visible', 'visible'), ('is_featured', 'featured'),
            ('require_login', 'login'), ('is_locked', 'locked'),
            ('is_organization_only', 'org_only'),
        ]

        for model_field, opt_key in str_fields:
            val = opts.get(opt_key)
            if val is not None:
                setattr(s, model_field, val)
                changed.append(model_field)

        for model_field, opt_key in int_fields:
            val = opts.get(opt_key)
            if val is not None:
                setattr(s, model_field, val)
                changed.append(model_field)

        for model_field, opt_key in bool_fields:
            raw = opts.get(opt_key)
            if raw is not None:
                val = raw.lower() in ('y', 'yes', 'true')
                setattr(s, model_field, val)
                changed.append(model_field)

        if changed:
            s.save()
            self.stdout.write(self.style.SUCCESS(f'Exam #{s.id} updated: {", ".join(changed)}'))
        else:
            self.stdout.write('No changes.')

    @transaction.atomic
    def _exam_delete(self, opts):
        s = get_object_or_404(QuizSource, id=opts['id'])
        q_count = QuizQuestion.objects.filter(source=s).count()
        if not opts.get('force'):
            self.stdout.write(f'Are you sure you want to delete exam #{s.id} "{s.name}"?')
            self.stdout.write(f'This will also delete {q_count} questions and their options.')
            confirm = input('Type "yes" to confirm: ')
            if confirm != 'yes':
                raise CommandError('Aborted.')
        s.delete()
        self.stdout.write(self.style.SUCCESS(f'Exam #{opts["id"]} deleted.'))

    # ════════════ E X A M   Q U E S T I O N ════════════

    def _exam_question(self, opts):
        action = opts['eq_action']
        if action == 'list':
            self._eq_list(opts)
        elif action == 'add':
            self._eq_add(opts)
        elif action == 'remove':
            self._eq_remove(opts)
        elif action == 'update':
            self._eq_update(opts)
        elif action == 'delete':
            self._eq_delete(opts)

    def _eq_list(self, opts):
        s = get_object_or_404(QuizSource, id=opts['exam_id'])
        qs = QuizQuestion.objects.filter(source=s).prefetch_related('tags', 'options').order_by('id')

        if opts.get('json'):
            data = []
            for q in qs:
                opts_data = [{'label': o.label, 'content': o.content, 'is_correct': o.is_correct}
                             for o in q.options.all()]
                data.append({
                    'id': q.id,
                    'type': q.type,
                    'difficulty': q.difficulty,
                    'content': q.content,
                    'explanation': q.explanation,
                    'tags': [t.slug for t in q.tags.all()],
                    'options': opts_data,
                })
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'\nQuestions for exam #{s.id} "{s.name}":')
        self.stdout.write('─' * 100)
        hdr = f'{"ID":6s} {"Type":10s} {"Difficulty":12s} {"Tags":20s} {"Content preview":50s}'
        self.stdout.write(hdr)
        self.stdout.write('─' * 100)
        for q in qs:
            tags = ', '.join(t.name for t in q.tags.all()) or '-'
            content_preview = q.content[:60].replace('\n', ' ')
            self.stdout.write(
                f'{q.id:6d} {q.type:10s} {q.difficulty:12s} {tags:20s} {content_preview[:48]:50s}')

    @transaction.atomic
    def _eq_add(self, opts):
        s = get_object_or_404(QuizSource, id=opts['exam_id'])

        q_type = QUESTION_TYPE_MAP.get(opts['type'].lower(), 'choice')
        difficulty = DIFFICULTY_MAP.get(opts['difficulty'].lower(), 'easy')

        q = QuizQuestion(
            source=s,
            content=opts['content'],
            type=q_type,
            difficulty=difficulty,
            explanation=opts['explanation'] or None,
        )
        q.save()

        # Add tags
        for slug in opts['tag']:
            tag = QuizTag.objects.filter(slug=slug).first()
            if tag:
                q.tags.add(tag)
            else:
                self.stdout.write(self.style.WARNING(f'Tag "{slug}" not found, skipping.'))

        # Add options
        if opts['options']:
            self._parse_and_add_options(q, opts['options'])

        self.stdout.write(self.style.SUCCESS(f'Question #{q.id} added to exam #{s.id}.'))

    @transaction.atomic
    def _eq_remove(self, opts):
        s = get_object_or_404(QuizSource, id=opts['exam_id'])
        q = get_object_or_404(QuizQuestion, id=opts['question_id'], source=s)
        q.source = None
        q.save()
        self.stdout.write(self.style.SUCCESS(f'Question #{q.id} removed from exam #{s.id}.'))

    @transaction.atomic
    def _eq_update(self, opts):
        q = get_object_or_404(QuizQuestion, id=opts['question_id'])
        changed = []

        if opts.get('content') is not None:
            q.content = opts['content']
            changed.append('content')
        if opts.get('type') is not None:
            mapped = QUESTION_TYPE_MAP.get(opts['type'].lower())
            if mapped:
                q.type = mapped
                changed.append('type')
            else:
                raise CommandError(f'Invalid type: {opts["type"]}')
        if opts.get('difficulty') is not None:
            mapped = DIFFICULTY_MAP.get(opts['difficulty'].lower())
            if mapped:
                q.difficulty = mapped
                changed.append('difficulty')
            else:
                raise CommandError(f'Invalid difficulty: {opts["difficulty"]}')
        if opts.get('explanation') is not None:
            q.explanation = opts['explanation'] or None
            changed.append('explanation')

        if opts.get('tag') is not None:
            q.tags.clear()
            for slug in opts['tag']:
                tag = QuizTag.objects.filter(slug=slug).first()
                if tag:
                    q.tags.add(tag)
                else:
                    self.stdout.write(self.style.WARNING(f'Tag "{slug}" not found, skipping.'))
            changed.append('tags')

        q.save()

        if opts.get('options') is not None:
            q.options.all().delete()
            self._parse_and_add_options(q, opts['options'])
            changed.append('options')

        if changed:
            self.stdout.write(self.style.SUCCESS(f'Question #{q.id} updated: {", ".join(changed)}'))
        else:
            self.stdout.write('No changes.')

    @transaction.atomic
    def _eq_delete(self, opts):
        q = get_object_or_404(QuizQuestion, id=opts['question_id'])
        if not opts.get('force'):
            self.stdout.write(f'Delete question #{q.id}: {q.content[:60]}...')
            confirm = input('Type "yes" to confirm: ')
            if confirm != 'yes':
                raise CommandError('Aborted.')
        q.delete()
        self.stdout.write(self.style.SUCCESS(f'Question #{opts["question_id"]} deleted.'))

    # ════════════ B U L K ════════════

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

        if 'exams' not in data or not isinstance(data['exams'], list):
            raise CommandError('JSON must contain an "exams" array.')

        results = []
        for i, item in enumerate(data['exams']):
            name = item.get('name', '')
            result = {'index': i, 'name': name, 'status': 'ok', 'messages': []}
            try:
                if not name:
                    raise CommandError('Each exam must have a "name".')
                if QuizSource.objects.filter(name=name).exists():
                    raise CommandError(f'Exam "{name}" already exists.')

                # Ensure specified tags exist
                tags_slug_map = {}
                for tag_info in item.get('tags', []):
                    if isinstance(tag_info, dict):
                        t_name = tag_info.get('name', '')
                        t_slug = tag_info.get('slug', '')
                    else:
                        t_name = tag_info
                        t_slug = tag_info.lower().replace(' ', '_')
                    tag_obj, created = QuizTag.objects.get_or_create(
                        slug=t_slug,
                        defaults={'name': t_name or t_slug},
                    )
                    tags_slug_map[t_slug] = tag_obj
                    if created:
                        result['messages'].append(f'  Tag "{t_name}" auto-created.')

                # Resolve author
                user = None
                if item.get('author'):
                    user_obj = User.objects.filter(username=item['author']).first()
                    if not user_obj:
                        raise CommandError(f'User "{item["author"]}" not found.')
                    user = user_obj

                if not opts.get('dry_run'):
                    s = QuizSource(
                        name=name,
                        description=item.get('description', ''),
                        default_duration=item.get('duration', 45),
                        is_visible=item.get('visible', False),
                        is_featured=item.get('featured', False),
                        require_login=item.get('login', False),
                        is_locked=item.get('locked', False),
                        is_organization_only=item.get('org_only', False),
                        created_by=user,
                    )
                    s.save()
                    result['messages'].append(f'Exam "{name}" (#{s.id}) created.')

                    # Add questions
                    for q_idx, q_data in enumerate(item.get('questions', [])):
                        q_content = q_data.get('content', '')
                        if not q_content:
                            result['messages'].append(f'  WARNING: Question {q_idx + 1} has no content, skipped.')
                            continue

                        q_type = QUESTION_TYPE_MAP.get(str(q_data.get('type', 'choice')).lower(), 'choice')
                        q_diff = DIFFICULTY_MAP.get(str(q_data.get('difficulty', 'easy')).lower(), 'easy')

                        q = QuizQuestion(
                            source=s,
                            content=q_content,
                            type=q_type,
                            difficulty=q_diff,
                            explanation=q_data.get('explanation', None),
                        )
                        q.save()

                        # Add tags
                        for q_tag in q_data.get('tags', []):
                            tag_obj = QuizTag.objects.filter(slug=q_tag).first()
                            if tag_obj:
                                q.tags.add(tag_obj)

                        # Add options
                        for opt_data in q_data.get('options', []):
                            QuizOption.objects.create(
                                question=q,
                                label=opt_data.get('label', ''),
                                content=opt_data.get('content', ''),
                                is_correct=opt_data.get('is_correct', False),
                            )

                        result['messages'].append(f'  Question {q_idx + 1} (#{q.id}) added ({len(q_data.get("options", []))} options).')

            except CommandError as e:
                result['status'] = 'error'
                result['messages'].append(str(e))
            except Exception as e:
                result['status'] = 'error'
                result['messages'].append(f'Unexpected error: {e}')

            results.append(result)

        ok_count = sum(1 for r in results if r['status'] == 'ok')
        err_count = sum(1 for r in results if r['status'] == 'error')

        if opts.get('bulk_json_out'):
            self.stdout.write(json.dumps({'results': results, 'ok': ok_count, 'errors': err_count},
                                         indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'\nBulk import: {ok_count} OK, {err_count} errors')
        for r in results:
            prefix = '✓' if r['status'] == 'ok' else '✗'
            self.stdout.write(f'\n{prefix} [{r["index"]}] {r["name"]}')
            for msg in r['messages']:
                self.stdout.write(f'    {msg}')

    # ════════════ T A G ════════════

    def handle_tag(self, opts):
        if opts['tag_action'] == 'list':
            self._tag_list(opts)
        elif opts['tag_action'] == 'add':
            self._tag_add(opts)
        elif opts['tag_action'] == 'delete':
            self._tag_delete(opts)

    def _tag_list(self, opts):
        tags = QuizTag.objects.all().order_by('name')
        if opts.get('json'):
            data = [{'name': t.name, 'slug': t.slug, 'question_count': t.questions.count()} for t in tags]
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return
        self.stdout.write('Quiz Tags:')
        self.stdout.write('  {:<25s} {:<25s} {:>8s}'.format('Name', 'Slug', 'Questions'))
        self.stdout.write('  {} {} {}'.format('─' * 25, '─' * 25, '─' * 8))
        for t in tags:
            self.stdout.write(f'  {t.name:25s} {t.slug:25s} {t.questions.count():8d}')

    def _tag_add(self, opts):
        if QuizTag.objects.filter(name=opts['name']).exists():
            raise CommandError(f'Tag "{opts["name"]}" already exists.')
        if QuizTag.objects.filter(slug=opts['slug']).exists():
            raise CommandError(f'Slug "{opts["slug"]}" already in use.')
        t = QuizTag(name=opts['name'], slug=opts['slug'])
        t.save()
        self.stdout.write(self.style.SUCCESS(f'Tag "{opts["name"]}" (slug="{opts["slug"]}") created.'))

    def _tag_delete(self, opts):
        t = get_object_or_404(QuizTag, slug=opts['slug'])
        q_count = t.questions.count()
        t.delete()
        self.stdout.write(self.style.SUCCESS(f'Tag "{t.name}" deleted ({q_count} questions untagged).'))

    # ════════════ P A R S E R S ════════════

    @staticmethod
    def _parse_and_add_options(question, option_strings):
        for opt_str in option_strings:
            # Format: LABEL:"Content Text":true
            # or: A:"Answer A":true
            parts = opt_str.split(':', 2)
            if len(parts) != 3:
                raise CommandError(f'Invalid option format: "{opt_str}". Use LABEL:"Text":true/false')

            label = parts[0].strip()
            content = parts[1].strip()
            # Remove surrounding quotes if present
            if len(content) >= 2 and content.startswith('"') and content.endswith('"'):
                content = content[1:-1]
            is_correct = parts[2].strip().lower() in ('true', 't', 'yes', '1')

            QuizOption.objects.create(
                question=question,
                label=label,
                content=content,
                is_correct=is_correct,
            )
