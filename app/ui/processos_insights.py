from __future__ import annotations

from typing import Callable

import streamlit as st


def summarize_filters(
    *,
    filter_status: str,
    filter_atuacao: str,
    filter_categoria: str,
    filter_q: str,
    filter_ordem: str,
    somente_com_pasta: bool,
) -> list[str]:
    chips: list[str] = []

    if filter_status != "(Todos)":
        chips.append(f"Status: {filter_status}")
    if filter_atuacao != "(Todas)":
        chips.append(f"Atuação: {filter_atuacao}")
    if filter_categoria != "(Todas)":
        chips.append(f"Categoria: {filter_categoria}")
    if filter_q:
        chips.append(f"Busca: {filter_q}")
    if filter_ordem != "Mais recentes":
        chips.append(f"Ordem: {filter_ordem}")
    if somente_com_pasta:
        chips.append("Somente com pasta")

    return chips


def results_metrics(
    rows: list[dict], *, safe_strip: Callable[[object], str]
) -> dict[str, int]:
    ativos = sum(1 for r in rows if safe_strip(r.get("status")).lower() == "ativo")
    concluidos = sum(
        1 for r in rows if safe_strip(r.get("status")).lower().startswith("concl")
    )
    suspensos = sum(
        1 for r in rows if safe_strip(r.get("status")).lower() == "suspenso"
    )
    com_pasta = sum(1 for r in rows if bool(r.get("tem_pasta")))
    com_prazo = sum(1 for r in rows if int(r.get("prazos_abertos", 0) or 0) > 0)

    return {
        "resultado": len(rows),
        "ativos": ativos,
        "concluidos": concluidos,
        "suspensos": suspensos,
        "com_pasta": com_pasta,
        "com_prazo": com_prazo,
    }


def render_header(stats: dict[str, int], *, render_html: Callable[[str], None]) -> None:
    render_html(
        f"""
        <div class="sp-page-hero">
          <div class="sp-page-hero-grid">
            <div>
              <div class="sp-page-kicker">gestão operacional</div>
              <div class="sp-page-title">Trabalhos</div>
              <div class="sp-page-subtitle">
                Carteira central de processos, perícias e serviços técnicos, com acesso rápido
                a prazo, agenda, financeiro e contexto operacional.
              </div>
              <div class="sp-chip-row" style="margin-top:12px;">
                <span class="sp-chip">Hub operacional</span>
                <span class="sp-chip">Filtros rápidos</span>
                <span class="sp-chip">Ações por registro</span>
              </div>
            </div>
            <div class="sp-inline-metrics">
              <div class="sp-mini-stat"><div class="sp-mini-stat-label">total</div><div class="sp-mini-stat-value">{stats.get('total', 0)}</div><div class="sp-mini-stat-sub">registros</div></div>
              <div class="sp-mini-stat"><div class="sp-mini-stat-label">ativos</div><div class="sp-mini-stat-value">{stats.get('ativos', 0)}</div><div class="sp-mini-stat-sub">em andamento</div></div>
              <div class="sp-mini-stat"><div class="sp-mini-stat-label">concluídos</div><div class="sp-mini-stat-value">{stats.get('concluidos', 0)}</div><div class="sp-mini-stat-sub">finalizados</div></div>
              <div class="sp-mini-stat"><div class="sp-mini-stat-label">com pasta</div><div class="sp-mini-stat-value">{stats.get('com_pasta', 0)}</div><div class="sp-mini-stat-sub">organizados</div></div>
            </div>
          </div>
        </div>
        """
    )


def render_filter_summary(chips: list[str]) -> None:
    if not chips:
        st.caption("Visualização geral sem filtros específicos.")
        return
    st.caption(f"Filtros aplicados: {'  •  '.join(chips)}")


