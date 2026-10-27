type AppHeaderProps = {
  username: string | null;
};

export function AppHeader({ username }: AppHeaderProps) {
  return (
    // Equal side columns keep the wordmark centered over the Aura, with or without a username.
    <header className="grid h-14 shrink-0 grid-cols-[1fr_auto_1fr] items-center">
      <span className="col-start-2 text-wordmark text-fg">Sarjy</span>
      {username && <span className="justify-self-end text-label text-fg-muted">{username}</span>}
    </header>
  );
}
