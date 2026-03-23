from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PrazoRow:
    prazo_id: int
    processo_id: int
    processo_numero: str
    processo_tipo_acao: str | None
    processo_comarca: str | None
    processo_vara: str | None
    processo_contratante: str | None
    processo_papel: str | None

    evento: str
    data_limite: Any
    prioridade: str
    concluido: bool
    origem: str | None
    referencia: str | None
    observacoes: str | None
