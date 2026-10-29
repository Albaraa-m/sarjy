# Sarjy: Writeup

## Deep dive: food logging by voice

Food logging lets you tell Sarjy what you ate; it looks each food up in USDA, confirms the portions with you, and adds them to a daily log shown live on screen.

### Why food logging

Food logging exercises the whole system end to end, not one layer of it. One sentence ("I had two eggs and toast") goes through:

1. **Browser → agent:** mic audio over WebRTC (LiveKit) to the agent.
2. **STT:** Deepgram turns the audio into a transcript.
3. **LLM:** chooses which tools to call: look up each food, then propose a portion for each.
4. **External API:** USDA FoodData Central returns the nutrition data, and the server scales it to the portion.
5. **Database:** confirmed portions are saved to Postgres.
6. **Agent → browser, two channels at once:** Sarjy's reply is spoken by Cartesia TTS, while the food log is published to the room as structured state, and the UI shows it as it changes.

Mainly, I wanted to learn how voice and visuals can work together in real time. Most voice agents stop at audio in and audio out. I wanted the agent to publish structured JSON over the same LiveKit connection as the audio stream, so the browser could subscribe to it and re-render as the conversation moves. Every tool call is a state change the UI can show: a proposed food appears as pending while Sarjy reads it back, and a confirmed one moves to the log with updated macros/calories while Sarjy is still replying.

## How the work went

I had little time on days 1 and 2, so most of the building happened on days 3 to 5.

### Day 1: Planning

- **Docs:** Wrote the PRD/TDD before building.
- **Setup:** Created accounts for the providers (LiveKit, Deepgram, Groq, Cerebras, Cartesia).
- **Agent:** Set up a minimal cascaded voice agent (STT → LLM → TTS) with a LiveKit Cloud deployment config.

### Day 2: Core features

- **Memory:** Built cross-session memory: facts are pulled from the conversation and stored in Postgres.
- **Nutrition:** Gave the agent access to the USDA FoodData Central API.
- **Nutrition:** Built an early version of food logging (removed later and rebuilt on day 4).
- **Testing:** Set up a pytest suite that runs the agent with a real LLM.
- **Agent:** Split Nutrition and Memory into self-contained modules.
- **UX:** First round of voice tuning: replies written to be spoken, more patient turn-taking, and filler lines during slow lookups.

### Day 3: LLM reliability + web app

- **Agent:** Moved the main LLM to Qwen on Cerebras, with gpt-oss on Groq as fallback, because of free-tier rate limits.
- **Reliability:** Fixed replies cut short, made-up nutrition numbers, filler lines leaking into the chat history, and the assistant's name being saved as the user's.
- **Reliability:** Added logging for each reply (LLM output vs. spoken text vs. interruptions).
- **Prompt/Identity:** Presented Sarjy as a personal assistant that remembers naturally. Greets with a fixed line, and Deepgram is boosted to hear "Sarjy".
- **Web:** Built the Next.js app: token route, username gate, and a voice UI with the Aura visualizer and call controls.

### Day 4: Food logging (deep dive) + voice and UI polish

- **Nutrition:** Food logging by voice, end to end:
  - **Voice:** Say a food or a whole meal. Sarjy reads it back, and you confirm or change it ("yes, but no milk").
  - **Tool calls:** The agent looks foods up in USDA (raw foods and prepared dishes), proposes portions, and holds them as pending until you confirm.
  - **Data integrity:** The LLM picks a USDA match; the server computes and saves the numbers, so no saved number comes from the LLM.
  - **Database:** Confirmed portions go to a `food_log` table in Postgres.
  - **Live UI:** The agent publishes today's log (pending foods, logged foods, totals) to the LiveKit room. The web sidebar updates as you speak.
- **Reliability:** One shared database pool with fast timeouts and retries.
- **UX:** Upgraded TTS to Cartesia sonic-3.6, changed the voice, and tried to make it pronounce "Sarjy" the Arabic way (it doesn't work reliably).
- **Prompt/Identity:** Plain, conversational replies; greets and says goodbye by name.
- **Web:** Redesigned the UI: design tokens, purple accent, docked food log with goal meters, over-target states and animations.

### Day 5: Memory rewrite, code quality, docs

- **Memory:** Rewrote the memory module so it sees what Sarjy said, not just the user's message, and can remove or change facts as well as add them.
- **Code quality:** Big refactor, driven by Sarj's lint rules: typed Settings, Pydantic models, clearer naming, and fewer comments.
- **UX:** Asks for the missing word when speech recognition is unsure.
- **Web:** Polished the UI: simpler welcome screen, Instrument Sans, larger wordmark.
- **Docs:** Architecture, memory and nutrition flow diagrams; README; Loom demo.
