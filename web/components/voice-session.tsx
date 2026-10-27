"use client";

import {
  RoomAudioRenderer,
  SessionProvider,
  StartAudio,
  useAgent,
  useSession,
} from "@livekit/components-react";
import { TokenSource } from "livekit-client";
import { useEffect, useState } from "react";

import { CallControls } from "@/components/call-controls";
import { NutritionPanel } from "@/components/nutrition-panel";
import { SarjyAura } from "@/components/sarjy-aura";
import { Welcome } from "@/components/welcome";

const TOKEN_SOURCE = TokenSource.endpoint("/api/token");

export function VoiceSession() {
  const [username, setUsername] = useState<string | null>(null);

  return (
    <div className="flex min-h-dvh flex-col px-6 py-5">
      <header className="flex items-center justify-between text-label">
        <span className="font-semibold tracking-tight">Sarjy</span>
        {username && <span className="text-fg-muted">{username}</span>}
      </header>
      {username ? (
        <Conversation username={username} onEnd={() => setUsername(null)} />
      ) : (
        <Welcome onStart={setUsername} />
      )}
    </div>
  );
}

type ConversationProps = {
  username: string;
  onEnd: () => void;
};

function Conversation({ username, onEnd }: ConversationProps) {
  const session = useSession(TOKEN_SOURCE, { participantIdentity: username });
  const agent = useAgent(session);
  const [error, setError] = useState<string | null>(null);
  const { start, end } = session;

  // Shown right after the Start click, so the call starts immediately; leaving ends it.
  useEffect(() => {
    start({ tracks: { microphone: { enabled: true } } }).catch((caught: unknown) => {
      setError(caught instanceof Error ? caught.message : String(caught));
    });
    return () => void end();
  }, [start, end]);

  const failure = error ?? (agent.state === "failed" ? agent.failureReasons.join(", ") : null);

  return (
    <SessionProvider session={session}>
      <RoomAudioRenderer />
      <div className="flex flex-1 flex-col items-center justify-center gap-8 py-6 md:flex-row md:gap-16">
        <section className="flex flex-col items-center gap-4">
          <SarjyAura size="lg" state={agent.state} audioTrack={agent.microphoneTrack} />
          {/* The Aura shows listening, thinking and speaking; text is only for what it can't. */}
          <p className={failure ? "h-6 text-warning" : "h-6 text-fg-muted"}>
            {failure ?? (agent.isConnected ? null : "Connecting…")}
          </p>
          <StartAudio
            label="Tap to hear Sarjy"
            className="rounded-full border border-line bg-surface px-4 py-2 text-label hover:bg-surface-hover"
          />
        </section>
        <NutritionPanel attribute={agent.attributes.nutrition} />
      </div>
      <CallControls microphoneTrack={session.local.microphoneTrack} onEnd={onEnd} />
    </SessionProvider>
  );
}
