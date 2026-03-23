from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from db.models import Prazo, Processo


PrazoStatusFilter = Literal["all", "open", "closed"]


@dataclass(frozen=True)
class PrazoCreate:
    processo_id: int
    evento: str
    data_limite: datetime
    prioridade: str = "Média"
    origem: str | None = None
    referencia: str | None = None
    observacoes: str | None = None


@dataclass(frozen=True)
class PrazoUpdate:
    evento: str | None = None
    data_limite: datetime | None = None
    prioridade: str | None = None
    concluido: bool | None = None
    origem: str | None = None
    referencia: str | None = None
    observacoes: str | None = None


class PrazosService:
    _UPDATABLE_FIELDS = {
        "evento",
        "data_limite",
        "prioridade",
        "concluido",
        "origem",
        "referencia",
        "observacoes",
    }

    _PRIORIDADES_VALIDAS = {"Baixa", "Média", "Alta"}

    @staticmethod
    def _clean_str(val: str | None) -> str | None:
        if val is None:
            return None
        cleaned = val.strip()
        return cleaned or None

    @staticmethod
    def _normalize_prioridade_create(val: str | None) -> str:
        cleaned = PrazosService._clean_str(val)
        if cleaned is None:
            return "Média"
        return cleaned if cleaned in PrazosService._PRIORIDADES_VALIDAS else "Média"

    @staticmethod
    def _normalize_prioridade_update(val: str) -> str:
        cleaned = PrazosService._clean_str(val)
        if cleaned is None or cleaned not in PrazosService._PRIORIDADES_VALIDAS:
            raise ValueError("Prioridade inválida.")
        return cleaned

    @staticmethod
    def _validate_datetime(value: datetime | None, field_name: str) -> None:
        if value is None:
            raise ValueError(f"{field_name} é obrigatória.")
        if not isinstance(value, datetime):
            raise ValueError(f"{field_name} deve ser datetime.")

    @staticmethod
    def _validate_bool(value: Any, field_name: str) -> None:
        if not isinstance(value, bool):
            raise ValueError(f"{field_name} deve ser booleano.")

    @staticmethod
    def _owned_processo(session: Session, owner_user_id: int, processo_id: int) -> bool:
        stmt = select(Processo.id).where(
            Processo.id == processo_id,
            Processo.owner_user_id == owner_user_id,
        )
        return session.execute(stmt).first() is not None

    @staticmethod
    def _ensure_owned_processo(
        session: Session, owner_user_id: int, processo_id: int
    ) -> None:
        if not PrazosService._owned_processo(session, owner_user_id, processo_id):
            raise ValueError("Processo inválido para este usuário.")

    @staticmethod
    def _get_or_raise(session: Session, owner_user_id: int, prazo_id: int) -> Prazo:
        prazo = PrazosService.get(session, owner_user_id, prazo_id)
        if not prazo:
            raise ValueError("Prazo não encontrado.")
        return prazo

    @staticmethod
    def _base_join_stmt(owner_user_id: int) -> Select:
        return (
            select(Prazo, Processo)
            .join(Processo, Processo.id == Prazo.processo_id)
            .where(Processo.owner_user_id == owner_user_id)
        )

    @staticmethod
    def _apply_status_filter(stmt: Select, status: PrazoStatusFilter) -> Select:
        if status == "open":
            return stmt.where(Prazo.concluido.is_(False))
        if status == "closed":
            return stmt.where(Prazo.concluido.is_(True))
        return stmt

    @staticmethod
    def _default_order(stmt: Select) -> Select:
        return stmt.order_by(
            Prazo.concluido.asc(),
            Prazo.data_limite.asc(),
            Prazo.id.desc(),
        )

    @staticmethod
    def _normalize_update_payload(payload: PrazoUpdate) -> dict[str, Any]:
        raw = asdict(payload)
        data: dict[str, Any] = {}

        for field, val in raw.items():
            if field not in PrazosService._UPDATABLE_FIELDS:
                continue

            if field == "evento":
                if val is None:
                    continue
                cleaned = PrazosService._clean_str(val)
                if cleaned is None:
                    raise ValueError("Evento não pode ficar vazio.")
                data[field] = cleaned
                continue

            if field == "prioridade":
                if val is None:
                    continue
                data[field] = PrazosService._normalize_prioridade_update(val)
                continue

            if field == "data_limite":
                if val is None:
                    continue
                PrazosService._validate_datetime(val, "Data limite")
                data[field] = val
                continue

            if field == "concluido":
                if val is None:
                    continue
                PrazosService._validate_bool(val, "Concluído")
                data[field] = val
                continue

            if field in {"origem", "referencia", "observacoes"}:
                data[field] = PrazosService._clean_str(val)
                continue

            if val is not None:
                data[field] = val

        return data

    @staticmethod
    def create(session: Session, owner_user_id: int, payload: PrazoCreate) -> Prazo:
        evento = PrazosService._clean_str(payload.evento)
        if not evento:
            raise ValueError("Evento é obrigatório.")

        PrazosService._validate_datetime(payload.data_limite, "Data limite")
        PrazosService._ensure_owned_processo(
            session, owner_user_id, payload.processo_id
        )

        prazo = Prazo(
            processo_id=payload.processo_id,
            evento=evento,
            data_limite=payload.data_limite,
            prioridade=PrazosService._normalize_prioridade_create(payload.prioridade),
            concluido=False,
            origem=PrazosService._clean_str(payload.origem),
            referencia=PrazosService._clean_str(payload.referencia),
            observacoes=PrazosService._clean_str(payload.observacoes),
        )

        try:
            session.add(prazo)
            session.commit()
            session.refresh(prazo)
            return prazo
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def list_by_processo(
        session: Session,
        owner_user_id: int,
        processo_id: int,
        status: PrazoStatusFilter = "open",
    ) -> list[Prazo]:
        PrazosService._ensure_owned_processo(session, owner_user_id, processo_id)

        stmt = (
            select(Prazo)
            .join(Processo, Processo.id == Prazo.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Prazo.processo_id == processo_id,
            )
        )
        stmt = PrazosService._apply_status_filter(stmt, status)
        stmt = PrazosService._default_order(stmt)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def list_all(
        session: Session,
        owner_user_id: int,
        status: PrazoStatusFilter = "open",
    ) -> list[tuple[Prazo, Processo]]:
        stmt = PrazosService._base_join_stmt(owner_user_id)
        stmt = PrazosService._apply_status_filter(stmt, status)
        stmt = PrazosService._default_order(stmt)
        return list(session.execute(stmt).all())

    @staticmethod
    def get(session: Session, owner_user_id: int, prazo_id: int) -> Prazo | None:
        stmt = (
            select(Prazo)
            .join(Processo, Processo.id == Prazo.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Prazo.id == prazo_id,
            )
        )
        return session.execute(stmt).scalars().first()

    @staticmethod
    def update(
        session: Session,
        owner_user_id: int,
        prazo_id: int,
        payload: PrazoUpdate,
    ) -> Prazo:
        prazo = PrazosService._get_or_raise(session, owner_user_id, prazo_id)

        data = PrazosService._normalize_update_payload(payload)
        if not data:
            return prazo

        try:
            for field, value in data.items():
                setattr(prazo, field, value)

            session.commit()
            session.refresh(prazo)
            return prazo
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def delete(session: Session, owner_user_id: int, prazo_id: int) -> None:
        prazo = PrazosService._get_or_raise(session, owner_user_id, prazo_id)

        try:
            session.delete(prazo)
            session.commit()
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def set_concluido(
        session: Session,
        owner_user_id: int,
        prazo_id: int,
        concluido: bool,
    ) -> Prazo:
        PrazosService._validate_bool(concluido, "Concluído")
        return PrazosService.update(
            session,
            owner_user_id,
            prazo_id,
            PrazoUpdate(concluido=concluido),
        )

    @staticmethod
    def concluir(session: Session, owner_user_id: int, prazo_id: int) -> Prazo:
        return PrazosService.set_concluido(session, owner_user_id, prazo_id, True)

    @staticmethod
    def reabrir(session: Session, owner_user_id: int, prazo_id: int) -> Prazo:
        return PrazosService.set_concluido(session, owner_user_id, prazo_id, False)

    @staticmethod
    def set_data_limite(
        session: Session,
        owner_user_id: int,
        prazo_id: int,
        new_data_limite: datetime,
    ) -> Prazo:
        PrazosService._validate_datetime(new_data_limite, "Data limite")
        return PrazosService.update(
            session,
            owner_user_id,
            prazo_id,
            PrazoUpdate(data_limite=new_data_limite),
        )
