import { lazy, Suspense } from 'react';
import { useSessionStore } from '../../store/sessionStore';
import { UserMessage } from './UserMessage';
import { ThinkingBlock } from './ThinkingBlock';
import { BrandedArtifactCard } from './BrandedArtifactCard';
import { ChartArtifactBody } from './ChartArtifactBody';
import { SubAgentIndicator } from './SubAgentIndicator';
import { PlanRail } from './PlanRail';

// Lazy-load the markdown+LaTeX renderer. It pulls in react-markdown +
// remark-math + rehype-katex + the KaTeX runtime (~150KB gzipped). The
// fallback shows the raw text so the user sees the assistant response
// immediately while the chunk loads.
const MarkdownWithLatex = lazy(() => import('../renderers/MarkdownWithLatex'));

function AssistantTurn({ text }: { text: string }) {
  return (
    <Suspense fallback={<div className="whitespace-pre-wrap">{text}</div>}>
      <MarkdownWithLatex>{text}</MarkdownWithLatex>
    </Suspense>
  );
}

export function ChatStream() {
  const chat = useSessionStore((s) => s.session.chat);
  return (
    <div>
      {chat.map((turn) => {
        switch (turn.kind) {
          case 'user':
            return <UserMessage key={turn.id} text={turn.text} />;
          case 'assistant':
            return (
              <div key={turn.id} className="my-2 text-[12px]">
                <AssistantTurn text={turn.text} />
              </div>
            );
          case 'thinking':
            return <ThinkingBlock key={turn.id} tokens={turn.tokens} preview={turn.preview} />;
          case 'artifact':
            return (
              <BrandedArtifactCard
                key={turn.id}
                artifact={turn.artifact}
                body={
                  turn.artifact.kind === 'chart' ? (
                    <ChartArtifactBody artifactId={turn.artifact.id} />
                  ) : (
                    <div className="text-[10px] text-slate-500 italic">
                      {`${turn.artifact.kind} rendering deferred.`}
                    </div>
                  )
                }
              />
            );
          case 'subagent':
            return <SubAgentIndicator key={turn.id} msg={turn} />;
        }
      })}
      <PlanRail />
    </div>
  );
}
