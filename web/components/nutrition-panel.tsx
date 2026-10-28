"use client";

import { useState } from "react";

import { AnimatedNumber } from "@/components/animated-number";
import {
  type FoodEntry,
  type Macros,
  type NutritionSummary,
  parseNutritionSummary,
} from "@/lib/parse-nutrition-summary";
import { cn } from "@/lib/utils";

const MACROS = [
  { key: "protein_g", label: "Protein" },
  { key: "carbs_g", label: "Carbs" },
  { key: "fat_g", label: "Fat" },
] as const satisfies readonly { key: keyof Macros; label: string }[];

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
        <Summary summary={parsed.status === "ok" ? parsed.summary : null} />
      )}
    </aside>
  );
}

/** `summary` is null until the agent has published today's log. */
function Summary({ summary: published }: { summary: NutritionSummary | null }) {
  const summary = published ?? NOTHING_YET;
  // Rows already there when the log first loads stay still; later ones animate in.
  const [loadedEntryCount, setLoadedEntryCount] = useState<number | null>(null);
  if (published && loadedEntryCount === null) {
    setLoadedEntryCount(published.entries.length);
  }
  const pending = (key: keyof Macros) =>
    summary.pending.reduce((sum, entry) => sum + entry.macros[key], 0);
  // Newest first, where a food just confirmed from the pending box appears.
  const newestFirst = summary.entries.map((entry, index) => ({ entry, index })).reverse();

  return (
    <div className="flex min-h-0 flex-col gap-6">
      <Calories
        eaten={summary.totals.calories}
        target={summary.targets.calories}
        pending={pending("calories")}
      />
      <div className="grid shrink-0 grid-cols-3 gap-4">
        {MACROS.map(({ key, label }) => (
          <Macro
            key={key}
            label={label}
            eaten={summary.totals[key]}
            target={summary.targets[key]}
            pending={pending(key)}
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
              <EntryRow
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

type GoalProps = {
  eaten: number;
  target: number;
  pending: number;
};

function Calories({ eaten, target, pending }: GoalProps) {
  return (
    <section className="flex shrink-0 flex-col gap-2">
      <p className="flex items-baseline justify-between">
        <span className="text-figure">
          <AnimatedNumber value={eaten} /> <span className="text-body font-normal text-fg-muted">kcal</span>
        </span>
        <span className="text-label text-fg-muted">
          of <AnimatedNumber value={target} />
        </span>
      </p>
      <ProgressBar eaten={eaten} target={target} pending={pending} />
      <Difference eaten={eaten} target={target} unit="kcal" />
    </section>
  );
}

function Macro({ label, eaten, target, pending }: GoalProps & { label: string }) {
  return (
    <section className="flex flex-col gap-1.5">
      <span className="text-label text-fg-muted">{label}</span>
      <span className="text-body">
        <AnimatedNumber value={eaten} />
        <span className="text-fg-faint">
          {" / "}
          <AnimatedNumber value={target} /> g
        </span>
      </span>
      <ProgressBar eaten={eaten} target={target} pending={pending} />
      <Difference eaten={eaten} target={target} unit="g" />
    </section>
  );
}

function ProgressBar({ eaten, target, pending }: GoalProps) {
  const eatenShare = target > 0 ? Math.min(eaten / target, 1) : 0;
  const pendingShare = target > 0 ? Math.min(pending / target, 1 - eatenShare) : 0;

  return (
    <div className="flex h-1 overflow-hidden rounded-full bg-inset">
      <div
        className={cn("transition-[width]", eaten > target ? "bg-warning" : "bg-accent")}
        style={{ width: `${eatenShare * 100}%` }}
      />
      {/* What's still waiting for a "yes", so the user sees the effect before confirming. */}
      <div className="bg-accent-soft transition-[width]" style={{ width: `${pendingShare * 100}%` }} />
    </div>
  );
}

function Difference({ eaten, target, unit }: { eaten: number; target: number; unit: string }) {
  if (target === 0) {
    return <span className="text-caption">&nbsp;</span>;
  }
  const over = Math.round(eaten - target);
  if (over > 0) {
    return (
      <span className="text-caption text-warning">
        +{over.toLocaleString("en-US")} {unit} over
      </span>
    );
  }
  return (
    <span className="text-caption text-fg-faint">
      {(-over).toLocaleString("en-US")} {unit} left
    </span>
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
          <EntryRow key={entry.food} entry={entry} isNew={false} />
        ))}
      </ul>
    </div>
  );
}

function EntryRow({ entry, isNew }: { entry: FoodEntry; isNew: boolean }) {
  return (
    <li className="py-1">
      <div
        className={cn(
          "-mx-2 flex items-start justify-between gap-4 rounded-control px-2 py-2",
          isNew && "animate-entry-in",
        )}
      >
        <div className="flex min-w-0 flex-col gap-1">
          <span className="break-words">{entry["display_name"]}</span>
          <span className="flex items-center gap-2 text-caption text-fg-faint">
            {Math.round(entry.grams)} g
            <SourceTag source={entry.source} />
          </span>
        </div>
        <span className="shrink-0 text-right">
          {Math.round(entry.macros.calories).toLocaleString("en-US")}
          <span className="text-fg-faint"> kcal</span>
        </span>
      </div>
    </li>
  );
}

function SourceTag({ source }: { source: FoodEntry["source"] }) {
  if (source === "usda") {
    return <span className="rounded-tag bg-inset px-1.5 py-px text-fg-muted">USDA</span>;
  }
  return (
    <span className="rounded-tag border border-dashed border-line-strong px-1.5 text-fg-muted">
      Estimate
    </span>
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
