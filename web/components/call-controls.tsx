"use client";

import { type TrackReference, useTrackToggle } from "@livekit/components-react";
import { Track } from "livekit-client";
import { Mic, MicOff, PhoneOff } from "lucide-react";

import { AgentAudioVisualizerWave } from "@/components/agents-ui/agent-audio-visualizer-wave";
import { useCssColor } from "@/lib/use-css-color";
import { cn } from "@/lib/utils";

type CallControlsProps = {
  microphoneTrack: TrackReference | undefined;
  onEnd: () => void;
};

export function CallControls({ microphoneTrack, onEnd }: CallControlsProps) {
  const microphone = useTrackToggle({ source: Track.Source.Microphone });
  // The user's voice in gray, so purple stays Sarjy's.
  const waveColor = useCssColor("--color-fg-muted");

  return (
    <div className="flex flex-col items-center gap-4">
      {/* "speaking" makes the wave follow the volume of the track it's given: the user's mic. */}
      <AgentAudioVisualizerWave
        size="sm"
        state="speaking"
        color={waveColor}
        audioTrack={microphoneTrack}
        className={cn("aspect-auto w-64 transition-opacity", !microphone.enabled && "opacity-40")}
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void microphone.toggle()}
          disabled={microphone.pending}
          aria-label={microphone.enabled ? "Mute microphone" : "Unmute microphone"}
          aria-pressed={!microphone.enabled}
          className={cn(
            "grid size-12 place-items-center rounded-full border transition",
            microphone.enabled
              ? "border-line bg-surface text-fg hover:bg-surface-hover"
              : "border-accent bg-accent-soft text-fg",
          )}
        >
          {microphone.enabled ? <Mic className="size-4.5" /> : <MicOff className="size-4.5" />}
        </button>
        <button
          type="button"
          onClick={onEnd}
          aria-label="End call"
          className="grid size-12 place-items-center rounded-full border border-line bg-surface text-fg-muted transition hover:bg-surface-hover hover:text-fg"
        >
          <PhoneOff className="size-4.5" />
        </button>
      </div>
    </div>
  );
}
