jQuery(function ($) {
    $(document).on('martor:preview', function (e, $content) {
        function update_math() {
            if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
                window.MathJax.typesetPromise([$content[0]]).then(function () {
                    $content.find('.tex-image').hide();
                    $content.find('.tex-text').show();
                });
            } else if (window.MathJax && window.MathJax.Hub && typeof window.MathJax.Hub.Queue === 'function') {
                window.MathJax.Hub.Queue(["Typeset", window.MathJax.Hub, $content[0]], function () {
                    $content.find('.tex-image').hide();
                    $content.find('.tex-text').show();
                });
            } else {
                $content.find('.tex-image').hide();
                $content.find('.tex-text').show();
            }
        }

        var $jax = $content.find('.require-mathjax-support');
        if ($jax.length) {
            if (!('MathJax' in window)) {
                $.ajax({
                    type: 'GET',
                    url: $jax.attr('data-config'),
                    dataType: 'script',
                    cache: true,
                    success: function () {
                        window.MathJax.startup = {typeset: false};
                        $.ajax({
                            type: 'GET',
                            url: '/static/libs/mathjax/tex-chtml.min.js',
                            dataType: 'script',
                            cache: true,
                            success: update_math
                        });
                    }
                });
            } else {
                update_math();
            }
        }
    })
});
