# Voice Agent Deep-Dive: Latency, Guardrails, Monitoring, and Production Guide

This document provides a highly technical, production-focused set of questions and answers regarding the **ChikitAI** voice agent. It covers latency engineering, guardrails, API limits, system monitoring, model drift, real-world production challenges, and cost optimization, matching the code implementation in [main.py](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/voice_agent/main.py), [sarvam_client.py](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/voice_agent/sarvam_client.py), and [llm_engine.py](file:///c:/Users/DELL/Downloads/Personal/Companies/Resume_prep/voice_agent/llm_engine.py).

---

## 1. System Architecture & API Integrations

### Q1: What is the high-level architecture of your voice agent, and how does the bidirectional data flow work?
**Answer Pointers:**
*   **Telephony Layer:** We use the **Plivo API**. When a call is established, Plivo queries our `/plivo/answer` HTTP endpoint, which returns XML instructing Plivo to open a bidirectional WebSocket connection to `/plivo/stream` streaming audio at `8000Hz` using single-channel, `8-bit mu-law` encoding.
*   **Speech-to-Text (STT) + local VAD:** Raw mu-law audio packets are streamed to our WebSocket. A local Voice Activity Detection (VAD) module processes these packets. Once silence is detected, the accumulated PCM frames are packed into a WAV container and sent to **Sarvam's Speech-to-Text API (`saaras:v3`)** for transcription and language auto-detection.
*   **LLM Brain:** The transcribed text is sent to the `ConversationManager` using **OpenAI's GPT-4o API** with structured tool-calling. It maintains the conversation state, executes local database functions based on tool schemas, and generates a conversational response.
*   **Text-to-Speech (TTS):** The LLM's text output is sent to **Sarvam's Text-to-Speech API (`bulbul:v3`)** to synthesize vocal audio, which is converted to mono `8000Hz mu-law` format and written back to the Plivo WebSocket.

### Q2: How does the system handle multilingual switching, and how does it inform the LLM of the detected language?
**Answer Pointers:**
*   **Auto-Detection at STT:** When sending WAV audio to Sarvam's `saaras:v3` STT endpoint, we set the `language_code` to `"unknown"`. The Sarvam API auto-detects the spoken language (Odia, Hindi, or English) and returns a language code (e.g., `od-IN`, `hi-IN`, `en-IN`).
*   **Language-Aware Injections:** Our `llm_engine.py` maps the language code to a two-letter string (`or`, `hi`, `en`) and prepends a prompt tag directly to the user's message: `[LANGUAGE: <lang>] <user_text>`.
*   **System Prompt Execution:** In `agent_prompt.py`, the system prompt contains strict rules for each tag:
    *   `[LANGUAGE: en]` $\rightarrow$ Respond 100% in English.
    *   `[LANGUAGE: hi]` $\rightarrow$ Respond 100% in Hindi (Devanagari script).
    *   `[LANGUAGE: or]` $\rightarrow$ Respond 100% in Odia (Odia script).
*   **Low-Temperature Adherence:** We set the LLM `temperature = 0.05` to guarantee it does not deviate from these strict script and language rules, preventing it from mixing scripts or writing Hindi words in English characters.

---

## 2. Latency Analysis & Optimization

### Q3: Break down the step-by-step latency of your pipeline. What is the typical "Time-to-Talk" (latency budget) for a turn?
**Answer Pointers:**
A realistic roundtrip latency breakdown (unmitigated) is between **2.2s and 4.7s**, categorized as follows:
1.  **VAD Silence Detection (600ms):** The system waits for `SILENCE_FRAMES_NEED = 24` (~0.6 seconds of silence) to ensure the user has finished speaking. This is a local buffer delay.
2.  **STT Transcription (300ms – 600ms):** Network roundtrip to Sarvam's `/speech-to-text` endpoint + server-side speech analysis and language classification.
3.  **LLM Inference & Tool Loops (800ms – 2500ms):** Sending the prompt, getting a response from GPT-4o. If tool execution is triggered, the model makes a tool call, the server executes it locally, and sends a second payload to GPT-4o. This loop can add an extra 1.0s – 1.5s.
4.  **TTS Audio Synthesis (400ms – 800ms):** Compiling text to voice via Sarvam's `/text-to-speech` endpoint and downloading the base64 WAV payload.
5.  **Audio Processing & WebSocket Transit (100ms – 200ms):** Converting WAV to mu-law PCM format locally and transmitting it to Plivo's server.

### Q4: How did you optimize and mask latency so callers don't experience awkward silence?
**Answer Pointers:**
We implemented three key optimizations to lower and mask latency:
*   **VAD Parameter Tuning:** In `sarvam_client.py`, we tuned the VAD parameters:
    *   `SILENCE_FRAMES_NEED` was reduced from `40` (1.0s) to `24` (~0.6s). This saved **400ms** of silence detection time.
    *   `MIN_SPEECH_FRAMES = 8` (~0.2s) ensures short clicks or heavy breathing are immediately skipped, saving STT roundtrips.
*   **Latency Masking (Thinking/Wait Messages):** We designed an asynchronous `on_thinking` callback in `main.py`. The moment the local VAD triggers transcription, the system immediately plays a localized, pre-synthesized or fast-synthesized "wait" message to the user (*"Please wait a moment"*, *"कृपया एक पल प्रतीक्षा करें"*, or *"ଟିକେ ମୁହୂର୍ତ୍ତ ଅପେକ୍ଷା କରନ୍ତୁ"*). While the caller is hearing this audio (~1 second long), the LLM inference and database tool logic are running in the background.
*   **Strict Brevity & Formatting Rules:** In `agent_prompt.py`, responses are strictly limited to **under 20 words** and markdown formatting is completely disabled (`NO MARKDOWN EVER`). Shorter text responses generate faster on OpenAI (lower TTFT) and drastically reduce TTS synthesis time.

---

## 3. Rate Limits & API Security

### Q5: How are rate limits implemented in your FastAPI backend, and what limits are enforced?
**Answer Pointers:**
*   **Limiter Framework:** We use `slowapi` (a port of `limits` to FastAPI) to rate-limit endpoints based on the caller's remote IP address.
*   **Endpoint-Specific Limits:**
    *   **Read-Only Tools:** `/tool/check-specialty`, `/tool/check-doctor`, and `/tool/get-appointments` are limited to **60 requests per minute**.
    *   **Write/Transaction Tools:** `/tool/book-appointment`, `/tool/modify-appointment`, `/tool/cancel-appointment`, and `/tool/register-patient` are limited to **30 requests per minute** to protect the database layer.
    *   **Outbound Call Trigger:** `/trigger-call` is limited to **10 requests per minute** to prevent spamming outbound networks.
    *   **Webhooks:** `/webhook/bolna` is limited to **60 requests per minute**.

### Q6: Why do write endpoints have stricter limits than read endpoints? How does this protect your business logic?
**Answer Pointers:**
*   **Database Lock Prevention:** The system currently operates on a local file-based database (`hospital_db.json`). Parallel writes can cause resource locks, latency spikes, or race conditions. Restricting writes prevents database access bottlenecks.
*   **Telephony Cost Control:** Call triggering and write transactions cost real money. Enforcing stricter limits prevents malicious actors from launching automated scripts that perform mass bookings, which would inflate LLM/TTS/Telephony api usage and exhaust our token balances.

---

## 4. Guardrails & Hallucination Prevention

### Q7: How does your conversational flow prevent the LLM from inventing (hallucinating) doctor availability or booking slots?
**Answer Pointers:**
*   **Deterministic Conversational Flow:** We enforce a strict **6-step appointment booking pipeline** inside `agent_prompt.py`. The LLM is prohibited from moving to the next step, skipping, or combining steps.
*   **API-First Enforcement:** In `STEP 3 — List Availability`, the system prompt strictly states: `Call check_doctor_availability FIRST. NEVER guess or invent slots.` The LLM cannot speak a slot until it has issued a tool call and received the JSON response.
*   **Low Temperature setting:** Setting the temperature to `0.05` forces the LLM to choose the highest-probability tokens, making its output highly predictable and restricting its creative generation of non-existent schedules.

### Q8: What data normalization guardrails exist between the multilingual voice interface and the English database?
**Answer Pointers:**
*   **Implicit Parameter Translation:** In `agent_prompt.py` and `main.py`, we enforce normalizations:
    *   **Name & Specialty Resolution:** If a patient says the doctor's name or specialty in Odia or Hindi (e.g., *"କାର୍ଡିଓଲୋଜି"* or *"ने कार्डियोलॉजी"*), the LLM must translate it to the English equivalent (`Cardiology`) and strip suffix grammar markers (like the Odia *"-nka"* or *"-anka"*) before passing the string to the tool parameter.
    *   **Time & Day Conversion:** In `main.py` (`_tool_book_appointment` and `_tool_modify_appointment`), we normalize incoming day names and times from Odia/Hindi strings back to English standard values (e.g., `"ସୋମବାର"` or `"सोमवार"` $\rightarrow$ `"Monday"`; `"ସକାଳେ"` or `"सुबह"` $\rightarrow$ `"AM"`) before performing DB slot lookups.
    *   **Phone Number Cleansing:** Spoken digits in Hindi (*"आठ, पाँच..."*) or Odia (*"ଆଠ, ପାଞ୍ଚ..."*) are mapped to integers, and standard formatting (`+91XXXXXXXXXX`) is enforced. If digit capture fails twice, the system falls back to the telephony provider's verified `from_number` header.

### Q9: How are database transactions protected against file corruption or race conditions?
**Answer Pointers:**
*   **Atomic Saves with Temp Files:** In `main.py`, the `save_db(data)` function does not write directly to the active file. It writes to a temporary file (`hospital_db.json.tmp`), creates a backup copy of the current state (`hospital_db.json.bak`), and then performs an atomic swap (`os.replace`) to overwrite `hospital_db.json`. If the write fails or the process crashes mid-save, the original database file is unharmed, and the backup is preserved.
*   **Capacity Checks:** The booking tool checks the slot conflict matrix (`_get_booked_slots`) before reserving a slot. If the slot is taken, the booking is rejected, and the LLM is returned a list of alternative slots.

---

## 5. Production Challenges & System Resilience

### Q10: How does the system handle user interruptions while the bot is speaking? What are the limitations and solutions?
**Answer Pointers:**
*   **Current Code Implementation:** In `main.py`, while the TTS audio is playing, the `is_speaking` variable is set to `True`. The websocket handler ignores incoming audio chunks during this time (`if stt and not is_speaking:`). This is a *half-duplex* limitation; the user cannot interrupt the bot.
*   **Production Solution (True Full-Duplex):**
    1.  **Remove the `is_speaking` lock** on audio capture, allowing the STT to always listen.
    2.  **Websocket Interruption Event:** If the local VAD detects speech energy (`rms > SILENCE_THRESHOLD`) while the bot is playing audio, the server must immediately send a `stopAudio` command to Plivo to kill the playback buffer.
    3.  **Context Truncation:** We would clear the TTS play queue and add the user's interruption transcript to the LLM history, generating a response based on the new context.

### Q11: How do you handle background noise (dogs, keyboard typing) or breathing sounds triggering empty STT requests?
**Answer Pointers:**
*   **Minimum Speech Length:** In `sarvam_client.py`, we enforce `MIN_SPEECH_FRAMES = 8` (~0.2s of audio). If the VAD detects silence before this limit is reached, it resets the buffer, filtering out brief transient sounds.
*   **VAD Energy Thresholding:** The `SILENCE_THRESHOLD = 400` is calibrated for typical telephony line noise.
*   **Transcription Quality Filtering:** If the STT endpoint transcribes background noises as gibberish, the `llm_engine` checks the string. In `agent_prompt.py`, the fallback rule directs the LLM to ask clarifying questions: *"Sorry, I couldn't hear you properly."*

### Q12: How do you handle network drops or WebSocket disconnects mid-call?
**Answer Pointers:**
*   **State Persistence:** The call state is managed in the `SESSIONS` memory store using the Plivo `CallUUID`. If the WebSocket drops, the FastAPI handler catches `WebSocketDisconnect` and runs cleanup logic (`stt.close()`, canceling the tasks).
*   **Call Completion Logging:** The session cleanup logs the transaction and call metadata to the `call_transcripts` section of the database. This allows analytics tools to track disconnected calls.
*   **Reconnection Logic:** Telephony webhooks would notify the system if a user redials. The system can inspect the database, recognize the phone number had an active session that failed step 6, and immediately say: *"I see we got disconnected. Were we booking Dr. Santosh Rath for Monday?"*

---

## 6. Monitoring, Evaluation & Drift

### Q13: What core metrics do you track in production to monitor the voice agent?
**Answer Pointers:**
*   **Call Completion Rate (CCR):** The percentage of calls that successfully complete a transaction (booking/cancellation/modification) versus those that hang up mid-flow. Target: >95%.
*   **Average Handling Time (AHT):** The average duration of a call. A shorter AHT usually implies efficient STT/TTS roundtrips and clear user navigation.
*   **Turn Latency (P50/P90/P99):** The delay between user silence and bot response.
*   **STT Word Error Rate (WER) & Language Match Rate:** How accurately Sarvam transcribes accents and dialects, and how often it accurately identifies the language.
*   **Tool Execution Error Rate:** The frequency of database or parameter errors during API tool calls.

### Q14: How do you evaluate the conversational accuracy of the LLM?
**Answer Pointers:**
*   **Semantic Verification (LLM-as-a-Judge):** We extract saved logs from `call_transcripts` and run an offline pipeline where a stronger model (e.g. GPT-4o with specialized evaluators) checks:
    *   *Script Adherence:* Did the bot speak the requested language script?
    *   *Domain Guardrails:* Did the bot stray into general medical advice?
    *   *Step Adherence:* Did the bot skip any of the 6 booking steps?
*   **Regression Testing:** Running simulated conversation trees (mocking STT inputs) against the system prompt to ensure that code changes do not alter conversational flows.

### Q15: Explain Model Drift and Data Drift in voice systems. How do you combat them?
**Answer Pointers:**
*   **Model Drift:** Occurs when the underlying LLM provider (e.g. OpenAI) updates their model weights (e.g., a new gpt-4o version). This can lead to changes in prompt interpretation, affecting word count restrictions or formatting rules.
    *   *Fix:* Pin specific model versions (e.g., `gpt-4o-2024-08-06` instead of the generic `gpt-4o` pointer) and run regression suites before upgrading.
*   **Data Drift:** Occurs when customer demographics or user behavior shifts (e.g. more callers using regional slang, or calling from high-noise environments).
    *   *Fix:* Continuously review low-confidence transcriptions and fine-tune STT acoustic models, or update the system prompt vocabulary to handle new synonyms.

---

## 7. Cost Minimization Strategies

### Q16: How do you optimize costs when running a voice agent in production?
**Answer Pointers:**
*   **Local VAD Execution:** Doing Voice Activity Detection locally means we only make STT REST calls when there is actual, verified speech. We avoid paying for continuous server-side audio processing.
*   **Audio and TTS Caching:** Static phrases (like greetings, standard questions, and wait messages) do not need to be synthesized by Sarvam bulbul:v3 on every call. We pre-synthesize common phrases, save them as WAV/mu-law files, and play them directly from local disk, saving TTS API costs and eliminating TTS latency.
*   **Prompt Optimization:** System prompts contribute heavily to input token costs. We can split the massive system prompt into dynamic sub-prompts or migrate simple operations to cheaper models (like `gpt-4o-mini`), using the expensive `gpt-4o` only for complex reasoning and tool execution.
*   **Connection Timeouts:** Implementing strict session timeouts (`SESSION_TTL_H = 2` and WebSocket idle limits) to free up memory and prevent hanging calls from accumulating telephony fees.
