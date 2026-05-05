#!/usr/bin/env python3
import base64
import csv
import json
import mimetypes
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = Path('/workspace/life-os')
LOGS = BASE / 'logs'
OUT_CSV = LOGS / 'voice_journal.csv'
EVENTS_CSV = LOGS / 'chat_events.csv'
NUMERIC_CSV = LOGS / 'numeric_facts.csv'
STATE_FILE = BASE / '.state' / 'telegram_offset.txt'

LOCAL_TZ = ZoneInfo(os.getenv('LIFE_OS_TIMEZONE', 'Asia/Tashkent'))
UTC_OFFSET = os.getenv('LIFE_OS_UTC_OFFSET', '+05:00')

TELEGRAM_STT_BOT_TOKEN = os.getenv('TELEGRAM_STT_BOT_TOKEN', '').strip()
TELEGRAM_STT_ALLOW_SHARED_TOKEN = os.getenv('TELEGRAM_STT_ALLOW_SHARED_TOKEN', '').strip().lower() in {
    '1', 'true', 'yes', 'on'
}
TELEGRAM_BOT_TOKEN = TELEGRAM_STT_BOT_TOKEN
if not TELEGRAM_BOT_TOKEN and TELEGRAM_STT_ALLOW_SHARED_TOKEN:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', os.getenv('GOOGLE_API_KEY', '')).strip()
GEMINI_MODEL = os.getenv('GEMINI_STT_MODEL', 'gemini-3-flash').strip()
POLL_SECONDS = int(os.getenv('TELEGRAM_POLL_SECONDS', '2'))

