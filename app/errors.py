class AppError(Exception):
    """Base for all domain errors."""


class NotFoundError(AppError):
    pass


class UpstreamError(AppError):
    """Jikan (or another external service) failed or misbehaved."""


class ConflictError(AppError):
    """A uniqueness or state conflict — e.g. duplicate email."""
