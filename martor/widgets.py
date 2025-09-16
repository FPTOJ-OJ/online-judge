from django import forms
from django.contrib.admin import widgets
from django.template.loader import get_template

from .settings import (
    MARTOR_ENABLE_CONFIGS,
    MARTOR_MARKDOWNIFY_URL,
    MARTOR_SEARCH_USERS_URL,
    MARTOR_UPLOAD_URL,
)


class MartorWidget(forms.Textarea):
    UPLOADS_ENABLED = True

    def render(self, name, value, attrs=None, renderer=None, **kwargs):
        attributes_to_pass = {
            'data-enable-configs': MARTOR_ENABLE_CONFIGS,
            'data-upload-url': MARTOR_UPLOAD_URL,
            'data-markdownfy-url': MARTOR_MARKDOWNIFY_URL,
            'data-search-users-url': MARTOR_SEARCH_USERS_URL,
        }

        if 'class' in attrs:
            attrs['class'] += ' martor'
        else:
            attrs['class'] = 'martor'

        attributes_to_pass.update(attrs)
        attributes_to_pass.update(self.attrs)

        widget = super(MartorWidget, self).render(name, value, attributes_to_pass)

        template = get_template('martor/editor.html')
        mentions_enabled = MARTOR_ENABLE_CONFIGS.get('mention') == 'true'

        return template.render({
            'martor': widget,
            'field_name': name,
            'mentions_enabled': mentions_enabled,
            'uploads_enabled': self.UPLOADS_ENABLED,
        })

    class Media:
        css = {
            'all': (
                'plugins/css/ace.min.css',
                'plugins/css/semantic.css',
                'plugins/css/resizable.min.css',
                'martor/css/ckeditor.css',
            ),
        }
        js = (
            'plugins/js/ace.js',
            'plugins/js/semantic.min.js',
            'plugins/js/mode-markdown.js',
            'plugins/js/ext-language_tools.js',
            'plugins/js/theme-github.js',
            'plugins/js/theme-twilight.js',
            'plugins/js/highlight.min.js',
            'plugins/js/resizable.min.js',
            'martor/js/martor.js',
        )



class AdminMartorWidget(MartorWidget, widgets.AdminTextareaWidget):
    pass
