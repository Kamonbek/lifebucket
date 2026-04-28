# Supabase frontend integration

The current Lifebucket dashboard is a static GitHub Pages app, not a Next.js app yet.

Implemented now:
- npm dependencies installed:
  - @supabase/supabase-js
  - @supabase/ssr
- .env.local added for future Next.js migration.
- Next-compatible helpers added:
  - utils/supabase/client.ts
  - utils/supabase/server.ts
  - utils/supabase/middleware.ts
  - middleware.ts
- Static dashboard now uses Supabase browser client via CDN and falls back to CSV files if Supabase tables are unavailable.

Current dashboard data priority:
1. Try Supabase tables:
   - daily_logs
   - income_logs
   - expense_logs
   - projects
   - habits
   - time_blocks
2. If Supabase query fails, fall back to checked-in CSV files.

This means the dashboard remains live even before real Supabase data is fully synced.

Next.js migration note:
The pasted Supabase SSR setup is correct for a Next.js app, but this repository currently has no Next.js app structure (`app/`, `next.config.*`, etc.). When we migrate from static GitHub Pages to Next.js hosting, the helper files are already in place.
