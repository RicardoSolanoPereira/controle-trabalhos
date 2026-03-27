from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

import streamlit as st

from db.models import Processo
from ui_state import get_data_version

from .constants import KEY_CREATE_PROC, KEY_LIST_FILTRO_PROC, KEY_MOBILE_MODE


@dataclass(frozen=True)
class ProcMaps:
    labels: List[str]
    label_to_id: Dict[str, int]
    label_by_id: Dict[int, str]


def is_mobile_hint() -> bool:
    return bool(st.session_state.get(KEY_MOBILE_MODE, False))


def safe_str(value: Any) -> str:
    return str(value or "").strip()


def normalize_optional_str(value: str | None) -> str | None:
    text = safe_str(value)
    return text or None


def format_dt(dt: Optional[datetime]) -> str:
    return dt.strftime("%d/%m/%Y %H:%M") if dt else ""


def combine_date_time(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, 0)


def sanitize_end_dt(
    inicio: datetime,
    use_end: bool,
    d_fim: date,
    h_fim: time,
) -> Optional[datetime]:
    if not use_end:
        return None

    fim = combine_date_time(d_fim, h_fim)

    if fim == inicio:
        return None
    if fim < inicio:
        raise ValueError("A data/hora de fim não pode ser anterior ao início.")

    return fim


def ag_data_version(owner_user_id: int) -> int:
    return get_data_version(owner_user_id)


def proc_label(p: Processo) -> str:
    tipo = safe_str(getattr(p, "tipo_acao", None))
    papel = safe_str(getattr(p, "papel", None))
    numero = safe_str(getattr(p, "numero_processo", None))

    base = f"[{p.id}] {numero}"
    if tipo:
        base += f" – {tipo}"
    if papel:
        base += f"  •  {papel}"
    return base


def build_proc_maps(processos: List[Processo]) -> ProcMaps:
    labels: List[str] = []
    label_to_id: Dict[str, int] = {}
    label_by_id: Dict[int, str] = {}

    for p in processos:
        lbl = proc_label(p)
        labels.append(lbl)
        label_to_id[lbl] = int(p.id)
        label_by_id[int(p.id)] = lbl

    return ProcMaps(
        labels=labels,
        label_to_id=label_to_id,
        label_by_id=label_by_id,
    )


def build_agendamento_label(a, proc_label_by_id: Dict[int, str]) -> str:
    proc_lbl = proc_label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    return f"[#{a.id}] {format_dt(a.inicio)} — {a.tipo} — {a.status} — {proc_lbl}"


def parse_agendamento_id_from_label(label: str) -> int:
    head = label.split("]")[0]
    return int(head.replace("[#", "").strip())


def apply_pref_processo_defaults(proc_maps: ProcMaps) -> None:
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return

    try:
        pref_id_int = int(pref_id)
    except Exception:
        return

    pref_label = proc_maps.label_by_id.get(pref_id_int)
    if not pref_label:
        return

    st.session_state.setdefault(KEY_CREATE_PROC, pref_label)
    st.session_state.setdefault(KEY_LIST_FILTRO_PROC, pref_label)
