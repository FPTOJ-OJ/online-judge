import re

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from judge.models.profile import Profile

__all__ = ['MiscConfig', 'validate_regex', 'NavigationBar', 'BlogPost', 'SiteConfiguration']


class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=100, default='DMOJ: Modern Online Judge', verbose_name=_('Site Name'))
    site_short_name = models.CharField(max_length=20, default='DMOJ', verbose_name=_('Site Short Name'))
    logo = models.ImageField(upload_to='site_logo/', null=True, blank=True, verbose_name=_('Logo Image'))
    favicon = models.FileField(upload_to='site_favicon/', null=True, blank=True, verbose_name=_('Favicon'))
    welcome_message = models.TextField(blank=True, default='', verbose_name=_('Welcome Message (Markdown)'))
    meta_description = models.TextField(blank=True, default='', verbose_name=_('Meta Description'))
    meta_keywords = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Meta Keywords'))
    quiz_enabled = models.BooleanField(default=True, verbose_name=_('Enable Quiz/Exam Features'))
    logo_style = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Logo Custom Inline CSS'), help_text=_('Example: width: 120px; height: auto; margin-top: -2px;'))
    custom_css = models.TextField(blank=True, default='', verbose_name=_('Custom CSS'), help_text=_('Custom CSS rules to apply across the site.'))
    footer_text = models.TextField(blank=True, default='', verbose_name=_('Custom Footer HTML'), help_text=_('Custom HTML content to display in the footer.'))
    footer_override = models.BooleanField(default=False, verbose_name=_('Override Default Footer'), help_text=_('If checked, only the Custom Footer HTML will be displayed, replacing the default footer text.'))
    custom_js = models.TextField(blank=True, default='', verbose_name=_('Custom Javascript'), help_text=_('Custom JavaScript or script tags to inject before </body>.'))

    class Meta:
        verbose_name = _('Site Configuration')
        verbose_name_plural = _('Site Configurations')

    def __str__(self):
        return str(_("Site Configuration"))

    def save(self, *args, **kwargs):
        # Optimize logo if it's newly uploaded and not an SVG
        if self.logo:
            from django.core.files.uploadedfile import UploadedFile
            if isinstance(self.logo.file, UploadedFile):
                name = self.logo.name.lower()
                if not name.endswith('.svg'):
                    from PIL import Image
                    import io
                    from django.core.files.base import ContentFile
                    import os
                    try:
                        img = Image.open(self.logo.file)
                        if img.mode not in ('RGB', 'RGBA'):
                            img = img.convert('RGBA')
                        img.thumbnail((600, 150), Image.Resampling.LANCZOS)
                        out_buf = io.BytesIO()
                        img.save(out_buf, format='PNG', optimize=True)
                        new_name = os.path.basename(self.logo.name)
                        if not new_name.lower().endswith('.png'):
                            new_name = os.path.splitext(new_name)[0] + '.png'
                        self.logo.save(new_name, ContentFile(out_buf.getvalue()), save=False)
                    except Exception as e:
                        pass

        if self.favicon:
            from django.core.files.uploadedfile import UploadedFile
            if isinstance(self.favicon.file, UploadedFile):
                name = self.favicon.name.lower()
                if not name.endswith('.svg') and not name.endswith('.ico'):
                    from PIL import Image
                    import io
                    from django.core.files.base import ContentFile
                    import os
                    try:
                        img = Image.open(self.favicon.file)
                        if img.mode not in ('RGB', 'RGBA'):
                            img = img.convert('RGBA')
                        img.thumbnail((128, 128), Image.Resampling.LANCZOS)
                        out_buf = io.BytesIO()
                        img.save(out_buf, format='PNG', optimize=True)
                        new_name = os.path.basename(self.favicon.name)
                        if not new_name.lower().endswith('.png'):
                            new_name = os.path.splitext(new_name)[0] + '.png'
                        self.favicon.save(new_name, ContentFile(out_buf.getvalue()), save=False)
                    except Exception as e:
                        pass

        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj



class MiscConfig(models.Model):
    key = models.CharField(max_length=30, verbose_name=_('key'), db_index=True)
    value = models.TextField(verbose_name=_('value'), blank=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = _('configuration item')
        verbose_name_plural = _('miscellaneous configuration')


def validate_regex(regex):
    try:
        re.compile(regex, re.VERBOSE)
    except re.error as e:
        raise ValidationError('Invalid regex: %s' % e.message)


class NavigationBar(MPTTModel):
    class Meta:
        verbose_name = _('navigation item')
        verbose_name_plural = _('navigation bar')

    class MPTTMeta:
        order_insertion_by = ['order']

    order = models.PositiveIntegerField(db_index=True, verbose_name=_('order'))
    key = models.CharField(max_length=10, unique=True, verbose_name=_('identifier'))
    label = models.CharField(max_length=20, verbose_name=_('label'))
    path = models.CharField(max_length=255, verbose_name=_('link path'))
    regex = models.TextField(verbose_name=_('highlight regex'), validators=[validate_regex])
    parent = TreeForeignKey('self', verbose_name=_('parent item'), null=True, blank=True,
                            related_name='children', on_delete=models.CASCADE)

    def __str__(self):
        return self.label

    @property
    def pattern(self, cache={}):
        # A cache with a bad policy is an alias for memory leak
        # Thankfully, there will never be too many regexes to cache.
        if self.regex in cache:
            return cache[self.regex]
        else:
            pattern = cache[self.regex] = re.compile(self.regex, re.VERBOSE)
            return pattern


class BlogPost(models.Model):
    title = models.CharField(verbose_name=_('post title'), max_length=100)
    authors = models.ManyToManyField(Profile, verbose_name=_('authors'), blank=True)
    slug = models.SlugField(verbose_name=_('slug'))
    visible = models.BooleanField(verbose_name=_('public visibility'), default=False)
    sticky = models.BooleanField(verbose_name=_('sticky'), default=False)
    publish_on = models.DateTimeField(verbose_name=_('publish after'))
    content = models.TextField(verbose_name=_('post content'))
    summary = models.TextField(verbose_name=_('post summary'), blank=True)
    og_image = models.CharField(verbose_name=_('OpenGraph image'), default='', max_length=150, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_post', args=(self.id, self.slug))

    def can_see(self, user):
        if self.visible and self.publish_on <= timezone.now():
            return True
        return self.is_editable_by(user)

    def is_editable_by(self, user):
        if not user.is_authenticated:
            return False
        if user.has_perm('judge.edit_all_post'):
            return True
        return user.has_perm('judge.change_blogpost') and self.authors.filter(id=user.profile.id).exists()

    class Meta:
        permissions = (
            ('edit_all_post', _('Edit all posts')),
            ('change_post_visibility', _('Edit post visibility')),
        )
        verbose_name = _('blog post')
        verbose_name_plural = _('blog posts')
