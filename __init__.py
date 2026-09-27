"""Hermes plugin entrypoint: registers Gmail tools, a CLI login command and
a bundled skill. The dashboard half of this plugin (the "Mailbox" tab)
lives in dashboard/ and is discovered independently by `hermes dashboard`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The sibling gmail_mailbox_* modules are plain flat files (Hermes' own
# plugin loader does not reliably put this directory on sys.path or wire
# up package-relative imports for __init__.py plugins - verified against
# a real Hermes Agent install), so add our own directory explicitly. This
# also keeps names collision-proof against Hermes' own top-level modules
# (e.g. its own "tools" package shadows a plain tools.py here).
_PLUGIN_ROOT = str(Path(__file__).resolve().parent)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from gmail_mailbox_tools import TOOL_HANDLERS, TOOL_SCHEMAS  # noqa: E402

TOOLSET = "gmail_mailbox"


def register(ctx) -> None:
    for name, schema in TOOL_SCHEMAS.items():
        ctx.register_tool(
            name=name,
            toolset=TOOLSET,
            schema=schema,
            handler=TOOL_HANDLERS[name],
        )

    ctx.register_skill(
        name="gmail_mailbox",
        path=Path(__file__).parent / "skills" / "gmail_mailbox.md",
    )

    # A single top-level CLI command ("login" alone would collide with
    # Hermes' own built-in `hermes login`), with the actual verb nested
    # underneath - matches how other bundled plugins (photon, google_meet)
    # do it: `hermes gmail-mailbox login`.
    ctx.register_cli_command(
        name="gmail-mailbox",
        help="Manage the Gmail mailbox plugin (connect an account, etc.)",
        setup_fn=_setup_cli,
        handler_fn=_dispatch_cli,
    )


def _setup_cli(parser) -> None:
    subs = parser.add_subparsers(dest="gmail_mailbox_command", required=True)
    login = subs.add_parser("login", help="Connect a Gmail account via OAuth (opens a browser once).")
    login.add_argument(
        "--port",
        type=int,
        default=0,
        help="Local port for the OAuth redirect (0 = pick automatically).",
    )


def _dispatch_cli(args) -> str:
    if args.gmail_mailbox_command == "login":
        from gmail_mailbox_auth import run_login_flow

        run_login_flow(port=args.port)
        return "Gmail account connected. Token stored under ~/.hermes/plugins/gmail-mailbox/token.json."
    return f"Unknown gmail-mailbox subcommand: {args.gmail_mailbox_command}"
