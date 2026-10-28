# Diagrams

## Architecture

![Sarjy architecture](architecture.excalidraw.svg)

## Memory flow

```
SESSION START
┌──────────┐   load facts   ┌─────────────────┐
│ Postgres │ ─────────────► │  System prompt  │ ──► greeting by name
│ memories │                │ (+ known facts) │
└──────────┘                └─────────────────┘

EVERY USER TURN  (background, one at a time)
┌───────────────┐  turn + known facts  ┌───────────────┐  set / remove  ┌──────────┐
│ Conversation  │ ───────────────────► │ LLM extractor │ ─────────────► │ Postgres │
│               │                      │ (Groq 20B)    │                │ memories │
└───────────────┘                      └───────────────┘                └──────────┘
                                          ▲
CALL END ── any leftover turns ───────────┘
```

- A fact is saved seconds after it's said, so a redial right after hanging up already knows it.

## Nutrition flow

```
                         ┌──────┐
            "I had X"    │ User │   "yes" / "no" / "no milk"
         ┌───────────────┤      ├────────────────┐
         ▼               └──▲───┘                ▼
   ┌───────────┐            │ read-back    ┌───────────┐
   │    LLM    │────────────┘ "log it?"    │    LLM    │
   └─────┬─────┘                           └─────┬─────┘
         │ lookup_nutrition                      │ confirm_portions
         ▼                                       │ cancel_portions (all / by name)
   ┌───────────┐                                 │
   │ USDA API  │                                 │
   └─────┬─────┘                                 │
    found│     not found                         │
         ▼          ▼                            │
 ┌───────────────┐ ┌──────────────────────────┐  │
 │propose_portion│ │propose_estimated_portion │  │
 │ (USDA fdc_id) │ │ (LLM's numbers, flagged) │  │
 └───────┬───────┘ └────────────┬─────────────┘  │
         └──────────┬───────────┘                │
                    ▼                            ▼
       ┌─────────────────────────────────────────────┐
       │                Diary (agent)                │
       │      pending ──confirm──► eaten             │
       │         └──────cancel───► dropped           │
       └───────┬──────────────────────────┬──────────┘
               │ save (on confirm)        │ DailyIntake on every change
               ▼                          ▼
        ┌────────────┐             ┌────────────┐
        │  Postgres  │             │ Web panel  │
        │  food_log  │             │ (via Room) │
        └────────────┘             └────────────┘
```