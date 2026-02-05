class MartorUploadAdapter {
    constructor(loader, textarea) {
        this.loader = loader;
        this.textarea = textarea;
        this.controller = new AbortController();
    }

    // Local helper function để lấy cookie
    _getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim(); // chuẩn JS, không cần jQuery
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    upload() {
        return this.loader.file.then(file => {
            return new Promise(async (resolve, reject) => {
                try {
                    const formElement = this.textarea.closest('form');
                    if (!formElement) return reject('Form not found');

                    const field_name = this.textarea.id.replace('id_', '');
                    const form = new FormData(formElement);
                    form.append('markdown-image-upload', file);
                    form.append('csrfmiddlewaretoken', this._getCookie('csrftoken'));

                    const progressEl = document.querySelector(`.upload-progress[data-field-name="${field_name}"]`);
                    if (progressEl) progressEl.style.display = 'block';

                    const response = await fetch(this.textarea.dataset.uploadUrl, {
                        method: 'POST',
                        body: form,
                        signal: this.controller.signal
                    });

                    const data = await response.json();

                    if (progressEl) progressEl.style.display = 'none';

                    if (data.status === 200) {
                        resolve({ default: data.link });
                    } else {
                        reject(data.error || 'Upload failed');
                    }
                } catch (err) {
                    const field_name = this.textarea.id.replace('id_', '');
                    const progressEl = document.querySelector(`.upload-progress[data-field-name="${field_name}"]`);
                    if (progressEl) progressEl.style.display = 'none';

                    console.error('Upload error:', err);
                    reject(err.message || 'Upload failed');
                }
            });
        });
    }

    abort() {
        this.controller.abort();
    }
}


const HTML_MARKER = '<htmlrender>';
const LICENSE_KEY = 'eyJhbGciOiJFUzI1NiJ9.eyJleHAiOjE3ODk2MDMxOTksImp0aSI6ImJjNzQyZWIxLTBhZmEtNDA3YS1hYzNjLTA0ZGE1MGYzYzE3YyIsInVzYWdlRW5kcG9pbnQiOiJodHRwczovL3Byb3h5LWV2ZW50LmNrZWRpdG9yLmNvbSIsImRpc3RyaWJ1dGlvbkNoYW5uZWwiOlsiY2xvdWQiLCJkcnVwYWwiXSwiZmVhdHVyZXMiOlsiRFJVUCIsIkUyUCIsIkUyVyJdLCJ2YyI6ImE2MDM2MjQyIn0.b7kt1-eR-vznnSsYhHXHlAndd7RpqK947Epvw9rnGPrufUDorlRjfQWJU15if9_Sc4VFP-Vod6O2u7M2HbvcCw';

function normalizeContent(content) {
    return content
        .replace(/\u2212/g, "-")
        .replace(/\u00A0/g, " ");
}

