const HTML_MARKER = '<htmlrender>';

const {
    ClassicEditor,
    Alignment,
    Autoformat,
    AutoImage,
    AutoLink,
    Autosave,
    BalloonToolbar,
    BlockQuote,
    BlockToolbar,
    Bold,
    Bookmark,
    Code,
    CodeBlock,
    Emoji,
    Essentials,
    FindAndReplace,
    FontBackgroundColor,
    FontColor,
    FontFamily,
    FontSize,
    Fullscreen,
    GeneralHtmlSupport,
    Heading,
    Highlight,
    HorizontalLine,
    HtmlEmbed,
    ImageBlock,
    ImageCaption,
    ImageEditing,
    ImageInline,
    ImageInsert,
    ImageInsertViaUrl,
    ImageResize,
    ImageStyle,
    ImageTextAlternative,
    ImageToolbar,
    ImageUpload,
    ImageUtils,
    Indent,
    IndentBlock,
    Italic,
    Link,
    LinkImage,
    List,
    ListProperties,
    MediaEmbed,
    Mention,
    PageBreak,
    Paragraph,
    PasteFromMarkdownExperimental,
    PasteFromOffice,
    PlainTableOutput,
    RemoveFormat,
    ShowBlocks,
    SimpleUploadAdapter,
    SourceEditing,
    SpecialCharacters,
    SpecialCharactersArrows,
    SpecialCharactersCurrency,
    SpecialCharactersEssentials,
    SpecialCharactersLatin,
    SpecialCharactersMathematical,
    SpecialCharactersText,
    Strikethrough,
    Style,
    Subscript,
    Superscript,
    Table,
    TableCaption,
    TableCellProperties,
    TableColumnResize,
    TableLayout,
    TableProperties,
    TableToolbar,
    TextTransformation,
    TodoList,
    Underline
} = window.CKEDITOR;

const LICENSE_KEY =
    'eyJhbGciOiJFUzI1NiJ9.eyJleHAiOjE3ODk2MDMxOTksImp0aSI6ImJjNzQyZWIxLTBhZmEtNDA3YS1hYzNjLTA0ZGE1MGYzYzE3YyIsInVzYWdlRW5kcG9pbnQiOiJodHRwczovL3Byb3h5LWV2ZW50LmNrZWRpdG9yLmNvbSIsImRpc3RyaWJ1dGlvbkNoYW5uZWwiOlsiY2xvdWQiLCJkcnVwYWwiXSwiZmVhdHVyZXMiOlsiRFJVUCIsIkUyUCIsIkUyVyJdLCJ2YyI6ImE2MDM2MjQyIn0.b7kt1-eR-vznnSsYhHXHlAndd7RpqK947Epvw9rnGPrufUDorlRjfQWJU15if9_Sc4VFP-Vod6O2u7M2HbvcCw';

