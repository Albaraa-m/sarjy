import { z } from "zod";

const MacrosSchema = z.object({
  calories: z.number(),
  "protein_g": z.number(),
  "carbs_g": z.number(),
  "fat_g": z.number(),
});

const PortionSchema = z.object({
  name: z.string(),
  "usda_description": z.string().nullable(),
  grams: z.number(),
  macros: MacrosSchema,
  source: z.enum(["usda", "estimate"]),
});

// Mirrors DailyIntake.to_json() in agent/nutrition/diary.py.
const DailyIntakeSchema = z.object({
  day: z.string(),
  eaten: z.array(PortionSchema),
  pending: z.array(PortionSchema),
  totals: MacrosSchema,
  targets: MacrosSchema,
  remaining: MacrosSchema,
});

export type Macros = z.infer<typeof MacrosSchema>;
export type Portion = z.infer<typeof PortionSchema>;
export type DailyIntake = z.infer<typeof DailyIntakeSchema>;

type ParsedIntake =
  | { status: "waiting" }
  | { status: "ok"; intake: DailyIntake }
  | { status: "invalid"; error: string };

/** Parses the agent's `nutrition` attribute; `waiting` until the agent has published one. */
export function parseDailyIntake(attribute: string | undefined): ParsedIntake {
  if (attribute === undefined) {
    return { status: "waiting" };
  }
  try {
    return { status: "ok", intake: DailyIntakeSchema.parse(JSON.parse(attribute)) };
  } catch (error) {
    return { status: "invalid", error: error instanceof Error ? error.message : String(error) };
  }
}