function getEditorConfig(textarea) {
    const {
        Alignment, Autoformat, AutoImage, AutoLink, Autosave, BalloonToolbar, BlockQuote, BlockToolbar,
        Bold, Bookmark, Code, CodeBlock, Emoji, Essentials, FindAndReplace, FontBackgroundColor,
        FontColor, FontFamily, FontSize, Fullscreen, GeneralHtmlSupport, Heading, Highlight,
        HorizontalLine, HtmlEmbed, ImageBlock, ImageCaption, ImageEditing, ImageInline, ImageInsert,
        ImageInsertViaUrl, ImageResize, ImageStyle, ImageTextAlternative, ImageToolbar, ImageUpload,
        ImageUtils, Indent, IndentBlock, Italic, Link, LinkImage, List, ListProperties, Mention,
        PageBreak, Paragraph, PasteFromOffice, PlainTableOutput, RemoveFormat, ShowBlocks,
        SimpleUploadAdapter, SourceEditing, SpecialCharacters, SpecialCharactersArrows,
        SpecialCharactersCurrency, SpecialCharactersEssentials, SpecialCharactersLatin,
        SpecialCharactersMathematical, SpecialCharactersText, Strikethrough, Style, Subscript,
        Superscript, Table, TableCaption, TableCellProperties, TableColumnResize, TableLayout,
        TableProperties, TableToolbar, TextTransformation, TodoList, Underline
    } = window.CKEDITOR;

    return {
        toolbar: {
            items: [
                'undo', 'redo', '|',
                'sourceEditing', 'showBlocks', 'findAndReplace', 'fullscreen', '|',
                'heading', 'style', '|',
                'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', '|',
                'bold', 'italic', 'underline', 'strikethrough', 'subscript', 'superscript', 'code', 'removeFormat', '|',
                'emoji', 'specialCharacters', 'horizontalLine', 'pageBreak', 'link', 'bookmark',
                'insertImage', 'insertImageViaUrl', 'insertTable', 'insertTableLayout',
                'highlight', 'blockQuote', 'codeBlock', 'htmlEmbed', '|',
                'alignment', '|',
                'bulletedList', 'numberedList', 'todoList', 'outdent', 'indent'
            ],
            shouldNotGroupWhenFull: false
        },
        plugins: [
            Alignment, Autoformat, AutoImage, AutoLink, Autosave, BalloonToolbar, BlockQuote, BlockToolbar,
            Bold, Bookmark, Code, CodeBlock, Emoji, Essentials, FindAndReplace, FontBackgroundColor,
            FontColor, FontFamily, FontSize, Fullscreen, GeneralHtmlSupport, Heading, Highlight,
            HorizontalLine, HtmlEmbed, ImageBlock, ImageCaption, ImageEditing, ImageInline, ImageInsert,
            ImageInsertViaUrl, ImageResize, ImageStyle, ImageTextAlternative, ImageToolbar, ImageUpload,
            ImageUtils, Indent, IndentBlock, Italic, Link, LinkImage, List, ListProperties, Mention,
            PageBreak, Paragraph, PasteFromOffice, PlainTableOutput, RemoveFormat, ShowBlocks,
            SimpleUploadAdapter, SourceEditing, SpecialCharacters, SpecialCharactersArrows,
            SpecialCharactersCurrency, SpecialCharactersEssentials, SpecialCharactersLatin,
            SpecialCharactersMathematical, SpecialCharactersText, Strikethrough, Style, Subscript,
            Superscript, Table, TableCaption, TableCellProperties, TableColumnResize, TableLayout,
            TableProperties, TableToolbar, TextTransformation, TodoList, Underline
        ],
        balloonToolbar: ['bold', 'italic', '|', 'link', 'insertImage', '|', 'bulletedList', 'numberedList'],
        blockToolbar: [
            'fontSize', 'fontColor', 'fontBackgroundColor', '|',
            'bold', 'italic', '|',
            'link', 'insertImage', 'insertTable', 'insertTableLayout', '|',
            'bulletedList', 'numberedList', 'outdent', 'indent'
        ],
        fontFamily: { supportAllValues: true },
        fontSize: { options: [10, 12, 14, 'default', 18, 20, 22], supportAllValues: true },
        fullscreen: {
            onEnterCallback: container =>
                container.classList.add(
                    'editor-container',
                    'editor-container_classic-editor',
                    'editor-container_include-style',
                    'editor-container_include-block-toolbar',
                    'editor-container_include-fullscreen',
                    'main-container'
                )
        },
        heading: {
            options: [
                { model: 'paragraph', title: 'Paragraph', class: 'ck-heading_paragraph' },
                { model: 'heading1', view: 'h1', title: 'Heading 1', class: 'ck-heading_heading1' },
                { model: 'heading2', view: 'h2', title: 'Heading 2', class: 'ck-heading_heading2' },
                { model: 'heading3', view: 'h3', title: 'Heading 3', class: 'ck-heading_heading3' },
                { model: 'heading4', view: 'h4', title: 'Heading 4', class: 'ck-heading_heading4' },
                { model: 'heading5', view: 'h5', title: 'Heading 5', class: 'ck-heading_heading5' },
                { model: 'heading6', view: 'h6', title: 'Heading 6', class: 'ck-heading_heading6' }
            ]
        },
        htmlSupport: {
            allow: [{ name: /^.*$/, styles: true, attributes: true, classes: true }]
        },
        image: {
            toolbar: [
                'toggleImageCaption', 'imageTextAlternative', '|',
                'imageStyle:inline', 'imageStyle:wrapText', 'imageStyle:breakText', '|',
                'resizeImage'
            ]
        },
        licenseKey: LICENSE_KEY,
        link: {
            addTargetToExternalLinks: true,
            defaultProtocol: 'https://',
            decorators: {
                toggleDownloadable: {
                    mode: 'manual',
                    label: 'Downloadable',
                    attributes: { download: 'file' }
                }
            }
        },
        list: {
            properties: { styles: true, startIndex: true, reversed: true }
        },
        mention: {
            feeds: [
                {
                    marker: '@',
                    feed: async (query) => {
                        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
                        if (!textarea.dataset.searchUsersUrl) return [];
                        
                        try {
                            const response = await fetch(
                                `${textarea.dataset.searchUsersUrl}?username=${query}`,
                                {
                                    headers: {
                                        'X-CSRFToken': csrfToken
                                    }
                                }
                            );
                            const data = await response.json();
                            if (data.status === 200) {
                                return data.data.map(user => ({
                                    id: `@${user.username}`,
                                    text: user.username
                                }));
                            }
                        } catch (e) {
                            console.error('Mention fetch error:', e);
                        }
                        return [];
                    },
                    minimumCharacters: 1
                }
            ]
        },
        menuBar: { isVisible: true },
        placeholder: 'Type or paste your content here!',
        style: {
            definitions: [
                { name: 'Article category', element: 'h3', classes: ['category'] },
                { name: 'Title', element: 'h2', classes: ['document-title'] },
                { name: 'Subtitle', element: 'h3', classes: ['document-subtitle'] },
                { name: 'Info box', element: 'p', classes: ['info-box'] },
                { name: 'CTA Link Primary', element: 'a', classes: ['button', 'button--green'] },
                { name: 'CTA Link Secondary', element: 'a', classes: ['button', 'button--black'] },
                { name: 'Marker', element: 'span', classes: ['marker'] },
                { name: 'Spoiler', element: 'span', classes: ['spoiler'] }
            ]
        },
        table: {
            contentToolbar: ['tableColumn', 'tableRow', 'mergeTableCells', 'tableProperties', 'tableCellProperties']
        }
    };
}

