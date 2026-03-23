from __future__ import annotations

from typing import Any

import pandas as pd

from services.utils import ensure_br, format_date_br, now_br
from ui.prazos_components.types import PrazoRow


def safe_str(value: Any) -> str:
    return str(value or "").strip()


def norm(value: str | None) -> str | None:
    text = safe_str(value)
    return text or None


def dias_restantes(dt_like: Any) -> int:
    dt_br = ensure_br(dt_like)
    hoje = now_br().date()
    return (dt_br.date() - hoje).days


def status_label(dias: int, concluido: bool) -> str:
    if concluido:
        return "✅ Concluído"
    if dias < 0:
        return "🔴 Atrasado"
    if dias == 0:
        return "📅 Hoje"
    if dias <= 5:
        return "🟠 Urgente"
    if dias <= 10:
        return "🟡 Atenção"
    return "🟢 Planejado"


def priority_rank(prioridade: str) -> int:
    order = {"Alta": 0, "Média": 1, "Baixa": 2}
    return order.get(prioridade, 1)


def proc_label_dict(p: dict[str, Any]) -> str:
    pid = int(p["id"])
    numero = str(p.get("numero_processo") or "")
    tipo = safe_str(p.get("tipo_acao"))
    papel = safe_str(p.get("papel"))

    label = f"[{pid}] {numero}"
    if tipo:
        label += f" – {tipo}"
    if papel:
        label += f" • {papel}"
    return label


def filter_text(row: PrazoRow) -> str:
    parts = [
        row.processo_numero or "",
        row.processo_tipo_acao or "",
        row.processo_comarca or "",
        row.processo_vara or "",
        row.processo_contratante or "",
        row.processo_papel or "",
        row.evento or "",
        row.origem or "",
        row.referencia or "",
        row.observacoes or "",
        row.prioridade or "",
    ]
    return " ".join(str(x) for x in parts).lower()


def dicts_to_dataclass(items: list[dict[str, Any]]) -> list[PrazoRow]:
    out: list[PrazoRow] = []

    for item in items:
        prazo = item.get("prazo") or {}
        proc = item.get("proc") or {}

        out.append(
            PrazoRow(
                prazo_id=int(prazo.get("id") or 0),
                processo_id=int(proc.get("id") or 0),
                processo_numero=str(proc.get("numero_processo") or ""),
                processo_tipo_acao=proc.get("tipo_acao"),
                processo_comarca=proc.get("comarca"),
                processo_vara=proc.get("vara"),
                processo_contratante=proc.get("contratante"),
                processo_papel=proc.get("papel"),
                evento=str(prazo.get("evento") or ""),
                data_limite=prazo.get("data_limite"),
                prioridade=str(prazo.get("prioridade") or "Média"),
                concluido=bool(prazo.get("concluido") or False),
                origem=prazo.get("origem"),
                referencia=prazo.get("referencia"),
                observacoes=prazo.get("observacoes"),
            )
        )

    return out


def merge_obs_with_audit(obs: str | None, audit: str | None) -> str | None:
    base = safe_str(obs)
    audit_txt = safe_str(audit)

    if not base and not audit_txt:
        return None
    if base and not audit_txt:
        return base
    if not base and audit_txt:
        return f"🧮 {audit_txt}"
    return f"{base}\n🧮 {audit_txt}"


def apply_lista_filters(
    rows: list[PrazoRow],
    *,
    tipo_val: str | None,
    processo_id_val: int | None,
    prioridade_val: str | None,
    origem_val: str | None,
    busca: str,
) -> list[PrazoRow]:
    filtered: list[PrazoRow] = []

    for row in rows:
        papel = safe_str(row.processo_papel)
        origem = safe_str(row.origem)
        prioridade = safe_str(row.prioridade)

        if tipo_val and papel != tipo_val:
            continue
        if processo_id_val and int(row.processo_id) != int(processo_id_val):
            continue
        if prioridade_val and prioridade != prioridade_val:
            continue
        if origem_val and origem != origem_val:
            continue
        if busca and busca not in filter_text(row):
            continue

        filtered.append(row)

    return filtered


def split_status_groups(
    filtered: list[PrazoRow],
) -> tuple[
    list[PrazoRow], list[PrazoRow], list[PrazoRow], list[PrazoRow], list[PrazoRow]
]:
    abertos = [r for r in filtered if not r.concluido]
    hoje = [r for r in abertos if dias_restantes(r.data_limite) == 0]
    atrasados = [r for r in abertos if dias_restantes(r.data_limite) < 0]
    vencem7 = [r for r in abertos if 0 <= dias_restantes(r.data_limite) <= 7]
    concluidos = [r for r in filtered if r.concluido]
    return abertos, hoje, atrasados, vencem7, concluidos


def sort_operational(
    items: list[PrazoRow], reverse_days: bool = False
) -> list[PrazoRow]:
    return sorted(
        items,
        key=lambda r: (
            dias_restantes(r.data_limite) * (-1 if reverse_days else 1),
            priority_rank(r.prioridade),
            ensure_br(r.data_limite),
            -int(r.prazo_id),
        ),
    )


def build_df(items: list[PrazoRow], include_status: bool = True) -> pd.DataFrame | None:
    if not items:
        return None

    rows: list[dict[str, Any]] = []
    for item in items:
        dias = dias_restantes(item.data_limite)
        row: dict[str, Any] = {
            "prazo_id": int(item.prazo_id),
            "processo": f"{item.processo_numero} – {item.processo_tipo_acao or 'Sem tipo de ação'}",
            "evento": item.evento,
            "data_limite": format_date_br(item.data_limite),
            "dias": int(dias),
            "prioridade": item.prioridade,
            "origem": safe_str(item.origem) or "—",
            "_sort_dt": ensure_br(item.data_limite),
        }
        if include_status:
            row["status"] = status_label(dias, item.concluido)
        rows.append(row)

    return pd.DataFrame(rows)


def prazo_option_label(row: PrazoRow) -> str:
    dias = dias_restantes(row.data_limite)
    status = status_label(dias, row.concluido)
    return (
        f"[{int(row.prazo_id)}] {row.processo_numero} | "
        f"{row.evento} | {format_date_br(row.data_limite)} | {status}"
    )
