import "server-only";
import { z } from "zod";

const EnvSchema = z.object({
  LIVEKIT_URL: z.url(),
  LIVEKIT_API_KEY: z.string().min(1),
  LIVEKIT_API_SECRET: z.string().min(1),
});

export const env = EnvSchema.parse(process.env);
