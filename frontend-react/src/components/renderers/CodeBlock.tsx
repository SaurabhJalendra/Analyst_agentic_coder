import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import typescript from 'highlight.js/lib/languages/typescript';
import javascript from 'highlight.js/lib/languages/javascript';
import bash from 'highlight.js/lib/languages/bash';
import 'highlight.js/styles/github-dark.css';

hljs.registerLanguage('python', python);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('bash', bash);

export function CodeBlock({ code, language = 'python' }: { code: string; language?: string }) {
  const html = hljs.getLanguage(language) ? hljs.highlight(code, { language }).value : code;
  return (
    <pre className="bg-slate-900 text-slate-100 font-mono text-[10px] px-3 py-2 leading-relaxed overflow-x-auto">
      <code dangerouslySetInnerHTML={{ __html: html }} />
    </pre>
  );
}
