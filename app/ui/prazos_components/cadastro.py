from __future__ import annotations

from datetime import timedelta

import streamlit as st

from db.connection import get_session
from services.calendario_service import CalendarioService, RegrasCalendario
from services.prazos_service import PrazoCreate, PrazosService
from services.utils import date_to_br_datetime, format_date_br, now_br
from ui.theme import card, subtle_divider
from ui_state import bump_data_version
from ui.prazos_components.constants import (
    DEBUG_PRAZOS,
    KEY_C_AUDIT,
    KEY_C_BASE,
    KEY_C_DATA_LIM,
    KEY_C_DIAS,
    KEY_C_EVENTO,
    KEY_C_LOCAL,
    KEY_C_MODE,
    KEY_C_OBS,
    KEY_C_ORIGEM,
    KEY_C_PRIO,
    KEY_C_PROC,
    KEY_C_REF,
    KEY_C_USAR_TJSP,
    ORIGENS,
    PRIORIDADES,
)
from ui.prazos_components.helpers import merge_obs_with_audit, norm, safe_str
from ui.components.sections import section_card
from ui.prazos_components.state import request_list_tab, request_tab


def render_cadastro(
    *,
    owner_user_id: int,
    proc_labels: list[str],
    label_to_id: dict[str, int],
    proc_by_id: dict[int, dict[str, object]],
) -> None:
    with st.container(border=True):
        section_card(
            "Novo prazo",
            "Escolha o modo de contagem, confira a data final e salve.",
        )
        subtle_divider()

        sel_proc = st.selectbox("Trabalho *", proc_labels, index=0, key=KEY_C_PROC)
        processo_id = int(label_to_id[sel_proc])
        proc = proc_by_id.get(processo_id)
        comarca_proc = (safe_str(proc.get("comarca")) or None) if proc else None

        st.markdown("**1) Modo de contagem**")
        modo = st.selectbox(
            "Modo",
            ["Manual", "Dias corridos", "Dias úteis"],
            key=KEY_C_MODE,
        )

        subtle_divider()
        st.markdown("**2) Base e cálculo**")

        if modo == "Manual":
            st.date_input("Data limite *", key=KEY_C_DATA_LIM)
            st.session_state[KEY_C_AUDIT] = ""

        elif modo == "Dias corridos":
            c1, c2 = st.columns(2)
            base = c1.date_input("Data base", key=KEY_C_BASE)
            dias = c2.number_input("Qtd dias", min_value=1, step=1, key=KEY_C_DIAS)

            nova = base + timedelta(days=int(dias))
            st.session_state[KEY_C_DATA_LIM] = nova
            st.session_state[KEY_C_AUDIT] = "Auto: dias corridos"

            card(
                "Data final",
                nova.strftime("%d/%m/%Y"),
                f"Base: {base.strftime('%d/%m/%Y')} • +{int(dias)} dia(s)",
                tone="info",
            )

        else:
            c1, c2 = st.columns(2)
            base = c1.date_input("Data base (disponibilização DJE)", key=KEY_C_BASE)
            dias = c2.number_input(
                "Qtd dias úteis",
                min_value=1,
                step=1,
                key=KEY_C_DIAS,
            )

            usar_tjsp = st.checkbox(
                "Considerar calendário TJSP (inclui CPC art. 220 automaticamente)",
                key=KEY_C_USAR_TJSP,
            )

            incluir_municipal = st.checkbox(
                "Incluir feriados municipais da comarca",
                key=KEY_C_LOCAL,
                disabled=not bool(comarca_proc),
                help="Requer 'Comarca' preenchida no trabalho.",
            )

            regras = RegrasCalendario(
                incluir_nacional=True,
                incluir_estadual_sp=True,
                incluir_tjsp_geral=bool(usar_tjsp),
                incluir_tjsp_comarca=bool(usar_tjsp),
                incluir_municipal=bool(incluir_municipal),
            )

            aplicar_local = bool(comarca_proc)

            nova = CalendarioService.prazo_dje_tjsp(
                disponibilizacao=base,
                dias_uteis=int(dias),
                comarca=comarca_proc,
                municipio=None,
                aplicar_local=aplicar_local,
                regras=regras,
            )

            st.session_state[KEY_C_DATA_LIM] = nova

            if usar_tjsp:
                if incluir_municipal and comarca_proc:
                    st.session_state[KEY_C_AUDIT] = (
                        f"Auto: DJE + dias úteis (TJSP/CPC220 + municipal {comarca_proc})"
                    )
                else:
                    st.session_state[KEY_C_AUDIT] = (
                        "Auto: DJE + dias úteis (TJSP/CPC220)"
                    )
            else:
                if incluir_municipal and comarca_proc:
                    st.session_state[KEY_C_AUDIT] = (
                        f"Auto: DJE + dias úteis (Nac/Estadual + municipal {comarca_proc})"
                    )
                else:
                    st.session_state[KEY_C_AUDIT] = (
                        "Auto: DJE + dias úteis (Nac/Estadual)"
                    )

            card(
                "Data final",
                nova.strftime("%d/%m/%Y"),
                f"Base: {base.strftime('%d/%m/%Y')} • {int(dias)} dia(s) úteis"
                + (
                    f" • Comarca: {comarca_proc}"
                    if (incluir_municipal and comarca_proc)
                    else ""
                ),
                tone="info",
            )

            if DEBUG_PRAZOS:
                from datetime import date as _date

                st.markdown("### 🔎 DEBUG PRAZO")
                st.write("comarca_proc:", repr(comarca_proc))
                st.write("aplicar_local:", aplicar_local)
                st.write("incluir_municipal:", bool(incluir_municipal))
                st.write("usar_tjsp:", bool(usar_tjsp))
                st.write("base:", base)
                st.write("dias:", int(dias))
                st.write("nova:", nova)

                ini = _date(2026, 1, 15)
                fim = _date(2026, 2, 15)
                fer_set = CalendarioService.feriados_aplicaveis(
                    ini,
                    fim,
                    comarca=comarca_proc,
                    municipio=None,
                    aplicar_local=aplicar_local,
                    regras=regras,
                )
                st.write("feriados janela:", sorted(list(fer_set)))

        subtle_divider()
        st.markdown("**3) Detalhes do prazo**")

        preview_date = st.session_state.get(KEY_C_DATA_LIM, now_br().date())
        preview_event = safe_str(st.session_state.get(KEY_C_EVENTO))
        preview_prio = safe_str(st.session_state.get(KEY_C_PRIO) or "Média")

        p1, p2, p3 = st.columns(3)
        with p1:
            card(
                "Data apurada",
                format_date_br(preview_date),
                "resultado do cálculo",
                tone="info",
            )
        with p2:
            card(
                "Prioridade",
                preview_prio or "Média",
                "nível operacional",
                tone="neutral",
            )
        with p3:
            card(
                "Evento",
                preview_event or "A definir",
                "descrição principal",
                tone="neutral",
            )

        with st.form("form_prazo_create", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)

            evento = c1.text_input("Evento *", key=KEY_C_EVENTO)
            prioridade = c2.selectbox(
                "Prioridade",
                list(PRIORIDADES),
                index=1,
                key=KEY_C_PRIO,
            )
            origem = c3.selectbox(
                "Origem (opcional)",
                list(ORIGENS),
                index=0,
                key=KEY_C_ORIGEM,
            )

            referencia = st.text_input(
                "Referência (opcional)",
                placeholder="Ex.: fls. 389 / ID 12345 / mov. 12.1",
                key=KEY_C_REF,
            )
            obs = st.text_area("Observações", key=KEY_C_OBS)

            salvar = st.form_submit_button(
                "Salvar prazo",
                type="primary",
                use_container_width=True,
            )

        if salvar:
            if not safe_str(evento):
                st.error("Informe o evento.")
                return

            try:
                data_final = st.session_state.get(KEY_C_DATA_LIM, now_br().date())
                dt_lim = date_to_br_datetime(data_final)

                audit_txt = safe_str(st.session_state.get(KEY_C_AUDIT))
                obs_final = merge_obs_with_audit(obs, audit_txt)

                with get_session() as s:
                    prazo_novo = PrazosService.create(
                        s,
                        owner_user_id,
                        PrazoCreate(
                            processo_id=int(processo_id),
                            evento=safe_str(evento),
                            data_limite=dt_lim,
                            prioridade=prioridade,
                            origem=(origem or None),
                            referencia=norm(referencia),
                            observacoes=obs_final,
                        ),
                    )

                bump_data_version(owner_user_id)

                request_tab("Lista")
                request_list_tab("Abertos")

                st.session_state[KEY_C_EVENTO] = ""
                st.session_state[KEY_C_REF] = ""
                st.session_state[KEY_C_OBS] = ""
                st.session_state[KEY_C_PRIO] = "Média"
                st.session_state[KEY_C_ORIGEM] = ""

                st.success(f"Prazo criado com sucesso. ID: {prazo_novo.id}")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao criar prazo: {e}")
