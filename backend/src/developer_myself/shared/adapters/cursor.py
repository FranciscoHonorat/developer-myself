"""Cursor opaco de paginação keyset: base64url de `{"t": instante, "id": desempate}`."""

import base64
import binascii
import json
from datetime import datetime

from developer_myself.shared.adapters.http import http_error


def encode_cursor(moment: datetime, tiebreak: str) -> str:
    raw = json.dumps({"t": moment.isoformat(), "id": tiebreak})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(token: str) -> tuple[datetime, str]:
    """Cursor vem do cliente: qualquer coisa fora do formato vira 422, nunca 500."""
    try:
        raw = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
        moment = datetime.fromisoformat(raw["t"])
        tiebreak = raw["id"]
        if not isinstance(tiebreak, str) or moment.tzinfo is None:
            raise ValueError
    except (binascii.Error, ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
        raise http_error(422, "Cursor de paginação inválido.", "INVALID_CURSOR") from exc
    return moment, tiebreak
