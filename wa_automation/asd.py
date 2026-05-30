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
    status: typing.Literal["PENDING", "SENT", "DELIVERED", "ERROR", "READ"]
    updated_at: datetime.datetime | None = None
    attachments: list[Attachment] | None = None
