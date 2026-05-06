class BusinessRuleError(Exception):
    """Business rule error."""


class ServiceNotReadyError(Exception):
    """Service method is not implemented or not ready."""


class AIServiceError(Exception):
    """AI assistant service error."""


class AIConnectionError(AIServiceError):
    """Cannot connect to local Ollama endpoint."""


class AIModelNotFoundError(AIServiceError):
    """Requested local model is not available."""


class AITimeoutError(AIServiceError):
    """AI request timed out."""


class AIResponseFormatError(AIServiceError):
    """AI response format cannot be parsed reliably."""