TIME_RE = re.compile(r'\b([01]?\d|2[0-3])[:.]([0-5]\d)(?:[:.]([0-5]\d))?\b')
NUMBER_RE = re.compile(r'(?<!\w)(\d+(?:[.,]\d+)?)(?!\w)')
SLEEP_HINT_RE = re.compile(r'\b(sleep|sleeping|go to sleep|bed|good night)\b', re.I)
WAKE_HINT_RE = re.compile(r'\b(wake|woke|wakeup|wake up|alarm)\b', re.I)


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

    if not EVENTS_CSV.exists():
        with EVENTS_CSV.open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow([
                'created_at_utc', 'event_local_date', 'event_local_datetime', 'timezone', 'utc_offset',
                'chat_id', 'user_id', 'username', 'message_id', 'message_type', 'has_text',
                'has_voice', 'has_audio', 'text_len', 'duration_sec'
            ])

    if not NUMERIC_CSV.exists():
        with NUMERIC_CSV.open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow([
                'created_at_utc', 'event_local_date', 'event_local_datetime', 'timezone',
                'chat_id', 'user_id', 'username', 'message_id', 'source_type',
                'fact_key', 'fact_value', 'fact_unit', 'confidence', 'evidence'
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
        'You are a transcription engine. Transcribe this audio faithfully. '
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


def append_row(path: Path, row: list[str]):
    with path.open('a', newline='', encoding='utf-8') as f:
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


def get_text_payload(msg: dict) -> str:
    text = msg.get('text') or msg.get('caption') or ''
    return text.strip()


def classify_message(msg: dict) -> str:
    if 'voice' in msg:
        return 'voice'
    if 'audio' in msg:
        return 'audio'
    if msg.get('text'):
        return 'text'
    return 'other'


def event_local_dt(msg: dict) -> datetime:
    ts = msg.get('date')
    if isinstance(ts, int):
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(LOCAL_TZ)
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def extract_numeric_facts(text: str):
    facts = []
    if not text:
        return facts

    times = []
    for m in TIME_RE.finditer(text):
        hh = m.group(1).zfill(2)
        mm = m.group(2)
        ss = m.group(3) or '00'
        val = f'{hh}:{mm}:{ss}'
        times.append((val, m.group(0)))
        facts.append(('time_mentioned', val, 'local_time', 'medium', m.group(0)))

    for m in NUMBER_RE.finditer(text):
        num = m.group(1).replace(',', '.')
        facts.append(('number_mentioned', num, 'raw_number', 'low', m.group(0)))

    low = text.lower()
    if times and SLEEP_HINT_RE.search(low):
        facts.append(('sleep_time_candidate', times[0][0], 'local_time', 'medium', times[0][1]))
    if times and WAKE_HINT_RE.search(low):
        facts.append(('wake_time_candidate', times[0][0], 'local_time', 'medium', times[0][1]))

    return facts


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            'TELEGRAM_STT_BOT_TOKEN is not set. '
            'For safety, this ingester no longer defaults to TELEGRAM_BOT_TOKEN. '
            'Set TELEGRAM_STT_BOT_TOKEN to a dedicated bot token, or explicitly set '
            'TELEGRAM_STT_ALLOW_SHARED_TOKEN=1 to reuse TELEGRAM_BOT_TOKEN.'
        )
    if not GEMINI_API_KEY:
        raise SystemExit('GEMINI_API_KEY (or GOOGLE_API_KEY) is not set')

    ensure_files()
    offset = load_offset()
    print(f'[start] polling telegram with model={GEMINI_MODEL} offset={offset} tz={LOCAL_TZ.key}')

    backoff = POLL_SECONDS
    while True:
        try:
            resp = telegram_api('getUpdates', {'timeout': 30, 'offset': offset, 'allowed_updates': json.dumps(['message'])})
            backoff = POLL_SECONDS
        except HTTPError as e:
            if e.code == 409:
                backoff = min(max(backoff * 2, POLL_SECONDS), 60)
                print(f'[warn] Telegram polling conflict (HTTP 409). Retrying in {backoff}s.')
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

            chat_id = chat.get('id')
            user_id = frm.get('id')
            username = frm.get('username') or frm.get('first_name') or 'unknown'
            message_id = msg.get('message_id')
            mtype = classify_message(msg)
            text_payload = get_text_payload(msg)
            local_dt = event_local_dt(msg)
            created_at = datetime.now(timezone.utc).isoformat()

            file_id, hinted_mime, duration = pick_audio(msg)

            append_row(EVENTS_CSV, [
                created_at,
                local_dt.strftime('%Y-%m-%d'),
                local_dt.strftime('%Y-%m-%d %H:%M:%S'),
                LOCAL_TZ.key,
                UTC_OFFSET,
                str(chat_id),
                str(user_id),
                username,
                str(message_id),
                mtype,
                '1' if bool(text_payload) else '0',
                '1' if 'voice' in msg else '0',
                '1' if 'audio' in msg else '0',
                str(len(text_payload)),
                str(duration),
            ])

            if text_payload:
                for fk, fv, fu, conf, ev in extract_numeric_facts(text_payload):
                    append_row(NUMERIC_CSV, [
                        created_at,
                        local_dt.strftime('%Y-%m-%d'),
                        local_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        LOCAL_TZ.key,
                        str(chat_id),
                        str(user_id),
                        username,
                        str(message_id),
                        'text', fk, fv, fu, conf, ev
                    ])

            if not file_id:
                continue

            try:
                audio_bytes, detected_mime = get_file_bytes(file_id)
                mime = hinted_mime or detected_mime
                transcript = transcribe_with_gemini(audio_bytes, mime)

                append_row(OUT_CSV, [
                    created_at, str(chat_id), str(user_id), username, str(message_id), file_id,
                    mime, str(duration), GEMINI_MODEL, transcript
                ])

                for fk, fv, fu, conf, ev in extract_numeric_facts(transcript):
                    append_row(NUMERIC_CSV, [
                        created_at,
                        local_dt.strftime('%Y-%m-%d'),
                        local_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        LOCAL_TZ.key,
                        str(chat_id),
                        str(user_id),
                        username,
                        str(message_id),
                        'voice_transcript', fk, fv, fu, conf, ev
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
