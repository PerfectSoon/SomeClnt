import datetime

from wa_automation.asd import ChatType


def _detect_chat_type(chat_id: str, raw_chat: dict) -> ChatType:
    if chat_id.endswith("@g.us"):
        read_only = raw_chat.get("isReadOnly")
        can_send = raw_chat.get("canSend")

        is_broadcast = bool(read_only == True or can_send == False)
        if is_broadcast:
            return ChatType.BROADCAST

        return ChatType.GROUP

    if chat_id.endswith("@broadcast"):
        return ChatType.BROADCAST

    return ChatType.DIRECT


def _extract_preview_message(message: dict | None) -> str | None:
    if not message:
        return None

    return (
        message.get("body")
        or message.get("caption")
        or message.get("text")
        or None
    )


def _extract_last_message(raw_chat: dict) -> dict | None:
    msgs = raw_chat.get("msgs") or []

    if not msgs:
        return None

    return msgs[-1]


def _extract_timestamp(
    raw_chat: dict,
    last_message: dict | None,
) -> datetime.datetime | None:
    ts = (
        (last_message or {}).get("t")
        or raw_chat.get("lastChatEntryTimestamp")
        or raw_chat.get("t")
    )

    if not ts:
        return None

    return datetime.datetime.fromtimestamp(
        ts,
        tz=datetime.UTC,
    )

#Объект чата
"""
{
    "labels": [],
    "id": "120363306196183657@g.us",
    "t": 0,
    "unreadCount": 0,
    "unreadDividerOffset": 0,
    "archive": false,
    "isReadOnly": true,
    "isLocked": false,
    "muteExpiration": 0,
    "isAutoMuted": false,
    "name": "Очень пикантное предложение 🔥",
    "notSpam": false,
    "capiThreadControl": 0,
    "ephemeralDuration": 0,
    "ephemeralSettingTimestamp": 0,
    "disappearingModeInitiator": "chat",
    "disappearingModeTrigger": "chat_settings",
    "unreadMentionCount": 0,
    "hasUnreadMention": false,
    "archiveAtMentionViewedInDrawer": false,
    "hasChatBeenOpened": true,
    "tcToken": null,
    "tcTokenTimestamp": null,
    "endOfHistoryTransferType": 1,
    "pendingInitialLoading": false,
    "celebrationAnimationLastPlayed": 0,
    "hasOpened": true,
    "lastChatEntryTimestamp": 1780164690,
    "hasRequestedWelcomeMsg": false,
    "hasCtwaConsumerDataSharingDisclosureSystemMsg": false,
    "limitSharing": {
        "trigger": 0
    },
    "msgs": []
}
"""