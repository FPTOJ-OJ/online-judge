jQuery(function ($) {
    var pendingContents = [];
    $(document).on('martor:preview', function (e, $content) {
        function update_math_element($el) {
            if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
                window.MathJax.typesetPromise([$el[0]]).then(function () {
                    $el.find('.tex-image').hide();
                    $el.find('.tex-text').show();
                });
            } else if (window.MathJax && window.MathJax.Hub && typeof window.MathJax.Hub.Queue === 'function') {
                window.MathJax.Hub.Queue(["Typeset", window.MathJax.Hub, $el[0]], function () {
                    $el.find('.tex-image').hide();
                    $el.find('.tex-text').show();
                });
            } else {
                $el.find('.tex-image').hide();
                $el.find('.tex-text').show();
            }
        }

        var $jax = $content.find('.require-mathjax-support');
        if ($jax.length) {
            if (!('MathJax' in window)) {
                pendingContents.push($content);
                if (!window.MathJaxLoading) {
                    window.MathJaxLoading = true;
                    $.ajax({
                        type: 'GET',
                        url: $jax.attr('data-config'),
                        dataType: 'script',
                        cache: true,
                        success: function () {
                            window.MathJax.startup = {typeset: false};
                            $.ajax({
                                type: 'GET',
                                url: '/static/vendor/mathjax/tex-chtml.min.js',
                                dataType: 'script',
                                cache: true,
                                success: function () {
                                    window.MathJaxLoading = false;
                                    while (pendingContents.length > 0) {
                                        var $pending = pendingContents.shift();
                                        update_math_element($pending);
                                    }
                                },
                                error: function () {
                                    window.MathJaxLoading = false;
                                }
                            });
                        },
                        error: function () {
                            window.MathJaxLoading = false;
                        }
                    });
                }
            } else {
                if (window.MathJaxLoading) {
                    pendingContents.push($content);
                } else {
                    update_math_element($content);
                }
            }
        }
    })
});
