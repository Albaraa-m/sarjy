import {
  type FoodEntry,
  type Macros,
  type NutritionSummary,
  parseNutritionSummary,
} from "@/lib/parse-nutrition-summary";

const MACRO_ROWS = [
  { key: "calories", label: "Calories", unit: "kcal" },
  { key: "protein_g", label: "Protein", unit: "g" },
  { key: "carbs_g", label: "Carbs", unit: "g" },
  { key: "fat_g", label: "Fat", unit: "g" },
] as const satisfies readonly { key: keyof Macros; label: string; unit: string }[];

type NutritionPanelProps = {
  /** The agent's `nutrition` participant attribute (a JSON day summary). */
  attribute: string | undefined;
};

export function NutritionPanel({ attribute }: NutritionPanelProps) {
  const parsed = parseNutritionSummary(attribute);

  return (
    <aside className="w-full max-w-sm rounded-2xl bg-white/5 p-5 text-sm">
      <header className="mb-4 flex items-baseline justify-between">
        <h2 className="font-semibold">Today</h2>
        <span className="text-xs text-foreground/50">vs demo targets</span>
      </header>
      {parsed.status === "waiting" && <p className="text-foreground/50">Loading today…</p>}
      {parsed.status === "invalid" && (
        <p className="text-danger">Couldn&apos;t read today&apos;s log: {parsed.error}</p>
      )}
      {parsed.status === "ok" && <Summary summary={parsed.summary} />}
    </aside>
  );
}

function Summary({ summary }: { summary: NutritionSummary }) {
  return (
    <div className="flex flex-col gap-5">
      <ul className="flex flex-col gap-3">
        {MACRO_ROWS.map(({ key, label, unit }) => (
          <MacroBar
            key={key}
            label={label}
            unit={unit}
            eaten={summary.totals[key]}
            target={summary.targets[key]}
            pending={summary.pending?.macros[key] ?? 0}
          />
        ))}
      </ul>
      {summary.pending && <PendingEntry entry={summary.pending} />}
      <ul className="flex flex-col gap-2">
        {summary.entries.length === 0 && <li className="text-foreground/50">Nothing logged yet.</li>}
        {summary.entries.map((entry, index) => (
          <EntryRow key={`${index}-${entry.food}`} entry={entry} />
        ))}
      </ul>
    </div>
  );
}

type MacroBarProps = {
  label: string;
  unit: string;
  eaten: number;
  target: number;
  pending: number;
};

function MacroBar({ label, unit, eaten, target, pending }: MacroBarProps) {
  const eatenWidth = Math.min(eaten / target, 1) * 100;
  const pendingWidth = Math.min(pending / target, 1 - eatenWidth / 100) * 100;

  return (
    <li className="flex flex-col gap-1">
      <div className="flex justify-between">
        <span>{label}</span>
        <span className="tabular-nums text-foreground/60">
          {Math.round(eaten)} / {Math.round(target)} {unit}
        </span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-white/10">
        <div className="bg-accent transition-all" style={{ width: `${eatenWidth}%` }} />
        {/* What's still waiting for a "yes", so the user sees the effect before confirming. */}
        <div className="bg-accent/35 transition-all" style={{ width: `${pendingWidth}%` }} />
      </div>
    </li>
  );
}

function PendingEntry({ entry }: { entry: FoodEntry }) {
  return (
    <div className="rounded-xl border border-dashed border-accent/50 p-3">
      <p className="text-xs text-accent">Log this? Say yes or no.</p>
      <ul>
        <EntryRow entry={entry} />
      </ul>
    </div>
  );
}

function EntryRow({ entry }: { entry: FoodEntry }) {
  return (
    <li className="flex items-center justify-between gap-3">
      <span className="truncate">
        {entry.food}
        <span className="text-foreground/50"> · {Math.round(entry.grams)} g</span>
      </span>
      <span className="flex shrink-0 items-center gap-2 tabular-nums">
        {entry.source === "estimate" && (
          <span className="rounded-full bg-amber-400/15 px-2 py-0.5 text-xs text-amber-300">
            estimate
          </span>
        )}
        {Math.round(entry.macros.calories)} kcal
      </span>
    </li>
  );
}
