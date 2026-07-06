from martor.widgets import AdminMartorWidget as OldAdminMartorWidget, MartorWidget as OldMartorWidget

__all__ = ['MartorWidget', 'AdminMartorWidget']


class MartorWidget(OldMartorWidget):
    class Media:
        js = ['martor-mathjax.js']


class AdminMartorWidget(OldAdminMartorWidget):
    UPLOADS_ENABLED = True

    @property
    def media(self):
        from django.forms import Media
        super_media = super().media
        
        filtered_css = dict(super_media._css)
        
        # Thêm custom CSS nếu cần
        custom_css = ['martor-description.css', 'featherlight.css']
        if 'all' not in filtered_css:
            filtered_css['all'] = []
        for path in custom_css:
            if path not in filtered_css['all']:
                filtered_css['all'].append(path)
                
        # Thêm custom JavaScript resources
        custom_js = ['admin/js/jquery.init.js', 'martor-mathjax.js', 'libs/featherlight/featherlight.min.js']
        filtered_js = list(super_media._js)
        for path in custom_js:
            if path not in filtered_js:
                filtered_js.append(path)
                
        return Media(css=filtered_css, js=filtered_js)

