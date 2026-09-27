# Setup

## 1. Google Cloud OAuth client (once per Google account or Workspace org)

This works identically for a private Gmail account and a Google Workspace
account - it's the same Gmail API on Google's side either way. A Workspace
admin may need to approve the app in their org's OAuth policy before it
works for Workspace users; a private Gmail account has no such gate.

1. Go to https://console.cloud.google.com/ and create a project (or reuse one).
2. **APIs & Services -> Library**: enable the **Gmail API**.
3. **APIs & Services -> OAuth consent screen**: choose *External* (personal
   Gmail) or *Internal* (Workspace, restricted to your org). Add your own
   address as a test user if the app stays in "Testing" mode - that's fine
   for personal use, no Google review needed.
4. **APIs & Services -> Credentials -> Create Credentials -> OAuth client
   ID**, application type **Desktop app**. Copy the generated **Client ID**
   and **Client Secret**.

## 2. Install the plugin

```bash
hermes plugins install oliverhees/hermes-mailbox
hermes plugins enable gmail-mailbox
```

You'll be prompted for `GMAIL_OAUTH_CLIENT_ID` and `GMAIL_OAUTH_CLIENT_SECRET`
from step 1 (or export them as environment variables before starting Hermes).

## 3. Connect your mailbox

Run once, on the machine where Hermes runs and a browser is available:

```bash
hermes gmail-mailbox login
```

This opens a Google consent screen and stores a refresh token under
`~/.hermes/plugins/gmail-mailbox/token.json`. Nothing else needs the
client secret to enter model context - Hermes never sees it, only this
plugin's own OAuth code does.

## 4. See the Mailbox dashboard tab

```bash
hermes dashboard
```

Open it in a browser; a **Mailbox** tab appears in the nav (bundled
plugins are picked up automatically - if you installed this after the
dashboard was already running, hit
`curl http://127.0.0.1:9119/api/dashboard/plugins/rescan` or restart it).

## 5. Multiple mailboxes

Install the plugin under a second name (or a second `~/.hermes/plugins/`
directory) and set a different `GMAIL_ACCOUNT_LABEL`, `GMAIL_OAUTH_CLIENT_ID`
etc. per instance - each gets its own token file and its own dashboard tab.

## 6. Daily briefing automation

See `CRON_EXAMPLE.md` for a ready-to-use `cronjob_manage` prompt.