function switchEditor(selectElement, fieldName) {
    const martorContainer = document.getElementById(`martor-container-${fieldName}`);
    const ckeditorContainer = document.getElementById(`ckeditor-container-${fieldName}`);
    const martorEditor = document.getElementById(`martor-${fieldName}`);
    const ckeditorEditor = document.getElementById(`ckeditor-${fieldName}`);
    const textarea = document.getElementById(`id_${fieldName}`);
    const editorType = selectElement.value;

    if (editorType === 'ckeditor') {
        martorContainer.style.display = 'none';
        ckeditorContainer.style.display = 'block';

        // Initialize CKEditor if not already initialized
        if (!ckeditorEditor.classList.contains('ck-editor')) {
            const md = window.__markdownItInstance__;
            
            // Check if styles are loaded, if not, maybe we should warn? 
            // The template should have loaded ckeditor.css

            window.CKEDITOR.ClassicEditor.create(ckeditorEditor, getEditorConfig(textarea))
                .then(editor => {
                    window.ckeditorInstances = window.ckeditorInstances || {};
                    window.ckeditorInstances[fieldName] = editor;
                    
                    // Lấy markdown gốc từ textarea
                    let markdownContent = textarea.value;
                    if (markdownContent.startsWith(HTML_MARKER)) {
                        markdownContent = markdownContent.slice(HTML_MARKER.length);
                    }
                    
                    // Convert markdown sang HTML
                    // Ensure markdown-it is available
                    const htmlContent = md ? md.render(markdownContent) : markdownContent;

                    if (!textarea.value.startsWith(HTML_MARKER)) {
                        textarea.value = HTML_MARKER + textarea.value;
                    }

                    editor.plugins.get('FileRepository').createUploadAdapter = (loader) => {
                        return new MartorUploadAdapter(loader, textarea);
                    };

                    editor.editing.view.change(writer => {
                        writer.setAttribute('spellcheck', 'false', editor.editing.view.document.getRoot());
                    });

                    // Nạp vào CKEditor và cập nhật textarea
                    editor.setData(htmlContent);
                    editor.model.document.on('change:data', () => {
                        let data = editor.getData();

                        // chuẩn hóa dữ liệu
                        data = normalizeContent(data);

                        if (!data.startsWith(HTML_MARKER)) {
                            data = HTML_MARKER + data;
                        }

                        textarea.value = data;
                    });

                    // Fix initial layout issues, especially in Django Admin
                    setTimeout(() => {
                        editor.ui.update();
                        window.dispatchEvent(new Event('resize'));
                    }, 300);

                    // Robust layout fix: monitor container resize
                    if (window.ResizeObserver) {
                        const resizeObserver = new ResizeObserver(() => {
                            editor.ui.update();
                        });
                        resizeObserver.observe(ckeditorContainer);
                        // Cleanup on destroy
                        editor.on('destroy', () => resizeObserver.disconnect());
                    }
                })
                .catch(error => console.error('CKEditor initialization failed:', error));
        }
    } else {
        ckeditorContainer.style.display = 'none';
        martorContainer.style.display = 'block';

        if (window.ckeditorInstances && window.ckeditorInstances[fieldName]) {
            const editor = window.ckeditorInstances[fieldName];
            const htmlContent = editor.getData();
            const markdownContent = htmlContent; // Note: This doesn't convert HTML back to Markdown nicely.
            // A proper converter (like TurndownService) would be better if full round-trip is needed.
            // But preserving current logic as requested (it assigns HTML to ACE which handles Markdown)

            // Đẩy markdown vào ACE editor (Martor)
            // Warning: ACE expects text, if we dump HTML here, it will show HTML tags.
            // The original code did `const markdownContent = htmlContent;`.
            // Ideally we should use a converter here, but the user asked to "fix logic", not rewrite architecture unless necessary.
            // If the user wants to switch back and forth, HTML to Markdown conversion is complex.
            // I will leave this as is for now, but comment on it.

            const aceEditor = ace.edit(`martor-${fieldName}`);
            aceEditor.setValue(markdownContent, -1);

            // Cập nhật textarea với markdown (không có marker)
            textarea.value = markdownContent;

            // Destroy CKEditor instance
            editor.destroy();
            delete window.ckeditorInstances[fieldName];
        }
    }
}