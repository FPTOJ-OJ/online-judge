import hashlib
import urllib.parse
from django.contrib.auth.models import AbstractUser
from django.utils.http import urlencode
from django.conf import settings
from judge.models import Profile
from judge.utils.unicode import utf8bytes
from . import registry

def get_initials_avatar_url(name):
    # Extract initials (e.g. "Kien Core" -> "KC", "John" -> "JO" or "J")
    parts = name.strip().split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1:
        initials = parts[0][:2].upper()
    else:
        initials = "?"

    # Select background color based on name hash
    PASTEL_COLORS = [
        '#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#6366F1', '#8B5CF6', '#EC4899',
        '#F43F5E', '#14B8A6', '#F97316', '#84CC16', '#22C55E', '#06B6D4', '#2563EB'
    ]
    color_index = sum(ord(c) for c in name) % len(PASTEL_COLORS)
    bg_color = PASTEL_COLORS[color_index]

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect width="100" height="100" rx="12" fill="{bg_color}"/>
  <text x="50" y="50" font-family="system-ui, -apple-system, sans-serif" font-size="40" font-weight="bold" fill="#ffffff" text-anchor="middle" dominant-baseline="central">{initials}</text>
</svg>'''
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg_content)

@registry.function
def gravatar(email, size=80, default=None):
    profile = None
    if isinstance(email, Profile):
        profile = email
        if default is None:
            default = profile.mute
        email = profile.user.email
    elif isinstance(email, AbstractUser):
        try:
            profile = email.profile
        except Profile.DoesNotExist:
            profile = None
        email = email.email
    else:
        # It's an email string. Let's try to find the Profile.
        try:
            profile = Profile.objects.get(user__email=email)
        except (Profile.DoesNotExist, Profile.MultipleObjectsReturned):
            profile = None

    # Check for custom uploaded avatar
    if profile and profile.avatar:
        return settings.AVATAR_URL_PREFIX + profile.avatar

    # Fallback to initials avatar if no custom avatar is present
    if profile:
        name = profile.username_display_override or profile.user.username
        return get_initials_avatar_url(name)
    elif email:
        name = email.split('@')[0]
        return get_initials_avatar_url(name)

    return get_initials_avatar_url("?")
