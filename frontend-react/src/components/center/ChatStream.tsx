import { useSessionStore } from '../../store/sessionStore';
import { UserMessage } from './UserMessage';
import { ThinkingBlock } from './ThinkingBlock';
import { BrandedArtifactCard } from './BrandedArtifactCard';
import { SubAgentIndicator } from './SubAgentIndicator';
import { PlanRail } from './PlanRail';
import { MarkdownWithLatex } from '../renderers/MarkdownWithLatex';

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
                <MarkdownWithLatex>{turn.text}</MarkdownWithLatex>
              </div>
            );
          case 'thinking':
            return <ThinkingBlock key={turn.id} tokens={turn.tokens} preview={turn.preview} />;
          case 'artifact':
            return (
              <BrandedArtifactCard
                key={turn.id}
                artifact={turn.artifact}
                body={<div className="text-[10px] text-slate-500 italic">Artifact rendering coming in Phase 3.</div>}
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
