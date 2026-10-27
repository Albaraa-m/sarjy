"use client";

import { type AgentState, StartAudio, type TrackReference } from "@livekit/components-react";

import { CallControls } from "@/components/call-controls";
import { NutritionPanel } from "@/components/nutrition-panel";
import { SarjyAura } from "@/components/sarjy-aura";

type CallScreenProps = {
  agentState: AgentState;
  agentTrack: TrackReference | undefined;
  microphoneTrack: TrackReference | undefined;
  /** Only what the Aura can't show: connecting, or why the call failed. */
  status: { text: string; isError: boolean } | null;
  nutritionAttribute: string | undefined;
  onEnd: () => void;
};

export function CallScreen({
  agentState,
  agentTrack,
  microphoneTrack,
  status,
  nutritionAttribute,
  onEnd,
}: CallScreenProps) {
  return (
    <div className="grid min-h-0 flex-1 grid-cols-[1fr_400px] grid-rows-[minmax(0,1fr)] items-center gap-12 pb-10">
      <section className="flex flex-col items-center">
        <p className={status?.isError ? "h-5 text-label text-warning" : "h-5 text-label text-fg-muted"}>
          {status?.text}
        </p>
        {/* The glow fills only the middle of the Aura's square, so its edges overlap neighbors. */}
        <SarjyAura size="xl" state={agentState} audioTrack={agentTrack} className="-my-14" />
        <StartAudio
          label="Tap to hear Sarjy"
          className="mb-4 rounded-full border border-line bg-surface px-4 py-2 text-label hover:bg-surface-hover"
        />
        <CallControls microphoneTrack={microphoneTrack} onEnd={onEnd} />
      </section>
      <NutritionPanel attribute={nutritionAttribute} />
    </div>
  );
}
