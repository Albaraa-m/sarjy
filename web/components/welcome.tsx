"use client";

import { CornerDownLeft } from "lucide-react";
import { type FormEvent, useState } from "react";

import { SarjyAura } from "@/components/sarjy-aura";
import { USERNAME_PATTERN } from "@/lib/username-pattern";
import { cn } from "@/lib/utils";

type WelcomeProps = {
  onStart: (username: string) => void;
};

export function Welcome({ onStart }: WelcomeProps) {
  const [input, setInput] = useState("");
  const username = input.trim().toLowerCase();
  const isValid = USERNAME_PATTERN.test(username);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (isValid) {
      onStart(username);
    }
  }

  return (
    <section className="flex flex-1 flex-col items-center justify-center pb-14">
      <SarjyAura size="xl" state="idle" className="-mt-14 -mb-16" />
      <form
        onSubmit={submit}
        className="flex w-full max-w-xs items-center gap-2 border-b border-line transition focus-within:border-accent-line"
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="username"
          aria-label="Username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          autoFocus
          className="h-10 min-w-0 flex-1 bg-transparent text-body outline-none placeholder:text-fg-faint"
        />
        {/* Stays mounted while hidden, so the field doesn't shift when it appears. */}
        <button
          type="submit"
          disabled={!isValid}
          aria-label="Start talking"
          className={cn(
            "grid size-7 place-items-center rounded-tag text-fg-muted transition outline-none hover:bg-surface-hover hover:text-fg focus-visible:ring-3 focus-visible:ring-accent-soft",
            !isValid && "invisible opacity-0",
          )}
        >
          <CornerDownLeft className="size-4" />
        </button>
      </form>
    </section>
  );
}
