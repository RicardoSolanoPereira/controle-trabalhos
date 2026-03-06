class AppError(Exception):
    """Erro base da aplicação."""

    pass


class ValidationError(AppError):
    """Erro de validação de dados."""

    pass


class NotFoundError(AppError):
    """Registro não encontrado."""

    pass


class ConflictError(AppError):
    """Conflito de dados (ex.: duplicidade)."""

    pass
