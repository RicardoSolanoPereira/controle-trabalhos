from pathlib import Path
import os

from ui.shared.constants import ATUACAO_UI


ATUACAO_UI_ALL = ATUACAO_UI
ATUACAO_UI_PROCESSOS = {k: v for k, v in ATUACAO_UI.items() if k != "(Todas)"}

STATUS_VALIDOS = ("Ativo", "Concluído", "Suspenso")

CATEGORIAS_UI = [
    "Perícia",
    "Assistência Técnica",
    "Consultoria",
    "Análise documental",
    "Vistoria",
    "Topografia",
    "Avaliação imobiliária",
    "Regularização",
    "Outros",
]

ROOT_TRABALHOS = Path(os.getenv("ROOT_TRABALHOS", r"D:\\TRABALHOS"))

MENU_PRAZOS_KEY = "Prazos"
MENU_AGENDA_KEY = "Agenda"
MENU_FIN_KEY = "Financeiro"

SECTION_CARTEIRA = "Carteira"
SECTION_NOVO = "Novo"
SECTION_PAINEL = "Painel do trabalho"
SECTIONS = (SECTION_CARTEIRA, SECTION_NOVO, SECTION_PAINEL)

K_SECTION = "processos_section"
K_SECTION_SELECTOR = "processos_section_selector"
K_SELECTED_ID = "processo_selected_id"
K_SECTION_LEGACY = "trabalhos_section"
K_SECTION_SELECTOR_LEGACY = "trabalhos_section_selector"

K_FILTER_STATUS = "processos_filter_status"
K_FILTER_ATUACAO = "processos_filter_atuacao"
K_FILTER_CATEGORIA = "processos_filter_categoria"
K_FILTER_Q = "processos_filter_q"
K_FILTER_ORDEM = "processos_filter_ordem"
K_FILTER_SOMENTE_COM_PASTA = "processos_filter_somente_com_pasta"
K_FILTER_PAGE = "processos_filter_page"

K_CREATE_PASTA = "proc_create_pasta"
K_CREATE_NUMERO = "proc_create_numero"
K_CREATE_ATUACAO = "proc_create_atuacao"
K_CREATE_STATUS = "proc_create_status"
K_CREATE_CATEGORIA = "proc_create_categoria"
K_CREATE_TIPO = "proc_create_tipo_acao"
K_CREATE_COMARCA = "proc_create_comarca"
K_CREATE_VARA = "proc_create_vara"
K_CREATE_CONTRATANTE = "proc_create_contratante"
K_CREATE_OBS = "proc_create_obs"

K_EDIT_SEARCH = "proc_edit_search"

CARD_PAGE_SIZE = 20
CARD_PAGE_SIZE_OPTIONS = [10, 20, 30, 50]
