# Voice Agent - Interview Preparation Guide

This guide is designed to help you defend the three specific bullet points on your resume regarding the Multilingual AI Voice System. The questions and answers are structured from the perspective of an **AI/Data Science Engineer** who designed the intelligence, prompt logic, and tool architecture.

---

## Resume Bullet 1: Conversational Design & Multilingual Architecture
> *"Worked on the development of a conversational Design & human-like multilingual AI voice system capable of handling more than 1000+ calls daily. The platform integrates speech-to-text (STT), text-to-speech (TTS), and LLM to deliver natural interactions."*

### Q1: How did you handle multilingual context switching where users might speak Hindi, Odia, or English?
**Answer Pointers:**
- **Dynamic Tagging Strategy:** Explain that the Speech-to-Text (STT) layer (Sarvam API) detects the spoken language. We passed this raw language code into the LLM system prompt as a dynamic tag (e.g., `[LANGUAGE: or/hi/en]`) injected into every user turn.
- **Strict Persona Constraints:** The `agent_prompt.py` was heavily engineered with absolute priority rules. If the tag was Odia, the LLM was restricted to 100% Odia script.
- **Data Normalization:** Emphasize that while interaction was multilingual, all backend queries needed to be English. You built the logic that forced the LLM to translate Odia/Hindi names, specialties, and numeric time ("ସକାଳେ" to "AM") back into English *before* passing parameters to the Function Calling tools.

### Q2: How did you ensure the conversations felt “human-like” rather than robotic?
**Answer Pointers:**
- **Latency Overbreadth:** Conversational design relies on low latency. Talk about optimizing the Voice Activity Detection (VAD) buffer frames so the bot knows exactly when to stop listening and start processing, reducing awkward silence.
- **Formatting Constraints Restrictions:** LLMs love using markdown (asterisks, bullet points). You strictly prohibited Markdown in the system prompt (`NO MARKDOWN EVER`) because STT/TTS architectures crash or sound robotic when trying to vocalize asterisks.
- **Terse, 20-word limits:** You engineered the prompts to keep responses under 20 words. Humans over the phone don't want paragraphs; they want direct, conversational back-and-forth.

---

## Resume Bullet 2: Autonomous Tooling & Impact
> *"Reduced manual appointment scheduling and admin work by 70% by building a multilingual AI voice system that autonomously manages registration, rescheduling, and cancellations, without human intervention."*

### Q3: How did the system autonomously schedule appointments without hallucinating slots that didn’t exist?
**Answer Pointers:**
- **Deterministic 6-Step Flow:** You designed a strict, unbendable 6-step conversational flow inside the `agent_prompt.py`. The LLM was forbidden from guessing availability.
- **OpenAI Function Calling (Tools):** You designed JSON schemas (`check_specialty_availability`, `book_appointment`) in `llm_engine.py` using OpenAI's tool-calling API. 
- **The Query Loop:** Explain the `while True:` loop architecture. When the user asks for a booking, the LLM generates a tool call, queries the live `hospital_db.json`, receives the JSON slot data, translates it to the user's requested language, and *then* speaks. 

### Q4: How did the AI handle complex tasks like 'Rescheduling' vs. 'Canceling'?
**Answer Pointers:**
- **Slot Conflict Matrix Verification:** Before modifying an appointment, the system had to verify that the target doctor wasn't double-booked. You provided the LLM with a `modify_appointment` tool that checked an internal slot matrix constraint.
- **Caller Context Verification:** The system relied on Webhook integrations with telephony providers (like Twilio/Plivo/Bolna) to pull the caller’s `from_number`. You enforced a rule that the agent must read the user's phone number digit-by-digit back to them to get explicit confirmation before altering database entries.

---

## Resume Bullet 3: Prompt Engineering & Reliability
> *"Used multimodal AI and prompt engineering to build reliable, real-time systems, achieving 95% call completion rate with accurate and consistent responses."*

### Q5: Achieving a 95% completion rate implies very high reliability. What prompt engineering techniques did you use to prevent the LLM from getting confused or going off-topic?
**Answer Pointers:**
- **Guardrails & Fallback Behaviors:** You built specific instructions for Edge cases. For example, if a user mumbled or the intent was unclear after 2 turns, the agent had a rule: *"ask 'Book, modify, or cancel?'"*. Or, if an unrelated medical question was asked, the bot politely redirected back to appointment logistics.
- **Temperature Control:** Highlight that you set the LLM Temperature extremely low (`0.05` in `llm_engine.py`) to enforce highly deterministic, consistent behavior. A receptionist bot does not need creativity; it needs accuracy.
- **Data Engineering for Digits:** Phone numbers over voice are incredibly difficult. You wrote specific prompts explaining how to process stringified digits (transforming Odia word-numbers into pure digits) and instructed the system to pause when reading back numbers.

### Q6: If the user suddenly interrupts the AI and changes their mind halfway through booking, how does your architecture handle that?
**Answer Pointers:**
- **Asynchronous Execution & Session Memory:** The `llm_engine.py` maintains an append-only conversation history (messages array). If the user interrupts, the new transcript segment is tacked onto the array.
- **Turn-by-turn re-evaluation:** Because every utterance is processed as a brand new inference call containing the full prior context, the LLM naturally handles the pivot. If it had partially collected "Cardiology, next Monday," but the user interrupts with "Wait, no, Orthopedics tomorrow", the context updates. The functional design means the LLM simply drops the `book_appointment` action and triggers the `check_specialty_availability` tool for Orthopedics.



How the call is happeing

Here is the exact step-by-step breakdown of your conversation, analyzing exactly where STT (Speech-to-Text), LLM (Language Model/Brain), and TTS (Text-to-Speech) are firing during each specific turn based on your system's architecture.

