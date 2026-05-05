#!/usr/bin/env python3
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/workspace/life-os')
LOGS = BASE / 'logs'
SESSIONS_DIR = Path('/opt/data/sessions')
OUT = LOGS / 'platform_message_daily.csv'

LOCAL_TZ = ZoneInfo('Asia/Tashkent')
UTC_OFFSET = '+05:00'

# Count only human-origin platforms. Exclude autonomous/internal sources like cron.
ALLOWED_PLATFORMS = {'telegram', 'cli'}

VOICE_MARKER = re.compile(r'^\[The user sent a voice message~', re.I)
TEXT_MARKER = re.compile(r'^\[The user sent a text message~', re.I)


def _content_to_text(content) -> str:
    if content is None:
        return ''
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # Common schema: {"type": "text", "text": "..."}
                txt = item.get('text') if isinstance(item.get('text'), str) else ''
                if txt:
                    parts.append(txt)
        return ' '.join(parts)
    if isinstance(content, dict):
        txt = content.get('text')
        return txt if isinstance(txt, str) else ''
    return str(content)


def classify_user_message(content) -> str:
    c = _content_to_text(content).strip()
    if not c:
        return 'other'
    if VOICE_MARKER.match(c):
        return 'voice'
    if TEXT_MARKER.match(c):
        return 'text'
    return 'text'


def parse_ts(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except Exception:
        return datetime.now(timezone.utc)


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    agg = defaultdict(lambda: {'total': 0, 'voice': 0, 'text': 0, 'other': 0, 'conf': 'high', 'note': ''})

    # Track which sessions were handled exactly via jsonl
    exact_sids = set()

    # Pass 1: exact per-message timestamp from jsonl (best)
    for jl in sorted(SESSIONS_DIR.glob('*.jsonl')):
        sid = jl.stem
        sess_json = SESSIONS_DIR / f'session_{sid}.json'
        platform = 'unknown'
        if sess_json.exists():
            try:
                platform = (json.loads(sess_json.read_text(encoding='utf-8')).get('platform') or 'unknown').lower()
            except Exception:
                pass

        if platform not in ALLOWED_PLATFORMS:
            continue

        try:
            lines = jl.read_text(encoding='utf-8').splitlines()
        except Exception:
            continue

        used = False
        for line in lines:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get('role') != 'user':
                continue

            dt_local = parse_ts(obj.get('timestamp')).astimezone(LOCAL_TZ)
            date_local = dt_local.strftime('%Y-%m-%d')
            mtype = classify_user_message(obj.get('content', ''))
            key = (date_local, platform)
            a = agg[key]
            a['total'] += 1
            if mtype == 'voice':
                a['voice'] += 1
            elif mtype == 'text':
                a['text'] += 1
            else:
                a['other'] += 1
            a['conf'] = 'high'
            a['note'] = 'Exact from JSONL per-message timestamps.'
            used = True
        if used:
            exact_sids.add(sid)

    # Pass 2: fallback from session_*.json for sessions lacking jsonl
    for sj in sorted(SESSIONS_DIR.glob('session_*.json')):
        sid = sj.stem.replace('session_', '', 1)
        if sid in exact_sids:
            continue
        try:
            data = json.loads(sj.read_text(encoding='utf-8'))
        except Exception:
            continue

        platform = (data.get('platform') or 'unknown').lower()
        if platform not in ALLOWED_PLATFORMS:
            continue
        fallback_ts = data.get('session_start') or data.get('last_updated')
        date_local = parse_ts(fallback_ts).astimezone(LOCAL_TZ).strftime('%Y-%m-%d')

        for msg in (data.get('messages') or []):
            if msg.get('role') != 'user':
                continue
            mtype = classify_user_message(msg.get('content', ''))
            key = (date_local, platform)
            a = agg[key]
            a['total'] += 1
            if mtype == 'voice':
                a['voice'] += 1
            elif mtype == 'text':
                a['text'] += 1
            else:
                a['other'] += 1
            # Downgrade confidence where date is session-level inferred.
            a['conf'] = 'medium'
            a['note'] = 'Exact message counts; date inferred from session timestamp for non-JSONL sessions.'

    headers = [
        'date_local', 'platform', 'timezone', 'utc_offset',
        'total_messages', 'voice_messages', 'text_messages', 'other_messages',
        'count_confidence', 'notes'
    ]

    with OUT.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for (date_local, platform) in sorted(agg.keys()):
            c = agg[(date_local, platform)]
            w.writerow({
                'date_local': date_local,
                'platform': platform,
                'timezone': LOCAL_TZ.key,
                'utc_offset': UTC_OFFSET,
                'total_messages': c['total'],
                'voice_messages': c['voice'],
                'text_messages': c['text'],
                'other_messages': c['other'],
                'count_confidence': c['conf'],
                'notes': c['note']
            })

    print(f'platform_message_daily_updated rows={len(agg)} path={OUT}')


if __name__ == '__main__':
    main()
