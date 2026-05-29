from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict

from .client import WhatsAppClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automate WhatsApp Web with Python + Playwright.")
    parser.add_argument("--profile", default="storage/whatsapp-profile", help="Persistent browser profile path.")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--timeout", type=int, default=30_000, help="Default Playwright timeout in ms.")

    commands = parser.add_subparsers(dest="command", required=True)

    login = commands.add_parser("login", help="Log in to WhatsApp Web with a phone number.")
    login.add_argument("phone", help="Phone number in international format, for example +79991234567.")

    chats = commands.add_parser("chats", help="Collect chats from the sidebar.")
    chats.add_argument("--limit", type=int, default=50)

    messages = commands.add_parser("messages", help="Collect recent messages from a chat.")
    messages.add_argument("chat", help="Exact chat title.")
    messages.add_argument("--limit", type=int, default=50)

    send = commands.add_parser("send", help="Send a message to a chat.")
    send.add_argument("chat", help="Exact chat title.")
    send.add_argument("message", help="Message text.")

    return parser


async def run(args: argparse.Namespace) -> None:
    async with WhatsAppClient(
        user_data_dir=args.profile,
        headless=args.headless,
        timeout_ms=args.timeout,
    ) as client:
        if args.command == "login":
            await client.login_with_phone(args.phone)
            print("Logged in.")
        elif args.command == "chats":
            open_chat = await client.open_chat_by_id("212179974418532@lid")
            # chats = await client.collect_chats()
            time.sleep(100)
            # print(json.dumps([asdict(chat) for chat in chats], ensure_ascii=False, indent=2))
        elif args.command == "messages":
            messages = await client.collect_messages(args.chat, limit=args.limit)
            print(json.dumps([asdict(message) for message in messages], ensure_ascii=False, indent=2))
        elif args.command == "send":
            await client.send_message()
            print("Message sent.")
        else:
            raise ValueError(f"Unsupported command: {args.command}")


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
