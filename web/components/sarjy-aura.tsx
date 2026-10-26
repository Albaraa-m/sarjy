import { type ComponentProps } from "react";

import { AgentAudioVisualizerAura } from "@/components/agents-ui/agent-audio-visualizer-aura";

type SarjyAuraProps = Omit<ComponentProps<typeof AgentAudioVisualizerAura>, "themeMode">;

// The shader adds faint noise to every pixel of its square, which shows as a box on the page;
// the radial mask fades the square's edges out so only the glow remains.
export function SarjyAura(props: SarjyAuraProps) {
  return (
    <AgentAudioVisualizerAura
      themeMode="dark"
      className="[mask-image:radial-gradient(closest-side,black_55%,transparent)]"
      {...props}
    />
  );
}
