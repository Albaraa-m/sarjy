import { VoiceSession } from "@/components/voice-session";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8">
      <h1 className="text-2xl font-semibold">Sarjy</h1>
      <VoiceSession />
    </main>
  );
}
