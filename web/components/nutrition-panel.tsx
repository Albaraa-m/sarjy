"use client";

import { useState } from "react";

import { FoodEntryRow } from "@/components/food-entry-row";
import { CaloriesMeter, MacroMeter } from "@/components/goal-meters";
import {
  type FoodEntry,
  type Macros,
  type NutritionSummary,
  parseNutritionSummary,
} from "@/lib/parse-nutrition-summary";

const MACROS: readonly { key: keyof Macros; label: string }[] = [
  { key: "protein_g", label: "Protein" },
  { key: "carbs_g", label: "Carbs" },
  { key: "fat_g", label: "Fat" },
];

const NO_MACROS: Macros = { calories: 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0 };
// Shown until the agent publishes today's log, so the panel keeps its shape and counts up from 0.
const NOTHING_YET: NutritionSummary = {
  day: "",
  entries: [],
  pending: [],
  totals: NO_MACROS,
  targets: NO_MACROS,
  remaining: NO_MACROS,
};

type NutritionPanelProps = {
  /** The agent's `nutrition` participant attribute (a JSON day summary). */
  attribute: string | undefined;
};

export function NutritionPanel({ attribute }: NutritionPanelProps) {
  const parsed = parseNutritionSummary(attribute);

  return (
    <aside className="flex h-full w-[380px] shrink-0 flex-col border-l border-line bg-surface px-6 text-body">
      <header className="mb-3 flex h-14 shrink-0 items-center justify-between">
        <h2 className="text-title">Today</h2>
        <span className="text-caption text-fg-faint">Daily targets</span>
      </header>
      {parsed.status === "invalid" ? (
        <p className="text-warning">Couldn&apos;t read today&apos;s log: {parsed.error}</p>
      ) : (
        <Summary published={parsed.status === "ok" ? parsed.summary : null} />
      )}
    </aside>
  );
}

/** `published` is null until the agent has published today's log. */
function Summary({ published }: { published: NutritionSummary | null }) {
  const summary = published ?? NOTHING_YET;
  // Rows already there when the log first loads stay still; later ones animate in.
  const [loadedEntryCount, setLoadedEntryCount] = useState<number | null>(null);
  if (published && loadedEntryCount === null) {
    setLoadedEntryCount(published.entries.length);
  }
  const pendingTotal = (key: keyof Macros) =>
    summary.pending.reduce((sum, entry) => sum + entry.macros[key], 0);
  // Newest first, where a food just confirmed from the pending box appears.
  const newestFirst = summary.entries.map((entry, index) => ({ entry, index })).reverse();

  return (
    <div className="flex min-h-0 flex-col gap-6">
      <CaloriesMeter
        eaten={summary.totals.calories}
        target={summary.targets.calories}
        pending={pendingTotal("calories")}
      />
      <div className="grid shrink-0 grid-cols-3 gap-4">
        {MACROS.map(({ key, label }) => (
          <MacroMeter
            key={key}
            label={label}
            eaten={summary.totals[key]}
            target={summary.targets[key]}
            pending={pendingTotal(key)}
          />
        ))}
      </div>
      {summary.pending.length > 0 && <PendingFoods entries={summary.pending} />}
      {published && summary.entries.length === 0 && summary.pending.length === 0 && <EmptyLog />}
      {summary.entries.length > 0 && (
        <div className="flex min-h-0 flex-col border-t border-line">
          {/* Scrolls on its own, fading out at the bottom, so the totals above stay in view.
              The side padding gives the rows' highlight room without a sideways scrollbar. */}
          <ul className="-mx-2 min-h-0 divide-y divide-line overflow-y-auto px-2 pb-8 [mask-image:linear-gradient(to_bottom,black_calc(100%-2.5rem),transparent)]">
            {newestFirst.map(({ entry, index }) => (
              <FoodEntryRow
                key={`${index}-${entry.food}`}
                entry={entry}
                isNew={loadedEntryCount !== null && index >= loadedEntryCount}
              />
            ))}
          </ul>
          <p className="shrink-0 py-3 text-caption text-fg-faint">
            {summary.entries.length} {summary.entries.length === 1 ? "food" : "foods"} logged today
          </p>
        </div>
      )}
    </div>
  );
}

function PendingFoods({ entries }: { entries: FoodEntry[] }) {
  return (
    <div className="-mx-3 shrink-0 rounded-control border border-accent-line bg-accent-faint px-3 pt-3">
      <p className="flex items-center gap-2 text-caption">
        <span className="size-1.5 animate-pulse rounded-full bg-accent" />
        <span className="font-medium">Log {entries.length > 1 ? "these" : "this"}?</span>
        <span className="text-fg-faint">Say yes or no.</span>
      </p>
      <ul className="divide-y divide-line">
        {entries.map((entry) => (
          <FoodEntryRow key={entry.food} entry={entry} isNew={false} />
        ))}
      </ul>
    </div>
  );
}

function EmptyLog() {
  return (
    <div className="flex flex-col gap-1 border-t border-line pt-5 pb-6">
      <p>Tell Sarjy what you ate.</p>
      <p className="text-label text-fg-faint">Try &ldquo;I had a banana for breakfast.&rdquo;</p>
    </div>
  );
}
