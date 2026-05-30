from __future__ import annotations

import asyncio
import datetime
import random
import time
import typing
from pathlib import Path
from typing import Any, Coroutine, Literal

from playwright.async_api import BrowserContext, Page, TimeoutError, async_playwright

from wa_automation.asd import Attachment, Message

WHATSAPP_URL = "https://web.whatsapp.com/"


class WhatsAppClient:

    def __init__(
        self,
        user_data_dir: str | Path = "storage/whatsapp-profile",
        headless: bool = False,
        timeout_ms: int = 30_000,
        slow_mo_ms: int = 0,
    ) -> None:
        self.user_data_dir = Path(user_data_dir)
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.slow_mo_ms = slow_mo_ms
        self._playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> "WhatsAppClient":
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self.context = await self._playwright.chromium.launch_persistent_context(
            # user_data_dir=str(self.user_data_dir),
            user_data_dir=r"C:\Users\Nikita\AppData\Local\Google\Chrome\User Data",
            headless=self.headless,
            slow_mo=self.slow_mo_ms,
            viewport={"width": 1440, "height": 950},
            locale="ru-RU",
            args=["--profile-directory=Default","--disable-blink-features=AutomationControlled"],
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        await self.page.goto(WHATSAPP_URL, wait_until="domcontentloaded")
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.context:
            await self.context.close()
        if self._playwright:
            await self._playwright.stop()

    async def login_with_phone(self, phone_number: str) -> None:

        page = self._page
        await page.goto(WHATSAPP_URL, wait_until="domcontentloaded")

        login_by_phone_number = self._page.locator(
            "[data-testid='link-device-qrcode-alt-linking-hint']"
        )
        #TODO: не может кликнуть
        await login_by_phone_number.click()

        phone_screen = self._page.locator(
            "[data-testid='link-device-phone-number-entry-screen']"
        )

        phone_input =  phone_screen.locator("input[data-testid='phone-number-input']")
        error = phone_screen.locator(
            "#link-device-phone-number-entry-screen-error"
        )
        next_button = phone_screen.locator("button[type='button'][aria-disabled='false']").last

        await phone_input.click()
        await phone_input.clear()
        await phone_input.type(phone_number)


        try:
            await next_button.click()
            await error.wait_for(state="visible", timeout=5000)
            error_text = await error.inner_text()
            raise ValueError(f"WhatsApp отклонил номер: {error_text}")
        except TimeoutError:
            pass

        code_cells = self._page.locator(
            "[data-testid='link-with-phone-number-code-cells']"
        )
        raw_code = await code_cells.get_attribute("data-link-code")

        if not raw_code:
            raise RuntimeError("Не удалось получить код входа")

        code = raw_code.replace(",", "")

        print(code)
        #TODO: возможно добавить проверку на смену кода
        #Проверка что успешно войдено
        await self.wait_for_whatsapp_modules()


    async def _get_chats_from_internal_store(self) -> list[dict]:
        return await self._page.evaluate(
            """
            async () => {
                const { Chat } = window.require('WAWebCollections');

                const chats = Chat.getModelsArray();

                return chats.map((chat) => {
                    const data = typeof chat.serialize === 'function'
                        ? chat.serialize()
                        : chat;

                    const id =
                        data?.id?._serialized ||
                        chat?.id?._serialized ||
                        String(chat?.id || '');

                    const title =
                        data?.formattedTitle ||
                        data?.name ||
                        chat?.formattedTitle ||
                        chat?.name ||
                        '';

                    const lastMessage =
                        data?.lastMessage ||
                        chat?.lastMessage ||
                        chat?.msgs?.getModelsArray?.()?.at?.(-1) ||
                        null;

                    const previewMessage =
                        lastMessage?.body ||
                        lastMessage?.caption ||
                        lastMessage?.text ||
                        '';

                    const timestamp =
                        data?.t ||
                        chat?.t ||
                        lastMessage?.t ||
                        null;

                    return {
                        id,
                        title,
                        preview_message: previewMessage || null,
                        preview_last_time_message: timestamp,
                    };
                });
            }
            """
        )

    async def collect_chats(self) -> None:
        await self.wait_for_whatsapp_modules()
        chats = await self._get_chats_from_internal_store()

        for chat in chats:
            print(chat)

    async def wait_for_whatsapp_modules(self) -> None:
        try:
            await self._page.locator("#pane-side").wait_for(
                state="visible",
                timeout=30000,
            )
            await self._page.wait_for_function(
                """
                () => {
                    const safeRequire = (name) => {
                        try {
                            return window.require ? window.require(name) : null;
                        } catch (e) {
                            return null;
                        }
                    };
    
                    return Boolean(
                        safeRequire("WAWebCollections")?.Chat &&
                        safeRequire("WAWebWidFactory") &&
                        safeRequire("WAWebCmd")?.Cmd
                    );
                }
                """,
                timeout=30000,
            )

        except TimeoutError:
            print("НЕ СМАГЛОСЯ")

    async def open_chat_by_id(self, chat_id: str) -> None:
        opened = await self._page.evaluate(
            """
            async (chatId) => {
                const Chat = window.require("WAWebCollections").Chat;
                const WidFactory = window.require("WAWebWidFactory");
                const Cmd = window.require("WAWebCmd").Cmd;

                const wid = WidFactory.createWid(chatId);

                const chat = Chat.getModelsArray().find((chat) => {
                    return chat?.id?.equals?.(wid);
                });

                if (!chat) {
                    return false;
                }

                if (Cmd.openChatBottom) {
                    await Cmd.openChatBottom({ chat });
                    return true;
                }

                if (Cmd.openChatAt) {
                    await Cmd.openChatAt({ chat });
                    return true;
                }

                return false;
            }
            """,
            chat_id,
        )

        if not opened:
            raise RuntimeError(f"Не удалось открыть чат: {chat_id}")

        #TODO: Добавить проверку что чат открылся, по селекктору

    async def _typing_text(
            self,
            text: str,
            min_delay_ms: int = 100,
            max_delay_ms: int = 500,
    ) -> None:
        for char in text:
            delay_ms = random.uniform(min_delay_ms, max_delay_ms)

            if char == " ":
                delay_ms = random.uniform(min_delay_ms*1.5, max_delay_ms*1.5)

            await self._page.keyboard.type(char, delay=delay_ms)

    async def _check_correct_message_status(self, chat_id: str, messages_count_before: int, retry_count: int = 3) -> Message:
        message: Message | None  = None
        corrected_message_statuses: set[typing.Literal["DELIVERED", "READ", "ERROR"]] = {"DELIVERED", "READ", "ERROR"}
        count_of_try = 0
        while count_of_try < retry_count:
            messages = await self._get_loaded_raw_messages(chat_id)
            messages_count_after = len(messages)

            is_correct_diff_messages = (messages_count_after - messages_count_before) == 1

            if not is_correct_diff_messages:
                if message:
                    return message
                raise Exception("Уже кто-то отправил сообщение, не могу найти")
                #TODO: подумать что делать если сообщение уже кто-то отправил

            message = self._message_from_raw(messages[-1])
            if not message:
                raise Exception("Нет прапвильного типа")

            if message.status in corrected_message_statuses:
                return message

            count_of_try += 1
            await self._page.wait_for_timeout(1000)

        if message:
            return message

        raise Exception("Сообщение не найдено")

    async def send_message(self) -> Message:
        await self.wait_for_whatsapp_modules()
        chat_id = "142940974391481@lid"
        #"142940974391481@lid" - Lera
        #"190417509294162@lid" - Me
        message = "МЯУ"

        await self.open_chat_by_id(chat_id)

        compose_box = self._page.locator(
            "[data-testid='conversation-compose-box-input'][contenteditable='true']"
        )

        await compose_box.wait_for(state="visible", timeout=30000)
        await compose_box.click()
        await compose_box.clear()
        await self._typing_text(message)

        messages_count_before = len(await self._get_loaded_raw_messages(chat_id))

        await self._page.keyboard.press("Enter")
        await self._page.wait_for_timeout(1000)

        return await self._check_correct_message_status(chat_id, messages_count_before)


    #TODO: Сделать проверку что даты не могут протеворечить друг другу, в Pydantic модели на входеу
    async def get_messages(
            self,
            chat_id: str,
            cursor: str | None = None,
            after_date: datetime.datetime | None = None,
            before_date: datetime.datetime | None = None,
            limit: int = 50,
    ) -> list[Message]:
        await self.wait_for_whatsapp_modules()
        await self.open_chat_by_id(chat_id)
        await self._wait_chat_opened()

        loaded_messages: list[dict] = []
        seen_ids: set[str] = set()
        previous_oldest_id: str | None = None
        max_scroll_attempts = 30

        for _ in range(max_scroll_attempts):
            raw_messages = await self._get_loaded_raw_messages(chat_id)

            self._append_unique_raw_messages(
                target=loaded_messages,
                seen_ids=seen_ids,
                messages=raw_messages,
            )

            loaded_messages.sort(key=lambda item: item.get("timestamp") or 0)

            filtered_messages = self._filter_raw_messages(
                raw_messages=loaded_messages,
                cursor=cursor,
                after_date=after_date,
                before_date=before_date,
            )

            if self._should_stop_collecting_messages(
                    loaded_messages=loaded_messages,
                    filtered_messages=filtered_messages,
                    cursor=cursor,
                    after_date=after_date,
                    limit=limit,
                    previous_oldest_id=previous_oldest_id,
            ):
                break

            previous_oldest_id = self._oldest_message_id(loaded_messages)

            await self._scroll_opened_chat_up()

        return self._raw_messages_to_messages(filtered_messages[-limit:])

    async def _wait_chat_opened(self) -> None:
        await self._page.locator(
            "[data-testid='conversation-compose-box-input'][contenteditable='true']"
        ).wait_for(state="visible", timeout=30000)

    def _append_unique_raw_messages(
            self,
            target: list[dict],
            seen_ids: set[str],
            messages: list[dict],
    ) -> None:
        for message in messages:
            message_id = message.get("message_id")

            if not message_id or message_id in seen_ids:
                continue

            seen_ids.add(message_id)
            target.append(message)

    def _should_stop_collecting_messages(
            self,
            loaded_messages: list[dict],
            filtered_messages: list[dict],
            cursor: str | None,
            after_date: datetime.datetime | None,
            limit: int,
            previous_oldest_id: str | None,
    ) -> bool:
        if len(filtered_messages) >= limit:
            return True

        if cursor and self._has_message(loaded_messages, cursor):
            return True

        if self._is_after_date_boundary_reached(loaded_messages, after_date):
            return True

        oldest_id = self._oldest_message_id(loaded_messages)

        return bool(oldest_id and oldest_id == previous_oldest_id)

    def _has_message(self, messages: list[dict], message_id: str) -> bool:
        return any(
            item.get("message_id") == message_id
            for item in messages
        )

    def _oldest_message_id(self, messages: list[dict]) -> str | None:
        if not messages:
            return None

        return messages[0].get("message_id")

    def _raw_messages_to_messages(self, raw_messages: list[dict]) -> list[Message]:
        messages: list[Message] = []

        for raw_message in raw_messages:
            message = self._message_from_raw(raw_message)

            if message is None:
                continue

            messages.append(message)

        return messages

    async def _get_loaded_raw_messages(self, chat_id: str) -> list[dict]:
        return await self._page.evaluate(
            """
            (chatId) => {
                const Chat = window.require("WAWebCollections").Chat;
                const WidFactory = window.require("WAWebWidFactory");

                const wid = WidFactory.createWid(chatId);

                const chat = Chat.getModelsArray().find((chat) => {
                    return (chat?.id?.equals?.(wid));
                });

                if (!chat) {
                    return [];
                }

                const messages = chat.msgs?.getModelsArray?.() || [];

                return messages.map((msg) => ({
                    message_id: msg?.id?.id || null,
                    chat_id: msg?.id?.remote?._serialized || msg?.id?.remote || chatId,
                    timestamp: msg?.t || null,

                    body: msg?.body || null,
                    caption: msg?.caption || null,
                    type: msg?.type || null,

                    from_me: Boolean(msg?.id?.fromMe || msg?.isSentByMe),
                    from: msg?.from?._serialized || msg?.from || null,
                    to: msg?.to?._serialized || msg?.to || null,
                    author: msg?.author?._serialized || msg?.author || null,

                    ack: msg?.ack ?? null,
                    latest_edit_timestamp_ms: msg?.latestEditSenderTimestampMs || null,

                    mimetype: msg?.mimetype || null,
                    filename: msg?.filename || msg?.fileName || null,
                    size: msg?.size || msg?.fileSize || null,
                    media_key: msg?.mediaKey || null,
                    client_url: msg?.clientUrl || null,
                    direct_path: msg?.directPath || null,
                }));
            }
            """,
            chat_id,
        )

    def _filter_raw_messages(
            self,
            raw_messages: list[dict],
            cursor: str | None,
            after_date: datetime.datetime | None,
            before_date: datetime.datetime | None,
    ) -> list[dict]:
        messages = sorted(
            [item for item in raw_messages if item.get("message_id") and item.get("timestamp")],
            key=lambda item: item["timestamp"],
        )

        cursor_index = None

        if cursor:
            cursor_index = next(
                (
                    index for index, item in enumerate(messages)
                    if item["message_id"] == cursor
                ),
                None,
            )

        if cursor_index is not None:
            messages = messages[cursor_index:]

            if before_date:
                before_ts = before_date.timestamp()
                messages = [
                    item for item in messages
                    if item["timestamp"] <= before_ts
                ]

            return messages

        if after_date:
            after_ts = after_date.timestamp()
            messages = [
                item for item in messages
                if item["timestamp"] >= after_ts
            ]

        if before_date:
            before_ts = before_date.timestamp()
            messages = [
                item for item in messages
                if item["timestamp"] <= before_ts
            ]

        return messages

    def _is_after_date_boundary_reached(
            self,
            raw_messages: list[dict],
            after_date: datetime.datetime | None,
    ) -> bool:
        if not after_date or not raw_messages:
            return False

        timestamps = [
            item["timestamp"]
            for item in raw_messages
            if item.get("timestamp")
        ]

        if not timestamps:
            return False

        return min(timestamps) <= after_date.timestamp()

    def _message_from_raw(self, raw: dict) -> Message | None:
        type = raw.get("type")
        norm_types = ("chat", "sticker", "document", "video", "ptt", "audio", "image")
        if type not in norm_types:
            return None

        message_id = raw.get("message_id")
        message_body = raw.get("body") or raw.get("caption") or ""
        created_at = datetime.datetime.fromtimestamp(
            raw["timestamp"],
            tz=datetime.UTC,
        )

        updated_at = None
        if raw.get("latest_edit_timestamp_ms"):
            updated_at = datetime.datetime.fromtimestamp(
                raw["latest_edit_timestamp_ms"] / 1000,
                tz=datetime.UTC,
            )

        direction = "OUTBOUND" if raw.get("from_me") else "INBOUND"
        sender_id = raw.get("from")
        status = self._status_from_ack(raw.get("ack")) if direction == "OUTBOUND" else "READ"
        attachment = self._attachment_from_raw(raw)

        return Message(
            id=message_id,
            text=message_body,
            created_at=created_at,
            sender_id=sender_id,
            direction=direction,
            status=status,
            updated_at=updated_at,
            attachments=[attachment] if attachment else None,
        )

    #TODO: переделать парсинг аттачментов
    def _attachment_from_raw(self, raw: dict) -> Attachment | None:
        if not any([
            raw.get("mimetype"),
            raw.get("filename"),
            raw.get("size"),
            raw.get("media_key"),
            raw.get("client_url"),
            raw.get("direct_path"),
        ]):
            return None

        return Attachment(
            id=raw.get("message_id"),
            filename=raw.get("filename") or "",
            mimetype=raw.get("mimetype") or "",
            size=raw.get("size") or 0,
        )

    def _status_from_ack(
            self,
            ack: int,
    ) -> typing.Literal["PENDING", "SENT", "DELIVERED", "ERROR", "READ"]:
        #TODO - подумать нужен ли Pending или все таки это ERROR
        if ack == 0:
            return "PENDING"

        if ack == 1:
            return "SENT"

        if ack == 2:
            return "DELIVERED"

        if ack == 3:
            return "READ"

        return "ERROR"

    async def _scroll_opened_chat_up(self) -> None:
        await self._page.mouse.move(700, 450)
        await self._page.mouse.wheel(0, -3500)
        await self._page.wait_for_timeout(1200)


    @property
    def _page(self) -> Page:
        if self.page is None:
            raise RuntimeError("Client is not started. Use 'async with WhatsAppClient(...)'.")
        return self.page

    async def send_message_tg(self) -> dict | None:
        await self._page.goto("https://web.telegram.org/k/#@valbe_e")
        await self._page.wait_for_timeout(5000)



        bubble = self._page.locator(".bubble[data-mid]").last
        prev_data_mid = await bubble.get_attribute("data-mid")
        print(prev_data_mid)

        await self._page.wait_for_timeout(5000)

        bubble = self._page.locator(".bubble[data-mid]").last
        data_mid = await bubble.get_attribute("data-mid")
        print(data_mid)

        if data_mid == prev_data_mid:
            raise Exception("ID одинаковые")

        message_raw = await self._page.evaluate(
            """
            async (messageId) => {
                return await window.apiManagerProxy.getMessageById(Number(messageId));
            }
            """,
            data_mid,
        )
        message = self.telegram_message_from_raw(message_raw)
        print(message)


    def telegram_message_from_raw(self, raw: dict) -> Message:
        message_id = str(raw.get("mid") or raw.get("id"))

        direction = "OUTBOUND" if raw.get("pFlags", {}).get("out") else "INBOUND"

        return Message(
            id=message_id,
            text=raw.get("message") or "",
            created_at=datetime.datetime.fromtimestamp(
                raw["date"],
                tz=datetime.UTC,
            ),
            sender_id=str(raw["fromId"]),
            direction=direction,
            status=self._get_telegram_status(raw, direction),
            updated_at=self._get_updated_at(raw),
            attachments=self._get_telegram_attachments(raw),
        )

    def _get_telegram_status(
            self,
            raw: dict,
            direction: typing.Literal["INBOUND", "OUTBOUND"],
    ) -> typing.Literal["PENDING", "SENT", "DELIVERED", "ERROR", "READ"]:
        if direction == "INBOUND":
            return "READ"
        #{
        #     "out": true,
        #     "unread": true,
        #     "is_outgoing": true - ошибка сети отправлено
        # }
        pflags = raw.get("pFlags", {})

        if pflags.get("is_outgoing"):
            return "SENT"

        is_delivered = pflags.get("unread") and pflags.get("out")
        is_read = pflags.get("out")

        if is_delivered:
            return "DELIVERED"

        if is_read:
            return "READ"

        return "ERROR"

    def _get_updated_at(self, raw: dict) -> datetime.datetime | None:
        edit_date = raw.get("edit_date")

        if not edit_date:
            return None

        return datetime.datetime.fromtimestamp(
            edit_date,
            tz=datetime.UTC,
        )

    def _get_telegram_attachments(self, raw: dict) -> list[Attachment] | None:
        media = raw.get("media") or {}
        document = media.get("document")

        if not document:
            return None

        attachment = Attachment(
            id=str(document.get("id") or ""),
            filename=self._get_document_filename(document),
            mimetype=document.get("mime_type") or "",
            size=int(document.get("size") or 0),
        )

        return [attachment]

    def _get_document_filename(self, document: dict) -> str:
        if document.get("file_name"):
            return document["file_name"]

        for attr in document.get("attributes") or []:
            if attr.get("_") == "documentAttributeFilename":
                return attr.get("file_name") or ""

        return ""


