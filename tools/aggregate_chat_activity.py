#!/usr/bin/env python3
import csv
from collections import defaultdict
from pathlib import Path

BASE = Path('/workspace/life-os')
LOGS = BASE / 'logs'
EVENTS = LOGS / 'chat_events.csv'
OUT = LOGS / 'chat_activity_daily.csv'


def read_rows(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows):
    headers = [
        'date_local','timezone','utc_offset','total_messages','voice_messages','text_messages','other_messages','count_confidence','notes'
    ]
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    events = read_rows(EVENTS)
    agg = defaultdict(lambda: {'total': 0, 'voice': 0, 'text': 0, 'other': 0, 'tz': 'Asia/Tashkent', 'off': '+05:00'})

    for e in events:
        d = (e.get('event_local_date') or '').strip()
        if not d:
            continue
        a = agg[d]
        a['total'] += 1
        mtype = (e.get('message_type') or 'other').strip().lower()
        if mtype == 'voice' or mtype == 'audio':
            a['voice'] += 1
        elif mtype == 'text':
            a['text'] += 1
        else:
            a['other'] += 1
        a['tz'] = e.get('timezone') or a['tz']
        a['off'] = e.get('utc_offset') or a['off']

    rows = []
    for d in sorted(agg.keys()):
        a = agg[d]
        rows.append({
            'date_local': d,
            'timezone': a['tz'],
            'utc_offset': a['off'],
            'total_messages': str(a['total']),
            'voice_messages': str(a['voice']),
            'text_messages': str(a['text']),
            'other_messages': str(a['other']),
            'count_confidence': 'high',
            'notes': 'Computed from chat_events.csv'
        })

    write_rows(OUT, rows)
    print(f'chat_activity_daily_updated rows={len(rows)}')


if __name__ == '__main__':
    main()
