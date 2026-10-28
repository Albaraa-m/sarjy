"use client";

import { useState } from "react";

import { CaloriesMeter, MacroMeter } from "@/components/goal-meters";
import { PortionRow } from "@/components/portion-row";
import {
  type DailyIntake,
  type Macros,
  parseDailyIntake,
  type Portion,
} from "@/lib/parse-daily-intake";

const MACROS: readonly { key: keyof Macros; label: string }[] = [
  { key: "protein_g", label: "Protein" },
  { key: "carbs_g", label: "Carbs" },
  { key: "fat_g", label: "Fat" },
];

const NO_MACROS: Macros = { calories: 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0 };
// Shown until the agent publishes today's log, so the panel keeps its shape and counts up from 0.
const NOTHING_YET: DailyIntake = {
  day: "",
  eaten: [],
  pending: [],
  totals: NO_MACROS,
  targets: NO_MACROS,
  remaining: NO_MACROS,
};

type NutritionPanelProps = {
  /** The agent's `nutrition` participant attribute (a JSON daily intake). */
  attribute: string | undefined;
};

export function NutritionPanel({ attribute }: NutritionPanelProps) {
  const parsed = parseDailyIntake(attribute);

  return (
    <aside className="flex h-full w-[380px] shrink-0 flex-col border-l border-line bg-surface px-6 text-body">
      <header className="mb-3 flex h-14 shrink-0 items-center justify-between">
        <h2 className="text-title">Today</h2>
        <span className="text-caption text-fg-faint">Daily targets</span>
      </header>
      {parsed.status === "invalid" ? (
        <p className="text-warning">Couldn&apos;t read today&apos;s log: {parsed.error}</p>
      ) : (
        <Intake published={parsed.status === "ok" ? parsed.intake : null} />
      )}
    </aside>
  );
}

/** `published` is null until the agent has published today's log. */
function Intake({ published }: { published: DailyIntake | null }) {
  const intake = published ?? NOTHING_YET;
  // Rows already there when the log first loads stay still; later ones animate in.
  const [loadedEatenCount, setLoadedEatenCount] = useState<number | null>(null);
  if (published && loadedEatenCount === null) {
    setLoadedEatenCount(published.eaten.length);
  }
  const pendingTotal = (key: keyof Macros) =>
    intake.pending.reduce((sum, portion) => sum + portion.macros[key], 0);
  // Newest first, where a food just confirmed from the pending box appears.
  const newestFirst = intake.eaten.map((portion, index) => ({ portion, index })).reverse();

  return (
    <div className="flex min-h-0 flex-col gap-6">
      <CaloriesMeter
        eaten={intake.totals.calories}
        target={intake.targets.calories}
        pending={pendingTotal("calories")}
      />
      <div className="grid shrink-0 grid-cols-3 gap-4">
        {MACROS.map(({ key, label }) => (
          <MacroMeter
            key={key}
            label={label}
            eaten={intake.totals[key]}
            target={intake.targets[key]}
            pending={pendingTotal(key)}
          />
        ))}
      </div>
      {intake.pending.length > 0 && <PendingPortions portions={intake.pending} />}
      {published && intake.eaten.length === 0 && intake.pending.length === 0 && <EmptyLog />}
      {intake.eaten.length > 0 && (
        <div className="flex min-h-0 flex-col border-t border-line">
          {/* Scrolls on its own, fading out at the bottom, so the totals above stay in view.
              The side padding gives the rows' highlight room without a sideways scrollbar. */}
          <ul className="-mx-2 min-h-0 divide-y divide-line overflow-y-auto px-2 pb-8 [mask-image:linear-gradient(to_bottom,black_calc(100%-2.5rem),transparent)]">
            {newestFirst.map(({ portion, index }) => (
              <PortionRow
                key={`${index}-${portion.name}`}
                portion={portion}
                isNew={loadedEatenCount !== null && index >= loadedEatenCount}
              />
            ))}
          </ul>
          <p className="shrink-0 py-3 text-caption text-fg-faint">
            {intake.eaten.length} {intake.eaten.length === 1 ? "food" : "foods"} logged today
          </p>
        </div>
      )}
    </div>
  );
}

function PendingPortions({ portions }: { portions: Portion[] }) {
  return (
    <div className="-mx-3 shrink-0 rounded-control border border-accent-line bg-accent-faint px-3 pt-3">
      <p className="flex items-center gap-2 text-caption">
        <span className="size-1.5 animate-pulse rounded-full bg-accent" />
        <span className="font-medium">Log {portions.length > 1 ? "these" : "this"}?</span>
        <span className="text-fg-faint">Say yes or no.</span>
      </p>
      <ul className="divide-y divide-line">
        {portions.map((portion) => (
          <PortionRow key={portion.name} portion={portion} isNew={false} />
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
