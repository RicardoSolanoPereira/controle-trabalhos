from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any
from ui.shared.constants import ATUACAO_UI

import pandas as pd


ROOT_TRABALHOS = Path(os.getenv("ROOT_TRABALHOS", r"D:\TRABALHOS"))


def strip_html(text: str | None) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"</div\s*>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compact_text(v: str | None, max_len: int = 120) -> str:
    txt = strip_html(v)
    if len(txt) <= max_len:
        return txt
    return txt[: max_len - 1].rstrip() + "…"


def safe_strip(value: Any) -> str:
    return strip_html("" if value is None else str(value))


def escape_text(value: Any) -> str:
    return html.escape(safe_strip(value))


def fmt_money(value: Any) -> str:
    try:
        num = float(value or 0)
    except Exception:
        num = 0.0
    s = f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_date(value: Any) -> str:
    if value is None:
        return "—"
    try:
        dt = pd.to_datetime(value)
        if pd.isna(dt):
            return "—"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return "—"


def fmt_datetime(value: Any) -> str:
    if value is None:
        return "—"
    try:
        dt = pd.to_datetime(value)
        if pd.isna(dt):
            return "—"
        if dt.hour == 0 and dt.minute == 0:
            return dt.strftime("%d/%m/%Y")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"


def status_badge(status: str) -> str:
    s = (status or "").strip().lower()
    if s == "ativo":
        return "🟢 Ativo"
    if s in ("concluído", "concluido"):
        return "✅ Concluído"
    if s == "suspenso":
        return "⏸ Suspenso"
    return status or "—"


def status_chip_class(status: str | None) -> str:
    s = (status or "").strip().lower()
    if s == "ativo":
        return "sp-chip-success"
    if s in ("concluído", "concluido"):
        return "sp-chip-neutral"
    if s == "suspenso":
        return "sp-chip-warning"
    return "sp-chip-info"


def status_tone(status: str | None) -> str:
    s = (status or "").strip().lower()
    if s == "ativo":
        return "success"
    if s in ("concluído", "concluido"):
        return "neutral"
    if s == "suspenso":
        return "warning"
    return "info"


def norm_tipo_trabalho(val: str | None) -> str:
    v = (val or "").strip()
    if not v:
        return "Assistente Técnico"
    v_low = v.lower()
    if v_low in ("perito", "perito judicial"):
        return "Perito Judicial"
    if v_low in ("assistente", "assistente tecnico", "assistente técnico"):
        return "Assistente Técnico"
    if v_low in (
        "particular",
        "trabalho particular",
        "avaliação particular",
        "avaliacao",
    ):
        return "Trabalho Particular"
    return v


def atuacao_badge(db_val: str | None) -> str:
    v = norm_tipo_trabalho(db_val)
    if v == "Perito Judicial":
        return "⚖️ Perícia (Juízo)"
    if v == "Assistente Técnico":
        return "🛠️ Assistência Técnica"
    if v == "Trabalho Particular":
        return "🏷️ Particular"
    return v


def atuacao_chip_class(db_val: str | None) -> str:
    v = norm_tipo_trabalho(db_val)
    if v == "Perito Judicial":
        return "sp-chip-info"
    if v == "Assistente Técnico":
        return "sp-chip-success"
    if v == "Trabalho Particular":
        return "sp-chip-warning"
    return "sp-chip-neutral"


def atuacao_label_from_db(db_val: str | None) -> str:
    v = norm_tipo_trabalho(db_val)
    for label, db in ATUACAO_UI.items():
        if db == v:
            return label
    return v


def atuacao_db_from_label(label: str) -> str:
    return ATUACAO_UI.get(label, "Assistente Técnico")


def guess_pasta_local(numero: str) -> str:
    n = (numero or "").strip()
    if not n:
        return ""
    safe = re.sub(r"[\\/]+", "-", n)
    safe = re.sub(r'[:*?"<>|]+', "", safe).strip()
    return rf"{ROOT_TRABALHOS}\{safe}"
