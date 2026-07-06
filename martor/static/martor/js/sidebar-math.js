/**
 * Name         : MathLive Sidebar Editor v1.0
 * Created by   : Ha Tri Kien
 * License      : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
 * REQ          : <script src="https://unpkg.com/mathlive@0.107.0/mathlive.min.js"></script>
 **/
!function () {
    // 1. Inject Styles Immediately
    const styleElement = document.createElement("style");
    styleElement.textContent = `
        /* Math Keyboard Fix */
        .ML__keyboard {
            z-index: 10000000000 !important;
        }

        /* Spinner Animation */
        @keyframes math-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .math-loading-spinner {
            animation: math-spin 1s linear infinite;
        }

        /* Sidebar Toggle Button */
        .math-sidebar-toggle {
            position: fixed;
            bottom: 30px;
            right: 20px;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #ffffff;
            font-size: 22px;
            font-family: "Outfit", "Inter", system-ui, -apple-system, sans-serif;
            border: none;
            cursor: pointer;
            z-index: 10000000;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .math-sidebar-toggle:hover {
            transform: scale(1.08) rotate(8deg);
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.6);
        }
        .math-sidebar-toggle:active {
            transform: scale(0.95);
        }

        /* Sidebar Container */
        .math-sidebar-container {
            position: fixed;
            top: 0;
            right: 0;
            height: 100%;
            width: 320px;
            background: #ffffff;
            box-shadow: -10px 0 30px rgba(0, 0, 0, 0.08);
            transform: translateX(110%);
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.3s ease;
            display: none;
            flex-direction: column;
            color: #1f2937;
            z-index: 10000000;
            border-left: 1px solid #e5e7eb;
            font-family: "Inter", system-ui, -apple-system, sans-serif;
        }
        .math-sidebar-container.open {
            display: flex;
            transform: translateX(0);
        }

        /* Resize Handles */
        .math-sidebar-resizer-w {
            width: 8px;
            height: 100%;
            position: absolute;
            left: -4px;
            top: 0;
            cursor: ew-resize;
            z-index: 10;
            transition: background-color 0.2s;
        }
        .math-sidebar-resizer-w:hover {
            background-color: rgba(37, 99, 235, 0.15);
        }
        .math-sidebar-resizer-h {
            width: 100%;
            height: 8px;
            cursor: ns-resize;
            z-index: 10;
            background-color: #f3f4f6;
            border-top: 1px solid #e5e7eb;
            transition: background-color 0.2s;
        }
        .math-sidebar-resizer-h:hover {
            background-color: rgba(37, 99, 235, 0.15);
        }

        /* Header */
        .math-sidebar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid #f3f4f6;
        }
        .math-sidebar-header h5 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #111827;
        }

        /* Dark Mode Toggle Button */
        .math-sidebar-dark-toggle {
            background: none !important;
            border: none !important;
            cursor: pointer !important;
            color: #6b7280 !important;
            padding: 6px !important;
            border-radius: 8px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: background-color 0.2s, color 0.2s !important;
            box-shadow: none !important;
            width: auto !important;
            height: auto !important;
        }
        .math-sidebar-dark-toggle:hover {
            background-color: #f3f4f6 !important;
            color: #111827 !important;
        }

        /* Tab Controls */
        .math-sidebar-tabs {
            display: flex !important;
            padding: 4px !important;
            background: #f3f4f6 !important;
            margin: 16px 20px !important;
            border-radius: 8px !important;
            gap: 4px !important;
        }
        .math-sidebar-tab-btn {
            flex: 1 !important;
            padding: 8px !important;
            border: none !important;
            background: transparent !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            color: #4b5563 !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 6px !important;
            box-shadow: none !important;
            width: auto !important;
            height: auto !important;
            line-height: normal !important;
        }
        .math-sidebar-tab-btn.active {
            background: #ffffff !important;
            color: #2563eb !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
        }

        /* Scrollable Body */
        .math-sidebar-body {
            flex: 1;
            padding: 0 20px 20px 20px;
            overflow-y: auto;
            box-sizing: border-box;
        }

        /* Form Group */
        .math-sidebar-group {
            margin-bottom: 16px;
        }
        .math-sidebar-label {
            display: block;
            font-size: 11px;
            font-weight: 600;
            color: #4b5563;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Math Input Area */
        .math-input-wrapper {
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 10px;
            background: #ffffff;
            transition: border-color 0.2s, box-shadow 0.2s;
            box-sizing: border-box;
        }
        .math-input-wrapper:focus-within {
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }
        .math-input-wrapper math-field {
            width: 100%;
            border: none;
            outline: none;
            box-sizing: border-box;
            background: transparent;
        }

        /* Textarea Output */
        .math-sidebar-textarea {
            width: 100%;
            font-size: 13px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px;
            resize: none;
            color: #374151;
            box-sizing: border-box;
            outline: none;
            transition: all 0.2s;
        }
        .math-sidebar-textarea:focus {
            border-color: #2563eb;
            background: #ffffff;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.10);
        }

        /* Settings Input */
        .math-sidebar-input {
            width: 100%;
            padding: 8px 12px;
            font-size: 14px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            background: #ffffff;
            box-sizing: border-box;
            color: #1f2937;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .math-sidebar-input:focus {
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
            outline: none;
        }
        .math-sidebar-color {
            width: 100%;
            height: 38px;
            padding: 2px 4px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            background: #ffffff;
            cursor: pointer;
            box-sizing: border-box;
        }

        /* Action Buttons */
        .math-sidebar-actions {
            display: flex !important;
            gap: 8px !important;
            margin-top: 20px !important;
        }
        .math-sidebar-btn {
            flex: 1 !important;
            padding: 9px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            border-radius: 8px !important;
            border: none !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 6px !important;
            box-shadow: none !important;
            width: auto !important;
            height: auto !important;
            margin: 0 !important;
        }
        .math-sidebar-btn-primary {
            background-color: #2563eb !important;
            color: #ffffff !important;
        }
        .math-sidebar-btn-primary:hover {
            background-color: #1d4ed8 !important;
            color: #ffffff !important;
        }
        .math-sidebar-btn-warning {
            background-color: #f59e0b !important;
            color: #ffffff !important;
        }
        .math-sidebar-btn-warning:hover {
            background-color: #d97706 !important;
            color: #ffffff !important;
        }
        .math-sidebar-btn-secondary {
            background-color: #f3f4f6 !important;
            color: #4b5563 !important;
        }
        .math-sidebar-btn-secondary:hover {
            background-color: #e5e7eb !important;
            color: #1f2937 !important;
        }

        /* --- Dark Mode Theme --- */
        .math-sidebar-container.dark {
            background-color: #1f2937 !important;
            color: #f9fafb !important;
            border-left-color: #374151 !important;
            box-shadow: -10px 0 30px rgba(0, 0, 0, 0.25) !important;
        }
        .math-sidebar-container.dark .math-sidebar-header {
            border-bottom-color: #374151 !important;
        }
        .math-sidebar-container.dark .math-sidebar-header h5 {
            color: #ffffff !important;
        }
        .math-sidebar-container.dark .math-sidebar-dark-toggle {
            color: #9ca3af !important;
        }
        .math-sidebar-container.dark .math-sidebar-dark-toggle:hover {
            background-color: #374151 !important;
            color: #ffffff !important;
        }
        .math-sidebar-container.dark .math-sidebar-tabs {
            background-color: #374151 !important;
        }
        .math-sidebar-container.dark .math-sidebar-tab-btn {
            color: #9ca3af !important;
        }
        .math-sidebar-container.dark .math-sidebar-tab-btn.active {
            background-color: #1f2937 !important;
            color: #60a5fa !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2) !important;
        }
        .math-sidebar-container.dark .math-sidebar-label {
            color: #9ca3af !important;
        }
        .math-sidebar-container.dark .math-sidebar-textarea {
            background-color: #111827 !important;
            border-color: #374151 !important;
            color: #e5e7eb !important;
        }
        .math-sidebar-container.dark .math-sidebar-textarea:focus {
            border-color: #60a5fa !important;
        }
        .math-sidebar-container.dark .math-sidebar-input {
            background-color: #111827 !important;
            border-color: #374151 !important;
            color: #e5e7eb !important;
        }
        .math-sidebar-container.dark .math-sidebar-input:focus {
            border-color: #60a5fa !important;
        }
        .math-sidebar-container.dark .math-sidebar-color {
            background-color: #111827 !important;
            border-color: #374151 !important;
        }
        .math-sidebar-container.dark .math-sidebar-btn-secondary {
            background-color: #374151 !important;
            color: #d1d5db !important;
        }
        .math-sidebar-container.dark .math-sidebar-btn-secondary:hover {
            background-color: #4b5563 !important;
            color: #ffffff !important;
        }
        .math-sidebar-container.dark .math-sidebar-resizer-h {
            background-color: #374151 !important;
            border-top-color: #4b5563 !important;
        }
    `;
    document.head.appendChild(styleElement);

    // Helper for loading script dynamically
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) {
                resolve();
                return;
            }
            const s = document.createElement("script");
            s.src = src;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    // 2. Create Toggle Button
    const toggleBtn = document.createElement("button");
    toggleBtn.className = "math-sidebar-toggle";
    toggleBtn.innerHTML = "∫";
    document.body.appendChild(toggleBtn);

    // Initialize state trackers
    let isInitialized = false;
    let isLoading = false;
    let settings = {};
    let sidebar = null;

    // MutationObserver to watch keyboard and elevate zIndex
    new MutationObserver(mutations => {
        for (const mutation of mutations) {
            if (mutation.type === "childList") {
                document.querySelectorAll(".ML__keyboard").forEach(kbd => {
                    kbd.style.zIndex = "10000000000";
                });
            }
        }
    }).observe(document.body, { childList: true, subtree: true });

    // 3. Initialize Sidebar DOM and Bindings (lazy loaded)
    function initSidebar() {
        settings = JSON.parse(localStorage.getItem("mathEditorSettings")) || {
            startDelimiter: "~",
            endDelimiter: "~",
            mathFieldFontSize: "16",
            mathFieldColor: "#000000",
            mathFieldBackground: "#ffffff"
        };

        sidebar = document.createElement("div");
        sidebar.className = "math-sidebar-container";
        sidebar.innerHTML = `
            <div class="math-sidebar-resizer-w"></div>
            <div class="math-sidebar-header">
                <h5>Math Editor</h5>
                <button class="math-sidebar-dark-toggle" title="Toggle Dark Mode">
                    <svg style="width: 18px; height: 18px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                    </svg>
                </button>
            </div>
            <div class="math-sidebar-tabs">
                <button class="math-sidebar-tab-btn editor-tab active">
                    <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
                    </svg>
                    Editor
                </button>
                <button class="math-sidebar-tab-btn settings-tab">
                    <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    Settings
                </button>
            </div>
            
            <div class="math-sidebar-body">
                <!-- Editor Content -->
                <div class="editor-content" style="display: block;">
                    <div class="math-sidebar-group">
                        <label class="math-sidebar-label">Math Input</label>
                        <div class="math-input-wrapper">
                            <math-field class="math-input" style="font-size: ${settings.mathFieldFontSize}px; color: ${settings.mathFieldColor}; background: ${settings.mathFieldBackground};"></math-field>
                        </div>
                    </div>
                    <div class="math-sidebar-group">
                        <label class="math-sidebar-label">LaTeX Output</label>
                        <textarea class="latex-output" rows="3" readonly></textarea>
                    </div>
                    <div class="math-sidebar-actions">
                        <button class="math-sidebar-btn math-sidebar-btn-primary copy-btn">
                            <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
                            </svg>
                            <span>Copy</span>
                        </button>
                        <button class="math-sidebar-btn math-sidebar-btn-warning clear-btn">
                            <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                            Clear
                        </button>
                        <button class="math-sidebar-btn math-sidebar-btn-secondary close-btn">
                            Close
                        </button>
                    </div>
                </div>
                
                <!-- Settings Content -->
                <div class="settings-content" style="display: none;">
                    <div class="math-sidebar-group">
                        <label class="math-sidebar-label">Start Delimiter</label>
                        <input type="text" class="start-delimiter" class="math-sidebar-input" style="width: 100%; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; padding: 6px; box-sizing: border-box;" value="${settings.startDelimiter}">
                    </div>
                    <div class="math-sidebar-group">
                        <label class="math-sidebar-label">End Delimiter</label>
                        <input type="text" class="end-delimiter" class="math-sidebar-input" style="width: 100%; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; padding: 6px; box-sizing: border-box;" value="${settings.endDelimiter}">
                    </div>
                    <div class="math-sidebar-group">
                        <label class="math-sidebar-label">Math Font Size (px)</label>
                        <input type="number" class="math-font-size" class="math-sidebar-input" style="width: 100%; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; padding: 6px; box-sizing: border-box;" value="${settings.mathFieldFontSize}" min="10" max="28">
                    </div>
                    <div class="math-sidebar-group">
                        <label class="math-sidebar-label">Text Color</label>
                        <input type="color" class="math-color" class="math-sidebar-color" style="width: 100%; height: 36px; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; box-sizing: border-box;" value="${settings.mathFieldColor}">
                    </div>
                    <div class="math-sidebar-group">
                        <label class="math-sidebar-label">Background Color</label>
                        <input type="color" class="math-bg-color" class="math-sidebar-color" style="width: 100%; height: 36px; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; box-sizing: border-box;" value="${settings.mathFieldBackground}">
                    </div>
                </div>
            </div>
            <div class="math-sidebar-resizer-h"></div>
        `;
        document.body.appendChild(sidebar);

        // Bind inner refs
        const mathInput = sidebar.querySelector(".math-input");
        const latexOutput = sidebar.querySelector(".latex-output");
        const copyBtn = sidebar.querySelector(".copy-btn");
        const clearBtn = sidebar.querySelector(".clear-btn");
        const closeBtn = sidebar.querySelector(".close-btn");
        const darkToggle = sidebar.querySelector(".math-sidebar-dark-toggle");
        const resizeHandleW = sidebar.querySelector(".math-sidebar-resizer-w");
        const resizeHandleH = sidebar.querySelector(".math-sidebar-resizer-h");
        
        const startDelimiter = sidebar.querySelector(".start-delimiter");
        const endDelimiter = sidebar.querySelector(".end-delimiter");
        const mathFontSize = sidebar.querySelector(".math-font-size");
        const mathColor = sidebar.querySelector(".math-color");
        const mathBgColor = sidebar.querySelector(".math-bg-color");
        
        const tabEditor = sidebar.querySelector(".editor-tab");
        const tabSettings = sidebar.querySelector(".settings-tab");
        const contentEditor = sidebar.querySelector(".editor-content");
        const contentSettings = sidebar.querySelector(".settings-content");

        function updateSettings() {
            settings = {
                startDelimiter: startDelimiter.value,
                endDelimiter: endDelimiter.value,
                mathFieldFontSize: mathFontSize.value,
                mathFieldColor: mathColor.value,
                mathFieldBackground: mathBgColor.value
            };
            localStorage.setItem("mathEditorSettings", JSON.stringify(settings));
            
            mathInput.style.fontSize = `${settings.mathFieldFontSize}px`;
            mathInput.style.color = settings.mathFieldColor;
            mathInput.style.background = settings.mathFieldBackground;
            latexOutput.value = `${settings.startDelimiter}${mathInput.value}${settings.endDelimiter}`;
        }

        // Initialize state - wait for math-field custom element to be ready
        customElements.whenDefined('math-field').then(() => {
            mathInput.value = "f(x)=x+1";
            latexOutput.value = `${settings.startDelimiter}${mathInput.value}${settings.endDelimiter}`;
        });

        // Event listeners
        tabEditor.addEventListener("click", () => {
            tabEditor.classList.add("active");
            tabSettings.classList.remove("active");
            contentEditor.style.display = "block";
            contentSettings.style.display = "none";
        });

        tabSettings.addEventListener("click", () => {
            tabSettings.classList.add("active");
            tabEditor.classList.remove("active");
            contentSettings.style.display = "block";
            contentEditor.style.display = "none";
        });

        startDelimiter.addEventListener("input", updateSettings);
        endDelimiter.addEventListener("input", updateSettings);
        mathFontSize.addEventListener("input", updateSettings);
        mathColor.addEventListener("input", updateSettings);
        mathBgColor.addEventListener("input", updateSettings);

        closeBtn.addEventListener("click", () => {
            sidebar.classList.remove("open");
            setTimeout(() => { sidebar.style.display = "none"; }, 400);
            toggleBtn.innerHTML = "∫";
        });

        mathInput.addEventListener("input", () => {
            latexOutput.value = `${settings.startDelimiter}${mathInput.value}${settings.endDelimiter}`;
        });

        copyBtn.addEventListener("click", () => {
            latexOutput.select();
            document.execCommand("copy");
            
            const copyText = copyBtn.querySelector("span");
            const originalText = copyText.innerText;
            copyText.innerText = "Copied!";
            copyBtn.style.backgroundColor = "#10b981";
            
            setTimeout(() => {
                copyText.innerText = originalText;
                copyBtn.style.backgroundColor = "";
            }, 1500);
        });

        clearBtn.addEventListener("click", () => {
            mathInput.value = "";
            latexOutput.value = `${settings.startDelimiter}${settings.endDelimiter}`;
        });

        darkToggle.addEventListener("click", () => {
            sidebar.classList.toggle("dark");
        });

        // Horizontal Drag
        let isResizingW = false;
        resizeHandleW.addEventListener("mousedown", (e) => {
            e.preventDefault();
            isResizingW = true;
        });

        document.addEventListener("mousemove", (e) => {
            if (isResizingW) {
                const width = Math.min(Math.max(window.innerWidth - e.clientX, 260), 800);
                sidebar.style.width = `${width}px`;
            }
        });

        document.addEventListener("mouseup", () => {
            isResizingW = false;
        });

        // Vertical Drag
        let isResizingH = false;
        resizeHandleH.addEventListener("mousedown", (e) => {
            e.preventDefault();
            isResizingH = true;
        });

        document.addEventListener("mousemove", (e) => {
            if (isResizingH) {
                const height = Math.min(Math.max(window.innerHeight - e.clientY, 300), window.innerHeight);
                sidebar.style.height = `${height}px`;
            }
        });

        document.addEventListener("mouseup", () => {
            isResizingH = false;
        });

        // Keyboard Support
        mathInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && e.ctrlKey) {
                const val = mathInput.value;
                const tempSpan = document.createElement("span");
                tempSpan.innerHTML = `${settings.startDelimiter}${val}${settings.endDelimiter}`;
                document.body.appendChild(tempSpan);
                MathLive.renderMathInElement(tempSpan);
            }
        });

        isInitialized = true;
    }

    // 4. Toggle Button Action with Lazy Loading
    toggleBtn.addEventListener("click", async () => {
        // If sidebar is already created and visible, toggle it closed
        if (sidebar && sidebar.classList.contains("open")) {
            sidebar.classList.remove("open");
            setTimeout(() => { sidebar.style.display = "none"; }, 400);
            toggleBtn.innerHTML = "∫";
            return;
        }

        // If not initialized, lazy load library and DOM
        if (!isInitialized) {
            if (isLoading) return;
            isLoading = true;

            // Change button to rotating spinner
            toggleBtn.innerHTML = `
                <svg class="math-loading-spinner" style="width: 22px; height: 22px;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M21 8h-5V3"/>
                </svg>
            `;

            try {
                // Dynamically load MathLive
                await loadScript("https://unpkg.com/mathlive@0.107.0/mathlive.min.js");
                initSidebar();
            } catch (err) {
                console.error("Failed to load MathLive library:", err);
                toggleBtn.innerHTML = "∫";
                isLoading = false;
                alert("Failed to load Math Editor. Please check your internet connection.");
                return;
            }
            isLoading = false;
        }

        // Open the sidebar
        sidebar.style.display = "flex";
        setTimeout(() => { sidebar.classList.add("open"); }, 10);
        toggleBtn.innerHTML = "✕";
    });
}();