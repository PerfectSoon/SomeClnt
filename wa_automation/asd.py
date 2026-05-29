import datetime
import typing
from dataclasses import dataclass

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
    updated_at: datetime.datetime | None = None
    attachments: list[Attachment] | None = None


async def get_messages(
        chat_id: str,
        cursor: str | None = None,
        after_date: datetime.datetime | None = None,
        before_date: datetime.datetime | None = None,
        limit: int = 50
): ...