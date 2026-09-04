from __future__ import annotations
import base64
import json
import uuid
from typing import Literal
from pydantic import BaseModel, Field, ValidationError

PROTOCOL_VERSION = 1

MessageType = Literal["echo_request", "echo_response"]


class Envelope(BaseModel):
    """Versioned message envelope carried inside the length-prefixed wire framing.

    `payload_b64` keeps the envelope binary-safe (arbitrary bytes) while the
    envelope itself is transported as JSON, so it stays human-readable/greppable
    on the wire for anything but the raw payload.
    """

    type: MessageType
    version: int = PROTOCOL_VERSION
    correlation_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    payload_b64: str = ""

    @property
    def payload(self) -> bytes:
        return base64.b64decode(self.payload_b64) if self.payload_b64 else b""

    @classmethod
    def new(cls, type: MessageType, payload: bytes, *, correlation_id: str | None = None) -> Envelope:
        payload_b64 = base64.b64encode(payload).decode("ascii")
        if correlation_id is not None:
            return cls(type=type, payload_b64=payload_b64, correlation_id=correlation_id)
        return cls(type=type, payload_b64=payload_b64)


class ProtocolError(ValueError):
    """Raised when a received message isn't a valid Envelope."""


def encode_envelope(env: Envelope) -> bytes:
    return env.model_dump_json().encode("utf-8")


def decode_envelope(data: bytes) -> Envelope:
    try:
        return Envelope.model_validate(json.loads(data.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as e:
        raise ProtocolError(f"Invalid message envelope: {e}") from e
