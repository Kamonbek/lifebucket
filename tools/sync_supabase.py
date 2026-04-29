#!/usr/bin/env python3
import csv
import os
from pathlib import Path

import psycopg
from urllib.parse import quote

BASE = Path('/workspace/life-os')
LOGS = BASE / 'logs'
SCHEMA = BASE / 'supabase' / 'schema.sql'


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as f:
        return [{k: (v or '').strip() for k, v in r.items()} for r in csv.DictReader(f)]


def b(v):
    return str(v).strip().lower() in {'yes', 'y', 'true', '1'}


def n(v):
    try:
        return float(v) if str(v).strip() != '' else None
    except Exception:
        return None


def none_if_blank(v):
    return None if v == '' else v


def normalize_created_at_utc(row):
    v = none_if_blank(row.get('created_at_utc', ''))
    if v:
        return v
    local_dt = none_if_blank(row.get('event_local_datetime', ''))
    if local_dt:
        offset = none_if_blank(row.get('utc_offset', '')) or '+05:00'
        return local_dt.replace(' ', 'T') + offset
    return None


def normalize_pg_url(url):
    """Return a psycopg-safe URL even when the password contains raw @/: chars."""
    if not (url.startswith('postgresql://') or url.startswith('postgres://')):
        return url
    scheme, rest = url.split('://', 1)
    if '@' not in rest:
        return url
    creds, hostpart = rest.rsplit('@', 1)
    if ':' not in creds:
        return url
    user, password = creds.split(':', 1)
    return f"{scheme}://{quote(user, safe='')}:{quote(password, safe='')}@{hostpart}"


