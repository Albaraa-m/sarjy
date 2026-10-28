"use client";

import { type AgentState, type TrackReference } from "@livekit/components-react";

import { AgentAudioVisualizerAura } from "@/components/agents-ui/agent-audio-visualizer-aura";
import { useCssColor } from "@/lib/use-css-color";
import { cn } from "@/lib/utils";

type SarjyAuraProps = {
  state: AgentState;
  /** Sarjy's voice, which the Aura moves with; none before the call starts. */
  audioTrack?: TrackReference;
  className?: string;
};

// The shader adds faint noise to every pixel of its square, which shows as a box on the page;
// the radial mask fades the square's edges out so only the glow remains.
// The mask also lifts the canvas above later siblings, so it ignores clicks to keep the controls it overlaps usable.
export function SarjyAura({ state, audioTrack, className }: SarjyAuraProps) {
  const accent = useCssColor("--color-accent");

  return (
    <AgentAudioVisualizerAura
      size="xl"
      themeMode="dark"
      color={accent}
      state={state}
      audioTrack={audioTrack}
      className={cn("pointer-events-none [mask-image:radial-gradient(closest-side,black_55%,transparent)]", className)}
    />
  );
}
