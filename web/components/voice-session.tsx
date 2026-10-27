"use client";

import { RoomAudioRenderer, SessionProvider, useAgent, useSession } from "@livekit/components-react";
import { TokenSource } from "livekit-client";
import { useEffect, useState } from "react";

import { AppHeader } from "@/components/app-header";
import { CallScreen } from "@/components/call-screen";
import { Welcome } from "@/components/welcome";

const TOKEN_SOURCE = TokenSource.endpoint("/api/token");

export function VoiceSession() {
  const [username, setUsername] = useState<string | null>(null);

  if (username) {
    return <Conversation username={username} onEnd={() => setUsername(null)} />;
  }
  return (
    <div className="flex h-dvh flex-col px-6">
      <AppHeader username={null} />
      <Welcome onStart={setUsername} />
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
  const status = failure
    ? { text: failure, isError: true }
    : agent.isConnected
      ? null
      : { text: "Connecting…", isError: false };

  return (
    <SessionProvider session={session}>
      <RoomAudioRenderer />
      <CallScreen
        username={username}
        agentState={agent.state}
        agentTrack={agent.microphoneTrack}
        microphoneTrack={session.local.microphoneTrack}
        status={status}
        nutritionAttribute={agent.attributes.nutrition}
        onEnd={onEnd}
      />
    </SessionProvider>
  );
}
