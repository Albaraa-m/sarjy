type AppHeaderProps = {
  username: string | null;
};

export function AppHeader({ username }: AppHeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between">
      <span className="text-title font-semibold tracking-tight">Sarjy</span>
      {username && <span className="text-label text-fg-muted">{username}</span>}
    </header>
  );
}
