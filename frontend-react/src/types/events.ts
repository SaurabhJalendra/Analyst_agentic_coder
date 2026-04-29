import { z } from 'zod';

const planStep = z.object({ id: z.string(), description: z.string() });

export const eventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('plan.start'),       plan_id: z.string(), steps: z.array(planStep) }),
  z.object({ type: z.literal('plan.step.start'),  step_id: z.string() }),
  z.object({ type: z.literal('plan.step.done'),   step_id: z.string(), duration_ms: z.number() }),

  z.object({ type: z.literal('subagent.spawn'),   agent_id: z.string(), parent_id: z.string().nullable().optional(), kind: z.string(), model: z.string(), prompt: z.string() }),
  z.object({ type: z.literal('subagent.delta'),   agent_id: z.string(), tokens: z.number(), status_text: z.string().nullable().optional() }),
  z.object({ type: z.literal('subagent.done'),    agent_id: z.string(), duration_ms: z.number(), tokens: z.number(), result: z.string().nullable().optional() }),

  z.object({ type: z.literal('tool.start'),       call_id: z.string(), agent_id: z.string(), tool: z.string(), args_redacted: z.record(z.unknown()) }),
  z.object({ type: z.literal('tool.done'),        call_id: z.string(), duration_ms: z.number(), ok: z.boolean(), result_preview: z.string().nullable().optional() }),

  z.object({ type: z.literal('skill'),            name: z.string(), args: z.string().nullable().optional() }),
  z.object({ type: z.literal('memory'),           op: z.enum(['read', 'write']), path: z.string() }),
  z.object({ type: z.literal('wiki'),             op: z.enum(['read', 'ingest', 'lint', 'query']), target: z.string() }),

  z.object({ type: z.literal('source'),           source: z.string(), operation: z.string(), bytes: z.number().nullable().optional() }),

  z.object({ type: z.literal('thinking'),         agent_id: z.string(), tokens: z.number(), preview_text: z.string() }),

  z.object({ type: z.literal('artifact'),         artifact_id: z.string(), kind: z.enum(['chart', 'table', 'code', 'report', 'file']), title: z.string(), source_attribution: z.string(), methodology_id: z.string() }),

  z.object({ type: z.literal('message.delta'),    message_id: z.string(), append_text: z.string() }),
  z.object({ type: z.literal('message.done'),     message_id: z.string() }),

  z.object({ type: z.literal('cost.delta'),       usd: z.number(), tokens_in: z.number(), tokens_out: z.number() }),

  z.object({ type: z.literal('approval'),         approval_id: z.string(), description: z.string(), danger: z.boolean() }),
  z.object({ type: z.literal('error'),            code: z.string(), message: z.string(), recoverable: z.boolean() }),
  z.object({ type: z.literal('done'),             session_id: z.string() }),
]);

export type AnyEvent = z.infer<typeof eventSchema>;
export type EventOf<T extends AnyEvent['type']> = Extract<AnyEvent, { type: T }>;

export function parseEvent(json: string): AnyEvent {
  return eventSchema.parse(JSON.parse(json));
}
