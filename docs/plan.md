# Product Requirements

## Overview 
Build Sarjy, a voice assistant that listens and responds by voice.

## Functional Requirements
- Accessed through the browser
- Listens and responds by voice
- Remembers facts / preferences / etc.  across sessions: "What's my favorite color?" should work if you told it earlier.
- Calls at least one external API that makes it more useful
- Should be accessible via a working deployment URL that the reviewer can open without special setup.
  
## Non-functional Requirements
- Latency: For a real-time voice assistant, target is < 1 s time-to-first-audio
  
## Out of scope
- Scalability: For the purposes of this project, assume 1-2 concurrent users

## Key Scenarios
- Scenario 1: User asks a general question -> Sarjy responds 
- Scenario 2: User asks/requests something -> Sarjy calls the external API and responds
- Scenario 3: User asks/requests something Sarjy does not support -> Sarjy responds that it cannot do it
- Scenario 4: User shares a fact/preference -> In a later session, Sarjy recalls it

## Success Metrics
- Time-to-first-audio < 1 s 
- Memory recall works 100% in demo

## Deep Dive
Chosen Area: Latency 
*Details TBD*

---------------------------------

# Technical Design

## Architecture
Cascaded pipeline (STT -> LLM -> TTS) on LiveKit.

```
Browser (Next.js) --token--> Vercel /api/token
   |
   | WebRTC audio
   v
LiveKit Cloud (room) <--WebRTC audio--> Agent worker (LiveKit Agents)
                                          |-- Deepgram (STT)
                                          |-- Groq (LLM)
                                          |-- Cartesia (TTS)
                                          |-- Postgres (memory)
                                          |-- External API (TBD)
```

## Tech choices
- Framework: LiveKit
- STT: Deepgram Nova-3
- LLM: Groq gpt-oss-120b, low reasoning
- TTS: Cartesia Sonic
- DB: Postgres on Supabase
- Hosting: Frontend on Vercel, Agent on LiveKit Cloud

## Key Flows
- Conversation turn: User speaks -> turn detector detects end of speech -> STT final transcript -> LLM streams tokens -> TTS streams audio -> User hears response
- Memory read: On session start, load user's facts into the system prompt (no per-turn lookup)
- Memory write: After each turn, extract facts in the background and upsert by (user_id, key)
- User identity: Anonymous ID in browser localStorage, passed as LiveKit participant identity
- Tool call: LLM calls external API tool -> result fed back to LLM -> responds

## Deep Dive Design
*Details TBD*

---------------------------------

### Milestones
- [] Create a Voice agent that listens and responds 
- [] Allow the agent to remember facts/preferences
- [] Add an external API
- [] Deploy
- [] Deep dive into latency
- [] Write-up

### Open Questions
- What should the external API be?
- What latency levers to tune?
- What guardrails (if any)?
- Should I maintain evals?
- How much does deployment region affect latency?

### Decision Log
- Cascaded (STT -> LLM -> TTS) over Managed Voice API / Speech-to-Speech: control over per-stage latency and swapping providers
- LiveKit over Pipecat: per-stage metrics + semantic turn detector (either works)
- Deepgram Nova-3 over Groq Whisper: streams partial transcripts
- Groq gpt-oss-120b (easy to switch)
- Cartesia Sonic over ElevenLabs / Deepgram Aura-2 / Groq TTS: fastest time-to-first-audio
