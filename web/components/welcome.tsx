"use client";

import { type FormEvent, useState } from "react";

import { SarjyAura } from "@/components/sarjy-aura";
import { USERNAME_PATTERN } from "@/lib/username-pattern";

type WelcomeProps = {
  onStart: (username: string) => void;
};

export function Welcome({ onStart }: WelcomeProps) {
  const [input, setInput] = useState("");
  const username = input.trim().toLowerCase();

  function submit(event: FormEvent) {
    event.preventDefault();
    onStart(username);
  }

  return (
    <section className="flex flex-1 flex-col items-center justify-center gap-8">
      <SarjyAura size="lg" state="idle" />
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">Talk to Sarjy</h1>
        <p className="text-foreground/60">Your voice assistant. Just speak.</p>
      </div>
      <form onSubmit={submit} className="flex w-full max-w-xs flex-col gap-3">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Your name"
          aria-label="Your name"
          autoComplete="given-name"
          autoFocus
          className="h-12 rounded-full border border-white/10 bg-white/5 px-5 text-center outline-none transition placeholder:text-foreground/40 focus:border-accent/60"
        />
        <button
          type="submit"
          disabled={!USERNAME_PATTERN.test(username)}
          className="h-12 rounded-full bg-accent font-medium text-background transition hover:opacity-90 disabled:opacity-30"
        >
          Start talking
        </button>
      </form>
      <p className="text-xs text-foreground/40">Uses your microphone.</p>
    </section>
  );
}
