class AppBaseException(Exception):
    """Base class for all application exceptions."""
    pass


class AuthenticationError(AppBaseException):
    """Raised when authentication fails (401)."""
    pass


class AuthorizationError(AppBaseException):
    """Raised when user lacks required permission (403)."""
    pass


class NotFoundError(AppBaseException):
    """Raised when a requested resource does not exist (404)."""
    pass


class ConflictError(AppBaseException):
    """Raised when a resource already exists or state conflicts (409)."""
    pass


class AppValidationError(AppBaseException):
    """Raised when input data fails business-level validation (422)."""
    pass


class RAGProcessingError(AppBaseException):
    """Raised when RAG document processing fails (500)."""
    pass
