import { AccessToken, RoomAgentDispatch, RoomConfiguration } from "livekit-server-sdk";
import { z } from "zod";

import { env } from "@/lib/env";
import { USERNAME_PATTERN } from "@/lib/username-pattern";

const AGENT_NAME = "sarjy";
const TOKEN_TTL = "10m";

// Request and response use the format LiveKit's browser SDK expects from our endpoint (snake_case):
// https://docs.livekit.io/frontends/authentication/tokens/endpoint/
const TokenRequestSchema = z.object({
  "participant_identity": z.string().regex(USERNAME_PATTERN),
});

type TokenResponse = {
  "server_url": string;
  "participant_token": string;
};

export async function POST(request: Request) {
  const identity = await readIdentity(request);
  if (!identity) {
    return Response.json({ error: "Invalid token request" }, { status: 400 });
  }

  const token = await createTokenForNewSarjyRoom(identity);
  const response: TokenResponse = { "server_url": env.LIVEKIT_URL, "participant_token": token };
  return Response.json(response, { status: 201 });
}

async function readIdentity(request: Request): Promise<string | null> {
  const body: unknown = await request.json().catch(() => null);
  const parsed = TokenRequestSchema.safeParse(body);
  return parsed.success ? parsed.data["participant_identity"] : null;
}

// The server picks the room and the agent, so the browser can't join other rooms or agents.
async function createTokenForNewSarjyRoom(identity: string): Promise<string> {
  const token = new AccessToken(env.LIVEKIT_API_KEY, env.LIVEKIT_API_SECRET, {
    identity,
    ttl: TOKEN_TTL,
  });
  token.addGrant({
    roomJoin: true,
    room: `sarjy-${crypto.randomUUID()}`,
    canPublish: true,
    canSubscribe: true,
  });
  token.roomConfig = new RoomConfiguration({
    agents: [new RoomAgentDispatch({ agentName: AGENT_NAME })],
  });
  return token.toJwt();
}
