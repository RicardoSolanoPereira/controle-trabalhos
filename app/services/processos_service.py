from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, or_, case
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
# HELPERS
# ==================================================
def _clean_str(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v2 = " ".join(v.strip().split())
    return v2 if v2 else None


def _like(q: str) -> str:
    return f"%{q.strip()}%"


def _extract_categoria_prefix(obs: str) -> Optional[str]:
    if not obs:
        return None
    s = obs.strip()
    if not s.startswith("[Categoria:"):
        return None
    end = s.find("]")
    if end == -1:
        return None
    inside = s[len("[Categoria:") : end].strip()
    return inside if inside else None


def _remove_categoria_prefix(obs: str) -> str:
    if not obs:
        return ""
    s = obs.strip()
    if not s.startswith("[Categoria:"):
        return obs
    end = s.find("]")
    if end == -1:
        return obs
    return s[end + 1 :].lstrip()


def _status_rank_expr():
    status_lower = func.lower(Processo.status)
    return case(
        (status_lower == "ativo", 3),
        (status_lower == "suspenso", 2),
        (status_lower.in_(["concluido", "concluído"]), 1),
        else_=0,
    )


def _normalize_status(value: Optional[str]) -> str:
    v = (_clean_str(value) or "Ativo").lower()
    if v == "ativo":
        return "Ativo"
    if v in ("concluido", "concluído"):
        return "Concluído"
    if v == "suspenso":
        return "Suspenso"
    return "Ativo"


def _normalize_papel(value: Optional[str]) -> str:
    v = (_clean_str(value) or "Assistente Técnico").lower()
    if v in ("perito", "perito judicial"):
        return "Perito Judicial"
    if v in ("assistente", "assistente tecnico", "assistente técnico"):
        return "Assistente Técnico"
    if v in ("particular", "trabalho particular", "avaliação particular", "avaliacao"):
        return "Trabalho Particular"
    return _clean_str(value) or "Assistente Técnico"


def _normalize_numero(numero: Optional[str]) -> Optional[str]:
    return _clean_str(numero)


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
        numero = _normalize_numero(payload.numero_processo)
        if not numero:
            raise ValueError("numero_processo é obrigatório")

        proc = Processo(
            owner_user_id=owner_user_id,
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
        stmt = select(Processo).where(Processo.owner_user_id == int(owner_user_id))

        status_v = _clean_str(status)
        papel_v = _clean_str(papel)
        cat_v = _clean_str(categoria_servico)

        if status_v:
            stmt = stmt.where(Processo.status == _normalize_status(status_v))
        if papel_v:
            stmt = stmt.where(Processo.papel == _normalize_papel(papel_v))
        if cat_v:
            stmt = stmt.where(Processo.categoria_servico == cat_v)

        qv = _clean_str(q)
        if qv:
            stmt = stmt.where(_build_q_filter(qv))

        status_rank = _status_rank_expr()

        if order_desc:
            stmt = stmt.order_by(status_rank.desc(), Processo.id.desc())
        else:
            stmt = stmt.order_by(status_rank.asc(), Processo.id.asc())

        if limit is not None:
            lim = int(limit)
            if lim > 0:
                stmt = stmt.limit(lim)

        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> Optional[Processo]:
        stmt = select(Processo).where(
            Processo.id == int(processo_id),
            Processo.owner_user_id == int(owner_user_id),
        )
        return session.execute(stmt).scalars().first()

    @staticmethod
    def update(
        session: Session,
        owner_user_id: int,
        processo_id: int,
        payload: ProcessoUpdate,
    ) -> Processo:
        proc = ProcessosService.get(session, owner_user_id, processo_id)
        if not proc:
            raise ValueError("Processo não encontrado")

        data: Dict[str, Any] = {}
        for field, val in payload.__dict__.items():
            if val is None:
                continue
            if isinstance(val, str):
                val = _clean_str(val)
            data[field] = val

        if "numero_processo" in data:
            data["numero_processo"] = _normalize_numero(data["numero_processo"])
            if not data["numero_processo"]:
                raise ValueError("numero_processo não pode ficar vazio")

        if "papel" in data:
            data["papel"] = _normalize_papel(data["papel"])

        if "status" in data:
            data["status"] = _normalize_status(data["status"])

        if data:
            for k, v in data.items():
                setattr(proc, k, v)
            session.commit()
            session.refresh(proc)

        return proc

    @staticmethod
    def delete(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> None:
        proc = ProcessosService.get(session, owner_user_id, processo_id)
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
        proc = ProcessosService.get(session, owner_user_id, processo_id)
        if not proc:
            raise ValueError("Processo não encontrado")

        base_ref = _clean_str(proc.numero_processo) or "Sem referência"
        duplicate_ref = f"{base_ref} (cópia)"

        new_proc = Processo(
            owner_user_id=int(owner_user_id),
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
                .where(Processo.owner_user_id == int(owner_user_id))
            )
            or 0
        )

        ativos = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(
                    Processo.owner_user_id == int(owner_user_id),
                    func.lower(Processo.status) == "ativo",
                )
            )
            or 0
        )

        concluidos = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(
                    Processo.owner_user_id == int(owner_user_id),
                    func.lower(Processo.status).in_(["concluido", "concluído"]),
                )
            )
            or 0
        )

        suspensos = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(
                    Processo.owner_user_id == int(owner_user_id),
                    func.lower(Processo.status) == "suspenso",
                )
            )
            or 0
        )

        com_pasta = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(
                    Processo.owner_user_id == int(owner_user_id),
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
                .where(Processo.owner_user_id == int(owner_user_id))
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
        stmt = select(Processo).where(Processo.owner_user_id == int(owner_user_id))
        rows = list(session.execute(stmt).scalars().all())

        changed = 0
        for p in rows:
            current_cat = _clean_str(getattr(p, "categoria_servico", None))
            if only_if_empty and current_cat:
                continue

            obs = (p.observacoes or "").strip()
            cat = _extract_categoria_prefix(obs)
            if not cat:
                continue

            if remove_prefix:
                p.observacoes = _clean_str(_remove_categoria_prefix(obs))
            p.categoria_servico = _clean_str(cat)
            changed += 1

        if changed:
            session.commit()
        return changed
