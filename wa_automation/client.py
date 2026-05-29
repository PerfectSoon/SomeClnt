from __future__ import annotations

import asyncio
import datetime
import random
import time
from pathlib import Path

from playwright.async_api import BrowserContext, Page, TimeoutError, async_playwright


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


    async def send_message(self) -> None:
        await self.wait_for_whatsapp_modules()
        chat_id = "142940974391481@lid"
        message = "Не пиши"
        await self.open_chat_by_id(chat_id)
        await self.page.wait_for_timeout(timeout=10)
        compose_box = self._page.locator(
            "[data-testid='conversation-compose-box-input'][contenteditable='true']"
        )

        await compose_box.wait_for(state="visible", timeout=30000)
        await compose_box.click()
        await self._typing_text(message)
        await self._page.keyboard.press("Enter")
        #TODO: убедиться что оно доставлено

    async def get_messages(
            self,
            chat_id: str,
            cursor: str | None = None,
            after_date: datetime.datetime | None = None,
            before_date: datetime.datetime | None = None,
            limit: int = 50
    ):


    @property
    def _page(self) -> Page:
        if self.page is None:
            raise RuntimeError("Client is not started. Use 'async with WhatsAppClient(...)'.")
        return self.page
