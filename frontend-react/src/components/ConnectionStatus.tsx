import { Wifi, WifiOff, Loader2 } from 'lucide-react';

type ConnectionStatusType = 'connected' | 'disconnected' | 'checking';

interface ConnectionStatusProps {
  status: ConnectionStatusType;
}

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const statusConfig = {
    connected: {
      icon: Wifi,
      text: 'Connected',
      dotClass: 'bg-emerald-400 shadow-emerald-500/50',
      bgClass: 'bg-emerald-500/10 border-emerald-500/20',
      textClass: 'text-emerald-400',
    },
    disconnected: {
      icon: WifiOff,
      text: 'Disconnected',
      dotClass: 'bg-red-400 shadow-red-500/50',
      bgClass: 'bg-red-500/10 border-red-500/20',
      textClass: 'text-red-400',
    },
    checking: {
      icon: Loader2,
      text: 'Connecting',
      dotClass: 'bg-amber-400 shadow-amber-500/50',
      bgClass: 'bg-amber-500/10 border-amber-500/20',
      textClass: 'text-amber-400',
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={`flex items-center gap-2.5 px-3.5 py-2 rounded-xl text-sm border ${config.bgClass} backdrop-blur-sm transition-all duration-200`}>
      <div className="relative">
        <div className={`w-2 h-2 rounded-full ${config.dotClass} shadow-lg ${status === 'connected' ? 'animate-pulse' : ''}`} />
        {status === 'checking' && (
          <div className={`absolute inset-0 w-2 h-2 rounded-full ${config.dotClass} animate-ping`} />
        )}
      </div>
      <Icon size={14} className={`${config.textClass} ${status === 'checking' ? 'animate-spin' : ''}`} />
      <span className={`font-medium ${config.textClass}`}>{config.text}</span>
    </div>
  );
}
