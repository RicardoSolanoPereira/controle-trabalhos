from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from db.models import Agendamento, LancamentoFinanceiro, Prazo, Processo


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
    cleaned = " ".join(str(v).strip().split())
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
    status_lower = func.lower(func.coalesce(Processo.status, ""))
    return case(
        (status_lower == "ativo", 3),
        (status_lower == "suspenso", 2),
        (status_lower.in_(["concluido", "concluído"]), 1),
        else_=0,
    )


def _build_q_filter(qv: str):
    like = _like(qv)

    def c(col):
        return func.coalesce(col, "")

    return or_(
        c(Processo.numero_processo).ilike(like),
        c(Processo.comarca).ilike(like),
        c(Processo.vara).ilike(like),
        c(Processo.contratante).ilike(like),
        c(Processo.tipo_acao).ilike(like),
        c(Processo.categoria_servico).ilike(like),
        c(Processo.papel).ilike(like),
        c(Processo.status).ilike(like),
        c(Processo.observacoes).ilike(like),
        c(Processo.pasta_local).ilike(like),
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


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _to_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


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


def _numero_ja_existe(
    session: Session,
    owner_user_id: int,
    numero_processo: str,
    ignore_id: Optional[int] = None,
) -> bool:
    stmt = (
        select(func.count())
        .select_from(Processo)
        .where(
            _owner_stmt(owner_user_id),
            Processo.numero_processo == numero_processo,
        )
    )

    if ignore_id is not None:
        stmt = stmt.where(Processo.id != int(ignore_id))

    total = session.scalar(stmt) or 0
    return int(total) > 0


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


def _payload_to_update_data(payload: ProcessoUpdate) -> dict[str, Any]:
    data: dict[str, Any] = {}

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
# HELPERS DE DASHBOARD / LISTA OPERACIONAL
# ==================================================


def _processo_metrics_map(
    session: Session,
    owner_user_id: int,
    processo_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not processo_ids:
        return {}

    owner_clause = _owner_stmt(owner_user_id)

    prazos_rows = session.execute(
        select(
            Prazo.processo_id,
            func.count(Prazo.id).label("prazos_abertos"),
            func.min(Prazo.data_limite).label("proximo_prazo"),
        )
        .select_from(Prazo)
        .join(Processo, Processo.id == Prazo.processo_id)
        .where(
            owner_clause,
            Prazo.concluido.is_(False),
            Prazo.processo_id.in_(processo_ids),
        )
        .group_by(Prazo.processo_id)
    ).all()

    agenda_rows = session.execute(
        select(
            Agendamento.processo_id,
            func.count(Agendamento.id).label("agendamentos_futuros"),
            func.min(Agendamento.inicio).label("proximo_agendamento"),
        )
        .select_from(Agendamento)
        .join(Processo, Processo.id == Agendamento.processo_id)
        .where(
            owner_clause,
            Agendamento.status == "Agendado",
            Agendamento.processo_id.in_(processo_ids),
        )
        .group_by(Agendamento.processo_id)
    ).all()

    fin_rows = session.execute(
        select(
            LancamentoFinanceiro.processo_id,
            func.coalesce(
                func.sum(
                    case(
                        (
                            LancamentoFinanceiro.tipo == "Receita",
                            LancamentoFinanceiro.valor,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("receitas"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            LancamentoFinanceiro.tipo == "Despesa",
                            LancamentoFinanceiro.valor,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("despesas"),
        )
        .select_from(LancamentoFinanceiro)
        .join(Processo, Processo.id == LancamentoFinanceiro.processo_id)
        .where(
            owner_clause,
            LancamentoFinanceiro.processo_id.in_(processo_ids),
        )
        .group_by(LancamentoFinanceiro.processo_id)
    ).all()

    metrics: dict[int, dict[str, Any]] = {}

    for processo_id, prazos_abertos, proximo_prazo in prazos_rows:
        pid = int(processo_id)
        metrics.setdefault(pid, {})
        metrics[pid]["prazos_abertos"] = int(prazos_abertos or 0)
        metrics[pid]["proximo_prazo"] = _to_datetime(proximo_prazo)

    for processo_id, agendamentos_futuros, proximo_agendamento in agenda_rows:
        pid = int(processo_id)
        metrics.setdefault(pid, {})
        metrics[pid]["agendamentos_futuros"] = int(agendamentos_futuros or 0)
        metrics[pid]["proximo_agendamento"] = _to_datetime(proximo_agendamento)

    for processo_id, receitas, despesas in fin_rows:
        pid = int(processo_id)
        metrics.setdefault(pid, {})
        rec = _safe_float(receitas)
        desp = _safe_float(despesas)
        metrics[pid]["receitas"] = rec
        metrics[pid]["despesas"] = desp
        metrics[pid]["saldo"] = rec - desp

    return metrics


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

        if _numero_ja_existe(session, owner_user_id, proc.numero_processo):
            raise ValueError("Já existe processo com essa referência")

        try:
            session.add(proc)
            session.commit()
            session.refresh(proc)
            return proc
        except Exception:
            session.rollback()
            raise

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
    ) -> list[Processo]:
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
    def list_enriched(
        session: Session,
        owner_user_id: int,
        status: Optional[str] = None,
        papel: Optional[str] = None,
        categoria_servico: Optional[str] = None,
        q: Optional[str] = None,
        order_desc: bool = True,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        processos = ProcessosService.list(
            session,
            owner_user_id=owner_user_id,
            status=status,
            papel=papel,
            categoria_servico=categoria_servico,
            q=q,
            order_desc=order_desc,
            limit=limit,
        )

        processo_ids = [int(getattr(p, "id", 0) or 0) for p in processos]
        metrics_map = _processo_metrics_map(session, owner_user_id, processo_ids)

        rows: list[dict[str, Any]] = []

        for p in processos:
            pid = int(getattr(p, "id", 0) or 0)
            metrics = metrics_map.get(pid, {})
            pasta_local = getattr(p, "pasta_local", None) or ""

            rows.append(
                {
                    "id": pid,
                    "numero_processo": getattr(p, "numero_processo", "") or "",
                    "vara": getattr(p, "vara", "") or "",
                    "comarca": getattr(p, "comarca", "") or "",
                    "tipo_acao": getattr(p, "tipo_acao", "") or "",
                    "contratante": getattr(p, "contratante", "") or "",
                    "categoria_servico": getattr(p, "categoria_servico", "") or "",
                    "papel": getattr(p, "papel", "") or "",
                    "status": getattr(p, "status", "") or "",
                    "pasta_local": pasta_local,
                    "observacoes": getattr(p, "observacoes", "") or "",
                    "tem_pasta": bool(str(pasta_local).strip()),
                    "prazos_abertos": int(metrics.get("prazos_abertos", 0) or 0),
                    "proximo_prazo": metrics.get("proximo_prazo"),
                    "agendamentos_futuros": int(
                        metrics.get("agendamentos_futuros", 0) or 0
                    ),
                    "proximo_agendamento": metrics.get("proximo_agendamento"),
                    "receitas": _safe_float(metrics.get("receitas", 0)),
                    "despesas": _safe_float(metrics.get("despesas", 0)),
                    "saldo": _safe_float(metrics.get("saldo", 0)),
                }
            )

        return rows

    @staticmethod
    def get(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> Optional[Processo]:
        return _get_owned_processo(session, owner_user_id, processo_id)

    @staticmethod
    def get_enriched(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> Optional[dict[str, Any]]:
        proc = _get_owned_processo(session, owner_user_id, processo_id)
        if not proc:
            return None

        pid = int(getattr(proc, "id", 0) or 0)
        metrics = _processo_metrics_map(session, owner_user_id, [pid]).get(pid, {})
        pasta_local = getattr(proc, "pasta_local", None) or ""

        return {
            "id": pid,
            "numero_processo": getattr(proc, "numero_processo", "") or "",
            "vara": getattr(proc, "vara", "") or "",
            "comarca": getattr(proc, "comarca", "") or "",
            "tipo_acao": getattr(proc, "tipo_acao", "") or "",
            "contratante": getattr(proc, "contratante", "") or "",
            "categoria_servico": getattr(proc, "categoria_servico", "") or "",
            "papel": getattr(proc, "papel", "") or "",
            "status": getattr(proc, "status", "") or "",
            "pasta_local": pasta_local,
            "observacoes": getattr(proc, "observacoes", "") or "",
            "tem_pasta": bool(str(pasta_local).strip()),
            "prazos_abertos": int(metrics.get("prazos_abertos", 0) or 0),
            "proximo_prazo": metrics.get("proximo_prazo"),
            "agendamentos_futuros": int(metrics.get("agendamentos_futuros", 0) or 0),
            "proximo_agendamento": metrics.get("proximo_agendamento"),
            "receitas": _safe_float(metrics.get("receitas", 0)),
            "despesas": _safe_float(metrics.get("despesas", 0)),
            "saldo": _safe_float(metrics.get("saldo", 0)),
        }

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

        if "numero_processo" in data and _numero_ja_existe(
            session,
            owner_user_id,
            data["numero_processo"],
            ignore_id=int(processo_id),
        ):
            raise ValueError("Já existe processo com essa referência")

        if not data:
            return proc

        try:
            for field, value in data.items():
                setattr(proc, field, value)
            session.commit()
            session.refresh(proc)
            return proc
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def delete(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> None:
        proc = _get_owned_processo(session, owner_user_id, processo_id)
        if not proc:
            raise ValueError("Processo não encontrado")

        try:
            session.delete(proc)
            session.commit()
        except Exception:
            session.rollback()
            raise

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
        suffix = datetime.now().strftime("%H%M%S")
        duplicate_ref = f"{base_ref} - cópia {suffix}"

        while _numero_ja_existe(session, owner_user_id, duplicate_ref):
            suffix = datetime.now().strftime("%H%M%S%f")
            duplicate_ref = f"{base_ref} - cópia {suffix}"

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

        try:
            session.add(new_proc)
            session.commit()
            session.refresh(new_proc)
            return new_proc
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def stats(session: Session, owner_user_id: int) -> dict[str, int]:
        total = (
            session.scalar(
                select(func.count())
                .select_from(Processo)
                .where(_owner_stmt(owner_user_id))
            )
            or 0
        )

        grouped = session.execute(
            select(
                func.lower(func.coalesce(Processo.status, "")).label("status"),
                func.count().label("total"),
            )
            .where(_owner_stmt(owner_user_id))
            .group_by(func.lower(func.coalesce(Processo.status, "")))
        ).all()

        by_status = {str(status or ""): int(qty or 0) for status, qty in grouped}

        ativos = by_status.get("ativo", 0)
        suspensos = by_status.get("suspenso", 0)
        concluidos = by_status.get("concluido", 0) + by_status.get("concluído", 0)

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
    def summary(session: Session, owner_user_id: int) -> dict[str, dict[str, int]]:
        rows = list(
            session.execute(
                select(Processo.papel, Processo.status, func.count())
                .where(_owner_stmt(owner_user_id))
                .group_by(Processo.papel, Processo.status)
            ).all()
        )

        by_papel: dict[str, int] = {}
        by_status: dict[str, int] = {}

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

        try:
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
        except Exception:
            session.rollback()
            raise
