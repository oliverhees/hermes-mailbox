# Gmail Mailbox skill

You have tools (toolset `gmail_mailbox`) to read, search, label, draft and
send email through a connected Gmail account. Use them like this:

## Reading and searching
- `gmail_list_messages` / `gmail_search_messages` use Gmail's own search
  syntax: `is:unread`, `from:someone@example.com`, `newer_than:1d`,
  `has:attachment`, `label:invoices`, etc. Combine terms freely.
- `gmail_get_message` returns the full plain-text body and attachment
  metadata (attachments are not downloaded yet - only listed).

## Drafting and replying
- Prefer `gmail_reply` for anything answering an existing message - it
  keeps the subject and threading (`In-Reply-To`/`References`) correct.
  By default it creates a **draft** (`send: false`); only pass
  `send: true` when the user explicitly asked you to send, not just
  draft, a reply.
- Use `gmail_create_draft` / `gmail_send_message` for brand-new emails
  (not replies).
- Never send an email the user hasn't clearly asked you to send. When in
  doubt, create a draft and tell the user it's waiting for review.

## Daily briefings / automation
This plugin does not run its own scheduler - use Hermes' built-in cron
(`cronjob_manage`). A good daily-briefing job:

1. Calls `gmail_sync_stats` to refresh the counters the dashboard's
   Mailbox tab shows.
2. Reads today's unread/important mail with `gmail_search_messages`
   (e.g. `query: "is:unread newer_than:1d"`), and summarizes it: how many
   came in, who from, what looks important/urgent vs routine.
3. Calls `gmail_save_report(title, body)` with that summary so it shows
   up in the dashboard.

See `docs/CRON_EXAMPLE.md` in the plugin repo for a ready-to-use
`cronjob_manage` prompt.

## The dashboard request queue
The Mailbox dashboard tab lets the user click "let the agent draft this"
on any email, which queues a row rather than acting immediately (the
dashboard cannot call you directly). On a schedule (or when asked
"check my mailbox requests"), call `gmail_list_pending_requests`, act on
each one (usually `gmail_reply` with `send: false` to leave a draft for
review), then call `gmail_complete_request` with a short `result_note`
(e.g. `"created draft d123"`) so the dashboard shows it as done.