def main():
    con_url = os.environ.get('SUPABASE_CON_URL')
    if not con_url:
        raise SystemExit('SUPABASE_CON_URL is not set')
    con_url = normalize_pg_url(con_url)

    # Supabase transaction pooler (PgBouncer) is incompatible with auto-prepared statements.
    # Disable client-side statement preparation to avoid DuplicatePreparedStatement errors.
    with psycopg.connect(con_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA.read_text(encoding='utf-8'))

            for r in read_csv(LOGS / 'daily_log.csv'):
                cur.execute(
                    '''
                    insert into daily_logs(date,wake_time,sleep_hours,deep_work_hours,learning_hours,exercise,main_task_done,mood,energy,notes)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict(date) do update set
                      wake_time=excluded.wake_time,
                      sleep_hours=excluded.sleep_hours,
                      deep_work_hours=excluded.deep_work_hours,
                      learning_hours=excluded.learning_hours,
                      exercise=excluded.exercise,
                      main_task_done=excluded.main_task_done,
                      mood=excluded.mood,
                      energy=excluded.energy,
                      notes=excluded.notes,
                      updated_at=now()
                    ''',
                    (r.get('date'), none_if_blank(r.get('wake_time','')), n(r.get('sleep_hours','')), n(r.get('deep_work_hours','')),
                     n(r.get('learning_hours','')), b(r.get('exercise','')), b(r.get('main_task_done','')), none_if_blank(r.get('mood','')),
                     n(r.get('energy','')), none_if_blank(r.get('notes','')))
                )

            for r in read_csv(LOGS / 'income.csv'):
                cur.execute(
                    '''
                    insert into income_logs(date,source,amount,currency,note)
                    values (%s,%s,%s,%s,%s)
                    on conflict(date, source, amount, currency, note) do nothing
                    ''',
                    (r.get('date'), r.get('source') or 'other', n(r.get('amount','')) or 0, r.get('currency') or 'USD', none_if_blank(r.get('note','')))
                )

            for r in read_csv(LOGS / 'expenses.csv'):
                cur.execute(
                    '''
                    insert into expense_logs(date,category,amount,currency,note)
                    values (%s,%s,%s,%s,%s)
                    on conflict(date, category, amount, currency, note) do nothing
                    ''',
                    (r.get('date'), r.get('category') or 'other', n(r.get('amount','')) or 0, r.get('currency') or 'USD', none_if_blank(r.get('note','')))
                )

            for r in read_csv(LOGS / 'projects.csv'):
                cur.execute(
                    '''
                    insert into projects(project,status,priority,deadline,current_milestone,next_action)
                    values (%s,%s,%s,%s,%s,%s)
                    on conflict(project) do update set
                      status=excluded.status,
                      priority=excluded.priority,
                      deadline=excluded.deadline,
                      current_milestone=excluded.current_milestone,
                      next_action=excluded.next_action,
                      updated_at=now()
                    ''',
                    (r.get('project'), none_if_blank(r.get('status','')), none_if_blank(r.get('priority','')), none_if_blank(r.get('deadline','')),
                     none_if_blank(r.get('current_milestone','')), none_if_blank(r.get('next_action','')))
                )

            for r in read_csv(LOGS / 'habits.csv'):
                cur.execute(
                    '''
                    insert into habits(date,habit,done,score_0_1,notes)
                    values (%s,%s,%s,%s,%s)
                    on conflict(date, habit) do update set
                      done=excluded.done,
                      score_0_1=excluded.score_0_1,
                      notes=excluded.notes,
                      updated_at=now()
                    ''',
                    (r.get('date'), r.get('habit'), b(r.get('done','')), n(r.get('score_0_1','')), none_if_blank(r.get('notes','')))
                )

            for r in read_csv(LOGS / 'time_blocks.csv'):
                cur.execute(
                    '''
                    insert into time_blocks(date,block_name,planned_minutes,actual_minutes,category,quality_1_10,notes)
                    values (%s,%s,%s,%s,%s,%s,%s)
                    on conflict(date, block_name) do update set
                      planned_minutes=excluded.planned_minutes,
                      actual_minutes=excluded.actual_minutes,
                      category=excluded.category,
                      quality_1_10=excluded.quality_1_10,
                      notes=excluded.notes,
                      updated_at=now()
                    ''',
                    (r.get('date'), r.get('block_name'), n(r.get('planned_minutes','')), n(r.get('actual_minutes','')),
                     none_if_blank(r.get('category','')), n(r.get('quality_1_10','')), none_if_blank(r.get('notes','')))
                )

            for r in read_csv(LOGS / 'outcomes.csv'):
                cur.execute(
                    '''
                    insert into outcomes(date,weekly_goal,metric_name,target,actual,status,notes)
                    values (%s,%s,%s,%s,%s,%s,%s)
                    on conflict(date, weekly_goal, metric_name) do update set
                      target=excluded.target,
                      actual=excluded.actual,
                      status=excluded.status,
                      notes=excluded.notes,
                      updated_at=now()
                    ''',
                    (r.get('date'), r.get('weekly_goal'), r.get('metric_name'), n(r.get('target','')), n(r.get('actual','')),
                     none_if_blank(r.get('status','')), none_if_blank(r.get('notes','')))
                )

            for r in read_csv(LOGS / 'voice_journal.csv'):
                msg_id = r.get('message_id')
                if not msg_id:
                    continue
                cur.execute(
                    '''
                    insert into voice_journal(message_id, created_at_utc, chat_id, user_id, username, file_id, mime_type, duration_sec, gemini_model, transcript)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict(message_id) do update set
                      created_at_utc=excluded.created_at_utc,
                      chat_id=excluded.chat_id,
                      user_id=excluded.user_id,
                      username=excluded.username,
                      file_id=excluded.file_id,
                      mime_type=excluded.mime_type,
                      duration_sec=excluded.duration_sec,
                      gemini_model=excluded.gemini_model,
                      transcript=excluded.transcript,
                      updated_at=now()
                    ''',
                    (
                        int(msg_id),
                        normalize_created_at_utc(r),
                        int(r.get('chat_id')) if r.get('chat_id') else None,
                        int(r.get('user_id')) if r.get('user_id') else None,
                        none_if_blank(r.get('username','')),
                        none_if_blank(r.get('file_id','')),
                        none_if_blank(r.get('mime_type','')),
                        n(r.get('duration_sec','')),
                        none_if_blank(r.get('gemini_model','')),
                        none_if_blank(r.get('transcript','')),
                    )
                )

            for r in read_csv(LOGS / 'sleep_log.csv'):
                d = r.get('date_local')
                if not d:
                    continue
                cur.execute(
                    '''
                    insert into sleep_log(date_local,sleep_time_local,wake_time_local,sleep_source,wake_source,timezone,utc_offset,confidence,notes)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict(date_local) do update set
                      sleep_time_local=excluded.sleep_time_local,
                      wake_time_local=excluded.wake_time_local,
                      sleep_source=excluded.sleep_source,
                      wake_source=excluded.wake_source,
                      timezone=excluded.timezone,
                      utc_offset=excluded.utc_offset,
                      confidence=excluded.confidence,
                      notes=excluded.notes,
                      updated_at=now()
                    ''',
                    (
                        d,
                        none_if_blank(r.get('sleep_time_local','')),
                        none_if_blank(r.get('wake_time_local','')),
                        none_if_blank(r.get('sleep_source','')),
                        none_if_blank(r.get('wake_source','')),
                        none_if_blank(r.get('timezone','')),
                        none_if_blank(r.get('utc_offset','')),
                        none_if_blank(r.get('confidence','')),
                        none_if_blank(r.get('notes','')),
                    )
                )

            for r in read_csv(LOGS / 'chat_events.csv'):
                chat_id = r.get('chat_id')
                msg_id = r.get('message_id')
                if not chat_id or not msg_id:
                    continue
                cur.execute(
                    '''
                    insert into chat_events(chat_id,message_id,created_at_utc,event_local_date,event_local_datetime,timezone,utc_offset,user_id,username,message_type,has_text,has_voice,has_audio,text_len,duration_sec)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict(chat_id, message_id) do update set
                      created_at_utc=excluded.created_at_utc,
                      event_local_date=excluded.event_local_date,
                      event_local_datetime=excluded.event_local_datetime,
                      timezone=excluded.timezone,
                      utc_offset=excluded.utc_offset,
                      user_id=excluded.user_id,
                      username=excluded.username,
                      message_type=excluded.message_type,
                      has_text=excluded.has_text,
                      has_voice=excluded.has_voice,
                      has_audio=excluded.has_audio,
                      text_len=excluded.text_len,
                      duration_sec=excluded.duration_sec,
                      updated_at=now()
                    ''',
                    (
                        int(chat_id),
                        int(msg_id),
                        normalize_created_at_utc(r),
                        none_if_blank(r.get('event_local_date','')),
                        none_if_blank(r.get('event_local_datetime','')),
                        none_if_blank(r.get('timezone','')),
                        none_if_blank(r.get('utc_offset','')),
                        int(r.get('user_id')) if r.get('user_id') else None,
                        none_if_blank(r.get('username','')),
                        none_if_blank(r.get('message_type','')),
                        b(r.get('has_text','')),
                        b(r.get('has_voice','')),
                        b(r.get('has_audio','')),
                        int(float(r.get('text_len') or 0)) if str(r.get('text_len','')).strip() != '' else None,
                        n(r.get('duration_sec','')),
                    )
                )

            for r in read_csv(LOGS / 'numeric_facts.csv'):
                chat_id = r.get('chat_id')
                msg_id = r.get('message_id')
                if not chat_id or not msg_id:
                    continue
                cur.execute(
                    '''
                    insert into numeric_facts(chat_id,message_id,source_type,fact_key,fact_value,fact_unit,confidence,evidence,created_at_utc,event_local_date,event_local_datetime,timezone,user_id,username)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict(chat_id, message_id, source_type, fact_key, fact_value, evidence) do update set
                      fact_unit=excluded.fact_unit,
                      confidence=excluded.confidence,
                      created_at_utc=excluded.created_at_utc,
                      event_local_date=excluded.event_local_date,
                      event_local_datetime=excluded.event_local_datetime,
                      timezone=excluded.timezone,
                      user_id=excluded.user_id,
                      username=excluded.username,
                      updated_at=now()
                    ''',
                    (
                        int(chat_id),
                        int(msg_id),
                        r.get('source_type') or 'unknown',
                        r.get('fact_key') or 'unknown',
                        none_if_blank(r.get('fact_value','')),
                        none_if_blank(r.get('fact_unit','')),
                        none_if_blank(r.get('confidence','')),
                        none_if_blank(r.get('evidence','')),
                        normalize_created_at_utc(r),
                        none_if_blank(r.get('event_local_date','')),
                        none_if_blank(r.get('event_local_datetime','')),
                        none_if_blank(r.get('timezone','')),
                        int(r.get('user_id')) if r.get('user_id') else None,
                        none_if_blank(r.get('username','')),
                    )
                )

            for r in read_csv(LOGS / 'chat_activity_daily.csv'):
                d = r.get('date_local')
                if not d:
                    continue
                cur.execute(
                    '''
                    insert into chat_activity_daily(date_local,timezone,utc_offset,total_messages,voice_messages,text_messages,other_messages,count_confidence,notes)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict(date_local) do update set
                      timezone=excluded.timezone,
                      utc_offset=excluded.utc_offset,
                      total_messages=excluded.total_messages,
                      voice_messages=excluded.voice_messages,
                      text_messages=excluded.text_messages,
                      other_messages=excluded.other_messages,
                      count_confidence=excluded.count_confidence,
                      notes=excluded.notes,
                      updated_at=now()
                    ''',
                    (
                        d,
                        none_if_blank(r.get('timezone','')),
                        none_if_blank(r.get('utc_offset','')),
                        int(float(r.get('total_messages') or 0)),
                        int(float(r.get('voice_messages') or 0)),
                        int(float(r.get('text_messages') or 0)),
                        int(float(r.get('other_messages') or 0)),
                        none_if_blank(r.get('count_confidence','')),
                        none_if_blank(r.get('notes','')),
                    )
                )

            for r in read_csv(LOGS / 'platform_message_daily.csv'):
                d = r.get('date_local')
                platform = r.get('platform')
                if not d or not platform:
                    continue
                cur.execute(
                    '''
                    insert into platform_message_daily(date_local,platform,timezone,utc_offset,total_messages,voice_messages,text_messages,other_messages,count_confidence,notes)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict(date_local, platform) do update set
                      timezone=excluded.timezone,
                      utc_offset=excluded.utc_offset,
                      total_messages=excluded.total_messages,
                      voice_messages=excluded.voice_messages,
                      text_messages=excluded.text_messages,
                      other_messages=excluded.other_messages,
                      count_confidence=excluded.count_confidence,
                      notes=excluded.notes,
                      updated_at=now()
                    ''',
                    (
                        d,
                        platform,
                        none_if_blank(r.get('timezone','')),
                        none_if_blank(r.get('utc_offset','')),
                        int(float(r.get('total_messages') or 0)),
                        int(float(r.get('voice_messages') or 0)),
                        int(float(r.get('text_messages') or 0)),
                        int(float(r.get('other_messages') or 0)),
                        none_if_blank(r.get('count_confidence','')),
                        none_if_blank(r.get('notes','')),
                    )
                )

            cur.execute('select * from life_os_latest_summary')
            row = cur.fetchone()
            cols = [d.name for d in cur.description]
            print(dict(zip(cols, row)))

        conn.commit()


if __name__ == '__main__':
    main()
