# WhatsApp Web Automation

Python + Playwright automation for WhatsApp Web:

- login with a phone number;
- collect chats;
- collect messages from a chat;
- send a message to a chat.

WhatsApp Web does not provide a stable public browser automation API. The code uses resilient selector fallbacks, but UI changes in WhatsApp can still require selector updates.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

The browser profile is stored in `storage/whatsapp-profile`, so the login session is reused between runs.

Login with phone number:

```powershell
python -m wa_automation.cli login +79991234567
```

Collect chats:

```powershell
python -m wa_automation.cli chats --limit 50
```

Collect recent messages from a chat:

```powershell
python -m wa_automation.cli messages "Chat title" --limit 30
```

Send a message:

```powershell
python -m wa_automation.cli send "Chat title" "Hello from Playwright"
```

## Notes

- First login must run with a visible browser window.
- For unattended runs, log in once, then reuse the same profile.
- Use exact chat titles for `messages` and `send`.
- Be careful with bulk messaging. Respect WhatsApp terms, rate limits, and user consent.
