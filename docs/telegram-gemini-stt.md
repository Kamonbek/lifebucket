# Telegram + Gemini STT (daily voice journal)

This service transcribes Telegram voice/audio messages with Gemini and stores them in:

- `logs/voice_journal.csv`

Script:
- `tools/telegram_gemini_stt_ingest.py`

## Recommended model
Default is:
- `gemini-2.5-flash`

Why: good transcription quality/cost/latency balance for daily voice notes.

You can override with env:
- `GEMINI_STT_MODEL=gemini-2.5-flash`

## Required env vars
- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)

## Run

```bash
cd /workspace/life-os
TELEGRAM_BOT_TOKEN=... GEMINI_API_KEY=... python3 tools/telegram_gemini_stt_ingest.py
```

Optional:
- `TELEGRAM_POLL_SECONDS=2`

## Behavior
- Polls Telegram updates continuously
- Accepts `voice`, `audio`, and `document` with `audio/*` mime type
- Sends transcript back into Telegram chat
- Appends each transcript row to `logs/voice_journal.csv`
- Stores last Telegram offset in `.state/telegram_offset.txt`

## CSV schema
`voice_journal.csv` columns:
- `created_at_utc`
- `chat_id`
- `user_id`
- `username`
- `message_id`
- `file_id`
- `mime_type`
- `duration_sec`
- `gemini_model`
- `transcript`

## Notes
- This is separate from Hermes built-in STT provider config.
- It uses Gemini API directly so your Telegram voice journal can run on Gemini now.
- Keep API keys in environment variables, not in committed files.
