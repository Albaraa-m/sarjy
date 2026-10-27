"use client";

import { type ComponentProps } from "react";

import { AgentAudioVisualizerAura } from "@/components/agents-ui/agent-audio-visualizer-aura";
import { useCssColor } from "@/lib/use-css-color";
import { cn } from "@/lib/utils";

type SarjyAuraProps = Omit<ComponentProps<typeof AgentAudioVisualizerAura>, "themeMode" | "color">;

// The shader adds faint noise to every pixel of its square, which shows as a box on the page;
// the radial mask fades the square's edges out so only the glow remains.
export function SarjyAura({ className, ...props }: SarjyAuraProps) {
  const accent = useCssColor("--color-accent");

  return (
    <AgentAudioVisualizerAura
      themeMode="dark"
      color={accent}
      className={cn("[mask-image:radial-gradient(closest-side,black_55%,transparent)]", className)}
      {...props}
    />
  );
}
