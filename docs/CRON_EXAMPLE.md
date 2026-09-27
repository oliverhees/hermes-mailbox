# Daily mailbox briefing (cron example)

Cron jobs run in a fresh session with no memory of any other chat, so the
prompt must be fully self-contained. Ask Hermes (in any chat) to set this
up with `cronjob_manage`, or describe it in plain language, e.g.:

> Lege einen Cronjob an, der jeden Morgen um 7 Uhr (`0 7 * * *`) läuft.
> Prompt für den Job:
>
> "Rufe zuerst das Tool gmail_sync_stats auf. Suche danach mit
> gmail_search_messages nach 'is:unread newer_than:1d'. Fasse in 5-10
> Stichpunkten zusammen: wie viele E-Mails kamen rein, von wem, welche
> wirken wichtig/dringend und welche sind Newsletter/Routine. Speichere
> diese Zusammenfassung anschließend mit gmail_save_report(title, body)
> ab - title z.B. 'Mailbox-Bericht 07.09.', body der Stichpunkttext.
> Bearbeite zuletzt offene Anfragen: rufe gmail_list_pending_requests auf,
> und erstelle für jede mit gmail_reply(send=false) einen Antwortentwurf,
> danach gmail_complete_request mit einer kurzen result_note."
>
> Zustellung (deliver): "local" reicht, da das eigentliche Ergebnis im
> Mailbox-Dashboard-Tab sichtbar wird, nicht im Chat.

That's it — no code required, `cronjob_manage` is a native Hermes tool the
agent already has. Adjust the schedule (`cron_expression`), the search
query, or add a delivery target like `telegram` if you also want a short
ping outside the dashboard.
