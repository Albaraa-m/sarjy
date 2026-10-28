import { type FoodEntry } from "@/lib/parse-nutrition-summary";
import { cn } from "@/lib/utils";

type FoodEntryRowProps = {
  entry: FoodEntry;
  /** Slides in with a brief highlight, for a food logged during this call. */
  isNew: boolean;
};

export function FoodEntryRow({ entry, isNew }: FoodEntryRowProps) {
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
