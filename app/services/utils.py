from __future__ import annotations

from datetime import datetime, date
from zoneinfo import ZoneInfo

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def now_br() -> datetime:
    return datetime.now(BRAZIL_TZ)


def date_to_br_datetime(d: date) -> datetime:
    # meia-noite local (SP)
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=BRAZIL_TZ)


def _parse_dt_like(value) -> datetime | None:
    """
    Aceita:
    - datetime (naive ou tz-aware)
    - date
    - str em ISO (com ou sem 'Z', com ou sem offset)
    - str 'dd/mm/YYYY'
    - str 'dd/mm/YYYY HH:MM' (opcional, melhora robustez)
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return date_to_br_datetime(value)

    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None

        # Normaliza ISO com Z -> +00:00 (fromisoformat não aceita "Z" puro)
        v_iso = v.replace("Z", "+00:00")

        # Tenta ISO primeiro (cobre 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM:SS',
        # com/sem microssegundos, com/sem offset)
        try:
            return datetime.fromisoformat(v_iso)
        except Exception:
            pass

        # Formatos BR comuns
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.strptime(v, fmt)
            except Exception:
                continue

        return None

    return None


def ensure_br(dt: datetime | date | str) -> datetime:
    """
    Garante datetime timezone-aware no fuso de São Paulo.
    - se vier naive, assume que já está em horário local (SP)
    - se vier tz-aware, converte para SP
    """
    parsed = _parse_dt_like(dt)
    if parsed is None:
        raise ValueError(f"Data inválida para ensure_br: {dt!r}")

    if parsed.tzinfo is None:
        # Assumimos SP para naive (padrão do app)
        return parsed.replace(tzinfo=BRAZIL_TZ)

    return parsed.astimezone(BRAZIL_TZ)


def format_date_br(dt: datetime | date | str) -> str:
    dt_br = ensure_br(dt)
    return dt_br.strftime("%d/%m/%Y")


def format_datetime_br(dt: datetime | date | str) -> str:
    """
    Extra opcional (não quebra nada se não usar):
    formato padrão para exibir data+hora em pt-BR.
    """
    dt_br = ensure_br(dt)
    return dt_br.strftime("%d/%m/%Y %H:%M")
