from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import time
from dataclasses import asdict

from pyexpat.errors import messages

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
#"142940974391481@lid" - Lera
        #"190417509294162@lid" - Me

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
            cursor = "3EB09C4437871769706A47"
            chat_id = "142940974391481@lid"
            limit = 50
            # after_date = datetime.datetime(2026, 5, 29, 10, 49, 57, tzinfo=datetime.timezone.utc)
            after_date = datetime.datetime(2026, 5, 29, tzinfo=datetime.timezone.utc)
            before_date = datetime.datetime(2026, 5, 29, tzinfo=datetime.timezone.utc)
            messages = await client.get_messages(chat_id=chat_id, limit=limit, after_date=after_date, before_date=None, cursor=cursor)
            print(messages)
        elif args.command == "send":
            await client.send_message_tg()
            # message = await client.send_message()
            # print("Message sent.", message)
        else:
            raise ValueError(f"Unsupported command: {args.command}")


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
