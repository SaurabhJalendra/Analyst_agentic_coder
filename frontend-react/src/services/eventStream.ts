import { parseEvent } from '../types/events';
import type { AnyEvent } from '../types/events';

export interface EventStreamHandle {
  close(): void;
}

export interface EventStreamOptions {
  url: string;
  onEvent: (ev: AnyEvent) => void;
  onError?: (err: Event) => void;
  onOpen?: () => void;
  lastEventId?: string;
}

/**
 * Wraps EventSource. Browser auto-reconnects with Last-Event-ID; we just
 * surface validated events. Malformed events are logged and dropped.
 */
export function openEventStream(opts: EventStreamOptions): EventStreamHandle {
  const es = new EventSource(opts.url, { withCredentials: false });

  es.onopen = () => opts.onOpen?.();
  es.onerror = (e) => opts.onError?.(e);

  es.addEventListener('message', (msg: MessageEvent<string>) => {
    try {
      const ev = parseEvent(msg.data);
      opts.onEvent(ev);
    } catch (err) {
      console.warn('[eventStream] dropped malformed event', err, msg.data);
    }
  });

  // SSE supports custom events; the backend names them by event type. Catch them all.
  // (browser EventSource fires both `message` and the named-event handlers; we listen
  // generically via a passthrough.)
  const types: AnyEvent['type'][] = [
    'plan.start', 'plan.step.start', 'plan.step.done',
    'subagent.spawn', 'subagent.delta', 'subagent.done',
    'tool.start', 'tool.done',
    'skill', 'memory', 'wiki', 'source', 'thinking',
    'artifact', 'message.delta', 'message.done',
    'cost.delta', 'approval', 'error', 'done',
  ];
  for (const t of types) {
    es.addEventListener(t, (msg) => {
      const e = msg as MessageEvent<string>;
      try {
        opts.onEvent(parseEvent(e.data));
      } catch (err) {
        console.warn('[eventStream] dropped malformed event', err, e.data);
      }
    });
  }

  return { close: () => es.close() };
}
