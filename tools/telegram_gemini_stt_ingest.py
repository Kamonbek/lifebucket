#!/usr/bin/env python3
import base64
import csv
import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path('/workspace/life-os')
LOGS = BASE / 'logs'
OUT_CSV = LOGS / 'voice_journal.csv'
STATE_FILE = BASE / '.state' / 'telegram_offset.txt'

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', os.getenv('GOOGLE_API_KEY', '')).strip()
GEMINI_MODEL = os.getenv('GEMINI_STT_MODEL', 'gemini-2.5-flash').strip()
POLL_SECONDS = int(os.getenv('TELEGRAM_POLL_SECONDS', '2'))


def ensure_files():
    LOGS.mkdir(parents=True, exist_ok=True)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not OUT_CSV.exists():
        with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow([
                'created_at_utc', 'chat_id', 'user_id', 'username', 'message_id', 'file_id',
                'mime_type', 'duration_sec', 'gemini_model', 'transcript'
            ])


def load_offset() -> int:
    if not STATE_FILE.exists():
        return 0
    try:
        return int(STATE_FILE.read_text(encoding='utf-8').strip() or '0')
    except Exception:
        return 0


def save_offset(offset: int) -> None:
    STATE_FILE.write_text(str(offset), encoding='utf-8')


def http_json(url: str, payload: dict | None = None, headers: dict | None = None):
    headers = headers or {}
    if payload is None:
        req = Request(url, headers=headers, method='GET')
    else:
        body = json.dumps(payload).encode('utf-8')
        req = Request(url, data=body, headers={'Content-Type': 'application/json', **headers}, method='POST')
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def telegram_api(method: str, params: dict | None = None):
    base = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}'
    if params:
        base += '?' + urlencode(params)
    return http_json(base)


def telegram_send(chat_id: int, text: str):
    telegram_api('sendMessage', {'chat_id': chat_id, 'text': text})


def get_file_bytes(file_id: str):
    r = telegram_api('getFile', {'file_id': file_id})
    if not r.get('ok'):
        raise RuntimeError(f'getFile failed: {r}')
    file_path = r['result']['file_path']
    file_url = f'https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}'
    with urlopen(file_url, timeout=120) as resp:
        data = resp.read()
    mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    return data, mime


def transcribe_with_gemini(audio_bytes: bytes, mime_type: str) -> str:
    b64 = base64.b64encode(audio_bytes).decode('ascii')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}'
    prompt = (
        'You are a transcription engine. Transcribe this audio faithfully. '\
        'Return only plain text transcript. Keep original language. No summaries.'
    )
    payload = {
        'contents': [{
            'parts': [
                {'text': prompt},
                {'inline_data': {'mime_type': mime_type, 'data': b64}}
            ]
        }],
        'generationConfig': {
            'temperature': 0,
            'topP': 0.1,
            'maxOutputTokens': 8192
        }
    }
    r = http_json(url, payload=payload)
    try:
        return r['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception:
        raise RuntimeError(f'Gemini response parse failed: {json.dumps(r)[:800]}')


def append_row(row: list[str]):
    with OUT_CSV.open('a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow(row)


def pick_audio(msg: dict):
    if 'voice' in msg:
        v = msg['voice']
        return v.get('file_id'), v.get('mime_type') or 'audio/ogg', v.get('duration') or 0
    if 'audio' in msg:
        a = msg['audio']
        return a.get('file_id'), a.get('mime_type') or 'audio/mpeg', a.get('duration') or 0
    if 'document' in msg:
        d = msg['document']
        mime = d.get('mime_type') or ''
        if mime.startswith('audio/'):
            return d.get('file_id'), mime, 0
    return None, None, 0


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit('TELEGRAM_BOT_TOKEN is not set')
    if not GEMINI_API_KEY:
        raise SystemExit('GEMINI_API_KEY (or GOOGLE_API_KEY) is not set')

    ensure_files()
    offset = load_offset()
    print(f'[start] polling telegram with model={GEMINI_MODEL} offset={offset}')

    backoff = POLL_SECONDS
    while True:
        try:
            resp = telegram_api('getUpdates', {'timeout': 30, 'offset': offset, 'allowed_updates': json.dumps(['message'])})
            backoff = POLL_SECONDS
        except HTTPError as e:
            if e.code == 409:
                # Another poller is currently consuming this bot token.
                backoff = min(max(backoff * 2, POLL_SECONDS), 60)
                print(f'[warn] Telegram polling conflict (HTTP 409). Another consumer may be running. Retrying in {backoff}s.')
                time.sleep(backoff)
                continue
            backoff = min(max(backoff * 2, POLL_SECONDS), 60)
            print(f'[warn] HTTP error from Telegram: {e}. Retrying in {backoff}s.')
            time.sleep(backoff)
            continue
        except URLError as e:
            backoff = min(max(backoff * 2, POLL_SECONDS), 60)
            print(f'[warn] Network error from Telegram: {e}. Retrying in {backoff}s.')
            time.sleep(backoff)
            continue
        except Exception as e:
            backoff = min(max(backoff * 2, POLL_SECONDS), 60)
            print(f'[warn] Unexpected polling error: {e}. Retrying in {backoff}s.')
            time.sleep(backoff)
            continue

        if not resp.get('ok'):
            print('[warn] getUpdates failed', resp)
            time.sleep(POLL_SECONDS)
            continue

        for upd in resp.get('result', []):
            offset = max(offset, upd['update_id'] + 1)
            msg = upd.get('message') or {}
            chat = msg.get('chat') or {}
            frm = msg.get('from') or {}

            file_id, hinted_mime, duration = pick_audio(msg)
            if not file_id:
                continue

            chat_id = chat.get('id')
            user_id = frm.get('id')
            username = frm.get('username') or frm.get('first_name') or 'unknown'
            message_id = msg.get('message_id')

            try:
                audio_bytes, detected_mime = get_file_bytes(file_id)
                mime = hinted_mime or detected_mime
                transcript = transcribe_with_gemini(audio_bytes, mime)
                created_at = datetime.now(timezone.utc).isoformat()
                append_row([
                    created_at, str(chat_id), str(user_id), username, str(message_id), file_id,
                    mime, str(duration), GEMINI_MODEL, transcript
                ])
                preview = (transcript[:700] + '…') if len(transcript) > 700 else transcript
                telegram_send(chat_id, f'Transcript saved.\n\n{preview}')
                print(f'[ok] {created_at} chat={chat_id} user={username} msg={message_id} chars={len(transcript)}')
            except Exception as e:
                err = str(e)
                print(f'[err] chat={chat_id} msg={message_id}: {err}')
                telegram_send(chat_id, 'Sorry, transcription failed on this audio. Please retry.')

        save_offset(offset)
        time.sleep(POLL_SECONDS)


if __name__ == '__main__':
    main()