def render_priority_banners(
    stats: dict[str, int],
    rows: list[dict],
    *,
    results_metrics_fn: Callable[[list[dict]], dict[str, int]],
    banner_html_fn: Callable[[str, str, str], str],
    render_html: Callable[[str], None],
) -> None:
    metrics = results_metrics_fn(rows)
    banners: list[str] = []

    if stats.get("ativos", 0) > 0:
        banners.append(
            banner_html_fn(
                "success",
                "Carteira ativa",
                f"{stats.get('ativos', 0)} trabalho(s) ativo(s) na base.",
            )
        )
    if metrics["resultado"] > 0:
        banners.append(
            banner_html_fn(
                "info",
                "Resultado atual",
                f"{metrics['resultado']} registro(s) retornado(s) com os filtros aplicados.",
            )
        )
    if stats.get("suspensos", 0) > 0:
        banners.append(
            banner_html_fn(
                "warning",
                "Atenção de carteira",
                f"{stats.get('suspensos', 0)} trabalho(s) suspenso(s) aguardando retomada.",
            )
        )
    if stats.get("com_pasta", 0) < stats.get("total", 0):
        faltantes = max(0, stats.get("total", 0) - stats.get("com_pasta", 0))
        banners.append(
            banner_html_fn(
                "warning",
                "Organização de arquivos",
                f"{faltantes} registro(s) ainda sem pasta local vinculada.",
            )
        )
    if not banners:
        banners.append(
            banner_html_fn(
                "success",
                "Base organizada",
                "Sem alertas relevantes no momento.",
            )
        )

    cols = st.columns(min(len(banners), 4))
    for col, banner in zip(cols, banners[:4]):
        with col:
            render_html(banner)


def render_overview_cards(
    stats: dict[str, int],
    *,
    grid: Callable,
    card: Callable,
) -> None:
    a, b, c, d, e = grid(5, columns_mobile=2)
    with a:
        card("Total", f"{stats.get('total', 0)}", "todos os registros", tone="info")
    with b:
        card("Ativos", f"{stats.get('ativos', 0)}", "em andamento", tone="success")
    with c:
        card(
            "Concluídos", f"{stats.get('concluidos', 0)}", "finalizados", tone="neutral"
        )
    with d:
        card("Suspensos", f"{stats.get('suspensos', 0)}", "pausados", tone="warning")
    with e:
        card("Com pasta", f"{stats.get('com_pasta', 0)}", "vínculo local", tone="info")


def render_list_insights(
    rows: list[dict],
    *,
    results_metrics_fn: Callable[[list[dict]], dict[str, int]],
    grid: Callable,
    card: Callable,
) -> None:
    metrics = results_metrics_fn(rows)
    a, b, c, d, e = grid(5, columns_mobile=2)
    with a:
        card("Resultado", f"{metrics['resultado']}", "nos filtros", tone="info")
    with b:
        card(
            "Ativos",
            f"{metrics['ativos']}",
            "na visualização",
            tone="success" if metrics["ativos"] else "neutral",
        )
    with c:
        card(
            "Concluídos", f"{metrics['concluidos']}", "na visualização", tone="neutral"
        )
    with d:
        card(
            "Suspensos",
            f"{metrics['suspensos']}",
            "na visualização",
            tone="warning" if metrics["suspensos"] else "neutral",
        )
    with e:
        card(
            "Com prazo",
            f"{metrics['com_prazo']}",
            "aberto(s)",
            tone="info" if metrics["com_prazo"] else "neutral",
        )


def render_empty_list(
    *,
    empty_state: Callable,
    grid: Callable,
    button: Callable,
    go_new: Callable[[], None],
    clear_filters: Callable[[], None],
) -> None:
    empty_state(
        title="Nenhum trabalho encontrado",
        subtitle="Ajuste os filtros ou cadastre um novo registro.",
        icon="📁",
    )
    a, b = grid(2, columns_mobile=1)
    with a:
        button(
            "➕ Cadastrar novo trabalho",
            key="proc_empty_new",
            type="primary",
            on_click=go_new,
        )
    with b:
        button("🧹 Limpar filtros", key="proc_empty_clear", on_click=clear_filters)
