// ~/.hermes/plugins/gmail-mailbox/desktop/plugin.js
//
// Native Hermes Desktop pane for the Gmail mailbox plugin. Loaded uncompiled
// (no JSX, no build step) - see docs/developer-guide/desktop-plugin-sdk.md.
// Talks to the same backend as the dashboard tab (dashboard/plugin_api.py,
// mounted at /api/plugins/gmail-mailbox/) via ctx.rest().
//
// Only three imports are allowed here: '@hermes/plugin-sdk', 'react' and
// 'react/jsx-runtime'.

import { createElement as h, useState } from 'react'
import {
  PANES_AREA,
  STATUSBAR_AREAS,
  useQuery,
  useQueryClient,
  Button,
  Badge,
  Separator,
  SearchField,
  ScrollArea,
  Skeleton,
  EmptyState,
  relativeTime,
} from '@hermes/plugin-sdk'

const REFRESH_MS = 45000

function useMailboxQuery(ctx, key, path) {
  return useQuery({
    queryKey: ['gmail-mailbox', key],
    queryFn: () => ctx.rest(path),
    refetchInterval: REFRESH_MS,
    retry: false,
  })
}

function buildMailboxPane(ctx) {
  return function MailboxPane() {
    var queryClient = useQueryClient()
    var queryState = useState('is:unread')
    var query = queryState[0]
    var setQuery = queryState[1]
    var selectedState = useState(null)
    var selectedId = selectedState[0]
    var setSelectedId = selectedState[1]

    var statusQ = useMailboxQuery(ctx, 'status', '/status')
    var statsQ = useMailboxQuery(ctx, 'stats', '/stats')
    var reportsQ = useMailboxQuery(ctx, 'reports', '/reports?limit=1')
    var requestsQ = useMailboxQuery(ctx, 'requests', '/requests?status=pending')
    var messagesQ = useQuery({
      queryKey: ['gmail-mailbox', 'messages', query],
      queryFn: () => ctx.rest('/messages?query=' + encodeURIComponent(query) + '&max_results=15'),
      enabled: Boolean(statusQ.data && statusQ.data.authenticated),
    })
    var detailQ = useQuery({
      queryKey: ['gmail-mailbox', 'message', selectedId],
      queryFn: () => ctx.rest('/messages/' + selectedId),
      enabled: Boolean(selectedId),
    })

    function requestDraft(messageId) {
      ctx
        .rest('/requests', { method: 'POST', body: { message_id: messageId, kind: 'draft_reply' } })
        .then(function () {
          queryClient.invalidateQueries({ queryKey: ['gmail-mailbox', 'requests'] })
        })
    }

    if (statusQ.isLoading) {
      return h('div', { className: 'p-3' }, h(Skeleton, { className: 'h-20 w-full' }))
    }

    if (!statusQ.data || !statusQ.data.authenticated) {
      return h(
        EmptyState,
        {
          title: 'Gmail nicht verbunden',
          description: "Einmal im Terminal ausführen: hermes gmail-mailbox login",
        }
      )
    }

    var latest = statsQ.data && statsQ.data.latest
    var report = reportsQ.data && reportsQ.data.reports && reportsQ.data.reports[0]
    var requests = (requestsQ.data && requestsQ.data.requests) || []
    var messages = (messagesQ.data && messagesQ.data.messages) || []
    var pendingIds = {}
    requests.forEach(function (r) { pendingIds[r.message_id] = true })

    return h(
      'div',
      { className: 'flex h-full flex-col gap-3 overflow-hidden p-3 text-sm' },

      h(
        'div',
        { className: 'grid grid-cols-3 gap-2' },
        h(StatChip, { label: 'Ungelesen', value: latest ? latest.unread_count : '-' }),
        h(StatChip, { label: 'Heute', value: latest ? latest.total_today : '-' }),
        h(StatChip, { label: 'Anfragen', value: requests.length })
      ),

      report
        ? h(
            'div',
            { className: 'rounded border border-(--ui-stroke-secondary) p-2' },
            h('div', { className: 'font-medium' }, report.title),
            h('div', { className: 'mt-1 line-clamp-3 text-(--ui-text-tertiary)' }, report.body),
            h('div', { className: 'mt-1 text-[0.6875rem] text-(--ui-text-quaternary)' }, relativeTime(report.created_at * 1000))
          )
        : null,

      h(Separator, null),

      h(SearchField, {
        value: query,
        onChange: function (e) { setQuery(e.target.value) },
        placeholder: 'is:unread newer_than:2d',
      }),

      h(
        ScrollArea,
        { className: 'flex-1' },
        h(
          'div',
          { className: 'flex flex-col gap-1' },
          messages.length === 0
            ? h('div', { className: 'p-2 text-(--ui-text-tertiary)' }, 'Keine Treffer.')
            : messages.map(function (m) {
                return h(
                  'div',
                  { key: m.id, className: 'rounded border border-(--ui-stroke-secondary) p-2' },
                  h(
                    'div',
                    { className: 'cursor-pointer', onClick: function () { setSelectedId(m.id) } },
                    h('div', { className: 'flex items-center gap-1 font-medium' },
                      m.unread ? h(Badge, { className: 'shrink-0' }, 'neu') : null,
                      h('span', { className: 'truncate' }, m.subject)),
                    h('div', { className: 'truncate text-(--ui-text-tertiary)' }, m.from)
                  ),
                  h(
                    Button,
                    {
                      className: 'mt-1 w-full',
                      disabled: Boolean(pendingIds[m.id]),
                      onClick: function () { requestDraft(m.id) },
                    },
                    pendingIds[m.id] ? 'Entwurf angefragt' : 'Entwurf vom Agenten'
                  ),
                  selectedId === m.id && detailQ.data
                    ? h('pre', { className: 'mt-2 whitespace-pre-wrap text-(--ui-text-secondary)' }, detailQ.data.body_text)
                    : null
                )
              })
        )
      )
    )
  }
}

function StatChip(props) {
  return h(
    'div',
    { className: 'rounded border border-(--ui-stroke-secondary) p-2 text-center' },
    h('div', { className: 'text-[0.6875rem] text-(--ui-text-tertiary)' }, props.label),
    h('div', { className: 'text-base font-semibold' }, String(props.value))
  )
}

function buildStatusChip(ctx) {
  return function MailboxStatusChip() {
    var q = useMailboxQuery(ctx, 'stats', '/stats')
    var latest = q.data && q.data.latest
    var unread = latest ? latest.unread_count : 0
    return h(
      'span',
      { className: 'px-1.5 text-[0.6875rem] text-(--ui-text-tertiary)' },
      unread ? unread + ' ungelesen' : 'Mailbox'
    )
  }
}

export default {
  id: 'gmail-mailbox',
  name: 'Gmail Mailbox',
  register(ctx) {
    ctx.register({
      id: 'pane',
      area: PANES_AREA,
      title: 'Mailbox',
      data: { placement: 'right', width: '340px' },
      render: () => h(buildMailboxPane(ctx), {}),
    })

    ctx.register({
      id: 'chip',
      area: STATUSBAR_AREAS.right,
      order: 130,
      render: () => h(buildStatusChip(ctx), {}),
    })
  },
}
