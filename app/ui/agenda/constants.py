from __future__ import annotations

from services.agendamentos_service import STATUS_VALIDOS, TIPOS_VALIDOS


# ==========================================================
# UI / MODO DE EXIBIÇÃO
# ==========================================================

KEY_MOBILE_MODE = "ui_mobile_mode"


# ==========================================================
# CREATE
# ==========================================================

KEY_CREATE_PROC = "ag_create_proc"
KEY_CREATE_TIPO = "ag_create_tipo"
KEY_CREATE_STATUS = "ag_create_status"
KEY_CREATE_DINI = "ag_create_dini"
KEY_CREATE_HINI = "ag_create_hini"
KEY_CREATE_USE_END = "ag_create_use_end"
KEY_CREATE_DFIM = "ag_create_dfim"
KEY_CREATE_HFIM = "ag_create_hfim"
KEY_CREATE_LOCAL = "ag_create_local"
KEY_CREATE_DESC = "ag_create_desc"


# ==========================================================
# LIST
# ==========================================================

KEY_LIST_FILTRO_PROC = "ag_list_filtro_proc"
KEY_LIST_FILTRO_TIPO = "ag_list_filtro_tipo"
KEY_LIST_FILTRO_STATUS = "ag_list_filtro_status"
KEY_LIST_LIMIT = "ag_list_limit"
KEY_LIST_ORDER = "ag_list_order"
KEY_LIST_BUSCA = "ag_list_busca"


# ==========================================================
# EDIT
# ==========================================================

KEY_EDIT_SELECTED = "ag_edit_selected"
KEY_EDIT_PICKER = "ag_edit_picker"
KEY_EDIT_PROC = "ag_edit_proc"
KEY_EDIT_TIPO = "ag_edit_tipo"
KEY_EDIT_STATUS = "ag_edit_status"
KEY_EDIT_DINI = "ag_edit_dini"
KEY_EDIT_HINI = "ag_edit_hini"
KEY_EDIT_USE_END = "ag_edit_use_end"
KEY_EDIT_DFIM = "ag_edit_dfim"
KEY_EDIT_HFIM = "ag_edit_hfim"
KEY_EDIT_LOCAL = "ag_edit_local"
KEY_EDIT_DESC = "ag_edit_desc"


# ==========================================================
# DELETE
# ==========================================================

KEY_DELETE_CONFIRM = "ag_del_confirm"


# ==========================================================
# DOMAIN OPTIONS
# ==========================================================

TIPOS = list(TIPOS_VALIDOS)
STATUS = list(STATUS_VALIDOS)
