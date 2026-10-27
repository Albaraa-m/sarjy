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
    <section className="flex flex-1 flex-col items-center justify-center gap-6 pb-14">
      <SarjyAura size="xl" state="idle" className="-mt-14 -mb-20" />
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-display font-semibold tracking-tight">Talk to Sarjy</h1>
        <p className="text-body text-fg-muted">Your voice assistant. Just speak.</p>
      </div>
      <form onSubmit={submit} className="mt-2 flex w-full max-w-xs flex-col gap-2">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Your name"
          aria-label="Your name"
          autoComplete="given-name"
          autoFocus
          className="h-11 rounded-control border border-line bg-surface px-4 text-center text-body outline-none transition placeholder:text-fg-faint focus:border-accent"
        />
        <button
          type="submit"
          disabled={!USERNAME_PATTERN.test(username)}
          className="h-11 rounded-control bg-accent text-body font-medium text-fg transition hover:opacity-90 disabled:opacity-35"
        >
          Start talking
        </button>
      </form>
      <p className="text-caption text-fg-faint">Uses your microphone.</p>
    </section>
  );
}
