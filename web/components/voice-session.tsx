"use client";

import { RoomAudioRenderer, SessionProvider, useAgent, useSession } from "@livekit/components-react";
import { TokenSource } from "livekit-client";
import { useState } from "react";

const TOKEN_SOURCE = TokenSource.endpoint("/api/token");
// Fixed until each browser gets its own identity (milestone 5).
const PARTICIPANT_IDENTITY = "web-dev";

export function VoiceSession() {
  const session = useSession(TOKEN_SOURCE, { participantIdentity: PARTICIPANT_IDENTITY });
  const agent = useAgent(session);
  const [error, setError] = useState<string | null>(null);

  async function toggleCall() {
    setError(null);
    try {
      if (session.isConnected) {
        await session.end();
      } else {
        await session.start({ tracks: { microphone: { enabled: true } } });
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  return (
    <SessionProvider session={session}>
      <RoomAudioRenderer />
      <div className="flex flex-col items-center gap-4">
        <p>Sarjy is {agent.state}</p>
        {agent.state === "failed" && <p>{agent.failureReasons.join(", ")}</p>}
        {error && <p>{error}</p>}
        <button
          type="button"
          onClick={() => void toggleCall()}
          disabled={session.connectionState === "connecting"}
          className="rounded-full border px-6 py-2 disabled:opacity-50"
        >
          {session.isConnected ? "End" : "Start"}
        </button>
      </div>
    </SessionProvider>
  );
}
