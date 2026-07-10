"""
Full CLI for User Management.
Django management command for AI agents.

Usage:
  python manage.py user_cli list [--staff] [--superuser] [--setter] [--admin] [--active] [--search QUERY] [--json]
  python manage.py user_cli detail <username>
  python manage.py user_cli promote <username> [--staff] [--superuser] [--setter] [--admin-rank]
  python manage.py user_cli demote <username> [--staff] [--superuser]
  python manage.py user_cli activate <username>
  python manage.py user_cli deactivate <username>
"""

import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db import transaction

from judge.models import Profile


DISPLAY_RANK_CHOICES = {'user': 'Normal User', 'setter': 'Problem Setter', 'admin': 'Admin'}


def get_object_or_404(qs_or_model, **kwargs):
    from django.shortcuts import _get_queryset
    qs = _get_queryset(qs_or_model)
    try:
        return qs.get(**kwargs)
    except qs.model.DoesNotExist:
        raise CommandError(f'{qs.model.__name__} not found: {kwargs}')
    except qs.model.MultipleObjectsReturned:
        raise CommandError(f'Multiple {qs.model.__name__} found: {kwargs}')


class Command(BaseCommand):
    help = 'Full CLI for user management'

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='subcommand', required=True)

        # ── list ──
        p_list = sub.add_parser('list', help='List users')
        p_list.add_argument('--staff', action='store_true', default=None, help='Filter by is_staff')
        p_list.add_argument('--superuser', action='store_true', default=None, help='Filter by is_superuser')
        p_list.add_argument('--setter', action='store_true', default=None, dest='is_setter',
                            help='Filter by display_rank=setter')
        p_list.add_argument('--admin', action='store_true', default=None, dest='is_admin_rank',
                            help='Filter by display_rank=admin')
        p_list.add_argument('--active', action='store_true', default=None, help='Filter by is_active')
        p_list.add_argument('--search', type=str, help='Search by username/email')
        p_list.add_argument('--json', action='store_true', help='JSON output')

        # ── detail ──
        p_detail = sub.add_parser('detail', help='Show user details')
        p_detail.add_argument('username', help='Username')

        # ── promote ──
        p_promote = sub.add_parser('promote', help='Promote a user')
        p_promote.add_argument('username', help='Username')
        p_promote.add_argument('--staff', action='store_true', help='Grant staff access')
        p_promote.add_argument('--superuser', action='store_true', help='Grant superuser access')
        p_promote.add_argument('--setter', action='store_true', dest='setter_rank',
                               help='Set profile rank to Problem Setter')
        p_promote.add_argument('--admin-rank', action='store_true', dest='admin_rank',
                               help='Set profile rank to Admin')

        # ── demote ──
        p_demote = sub.add_parser('demote', help='Demote a user')
        p_demote.add_argument('username', help='Username')
        p_demote.add_argument('--staff', action='store_true', help='Revoke staff access')
        p_demote.add_argument('--superuser', action='store_true', help='Revoke superuser access')

        # ── create ──
        p_create = sub.add_parser('create', help='Create a new user')
        p_create.add_argument('username', help='Username')
        p_create.add_argument('--email', default='', help='Email address')
        p_create.add_argument('--password', default='', help='Password (auto-generated if empty)')
        p_create.add_argument('--staff', action='store_true', help='Grant staff access')
        p_create.add_argument('--superuser', action='store_true', help='Grant superuser access')
        p_create.add_argument('--setter', action='store_true', dest='setter_rank',
                              help='Set profile rank to Problem Setter')

        # ── activate / deactivate ──
        p_activate = sub.add_parser('activate', help='Activate a user')
        p_activate.add_argument('username', help='Username')

        p_deactivate = sub.add_parser('deactivate', help='Deactivate a user')
        p_deactivate.add_argument('username', help='Username')

    def handle(self, *args, **options):
        sub = options['subcommand']
        if sub == 'list':
            self.handle_list(options)
        elif sub == 'detail':
            self.handle_detail(options)
        elif sub == 'create':
            self.handle_create(options)
        elif sub == 'promote':
            self.handle_promote(options)
        elif sub == 'demote':
            self.handle_demote(options)
        elif sub == 'activate':
            self.handle_activate(options)
        elif sub == 'deactivate':
            self.handle_deactivate(options)

    # ════════════════ L I S T ════════════════

    def handle_list(self, opts):
        qs = User.objects.select_related('profile').order_by('username')

        # Role filters: combine multiple role filters as OR
        role_filters = []
        if opts.get('staff') is not None:
            role_filters.append(Q(is_staff=True))
        if opts.get('superuser') is not None:
            role_filters.append(Q(is_superuser=True))
        if opts.get('is_setter') is not None:
            role_filters.append(Q(profile__display_rank='setter'))
        if opts.get('is_admin_rank') is not None:
            role_filters.append(Q(profile__display_rank='admin'))
        if role_filters:
            combined = role_filters[0]
            for rf in role_filters[1:]:
                combined |= rf
            qs = qs.filter(combined)

        if opts.get('active') is not None:
            qs = qs.filter(is_active=opts['active'])
        if opts.get('search'):
            q = opts['search']
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))

        if opts.get('json'):
            data = []
            for u in qs:
                profile = getattr(u, 'profile', None)
                data.append({
                    'username': u.username,
                    'email': u.email or '',
                    'is_staff': u.is_staff,
                    'is_superuser': u.is_superuser,
                    'is_active': u.is_active,
                    'display_rank': profile.display_rank if profile else 'user',
                    'display_rank_label': DISPLAY_RANK_CHOICES.get(profile.display_rank, 'Unknown') if profile else 'Normal User',
                    'date_joined': u.date_joined.isoformat(),
                    'last_login': u.last_login.isoformat() if u.last_login else None,
                    'organizations': [o.name for o in profile.organizations.all()] if profile else [],
                })
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return

        self.stdout.write(f'Users ({qs.count()}):')
        self.stdout.write('─' * 110)
        hdr = f'{"Username":20s} {"Email":30s} {"Active":7s} {"Staff":6s} {"Super":6s} {"Rank":15s} {"Orgs":20s}'
        self.stdout.write(hdr)
        self.stdout.write('─' * 110)
        for u in qs:
            profile = getattr(u, 'profile', None)
            active = '✓' if u.is_active else '✗'
            staff = '✓' if u.is_staff else '✗'
            superuser = '✓' if u.is_superuser else '✗'
            rank = DISPLAY_RANK_CHOICES.get(profile.display_rank, 'user') if profile else 'user'
            orgs = ', '.join(o.name for o in profile.organizations.all()[:2]) if profile else ''
            if profile and profile.organizations.count() > 2:
                orgs += f' ... (+{profile.organizations.count() - 2})'
            self.stdout.write(
                f'{u.username:20s} {(u.email or ""):30s} {active:7s} {staff:6s} {superuser:6s} {rank:15s} {orgs:20s}')

    # ════════════════ D E T A I L ════════════════

    def handle_detail(self, opts):
        u = get_object_or_404(User, username=opts['username'])
        profile = getattr(u, 'profile', None)
        rank_label = DISPLAY_RANK_CHOICES.get(profile.display_rank, 'Normal User') if profile else 'Normal User'
        orgs = ', '.join(o.name for o in profile.organizations.all()) if profile else '(none)'
        perms = list(u.get_all_permissions())
        groups = ', '.join(g.name for g in u.groups.all()) or '(none)'
        solved = profile.problem_count if profile else 0

        self.stdout.write(f'\nUser: {u.username}')
        self.stdout.write('═' * 60)
        self.stdout.write(f'  {"Username":25s} {u.username}')
        self.stdout.write(f'  {"Email":25s} {u.email or "(none)"}')
        self.stdout.write(f'  {"Active":25s} {"✓" if u.is_active else "✗"}')
        self.stdout.write(f'  {"Staff":25s} {"✓" if u.is_staff else "✗"}')
        self.stdout.write(f'  {"Superuser":25s} {"✓" if u.is_superuser else "✗"}')
        self.stdout.write(f'  {"Display Rank":25s} {rank_label} ({profile.display_rank if profile else "N/A"})')
        self.stdout.write(f'  {"Date Joined":25s} {u.date_joined}')
        self.stdout.write(f'  {"Last Login":25s} {u.last_login or "(never)"}')
        if profile:
            self.stdout.write(f'  {"Organizations":25s} {orgs}')
            self.stdout.write(f'  {"Problems Solved":25s} {solved}')
            self.stdout.write(f'  {"Points":25s} {profile.points}')
            self.stdout.write(f'  {"Muted":25s} {"✓" if profile.mute else "✗"}')
            self.stdout.write(f'  {"Unlisted":25s} {"✓" if profile.is_unlisted else "✗"}')
            self.stdout.write(f'  {"Notes":25s} {(profile.notes or "(none)")[:100]}')
            if profile.about:
                self.stdout.write(f'  {"About":25s} {profile.about[:100]}')
        self.stdout.write(f'  {"Groups":25s} {groups}')
        if perms:
            self.stdout.write(f'  {"Permissions":25s} ({len(perms)} total)')
            for p in sorted(perms):
                self.stdout.write(f'  {"":25s} {p}')
        else:
            self.stdout.write(f'  {"Permissions":25s} (none)')

    # ════════════════ C R E A T E ════════════════

    @transaction.atomic
    def handle_create(self, opts):
        username = opts['username']
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User "{username}" already exists.')

        password = opts.get('password') or User.objects.make_random_password(length=12)

        u = User(
            username=username,
            email=opts.get('email', ''),
            is_staff=opts.get('staff', False),
            is_superuser=opts.get('superuser', False),
            is_active=True,
        )
        u.set_password(password)
        u.save()

        # Auto-create profile
        Profile.objects.create(user=u)

        if opts.get('setter_rank'):
            u.profile.display_rank = 'setter'
            u.profile.save(update_fields=['display_rank'])

        result = f'User "{username}" created.'
        if not opts.get('password'):
            result += f' Auto-generated password: {password}'
        self.stdout.write(self.style.SUCCESS(result))

    # ════════════════ P R O M O T E ════════════════

    def handle_promote(self, opts):
        u = get_object_or_404(User, username=opts['username'])
        changed = []

        if opts.get('staff'):
            u.is_staff = True
            changed.append('staff')
        if opts.get('superuser'):
            u.is_superuser = True
            changed.append('superuser')
        if changed:
            u.save()

        profile = getattr(u, 'profile', None)
        if not profile:
            profile = Profile.objects.create(user=u)

        if opts.get('setter_rank'):
            old = profile.display_rank
            profile.display_rank = 'setter'
            profile.save(update_fields=['display_rank'])
            changed.append(f'rank: {old} → setter (Problem Setter)')

        if opts.get('admin_rank'):
            old = profile.display_rank
            profile.display_rank = 'admin'
            profile.save(update_fields=['display_rank'])
            changed.append(f'rank: {old} → admin (Admin)')

        if not changed:
            raise CommandError('No options specified. Use --staff, --superuser, --setter, or --admin-rank.')
        self.stdout.write(self.style.SUCCESS(f'User "{u.username}" promoted: {", ".join(changed)}'))

    # ════════════════ D E M O T E ════════════════

    def handle_demote(self, opts):
        u = get_object_or_404(User, username=opts['username'])
        changed = []

        if opts.get('staff'):
            u.is_staff = False
            changed.append('staff')
        if opts.get('superuser'):
            u.is_superuser = False
            changed.append('superuser')
        if not changed:
            raise CommandError('No options specified. Use --staff, --superuser.')
        u.save()
        self.stdout.write(self.style.SUCCESS(f'User "{u.username}" demoted: {", ".join(changed)}'))

    # ════════════════ A C T I V A T E / D E A C T I V A T E ════════════════

    def handle_activate(self, opts):
        u = get_object_or_404(User, username=opts['username'])
        if u.is_active:
            raise CommandError(f'User "{u.username}" is already active.')
        u.is_active = True
        u.save()
        self.stdout.write(self.style.SUCCESS(f'User "{u.username}" activated.'))

    def handle_deactivate(self, opts):
        u = get_object_or_404(User, username=opts['username'])
        if not u.is_active:
            raise CommandError(f'User "{u.username}" is already inactive.')
        if u.is_superuser:
            raise CommandError(f'Cannot deactivate superuser "{u.username}". Demote first.')
        u.is_active = False
        u.save()
        self.stdout.write(self.style.SUCCESS(f'User "{u.username}" deactivated.'))
