# hermes-mailbox

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that
connects a Gmail (personal or Google Workspace) account: native agent
tools to read/search/draft/reply/send mail, a **Mailbox** tab in the
Hermes Dashboard with live inbox stats and a daily-briefing history, and
a small request queue so you can click "let the agent draft this" on an
email straight from the dashboard.

Modeled on the structure of
[openmailsh/hermes-plugin](https://github.com/openmailsh/hermes-plugin),
but talks directly to the Gmail API via OAuth2 instead of a third-party
mail platform.

## What you get

- **Agent tools** (toolset `gmail_mailbox`): list/search/read messages,
  list labels, create drafts, reply (threaded), send, refresh stats,
  save a report, manage the dashboard request queue.
- **Dashboard tab** (`dashboard/`): unread/today counters, a 14-day
  volume sparkline, label breakdown, the latest saved reports, an inbox
  search box, and per-message "let the agent draft this" buttons.
- **Automation**: uses Hermes' own built-in cron (`cronjob_manage`) - no
  custom scheduler. See `docs/CRON_EXAMPLE.md` for a daily-briefing prompt.

## Setup

See [`docs/SETUP.md`](docs/SETUP.md).

## Repo layout

```
plugin.yaml              # CLI/gateway plugin manifest (tools, env vars)
__init__.py              # register(ctx): tools, CLI login command, skill
config.py, auth.py       # shared paths + OAuth2 login/refresh
client.py                # Gmail API wrapper
store.py                 # SQLite cache: stats history, reports, request queue
tools.py                 # tool schemas + handlers
skills/gmail_mailbox.md  # bundled skill (usage guidance for the agent)
dashboard/
  manifest.json          # dashboard tab config
  plugin_api.py          # FastAPI routes, mounted at /api/plugins/gmail-mailbox/
  dist/index.js          # React tab UI (Hermes Plugin SDK, no build step)
  dist/style.css
docs/
  SETUP.md
  CRON_EXAMPLE.md
```

## Status

MVP: single Gmail account, plain-text bodies only (attachments listed but
not downloaded), no push notifications (dashboard/tools poll on demand or
via cron). Generic IMAP/SMTP/POP3 support for non-Gmail providers is a
possible follow-up once this shape is validated.
