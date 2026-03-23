from __future__ import annotations

from typing import Any

from ui.processos_helpers import (
    atuacao_badge,
    atuacao_chip_class,
    compact_text,
    fmt_date,
    fmt_datetime,
    fmt_money,
    safe_strip,
    status_badge,
    status_chip_class,
    status_tone,
    strip_html,
)


def processo_view_model(r: dict) -> dict[str, Any]:
    ref = strip_html(r.get("numero_processo")) or "Sem referência"
    cliente = strip_html(r.get("contratante"))
    comarca = strip_html(r.get("comarca"))
    vara = strip_html(r.get("vara"))
    categoria = strip_html(r.get("categoria_servico"))
    descricao = strip_html(r.get("tipo_acao"))
    obs = compact_text(r.get("observacoes"), 180)
    pasta = safe_strip(r.get("pasta_local"))
    status = r.get("status")
    papel = r.get("papel")

    return {
        "id": int(r.get("id") or 0),
        "ref": ref,
        "cliente": cliente,
        "comarca": comarca,
        "vara": vara,
        "categoria": categoria,
        "descricao": descricao,
        "obs": obs,
        "pasta": pasta,
        "tem_pasta": bool(r.get("tem_pasta")),
        "status_raw": status,
        "status_label": status_badge(status),
        "status_class": status_chip_class(status),
        "status_tone": status_tone(status),
        "atuacao_label": atuacao_badge(papel),
        "atuacao_class": atuacao_chip_class(papel),
        "papel": papel,
        "prazos": int(r.get("prazos_abertos", 0) or 0),
        "proximo_prazo": fmt_date(r.get("proximo_prazo")),
        "agenda": int(r.get("agendamentos_futuros", 0) or 0),
        "proximo_agendamento": fmt_datetime(r.get("proximo_agendamento")),
        "saldo": fmt_money(r.get("saldo", 0)),
    }


def row_label(r: dict) -> str:
    vm = processo_view_model(r)
    parts = [vm["ref"], vm["atuacao_label"]]
    if vm["categoria"]:
        parts.append(vm["categoria"])
    if vm["cliente"]:
        parts.append(vm["cliente"])
    return " — ".join(parts)
