"use client";

import { type TrackReference, useTrackToggle } from "@livekit/components-react";
import { Track } from "livekit-client";
import { Mic, MicOff, PhoneOff } from "lucide-react";

import { AgentAudioVisualizerWave } from "@/components/agents-ui/agent-audio-visualizer-wave";
import { cn } from "@/lib/utils";

type CallControlsProps = {
  microphoneTrack: TrackReference | undefined;
  onEnd: () => void;
};

export function CallControls({ microphoneTrack, onEnd }: CallControlsProps) {
  const microphone = useTrackToggle({ source: Track.Source.Microphone });

  return (
    <footer className="flex flex-col items-center gap-4">
      {/* "speaking" makes the wave follow the volume of the track it's given: the user's mic. */}
      <AgentAudioVisualizerWave
        size="sm"
        state="speaking"
        audioTrack={microphoneTrack}
        className={cn("aspect-auto w-56 transition-opacity", !microphone.enabled && "opacity-20")}
      />
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => void microphone.toggle()}
          disabled={microphone.pending}
          aria-label={microphone.enabled ? "Mute microphone" : "Unmute microphone"}
          aria-pressed={!microphone.enabled}
          className={cn(
            "grid size-14 place-items-center rounded-full transition",
            microphone.enabled ? "bg-white/10 hover:bg-white/15" : "bg-foreground text-background",
          )}
        >
          {microphone.enabled ? <Mic className="size-5" /> : <MicOff className="size-5" />}
        </button>
        <button
          type="button"
          onClick={onEnd}
          aria-label="End call"
          className="grid size-14 place-items-center rounded-full bg-danger text-white transition hover:opacity-90"
        >
          <PhoneOff className="size-5" />
        </button>
      </div>
    </footer>
  );
}
