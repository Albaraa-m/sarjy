"use client";

import { type FormEvent, useState } from "react";

import { USERNAME_PATTERN } from "@/lib/username-pattern";

type UsernameFormProps = {
  onSubmit: (username: string) => void;
};

export function UsernameForm({ onSubmit }: UsernameFormProps) {
  const [input, setInput] = useState("");
  const username = input.trim().toLowerCase();

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit(username);
  }

  return (
    <form onSubmit={submit} className="flex flex-col items-center gap-3">
      <input
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder="Your name"
        aria-label="Your name"
        autoFocus
        className="rounded-full border px-4 py-2 text-center"
      />
      <p className="text-sm opacity-60">Sarjy remembers you by this name.</p>
      <button
        type="submit"
        disabled={!USERNAME_PATTERN.test(username)}
        className="rounded-full border px-6 py-2 disabled:opacity-50"
      >
        Start
      </button>
    </form>
  );
}
