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
  currency text not null default 'USD',
  note text,
  updated_at timestamptz not null default now(),
  unique(date, source, amount, currency, note)
);

create table if not exists expense_logs (
  id bigserial primary key,
  date date not null,
  category text not null default 'other',
  amount numeric not null default 0,
  currency text not null default 'USD',
  note text,
  updated_at timestamptz not null default now(),
  unique(date, category, amount, currency, note)
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

create or replace view life_os_latest_summary as
select
  (select count(*) from daily_logs) as daily_log_days,
  (select coalesce(sum(amount),0) from income_logs where currency = 'USD' and date >= current_date - interval '30 days') as income_30d_usd,
  (select coalesce(sum(amount),0) from expense_logs where currency = 'USD' and date >= current_date - interval '30 days') as expenses_30d_usd,
  (select count(*) from projects where status = 'active') as active_projects,
  now() as generated_at;

-- Static dashboard reads with the publishable/anon key. The data model currently
-- contains non-sensitive dummy or user-approved life metrics. Tighten these grants
-- later if you add private journals, banking details, or authentication.
grant usage on schema public to anon, authenticated;
grant select on daily_logs, income_logs, expense_logs, projects, habits, time_blocks, outcomes, life_os_latest_summary to anon, authenticated;
grant insert, update, delete on daily_logs, income_logs, expense_logs, projects, habits, time_blocks, outcomes to authenticated;
