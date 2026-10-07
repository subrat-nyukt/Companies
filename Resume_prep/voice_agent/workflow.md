The 5 Layers Explained
Layer	File	Technology	What it does


1. Telephony	main.py /plivo/*	Plivo API	Answers the phone call, streams raw audio in/out


2. STT + VAD	sarvam_client.py SarvamSTT	Sarvam saaras:v3	Detects speech vs silence, converts voice to text, auto-detects language


3. LLM Brain	llm_engine.py ConversationManager	OpenAI GPT-4o	Understands intent, decides to reply or trigger a tool


4. Tools / DB	main.py _tool_* functions	JSON DB	Books/modifies/cancels appointments in the database


5. TTS	sarvam_client.py sarvam_tts()	Sarvam bulbul:v3	Converts GPT's text reply back to voice in user's language