from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from db.models import Processo


# ==================================================
# DTOs
# ==================================================


@dataclass
class ProcessoCreate:
    numero_processo: str
    vara: Optional[str] = None
    comarca: Optional[str] = None
    tipo_acao: Optional[str] = None
    contratante: Optional[str] = None
    categoria_servico: Optional[str] = None

    papel: str = "Assistente Técnico"
    status: str = "Ativo"

    pasta_local: Optional[str] = None
    observacoes: Optional[str] = None


@dataclass
class ProcessoUpdate:
    numero_processo: Optional[str] = None
    vara: Optional[str] = None
    comarca: Optional[str] = None
    tipo_acao: Optional[str] = None
    contratante: Optional[str] = None
    categoria_servico: Optional[str] = None

    papel: Optional[str] = None
    status: Optional[str] = None

    pasta_local: Optional[str] = None
    observacoes: Optional[str] = None


# ==================================================
# HELPERS DE NORMALIZAÇÃO
# ==================================================


def _clean_str(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    cleaned = " ".join(v.strip().split())
    return cleaned if cleaned else None


def _normalize_owner_id(owner_user_id: int) -> int:
    return int(owner_user_id)


def _normalize_numero(numero: Optional[str]) -> Optional[str]:
    return _clean_str(numero)


def _normalize_status(value: Optional[str]) -> str:
    normalized = (_clean_str(value) or "Ativo").lower()

    if normalized == "ativo":
        return "Ativo"
    if normalized in ("concluido", "concluído"):
        return "Concluído"
    if normalized == "suspenso":
        return "Suspenso"

    return "Ativo"


def _normalize_papel(value: Optional[str]) -> str:
    normalized = (_clean_str(value) or "Assistente Técnico").lower()

    if normalized in ("perito", "perito judicial"):
        return "Perito Judicial"
    if normalized in ("assistente", "assistente tecnico", "assistente técnico"):
        return "Assistente Técnico"
    if normalized in (
        "particular",
        "trabalho particular",
        "avaliação particular",
        "avaliacao",
    ):
        return "Trabalho Particular"

    return _clean_str(value) or "Assistente Técnico"


# ==================================================
# HELPERS DE OBSERVAÇÕES / CATEGORIA
# ==================================================


def _extract_categoria_prefix(obs: str) -> Optional[str]:
    if not obs:
        return None

    text = obs.strip()
    if not text.startswith("[Categoria:"):
        return None

    end = text.find("]")
    if end == -1:
        return None

    inside = text[len("[Categoria:") : end].strip()
    return inside if inside else None


def _remove_categoria_prefix(obs: str) -> str:
    if not obs:
        return ""

    text = obs.strip()
    if not text.startswith("[Categoria:"):
        return obs

    end = text.find("]")
    if end == -1:
        return obs

    return text[end + 1 :].lstrip()


# ==================================================
# HELPERS DE QUERY
# ==================================================


def _like(q: str) -> str:
    return f"%{q.strip()}%"


def _owner_stmt(owner_user_id: int):
    return Processo.owner_user_id == _normalize_owner_id(owner_user_id)


def _status_rank_expr():
    status_lower = func.lower(Processo.status)
    return case(
        (status_lower == "ativo", 3),
        (status_lower == "suspenso", 2),
        (status_lower.in_(["concluido", "concluído"]), 1),
        else_=0,
    )


def _build_q_filter(qv: str):
    like = _like(qv)
    return or_(
        Processo.numero_processo.ilike(like),
        Processo.comarca.ilike(like),
        Processo.vara.ilike(like),
        Processo.contratante.ilike(like),
        Processo.tipo_acao.ilike(like),
        Processo.categoria_servico.ilike(like),
        Processo.papel.ilike(like),
        Processo.status.ilike(like),
        Processo.observacoes.ilike(like),
        Processo.pasta_local.ilike(like),
    )


def _apply_list_filters(
    stmt,
    *,
    status: Optional[str] = None,
    papel: Optional[str] = None,
    categoria_servico: Optional[str] = None,
    q: Optional[str] = None,
):
    status_v = _clean_str(status)
    papel_v = _clean_str(papel)
    categoria_v = _clean_str(categoria_servico)
    qv = _clean_str(q)

    if status_v:
        stmt = stmt.where(Processo.status == _normalize_status(status_v))
    if papel_v:
        stmt = stmt.where(Processo.papel == _normalize_papel(papel_v))
    if categoria_v:
        stmt = stmt.where(Processo.categoria_servico == categoria_v)
    if qv:
        stmt = stmt.where(_build_q_filter(qv))

    return stmt


def _apply_ordering(stmt, *, order_desc: bool):
    status_rank = _status_rank_expr()

    if order_desc:
        return stmt.order_by(status_rank.desc(), Processo.id.desc())
    return stmt.order_by(status_rank.asc(), Processo.id.asc())


def _count_by_status(
    session: Session, owner_user_id: int, status_normalized: str
) -> int:
    total = session.scalar(
        select(func.count())
        .select_from(Processo)
        .where(
            _owner_stmt(owner_user_id),
            func.lower(Processo.status) == status_normalized.lower(),
        )
    )
    return int(total or 0)


# ==================================================
# HELPERS DE ENTIDADE
# ==================================================


def _get_owned_processo(
    session: Session,
    owner_user_id: int,
    processo_id: int,
) -> Optional[Processo]:
    stmt = select(Processo).where(
        Processo.id == int(processo_id),
        _owner_stmt(owner_user_id),
    )
    return session.execute(stmt).scalars().first()


def _build_create_entity(owner_user_id: int, payload: ProcessoCreate) -> Processo:
    numero = _normalize_numero(payload.numero_processo)
    if not numero:
        raise ValueError("numero_processo é obrigatório")

    return Processo(
        owner_user_id=_normalize_owner_id(owner_user_id),
        numero_processo=numero,
        vara=_clean_str(payload.vara),
        comarca=_clean_str(payload.comarca),
        tipo_acao=_clean_str(payload.tipo_acao),
        contratante=_clean_str(payload.contratante),
        categoria_servico=_clean_str(payload.categoria_servico),
        papel=_normalize_papel(payload.papel),
        status=_normalize_status(payload.status),
        pasta_local=_clean_str(payload.pasta_local),
        observacoes=_clean_str(payload.observacoes),
    )


def _payload_to_update_data(payload: ProcessoUpdate) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    for field, value in payload.__dict__.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = _clean_str(value)
        data[field] = value

    if "numero_processo" in data:
        data["numero_processo"] = _normalize_numero(data["numero_processo"])
        if not data["numero_processo"]:
            raise ValueError("numero_processo não pode ficar vazio")

    if "papel" in data:
        data["papel"] = _normalize_papel(data["papel"])

    if "status" in data:
        data["status"] = _normalize_status(data["status"])

    return data


# ==================================================
# SERVICE
# ==================================================


class ProcessosService:
    @staticmethod
    def create(
        session: Session,
        owner_user_id: int,
        payload: ProcessoCreate,
    ) -> Processo:
        proc = _build_create_entity(owner_user_id, payload)
        session.add(proc)
        session.commit()
        session.refresh(proc)
        return proc

    @staticmethod
    def list(
        session: Session,
        owner_user_id: int,
        status: Optional[str] = None,
        papel: Optional[str] = None,
        categoria_servico: Optional[str] = None,
        q: Optional[str] = None,
        order_desc: bool = True,
        limit: Optional[int] = None,
    ) -> List[Processo]:
        stmt = select(Processo).where(_owner_stmt(owner_user_id))

        stmt = _apply_list_filters(
            stmt,
            status=status,
            papel=papel,
            categoria_servico=categoria_servico,
            q=q,
        )
        stmt = _apply_ordering(stmt, order_desc=order_desc)

        if limit is not None:
            limit_int = int(limit)
            if limit_int > 0:
                stmt = stmt.limit(limit_int)

        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> Optional[Processo]:
        return _get_owned_processo(session, owner_user_id, processo_id)

    @staticmethod
    def update(
        session: Session,
        owner_user_id: int,
        processo_id: int,
        payload: ProcessoUpdate,
    ) -> Processo:
        proc = _get_owned_processo(session, owner_user_id, processo_id)
        if not proc:
            raise ValueError("Processo não encontrado")

        data = _payload_to_update_data(payload)

        if data:
            for field, value in data.items():
                setattr(proc, field, value)
            session.commit()
            session.refresh(proc)

        return proc

    @staticmethod
    def delete(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> None:
        proc = _get_owned_processo(session, owner_user_id, processo_id)
        if not proc:
            raise ValueError("Processo não encontrado")

        session.delete(proc)
        session.commit()

    @staticmethod
    def duplicate(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> Processo:
        proc = _get_owned_processo(session, owner_user_id, processo_id)
        if not proc:
            raise ValueError("Processo não encontrado")

        base_ref = _clean_str(proc.numero_processo) or "Sem referência"
        duplicate_ref = f"{base_ref} (cópia)"

        new_proc = Processo(
            owner_user_id=_normalize_owner_id(owner_user_id),
            numero_processo=duplicate_ref,
            vara=_clean_str(proc.vara),
            comarca=_clean_str(proc.comarca),
            tipo_acao=_clean_str(proc.tipo_acao),
            contratante=_clean_str(proc.contratante),
            categoria_servico=_clean_str(proc.categoria_servico),
            papel=_normalize_papel(proc.papel),
            status=_normalize_status(proc.status),
            pasta_local=_clean_str(proc.pasta_local),
            observacoes=_clean_str(proc.observacoes),
        )
        session.add(new_proc)
        session.commit()
        session.refresh(new_proc)
        return new_proc

    @staticmethod
    def stats(session: Session, owner_user_id: int) -> Dict[str, int]:
        total = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(_owner_stmt(owner_user_id))
            )
            or 0
        )

        ativos = _count_by_status(session, owner_user_id, "Ativo")
        concluidos = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(
                    _owner_stmt(owner_user_id),
                    func.lower(Processo.status).in_(["concluido", "concluído"]),
                )
            )
            or 0
        )
        suspensos = _count_by_status(session, owner_user_id, "Suspenso")

        com_pasta = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(
                    _owner_stmt(owner_user_id),
                    Processo.pasta_local.is_not(None),
                    func.length(func.trim(Processo.pasta_local)) > 0,
                )
            )
            or 0
        )

        return {
            "total": int(total),
            "ativos": int(ativos),
            "concluidos": int(concluidos),
            "suspensos": int(suspensos),
            "com_pasta": int(com_pasta),
        }

    @staticmethod
    def summary(session: Session, owner_user_id: int) -> Dict[str, Dict[str, int]]:
        rows = list(
            session.execute(
                select(Processo.papel, Processo.status, func.count())
                .where(_owner_stmt(owner_user_id))
                .group_by(Processo.papel, Processo.status)
            ).all()
        )

        by_papel: Dict[str, int] = {}
        by_status: Dict[str, int] = {}

        for papel, status, total in rows:
            papel_key = _normalize_papel(papel)
            status_key = _normalize_status(status)
            by_papel[papel_key] = by_papel.get(papel_key, 0) + int(total or 0)
            by_status[status_key] = by_status.get(status_key, 0) + int(total or 0)

        return {
            "papel": by_papel,
            "status": by_status,
        }

    @staticmethod
    def backfill_categoria_from_observacoes(
        session: Session,
        owner_user_id: int,
        remove_prefix: bool = True,
        only_if_empty: bool = True,
    ) -> int:
        stmt = select(Processo).where(_owner_stmt(owner_user_id))
        rows = list(session.execute(stmt).scalars().all())

        changed = 0
        for processo in rows:
            current_cat = _clean_str(getattr(processo, "categoria_servico", None))
            if only_if_empty and current_cat:
                continue

            obs = (processo.observacoes or "").strip()
            categoria = _extract_categoria_prefix(obs)
            if not categoria:
                continue

            if remove_prefix:
                processo.observacoes = _clean_str(_remove_categoria_prefix(obs))
            processo.categoria_servico = _clean_str(categoria)
            changed += 1

        if changed:
            session.commit()

        return changed