function switchEditor(selectElement, fieldName) {
    const martorContainer = document.getElementById(`martor-container-${fieldName}`);
    const ckeditorContainer = document.getElementById(`ckeditor-container-${fieldName}`);
    const martorEditor = document.getElementById(`martor-${fieldName}`);
    const ckeditorEditor = document.getElementById(`ckeditor-${fieldName}`);
    const textareaId = document.getElementById(`id_${fieldName}`);
    const editorType = selectElement.value;

    if (editorType === 'ckeditor') {
        martorContainer.style.display = 'none';
        ckeditorContainer.style.display = 'block';

        // Initialize CKEditor if not already initialized
        if (!ckeditorEditor.classList.contains('ck-editor')) {
            const editorConfig = {
                toolbar: {
                    items: [
                        'undo', 'redo', '|',
                        'sourceEditing', 'showBlocks', 'findAndReplace', 'fullscreen', '|',
                        'heading', 'style', '|',
                        'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', '|',
                        'bold', 'italic', 'underline', 'strikethrough', 'subscript', 'superscript', 'code', 'removeFormat', '|',
                        'emoji', 'specialCharacters', 'horizontalLine', 'pageBreak', 'link', 'bookmark',
                        'insertImage', 'insertImageViaUrl', 'mediaEmbed', 'insertTable', 'insertTableLayout',
                        'highlight', 'blockQuote', 'codeBlock', 'htmlEmbed', '|',
                        'alignment', '|',
                        'bulletedList', 'numberedList', 'todoList', 'outdent', 'indent'
                    ],
                    shouldNotGroupWhenFull: false
                },
                plugins: [
                    Alignment,
                    Autoformat,
                    AutoImage,
                    AutoLink,
                    Autosave,
                    BalloonToolbar,
                    BlockQuote,
                    BlockToolbar,
                    Bold,
                    Bookmark,
                    Code,
                    CodeBlock,
                    Emoji,
                    Essentials,
                    FindAndReplace,
                    FontBackgroundColor,
                    FontColor,
                    FontFamily,
                    FontSize,
                    Fullscreen,
                    GeneralHtmlSupport,
                    Heading,
                    Highlight,
                    HorizontalLine,
                    HtmlEmbed,
                    ImageBlock,
                    ImageCaption,
                    ImageEditing,
                    ImageInline,
                    ImageInsert,
                    ImageInsertViaUrl,
                    ImageResize,
                    ImageStyle,
                    ImageTextAlternative,
                    ImageToolbar,
                    ImageUpload,
                    ImageUtils,
                    Indent,
                    IndentBlock,
                    Italic,
                    Link,
                    LinkImage,
                    List,
                    ListProperties,
                    MediaEmbed,
                    Mention,
                    PageBreak,
                    Paragraph,
                    PasteFromMarkdownExperimental,
                    PasteFromOffice,
                    PlainTableOutput,
                    RemoveFormat,
                    ShowBlocks,
                    SimpleUploadAdapter,
                    SourceEditing,
                    SpecialCharacters,
                    SpecialCharactersArrows,
                    SpecialCharactersCurrency,
                    SpecialCharactersEssentials,
                    SpecialCharactersLatin,
                    SpecialCharactersMathematical,
                    SpecialCharactersText,
                    Strikethrough,
                    Style,
                    Subscript,
                    Superscript,
                    Table,
                    TableCaption,
                    TableCellProperties,
                    TableColumnResize,
                    TableLayout,
                    TableProperties,
                    TableToolbar,
                    TextTransformation,
                    TodoList,
                    Underline
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
                                const response = await fetch(
                                    `${textareaId.dataset.searchUsersUrl}?username=${query}`,
                                    {
                                        headers: {
                                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                                        }
                                    }
                                );
                                const data = await response.json();
                                if (data.status === 200) {
                                    return data.data.map(user => ({
                                        id: `@${user.username}`,  // bắt buộc có @ ở đầu
                                        text: user.username       // label hiển thị
                                    }));
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
                },
                simpleUpload: {
                    uploadUrl: textareaId.dataset.uploadUrl, // Use Martor's upload URL
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                }
            };
            const converter = new showdown.Converter();

            ClassicEditor.create(ckeditorEditor, editorConfig)
                .then(editor => {
                    window.ckeditorInstances = window.ckeditorInstances || {};
                    window.ckeditorInstances[fieldName] = editor;
                    // Lấy markdown gốc từ textarea
                   
                    markdownContent = textareaId.value;
                    if (markdownContent.startsWith(HTML_MARKER)) {
                        markdownContent = markdownContent.slice(HTML_MARKER.length);
                    }
                    // Convert markdown sang HTML
                    const htmlContent = converter.makeHtml(markdownContent);
                    
                    if(!textareaId.value.startsWith(HTML_MARKER)){
                        textareaId.value = HTML_MARKER + textareaId.value;
                    }

                    // Nạp vào CKEditor
                    editor.setData(htmlContent);
                    editor.model.document.on('change:data', () => {
                        textareaId.value = editor.getData();
                        if(!textareaId.value.startsWith(HTML_MARKER)){
                            textareaId.value = HTML_MARKER + textareaId.value;
                        }
                    });
                    setTimeout(() => editor.ui.update(), 50);
                })
                .catch(error => console.error('CKEditor initialization failed:', error));
        }
    } else {
        ckeditorContainer.style.display = 'none';
        martorContainer.style.display = 'block';

        if (window.ckeditorInstances && window.ckeditorInstances[fieldName]) {
            const editor = window.ckeditorInstances[fieldName];
            const htmlContent = editor.getData();
            // Đẩy thẳng HTML vào ACE editor
            const aceEditor = ace.edit(`martor-${fieldName}`);
            aceEditor.setValue(htmlContent, -1);

            // Cập nhật textarea ẩn (để form submit có HTML)
            textareaId.value = htmlContent;
            if (textareaId.value.startsWith(HTML_MARKER)) {
                textareaId.value = textareaId.value.slice(HTML_MARKER.length);
            }

            // Destroy CKEditor instance
            editor.destroy();
            delete window.ckeditorInstances[fieldName];
        }
    }
}