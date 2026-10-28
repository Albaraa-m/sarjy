"use client";

import { type AgentState, StartAudio, type TrackReference } from "@livekit/components-react";

import { AppHeader } from "@/components/app-header";
import { CallControls } from "@/components/call-controls";
import { NutritionPanel } from "@/components/nutrition-panel";
import { SarjyAura } from "@/components/sarjy-aura";

type CallScreenProps = {
  username: string;
  agentState: AgentState;
  agentTrack: TrackReference | undefined;
  microphoneTrack: TrackReference | undefined;
  /** Only what the Aura can't show: connecting, or why the call failed. */
  status: { text: string; isError: boolean } | null;
  nutritionAttribute: string | undefined;
  onEnd: () => void;
};

export function CallScreen({
  username,
  agentState,
  agentTrack,
  microphoneTrack,
  status,
  nutritionAttribute,
  onEnd,
}: CallScreenProps) {
  return (
    <div className="flex h-dvh">
      <main className="flex min-w-0 flex-1 flex-col px-6">
        <AppHeader username={username} />
        <section className="flex flex-1 flex-col items-center justify-center pb-14">
          <p className={status?.isError ? "h-5 text-label text-warning" : "h-5 text-label text-fg-muted"}>
            {status?.text}
          </p>
          {/* The glow fills only the middle of the Aura's square, so its edges overlap neighbors. */}
          <SarjyAura state={agentState} audioTrack={agentTrack} className="-my-14" />
          <StartAudio
            label="Tap to hear Sarjy"
            className="mb-4 rounded-full border border-line bg-surface px-4 py-2 text-label hover:bg-surface-hover"
          />
          <CallControls microphoneTrack={microphoneTrack} onEnd={onEnd} />
        </section>
      </main>
      <NutritionPanel attribute={nutritionAttribute} />
    </div>
  );
}
