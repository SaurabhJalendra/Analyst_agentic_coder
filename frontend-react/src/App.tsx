// frontend-react/src/App.tsx
import { ThreePaneLayout } from './components/layout/ThreePaneLayout';
import { BrandBar } from './components/frame/BrandBar';
import { ComplianceBar } from './components/frame/ComplianceBar';
import { StatusBar } from './components/frame/StatusBar';
import { ComplianceFooter } from './components/frame/ComplianceFooter';
import { LeftRail } from './components/left/LeftRail';
import { ChatStream } from './components/center/ChatStream';
import { RightRail } from './components/right/RightRail';
import { PromptInput } from './components/prompt/PromptInput';
import { useSessionHistory } from './hooks/useSessionHistory';

function App() {
  // Reload chat history whenever the active session changes (cancellable).
  useSessionHistory();

  return (
    <ThreePaneLayout
      topBar={<BrandBar />}
      complianceBar={<ComplianceBar lastRefresh={new Date().toISOString().slice(11, 16) + ' GMT'} />}
      statusBar={<StatusBar />}
      left={<LeftRail />}
      center={<ChatStream />}
      right={<RightRail />}
      prompt={<PromptInput />}
      footer={<ComplianceFooter />}
    />
  );
}

export default App;
