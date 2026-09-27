(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  var React = SDK.React;
  var useState = SDK.hooks.useState;
  var useEffect = SDK.hooks.useEffect;
  var useCallback = SDK.hooks.useCallback;
  var C = SDK.components;
  var h = React.createElement;
  var API = "/api/plugins/gmail-mailbox";

  function StatCard(label, value, tone) {
    return h(
      C.Card,
      { className: "gm-stat-card" },
      h(C.CardContent, null,
        h("div", { className: "gm-stat-label" }, label),
        h("div", { className: "gm-stat-value" + (tone ? " gm-tone-" + tone : "") }, value)
      )
    );
  }

  function Sparkline(history) {
    if (!history || history.length === 0) {
      return h("p", { className: "text-sm text-muted-foreground" }, "Noch keine Historie - gmail_sync_stats muss erst laufen.");
    }
    var max = Math.max(1, ...history.map(function (p) { return p.total_today; }));
    return h(
      "div", { className: "gm-sparkline" },
      history.map(function (point, i) {
        var pct = Math.max(4, Math.round((point.total_today / max) * 100));
        var day = new Date(point.created_at * 1000).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
        return h("div", { key: i, className: "gm-bar-wrap", title: day + ": " + point.total_today + " Mails" },
          h("div", { className: "gm-bar", style: { height: pct + "%" } }),
          h("div", { className: "gm-bar-label" }, day)
        );
      })
    );
  }

  function MailboxPage() {
    var statusState = useState(null), status = statusState[0], setStatus = statusState[1];
    var statsState = useState(null), stats = statsState[0], setStats = statsState[1];
    var reportsState = useState([]), reports = reportsState[0], setReports = reportsState[1];
    var requestsState = useState([]), requests = requestsState[0], setRequests = requestsState[1];
    var messagesState = useState([]), messages = messagesState[0], setMessages = messagesState[1];
    var queryState = useState("is:unread"), query = queryState[0], setQuery = queryState[1];
    var selectedState = useState(null), selected = selectedState[0], setSelected = selectedState[1];
    var busyState = useState(false), busy = busyState[0], setBusy = busyState[1];

    var refreshAll = useCallback(function () {
      SDK.fetchJSON(API + "/status").then(setStatus).catch(function () { setStatus({ authenticated: false }); });
      SDK.fetchJSON(API + "/stats").then(setStats).catch(function () {});
      SDK.fetchJSON(API + "/reports?limit=3").then(function (r) { setReports(r.reports || []); }).catch(function () {});
      SDK.fetchJSON(API + "/requests?status=pending").then(function (r) { setRequests(r.requests || []); }).catch(function () {});
    }, []);

    useEffect(function () {
      refreshAll();
      var id = setInterval(refreshAll, 60000);
      return function () { clearInterval(id); };
    }, [refreshAll]);

    var runSearch = useCallback(function () {
      setBusy(true);
      SDK.fetchJSON(API + "/messages?query=" + encodeURIComponent(query) + "&max_results=20")
        .then(function (r) { setMessages(r.messages || []); })
        .catch(function () { setMessages([]); })
        .finally(function () { setBusy(false); });
    }, [query]);

    useEffect(function () { if (status && status.authenticated) runSearch(); }, [status]);

    function openMessage(id) {
      SDK.fetchJSON(API + "/messages/" + id).then(setSelected).catch(function () {});
    }

    function requestDraft(id) {
      SDK.fetchJSON(API + "/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: id, kind: "draft_reply" }),
      }).then(refreshAll);
    }

    if (!status) {
      return h(C.Card, null, h(C.CardContent, null, "Lade ..."));
    }

    if (!status.authenticated) {
      return h(
        C.Card, null,
        h(C.CardHeader, null, h(C.CardTitle, null, "Gmail noch nicht verbunden")),
        h(C.CardContent, null,
          h("p", { className: "text-sm text-muted-foreground" },
            "Auf dem Host, der Hermes ausführt, einmal ausführen:"),
          h("pre", { className: "gm-code" }, "hermes gmail-mailbox login")
        )
      );
    }

    var latest = stats && stats.latest;
    var byLabel = (latest && latest.by_label) || {};
    var labelEntries = Object.keys(byLabel).map(function (k) { return [k, byLabel[k]]; })
      .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 6);

    return h(
      "div", { className: "gm-root" },
      h("div", { className: "gm-stats-row" },
        StatCard("Ungelesen", latest ? latest.unread_count : "-", "warn"),
        StatCard("Heute eingegangen", latest ? latest.total_today : "-"),
        StatCard("Offene Agenten-Anfragen", requests.length, requests.length ? "warn" : undefined)
      ),

      h(C.Card, { className: "gm-section" },
        h(C.CardHeader, null, h(C.CardTitle, null, "Verlauf (14 Tage)")),
        h(C.CardContent, null, Sparkline(stats && stats.history))
      ),

      h(C.Card, { className: "gm-section" },
        h(C.CardHeader, null, h(C.CardTitle, null, "Nach Label")),
        h(C.CardContent, null,
          labelEntries.length === 0
            ? h("p", { className: "text-sm text-muted-foreground" }, "Keine Daten.")
            : labelEntries.map(function (entry) {
                return h("div", { key: entry[0], className: "gm-label-row" },
                  h("span", null, entry[0]), h(C.Badge, null, String(entry[1])));
              })
        )
      ),

      h(C.Card, { className: "gm-section" },
        h(C.CardHeader, null, h(C.CardTitle, null, "Letzte Berichte")),
        h(C.CardContent, null,
          reports.length === 0
            ? h("p", { className: "text-sm text-muted-foreground" }, "Noch kein Bericht. Der Agent legt hier z.B. den täglichen Mailbox-Bericht ab.")
            : reports.map(function (r) {
                return h("div", { key: r.id, className: "gm-report" },
                  h("div", { className: "gm-report-title" }, r.title),
                  h("div", { className: "gm-report-meta" }, SDK.utils.timeAgo(r.created_at)),
                  h("div", { className: "gm-report-body" }, r.body));
              })
        )
      ),

      h(C.Card, { className: "gm-section" },
        h(C.CardHeader, null, h(C.CardTitle, null, "Inbox durchsuchen")),
        h(C.CardContent, null,
          h("div", { className: "gm-search-row" },
            h(C.Input, {
              value: query,
              onChange: function (e) { setQuery(e.target.value); },
              placeholder: "z.B. is:unread newer_than:2d",
            }),
            h(C.Button, { onClick: runSearch, disabled: busy }, busy ? "..." : "Suchen")
          ),
          h("div", { className: "gm-message-list" },
            messages.map(function (m) {
              var pending = requests.some(function (r) { return r.message_id === m.id; });
              return h("div", { key: m.id, className: "gm-message-row" },
                h("div", { className: "gm-message-main", onClick: function () { openMessage(m.id); } },
                  h("div", { className: "gm-message-subject" },
                    m.unread ? h(C.Badge, { className: "gm-unread-badge" }, "neu") : null, " ", m.subject),
                  h("div", { className: "gm-message-from" }, m.from),
                  h("div", { className: "gm-message-snippet" }, m.snippet)
                ),
                h(C.Button, {
                  onClick: function () { requestDraft(m.id); },
                  disabled: pending,
                }, pending ? "Angefragt" : "Entwurf vom Agenten")
              );
            })
          )
        )
      ),

      selected
        ? h(C.Card, { className: "gm-section" },
            h(C.CardHeader, null, h(C.CardTitle, null, selected.subject)),
            h(C.CardContent, null,
              h("div", { className: "gm-message-from" }, selected.from + " → " + selected.to),
              h(C.Separator, null),
              h("pre", { className: "gm-body" }, selected.body_text))
          )
        : null
    );
  }

  window.__HERMES_PLUGINS__.register("gmail-mailbox", MailboxPage);
})();
