from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import asc, delete, desc, or_, select, update
from sqlalchemy.orm import Session

from db.models import Agendamento, Processo


STATUS_VALIDOS = ("Agendado", "Realizado", "Cancelado")
TIPOS_VALIDOS = ("Vistoria", "Reunião", "Audiência", "Outro")


# ==========================================================
# SENTINELA PARA UPDATE PARCIAL
# ==========================================================

_UNSET = object()


# ==========================================================
# DTOs
# ==========================================================


@dataclass(frozen=True)
class AgendamentoCreate:
    processo_id: int
    tipo: str
    inicio: datetime
    fim: Optional[datetime] = None
    local: Optional[str] = None
    descricao: Optional[str] = None
    status: str = "Agendado"


@dataclass(frozen=True)
class AgendamentoUpdate:
    processo_id: Any = field(default=_UNSET)
    tipo: Any = field(default=_UNSET)
    inicio: Any = field(default=_UNSET)
    fim: Any = field(default=_UNSET)
    local: Any = field(default=_UNSET)
    descricao: Any = field(default=_UNSET)
    status: Any = field(default=_UNSET)


# ==========================================================
# SERVICE
# ==========================================================


class AgendamentosService:
    # -------------------------
    # Helpers básicos
    # -------------------------
    @staticmethod
    def _clean_str(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    @staticmethod
    def _normalize_tipo(tipo: str) -> str:
        t = str(tipo or "").strip()
        if t not in TIPOS_VALIDOS:
            raise ValueError(f"tipo inválido (use: {', '.join(TIPOS_VALIDOS)})")
        return t

    @staticmethod
    def _normalize_status(status: str) -> str:
        s = str(status or "").strip()
        if s not in STATUS_VALIDOS:
            raise ValueError(f"status inválido (use: {', '.join(STATUS_VALIDOS)})")
        return s

    @staticmethod
    def _validate_interval(inicio: datetime, fim: Optional[datetime]) -> None:
        if not isinstance(inicio, datetime):
            raise ValueError("início inválido")
        if fim is not None and not isinstance(fim, datetime):
            raise ValueError("fim inválido")
        if fim is not None and fim < inicio:
            raise ValueError("fim não pode ser anterior ao início")

    @staticmethod
    def _assert_processo_owner(
        session: Session,
        owner_user_id: int,
        processo_id: int,
    ) -> None:
        stmt = select(Processo.id).where(
            Processo.id == int(processo_id),
            Processo.owner_user_id == int(owner_user_id),
        )
        exists = session.execute(stmt).first() is not None
        if not exists:
            raise ValueError("Processo não encontrado (ou não pertence ao usuário)")

    @staticmethod
    def _compute_alert_flags_for_status(status: str) -> dict[str, bool]:
        """
        Regras:
        - Agendado => alertas rearmados
        - Realizado/Cancelado => alertas marcados como já tratados
        """
        if status == "Agendado":
            return {
                "alerta_24h_enviado": False,
                "alerta_2h_enviado": False,
            }

        return {
            "alerta_24h_enviado": True,
            "alerta_2h_enviado": True,
        }

    @staticmethod
    def _compute_flags_for_update(
        *,
        inicio_old: datetime,
        fim_old: Optional[datetime],
        status_old: str,
        inicio_new: datetime,
        fim_new: Optional[datetime],
        status_new: str,
    ) -> dict[str, bool]:
        """
        Regras:
        - Se status final não for Agendado => não alertar mais
        - Se status final for Agendado:
            - se voltou para Agendado => rearmar
            - se mudou horário => rearmar
            - caso contrário => não mexe nas flags
        """
        if status_new != "Agendado":
            return {
                "alerta_24h_enviado": True,
                "alerta_2h_enviado": True,
            }

        voltou_para_agendado = status_old != "Agendado" and status_new == "Agendado"
        mudou_horario = (inicio_new != inicio_old) or (fim_new != fim_old)

        if voltou_para_agendado or mudou_horario:
            return {
                "alerta_24h_enviado": False,
                "alerta_2h_enviado": False,
            }

        return {}

    @staticmethod
    def _apply_filters(
        stmt,
        *,
        processo_id: Optional[int] = None,
        tipo: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
    ):
        if processo_id is not None:
            stmt = stmt.where(Agendamento.processo_id == int(processo_id))

        if tipo:
            stmt = stmt.where(
                Agendamento.tipo == AgendamentosService._normalize_tipo(tipo)
            )

        if status:
            stmt = stmt.where(
                Agendamento.status == AgendamentosService._normalize_status(status)
            )

        q_clean = AgendamentosService._clean_str(q)
        if q_clean:
            like = f"%{q_clean}%"
            stmt = stmt.where(
                or_(
                    Agendamento.local.ilike(like),
                    Agendamento.descricao.ilike(like),
                )
            )

        return stmt

    # -------------------------
    # CRUD
    # -------------------------
    @staticmethod
    def create(
        session: Session,
        owner_user_id: int,
        payload: AgendamentoCreate,
    ) -> Agendamento:
        if not payload.processo_id:
            raise ValueError("processo_id é obrigatório")

        AgendamentosService._assert_processo_owner(
            session,
            owner_user_id,
            int(payload.processo_id),
        )

        tipo = AgendamentosService._normalize_tipo(payload.tipo)
        status = AgendamentosService._normalize_status(payload.status or "Agendado")
        local = AgendamentosService._clean_str(payload.local)
        descricao = AgendamentosService._clean_str(payload.descricao)

        AgendamentosService._validate_interval(payload.inicio, payload.fim)

        flags = AgendamentosService._compute_alert_flags_for_status(status)

        a = Agendamento(
            processo_id=int(payload.processo_id),
            tipo=tipo,
            inicio=payload.inicio,
            fim=payload.fim,
            local=local,
            descricao=descricao,
            status=status,
            atualizado_em=datetime.utcnow(),
            **flags,
        )

        try:
            session.add(a)
            session.commit()
            session.refresh(a)
            return a
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def list(
        session: Session,
        owner_user_id: int,
        processo_id: Optional[int] = None,
        tipo: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        order: str = "asc",
        limit: int = 300,
    ) -> list[Agendamento]:
        limit = max(1, min(int(limit), 1000))
        order = "desc" if str(order).lower() == "desc" else "asc"

        stmt = (
            select(Agendamento)
            .join(Processo, Processo.id == Agendamento.processo_id)
            .where(Processo.owner_user_id == int(owner_user_id))
        )

        stmt = AgendamentosService._apply_filters(
            stmt,
            processo_id=processo_id,
            tipo=tipo,
            status=status,
            q=q,
        )

        stmt = stmt.order_by(
            desc(Agendamento.inicio) if order == "desc" else asc(Agendamento.inicio)
        )

        return list(session.execute(stmt.limit(limit)).scalars().all())

    @staticmethod
    def get(
        session: Session,
        owner_user_id: int,
        agendamento_id: int,
    ) -> Optional[Agendamento]:
        stmt = (
            select(Agendamento)
            .join(Processo, Processo.id == Agendamento.processo_id)
            .where(
                Agendamento.id == int(agendamento_id),
                Processo.owner_user_id == int(owner_user_id),
            )
        )
        return session.execute(stmt).scalars().first()

    @staticmethod
    def update(
        session: Session,
        owner_user_id: int,
        agendamento_id: int,
        payload: AgendamentoUpdate,
    ) -> Agendamento:
        a = AgendamentosService.get(session, owner_user_id, int(agendamento_id))
        if not a:
            raise ValueError("Agendamento não encontrado")

        inicio_old = a.inicio
        fim_old = a.fim
        status_old = a.status

        data: dict[str, Any] = {}

        if payload.processo_id is not _UNSET:
            pid = int(payload.processo_id)
            AgendamentosService._assert_processo_owner(session, owner_user_id, pid)
            data["processo_id"] = pid

        if payload.tipo is not _UNSET:
            data["tipo"] = AgendamentosService._normalize_tipo(payload.tipo)

        if payload.status is not _UNSET:
            data["status"] = AgendamentosService._normalize_status(payload.status)

        if payload.inicio is not _UNSET:
            if payload.inicio is None:
                raise ValueError("início não pode ser vazio")
            data["inicio"] = payload.inicio

        if payload.fim is not _UNSET:
            # aqui pode ser datetime OU None, ambos válidos
            data["fim"] = payload.fim

        if payload.local is not _UNSET:
            data["local"] = AgendamentosService._clean_str(payload.local)

        if payload.descricao is not _UNSET:
            data["descricao"] = AgendamentosService._clean_str(payload.descricao)

        inicio_new = data.get("inicio", a.inicio)
        fim_new = data.get("fim", a.fim)
        status_new = data.get("status", a.status)

        AgendamentosService._validate_interval(inicio_new, fim_new)

        data.update(
            AgendamentosService._compute_flags_for_update(
                inicio_old=inicio_old,
                fim_old=fim_old,
                status_old=status_old,
                inicio_new=inicio_new,
                fim_new=fim_new,
                status_new=status_new,
            )
        )

        data["atualizado_em"] = datetime.utcnow()

        try:
            session.execute(
                update(Agendamento)
                .where(Agendamento.id == int(agendamento_id))
                .values(**data)
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

        updated = AgendamentosService.get(session, owner_user_id, int(agendamento_id))
        if not updated:
            raise RuntimeError("Falha ao recarregar agendamento após update")
        return updated

    @staticmethod
    def set_status(
        session: Session,
        owner_user_id: int,
        agendamento_id: int,
        status: str,
    ) -> Agendamento:
        a = AgendamentosService.get(session, owner_user_id, int(agendamento_id))
        if not a:
            raise ValueError("Agendamento não encontrado")

        status_norm = AgendamentosService._normalize_status(status)

        data: dict[str, Any] = {
            "status": status_norm,
            "atualizado_em": datetime.utcnow(),
        }
        data.update(AgendamentosService._compute_alert_flags_for_status(status_norm))

        try:
            session.execute(
                update(Agendamento)
                .where(Agendamento.id == int(agendamento_id))
                .values(**data)
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

        updated = AgendamentosService.get(session, owner_user_id, int(agendamento_id))
        if not updated:
            raise RuntimeError("Falha ao recarregar agendamento após set_status")
        return updated

    @staticmethod
    def delete(
        session: Session,
        owner_user_id: int,
        agendamento_id: int,
    ) -> None:
        a = AgendamentosService.get(session, owner_user_id, int(agendamento_id))
        if not a:
            raise ValueError("Agendamento não encontrado")

        try:
            session.execute(
                delete(Agendamento).where(Agendamento.id == int(agendamento_id))
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
