import { z } from 'zod';

/**
 * WebSocket Event Schemas — Single Source of Truth for Frontend/Backend Contract
 * Based on app/api/chat.py and app/lib/graph/alma_registry.py
 */

export const BaseEventSchema = z.object({
  type: z.string(),
});

// --- Standard Chat Events ---

export const ConnectedEventSchema = BaseEventSchema.extend({
  type: z.literal('connected'),
  user: z.string(),
});

export const ChunkEventSchema = BaseEventSchema.extend({
  type: z.literal('chunk'),
  text: z.string(),
});

export const CanvasUpdateEventSchema = BaseEventSchema.extend({
  type: z.literal('canvas_update'),
  canvas: z.any(),
});

export const DoneEventSchema = BaseEventSchema.extend({
  type: z.literal('done'),
});

export const GuardrailBlockEventSchema = BaseEventSchema.extend({
  type: z.literal('guardrail_block'),
  text: z.string(),
});

export const ErrorEventSchema = BaseEventSchema.extend({
  type: z.literal('error'),
  message: z.string(),
});

// --- Debate Mode Events ---

export const DebateAlmaSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.string(),
  color: z.string(),
  avatar: z.string(),
});

export const PanelSelectedEventSchema = z.object({
  type: z.literal('panel_selected'),
  panel: z.record(z.string(), z.object({
    name: z.string(),
    rationale: z.string().optional(),
    angle: z.string().optional(),
  })),
  almas: z.array(DebateAlmaSchema),
});

export const DebateTurnStartEventSchema = BaseEventSchema.extend({
  type: z.literal('debate_turn_start'),
  alma_id: z.string(),
  role: z.string(),
  alma_name: z.string(),
});

export const DebateChunkEventSchema = BaseEventSchema.extend({
  type: z.literal('debate_chunk'),
  content: z.string(),
  role: z.string(),
});

export const DebateTurnEndEventSchema = BaseEventSchema.extend({
  type: z.literal('debate_turn_end'),
  role: z.string(),
  alma_name: z.string(),
  content: z.string(),
});

// --- Combined Type ---

export const ChatEventSchema = z.discriminatedUnion('type', [
  ConnectedEventSchema,
  ChunkEventSchema,
  CanvasUpdateEventSchema,
  DoneEventSchema,
  GuardrailBlockEventSchema,
  ErrorEventSchema,
  PanelSelectedEventSchema,
  DebateTurnStartEventSchema,
  DebateChunkEventSchema,
  DebateTurnEndEventSchema,
  z.object({ type: z.literal('pong') }),
  z.object({ type: z.literal('ping') }),
]);

export type ChatEvent = z.infer<typeof ChatEventSchema>;
