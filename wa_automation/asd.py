import datetime
import typing
from dataclasses import dataclass
from enum import StrEnum


@dataclass
class Attachment:
    id: str
    filename: str
    mimetype: str
    size: int


@dataclass
class Message:
    id: str
    text: str
    created_at: datetime.datetime
    sender_id: str
    direction: typing.Literal["INBOUND", "OUTBOUND"]
    status: typing.Literal["PENDING", "SENT", "DELIVERED", "ERROR", "READ"]
    updated_at: datetime.datetime | None = None
    attachments: list[Attachment] | None = None


class ChatType(StrEnum):
    DIRECT = "DIRECT"
    BROADCAST = "BROADCAST"
    GROUP = "GROUP"

@dataclass
class Chat:
    id: str
    title: str
    preview_message: str
    preview_last_time_message: datetime.datetime
    type: ChatType
    unread_count: int
