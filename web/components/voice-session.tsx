"use client";

import { RoomAudioRenderer, SessionProvider, useAgent, useSession } from "@livekit/components-react";
import { TokenSource } from "livekit-client";
import { useEffect, useState } from "react";

import { UsernameForm } from "@/components/username-form";

const TOKEN_SOURCE = TokenSource.endpoint("/api/token");

export function VoiceSession() {
  const [username, setUsername] = useState<string | null>(null);

  if (!username) {
    return <UsernameForm onSubmit={setUsername} />;
  }
  return <Conversation username={username} onEnd={() => setUsername(null)} />;
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

  return (
    <SessionProvider session={session}>
      <RoomAudioRenderer />
      <div className="flex flex-col items-center gap-4">
        <p>
          Hi {username}, Sarjy is {agent.state}
        </p>
        {agent.state === "failed" && <p>{agent.failureReasons.join(", ")}</p>}
        {error && <p>{error}</p>}
        <button type="button" onClick={onEnd} className="rounded-full border px-6 py-2">
          End
        </button>
      </div>
    </SessionProvider>
  );
}
