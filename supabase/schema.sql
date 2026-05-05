-- Life OS Supabase schema
-- Safe to run multiple times. Creates append-friendly tables for personal analytics.

create table if not exists daily_logs (
  date date primary key,
  wake_time text,
  sleep_hours numeric,
  deep_work_hours numeric,
  learning_hours numeric,
  exercise boolean,
  main_task_done boolean,
  mood text,
  energy numeric,
  notes text,
  updated_at timestamptz not null default now()
);

create table if not exists income_logs (
  id bigserial primary key,
  date date not null,
  source text not null default 'other',
  amount numeric not null default 0,
  currency text not null default 'UZS',
  note text,
  updated_at timestamptz not null default now(),
  unique(date, source, amount, currency, note)
);

create table if not exists expense_logs (
  id bigserial primary key,
  date date not null,
  category text not null default 'other',
  amount numeric not null default 0,
  currency text not null default 'UZS',
  note text,
  updated_at timestamptz not null default now(),
  unique(date, category, amount, currency, note)
);

create table if not exists expense_tags (
  id bigserial primary key,
  date date not null,
  category text,
  amount numeric,
  currency text,
  note text,
  need_want text,
  confidence text,
  rule text,
  updated_at timestamptz not null default now(),
  unique(date, category, amount, currency, note, need_want, confidence, rule)
);

create table if not exists projects (
  project text primary key,
  status text,
  priority text,
  deadline date,
  current_milestone text,
  next_action text,
  updated_at timestamptz not null default now()
);

create table if not exists habits (
  date date not null,
  habit text not null,
  done boolean,
  score_0_1 numeric,
  notes text,
  updated_at timestamptz not null default now(),
  primary key(date, habit)
);

create table if not exists time_blocks (
  date date not null,
  block_name text not null,
  planned_minutes numeric,
  actual_minutes numeric,
  category text,
  quality_1_10 numeric,
  notes text,
  updated_at timestamptz not null default now(),
  primary key(date, block_name)
);

create table if not exists outcomes (
  date date not null,
  weekly_goal text not null,
  metric_name text not null,
  target numeric,
  actual numeric,
  status text,
  notes text,
  updated_at timestamptz not null default now(),
  primary key(date, weekly_goal, metric_name)
);

create table if not exists voice_journal (
  message_id bigint primary key,
  created_at_utc timestamptz not null,
  journal_date date generated always as ((created_at_utc at time zone 'UTC')::date) stored,
  chat_id bigint,
  user_id bigint,
  username text,
  file_id text,
  mime_type text,
  duration_sec numeric,
  gemini_model text,
  transcript text,
  updated_at timestamptz not null default now()
);

create table if not exists sleep_log (
  date_local date primary key,
  sleep_time_local time,
  wake_time_local time,
  sleep_source text,
  wake_source text,
  timezone text,
  utc_offset text,
  confidence text,
  notes text,
  updated_at timestamptz not null default now()
);

create table if not exists chat_events (
  chat_id bigint not null,
  message_id bigint not null,
  created_at_utc timestamptz not null,
  event_local_date date,
  event_local_datetime timestamp,
  timezone text,
  utc_offset text,
  user_id bigint,
  username text,
  message_type text,
  has_text boolean,
  has_voice boolean,
  has_audio boolean,
  text_len integer,
  duration_sec numeric,
  updated_at timestamptz not null default now(),
  primary key(chat_id, message_id)
);

create table if not exists numeric_facts (
  chat_id bigint not null,
  message_id bigint not null,
  source_type text not null,
  fact_key text not null,
  fact_value text,
  fact_unit text,
  confidence text,
  evidence text,
  created_at_utc timestamptz not null,
  event_local_date date,
  event_local_datetime timestamp,
  timezone text,
  user_id bigint,
  username text,
  updated_at timestamptz not null default now(),
  primary key(chat_id, message_id, source_type, fact_key, fact_value, evidence)
);

create table if not exists chat_activity_daily (
  date_local date primary key,
  timezone text,
  utc_offset text,
  total_messages integer,
  voice_messages integer,
  text_messages integer,
  other_messages integer,
  count_confidence text,
  notes text,
  updated_at timestamptz not null default now()
);

create table if not exists platform_message_daily (
  date_local date not null,
  platform text not null,
  timezone text,
  utc_offset text,
  total_messages integer,
  voice_messages integer,
  text_messages integer,
  other_messages integer,
  count_confidence text,
  notes text,
  updated_at timestamptz not null default now(),
  primary key(date_local, platform)
);

drop view if exists life_os_latest_summary;
create view life_os_latest_summary as
select
  (select count(*) from daily_logs) as daily_log_days,
  (select coalesce(sum(amount),0) from income_logs where currency = 'UZS' and date >= current_date - interval '30 days') as income_30d_uzs,
  (select coalesce(sum(amount),0) from expense_logs where currency = 'UZS' and date >= current_date - interval '30 days') as expenses_30d_uzs,
  (select count(*) from projects where status = 'active') as active_projects,
  (select count(*) from voice_journal where created_at_utc >= now() - interval '7 days') as voice_entries_7d,
  now() as generated_at;

-- Static dashboard reads with the publishable/anon key. The data model currently
-- contains non-sensitive dummy or user-approved life metrics. Tighten these grants
-- later if you add private journals, banking details, or authentication.
grant usage on schema public to anon, authenticated;
grant select on daily_logs, income_logs, expense_logs, expense_tags, projects, habits, time_blocks, outcomes, voice_journal, sleep_log, chat_events, numeric_facts, chat_activity_daily, platform_message_daily, life_os_latest_summary to anon, authenticated;
grant insert, update, delete on daily_logs, income_logs, expense_logs, expense_tags, projects, habits, time_blocks, outcomes, voice_journal, sleep_log, chat_events, numeric_facts, chat_activity_daily, platform_message_daily to authenticated;
