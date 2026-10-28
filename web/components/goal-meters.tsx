import { AnimatedNumber } from "@/components/animated-number";
import { cn } from "@/lib/utils";

type GoalProps = {
  eaten: number;
  target: number;
  /** Foods proposed but not yet confirmed. */
  pending: number;
};

export function CaloriesMeter({ eaten, target, pending }: GoalProps) {
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

export function MacroMeter({ label, eaten, target, pending }: GoalProps & { label: string }) {
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
  // Targets are 0 until the log loads; keep the line's height so nothing jumps.
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
