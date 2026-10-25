create table if not exists memories (
    user_id    text        not null,
    key        text        not null,
    value      text        not null,
    updated_at timestamptz not null default now(),
    primary key (user_id, key)
);

