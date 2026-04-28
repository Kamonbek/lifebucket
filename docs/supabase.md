# Supabase integration

## Status
The Life OS schema and CSV sync script are ready.

Created:
- supabase/schema.sql
- tools/sync_supabase.py

## Run
Use a Supabase Postgres connection URL in `SUPABASE_CON_URL`:

```bash
cd /workspace/life-os
uv run --with 'psycopg[binary]' python tools/sync_supabase.py
```

## Important Supabase networking note
If the direct database URL looks like:

```text
postgresql://postgres:...@db.<project-ref>.supabase.co:5432/postgres
```

it may resolve to IPv6 only. Some runtimes, including this Hermes container, cannot reach IPv6 hosts. In that case use Supabase's connection pooler URL instead, usually from:

Supabase Dashboard -> Project Settings -> Database -> Connection string -> Transaction pooler

The pooler usually looks like:

```text
postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
```

After replacing `SUPABASE_CON_URL` with the pooler URL, rerun the sync command.

## Tables
- daily_logs
- income_logs
- expense_logs
- projects
- habits
- time_blocks
- outcomes

## View
- life_os_latest_summary
