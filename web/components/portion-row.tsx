import { type Portion } from "@/lib/parse-daily-intake";
import { cn } from "@/lib/utils";

type PortionRowProps = {
  portion: Portion;
  /** Slides in with a brief highlight, for a food logged during this call. */
  isNew: boolean;
};

export function PortionRow({ portion, isNew }: PortionRowProps) {
  return (
    <li className="py-1">
      <div
        className={cn(
          "-mx-2 flex items-start justify-between gap-4 rounded-control px-2 py-2",
          isNew && "animate-entry-in",
        )}
      >
        <div className="flex min-w-0 flex-col gap-1">
          <span className="break-words">{portion.name}</span>
          <span className="flex items-center gap-2 text-caption text-fg-faint">
            {Math.round(portion.grams)} g
            <SourceTag source={portion.source} />
          </span>
        </div>
        <span className="shrink-0 text-right">
          {Math.round(portion.macros.calories).toLocaleString("en-US")}
          <span className="text-fg-faint"> kcal</span>
        </span>
      </div>
    </li>
  );
}

function SourceTag({ source }: { source: Portion["source"] }) {
  if (source === "usda") {
    return <span className="rounded-tag bg-inset px-1.5 py-px text-fg-muted">USDA</span>;
  }
  return (
    <span className="rounded-tag border border-dashed border-line-strong px-1.5 text-fg-muted">
      Estimate
    </span>
  );
}
