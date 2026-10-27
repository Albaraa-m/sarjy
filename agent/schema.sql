create table if not exists memories (
    user_id    text        not null,
    key        text        not null,
    value      text        not null,
    updated_at timestamptz not null default now(),
    primary key (user_id, key)
);


-- One row per food portion the user confirmed eating. Macros are a snapshot, so later USDA
-- changes don't alter past days.
create table if not exists food_log (
    id         bigserial        primary key,
    user_id    text             not null,
    eaten_on   date             not null,
    food       text             not null,
    display_name text,                    -- what the UI shows; null on rows saved before it existed
    grams      double precision not null,
    calories   double precision not null,
    protein_g  double precision not null,
    carbs_g    double precision not null,
    fat_g      double precision not null,
    source     text             not null,  -- 'usda' or 'estimate'
    created_at timestamptz      not null default now()
);
create index if not exists food_log_user_day on food_log (user_id, eaten_on);
alter table food_log add column if not exists display_name text;
