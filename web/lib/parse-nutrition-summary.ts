import { z } from "zod";

const MacrosSchema = z.object({
  calories: z.number(),
  "protein_g": z.number(),
  "carbs_g": z.number(),
  "fat_g": z.number(),
});

const FoodEntrySchema = z.object({
  food: z.string(),
  "display_name": z.string(),
  grams: z.number(),
  macros: MacrosSchema,
  source: z.enum(["usda", "estimate"]),
});

// Mirrors DaySummary.to_json() in agent/nutrition/food_log.py.
const NutritionSummarySchema = z.object({
  day: z.string(),
  entries: z.array(FoodEntrySchema),
  pending: z.array(FoodEntrySchema),
  totals: MacrosSchema,
  targets: MacrosSchema,
  remaining: MacrosSchema,
});

export type Macros = z.infer<typeof MacrosSchema>;
export type FoodEntry = z.infer<typeof FoodEntrySchema>;
export type NutritionSummary = z.infer<typeof NutritionSummarySchema>;

type ParsedSummary =
  | { status: "waiting" }
  | { status: "ok"; summary: NutritionSummary }
  | { status: "invalid"; error: string };

/** Parses the agent's `nutrition` attribute; `waiting` until the agent has published one. */
export function parseNutritionSummary(attribute: string | undefined): ParsedSummary {
  if (attribute === undefined) {
    return { status: "waiting" };
  }
  try {
    return { status: "ok", summary: NutritionSummarySchema.parse(JSON.parse(attribute)) };
  } catch (error) {
    return { status: "invalid", error: error instanceof Error ? error.message : String(error) };
  }
}
