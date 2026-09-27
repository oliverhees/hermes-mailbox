"""Hermes plugin entrypoint: registers Gmail tools, a CLI login command and
a bundled skill. The dashboard half of this plugin (the "Mailbox" tab)
lives in dashboard/ and is discovered independently by `hermes dashboard`.
"""

from __future__ import annotations

from pathlib import Path

from tools import TOOL_HANDLERS, TOOL_SCHEMAS

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
        path=str(Path(__file__).parent / "skills" / "gmail_mailbox.md"),
    )

    ctx.register_cli_command(
        name="login",
        help="Connect a Gmail account via OAuth (opens a browser once).",
        setup_fn=_setup_login_args,
        handler_fn=_handle_login,
    )


def _setup_login_args(parser) -> None:
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Local port for the OAuth redirect (0 = pick automatically).",
    )


def _handle_login(args) -> str:
    from auth import run_login_flow

    run_login_flow(port=args.port)
    return "Gmail account connected. Token stored under ~/.hermes/plugins/gmail-mailbox/token.json."
