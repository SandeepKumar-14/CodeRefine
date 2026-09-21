/* CodeRefine — Monaco themes (UI only).
   Load with a normal <script> before app.js. Then in app.js:
     1) right after the editor is created:   window.applyCodeRefineMonaco(document.documentElement.dataset.theme);
     2) wherever the theme changes:          window.applyCodeRefineMonaco(newTheme);
   Remove/replace any existing monaco.editor.setTheme('vs') or  theme: 'vs'  in app.js. */
(function () {
  var defined = false;

  function define() {
    if (defined || !window.monaco) return;
    defined = true;

    monaco.editor.defineTheme('coderefine-light', {
      base: 'vs', inherit: true,
      rules: [
        { token: 'comment', foreground: '8A8F98', fontStyle: 'italic' },
        { token: 'keyword', foreground: '2F5FD0' },
        { token: 'string', foreground: '1F8F5F' },
        { token: 'number', foreground: 'A8690F' },
        { token: 'type', foreground: '7B5CD6' },
      ],
      colors: {
        'editor.background': '#FFFFFF',
        'editor.foreground': '#14171C',
        'editorGutter.background': '#FFFFFF',
        'editorLineNumber.foreground': '#8A8F98',
        'editorLineNumber.activeForeground': '#14171C',
        'editor.lineHighlightBackground': '#F7F6F2',
        'editor.selectionBackground': '#2F5FD022',
        'editorCursor.foreground': '#14171C',
        'editorIndentGuide.background1': '#E4E2DA',
        'editorWidget.background': '#FAFAF7',
        'editorWidget.border': '#E4E2DA',
      },
    });

    monaco.editor.defineTheme('coderefine-dark', {
      base: 'vs-dark', inherit: true,
      rules: [
        { token: 'comment', foreground: '6B7684', fontStyle: 'italic' },
        { token: 'keyword', foreground: '6FA8FF' },
        { token: 'string', foreground: '3FBF8F' },
        { token: 'number', foreground: 'E8A33D' },
        { token: 'type', foreground: 'B39DFF' },
      ],
      colors: {
        'editor.background': '#151B23',
        'editor.foreground': '#E8EAED',
        'editorGutter.background': '#151B23',
        'editorLineNumber.foreground': '#6B7684',
        'editorLineNumber.activeForeground': '#E8EAED',
        'editor.lineHighlightBackground': '#1B222C',
        'editor.selectionBackground': '#6FA8FF2E',
        'editorCursor.foreground': '#E8EAED',
        'editorIndentGuide.background1': '#262E3A',
        'editorWidget.background': '#151B23',
        'editorWidget.border': '#262E3A',
      },
    });

    monaco.editor.defineTheme('coderefine-nebula', {
      base: 'vs-dark', inherit: true,
      rules: [
        { token: 'comment', foreground: '766FA3', fontStyle: 'italic' },
        { token: 'keyword', foreground: '9D8CFF' },
        { token: 'string', foreground: '52D1A0' },
        { token: 'number', foreground: 'EDB25A' },
        { token: 'type', foreground: 'C9BEFF' },
      ],
      colors: {
        'editor.background': '#171330',
        'editor.foreground': '#ECE9FF',
        'editorGutter.background': '#171330',
        'editorLineNumber.foreground': '#766FA3',
        'editorLineNumber.activeForeground': '#ECE9FF',
        'editor.lineHighlightBackground': '#211B40',
        'editor.selectionBackground': '#9D8CFF33',
        'editorCursor.foreground': '#ECE9FF',
        'editorIndentGuide.background1': '#2E2758',
        'editorWidget.background': '#171330',
        'editorWidget.border': '#2E2758',
      },
    });
  }

  window.applyCodeRefineMonaco = function (theme) {
    if (!window.monaco) return;
    define();
    var name = theme === 'dark' ? 'coderefine-dark'
             : theme === 'nebula' ? 'coderefine-nebula'
             : 'coderefine-light';
    monaco.editor.setTheme(name);
  };
})();