In a real-time voice system like yours, all three happen in a pipeline loop during every single interaction.

Step 1: You Start the Call
You say: "Hello, I want to book an appointment." (English) Agent replies: "ଆପଣ କେଉଁ ବିଭାଗରେ ଦେଖାଇବାକୁ ଚାହୁଁଛନ୍ତି? ଆମ ପାଖରେ କାର୍ଡିଓଲୋଜି..." (Odia)

STT (Sarvam AI): Listens to your voice audio over the phone line and transcribes it precisely to the text string: "Hello, I want to book an appointment." It also analyzes your voice and attaches a language tag (e.g., [LANGUAGE: en]).
LLM (GPT-4o / Engine): Receives the STT text. It looks at the 6-step prompt rules and realizes this is Step 1: Ask Department. It generates the required text string asking for the department. (Note: If it replied in Odia here, the LLM either had a forced Odia persona constraint in the prompt, or the STT detected an Indic dialect and passed [LANGUAGE: or] by mistake).
TTS (Sarvam AI): Takes the Odia text string from the LLM, synthesizes a female/male Odia voice audio file, and streams it back to your ear over the phone.
Step 2: You Pick the Department
You say: "ମୁଁ କାର୍ଡିଓଲୋଜି ବିଭାଗରେ ଦେଖାଇବାକୁ ଚାହୁଁଛି।" (Odia) Agent replies: "ଏହି ବିଭାଗରେ ଉପଲବ୍ଧ ଡାକ୍ତରମାନେ ହେଉଛନ୍ତି... ଆପଣ କାହା ପାଖରେ ଦେଖାଇବେ?" (Odia)

STT: Captures your Odia pronunciation and transcribes it natively into the Odia script. It assigns the [LANGUAGE: or] tag.
LLM:
Reads the Odia text and recognizes you want the Cardiology department.
Translates: The LLM internally translates "କାର୍ଡିଓଲୋଜି" to the English "Cardiology".
Function Call / Tool Use: It pauses the conversation to execute the check_specialty_availability tool to look up doctors in the JSON database.
Generates Response: The tool returns the English names of the doctors. The LLM creates the sentence in Odia asking you to pick one.
TTS: Synthesizes the new Odia text into audio and plays it.
Step 3: You Pick the Doctor
You say: "Dr. Anupam Jena." (English/Name) Agent replies: "ଡାକ୍ତର [Anupam Jena] ଙ୍କ ପାଇଁ ଏହି ସମୟ ଗୁଡିକ ଖାଲି ଅଛି... ଆପଣ କେଉଁ ସମୟ ବାଛିବେ?" (Odia)

STT: Transcribes the name. Even if you speak the name with an English accent, the STT writes it down as text.
LLM:
Matches the name "Anupam Jena" to DR001 in its internal reference prompt.
Executes the check_doctor_availability tool.
Receives JSON arrays of available time slots (e.g., ["Monday 10:00 AM", ...]).
Translates those English slot concepts into natural Odia text.
TTS: Reads the translated Odia slots out loud directly to the caller.
Step 4: You Pick the Time Slot in a DIFFERENT Language
You say: "सोमवार सुबह दस बजे।" (Hindi) Agent replies: "ଦୟାକରି ଆପଣଙ୍କ ୧୦ ଅଙ୍କ ବିଶିଷ୍ଟ ମୋବାଇଲ ନମ୍ବର ଏକସାଥିରେ କୁହନ୍ତୁ।" (Odia)

STT: This is where the magic happens. The STT immediately recognizes the language swap, transcribing the audio into Devanagari script (सोमवार सुबह दस बजे) and assigns a new tag: [LANGUAGE: hi].
LLM:
Realizes you have picked a slot.
Converts the Hindi "सोमवार सुबह दस बजे" internally to "Monday 10:00 AM" to keep the booking data clean.
Progresses exactly to Step 4: Confirm Phone Number and generates the prompt asking for your phone number. (Note: Since it replied in Odia, the LLM is maintaining the conversation's base language despite your Hindi response).
TTS: Reads the text asking for the 10-digit number.
Step 5: You Say Your Phone Number
You say: "ଆଠ ପାଞ୍ଚ ଏକ ଶୂନ ଆଠ ଚାରି ଶୂନ ଛଅ ଶୂନ ସାତ।" (Odia words for 8510840607) Agent replies: "ଆପଣଙ୍କ ଅାପଏଣ୍ଟ୍ ମେଣ୍ଟ ବୁକ୍ କରିବା ପାଇଁ, ଦୟାକରି ରୋଗୀଙ୍କ ନାମ କୁହନ୍ତୁ।" (Odia)

STT: Hears your vocalized Odia numbers and writes them as Odia text strings ("ଆଠ", "ପାଞ୍ଚ", etc).
LLM:
Uses its raw intelligence to map Odia word numbers to actual integers (8510840607).
Formats it according to your exact rules: +918510840607.
Moves to Step 5: Ask Patient Name, generating the text to ask for a name.
TTS: Synthesizes that text into audio to ask the user.
Step 6: You Say Your Name
You say: "Mera naam Priya Sharma hai." (Hindi)

STT: Picks up the language shift again, transcribes it into Devanagari Hindi text (मेरा नाम प्रिया शर्मा है), and tags it [LANGUAGE: hi].
LLM:
Runs Entity Extraction to realize the patient's name is "Priya Sharma".
Now has all the variables required: Department, Doctor, Day, Time, Phone, and Name.
Executes the final book_appointment tool to write "Priya Sharma" into the JSON/Database.
Generates a successful confirmation message.
TTS: Speaks the final confirmation string, ending the interaction block.
   