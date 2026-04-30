// KaTeX CSS imported here (rather than in index.css) so this stylesheet is
// bundled into the lazy-loaded chunk along with the JS dependencies. Defers
// ~30KB of CSS + ~150KB of JS until the first markdown turn renders.
import 'katex/dist/katex.min.css';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export function MarkdownWithLatex({ children }: { children: string }) {
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}

// Default export so React.lazy() can consume it.
export default MarkdownWithLatex;
