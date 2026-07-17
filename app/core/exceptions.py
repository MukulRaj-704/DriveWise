"""Domain exceptions. Kept provider-agnostic so services never leak HTTP concerns."""


class DriveWiseError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidCredentialsError(DriveWiseError):
    status_code = 401
    default_message = "Invalid email or password."


class UserAlreadyExistsError(DriveWiseError):
    status_code = 409
    default_message = "A user with this email already exists."


class NotAuthenticatedError(DriveWiseError):
    status_code = 401
    default_message = "Authentication required."


class NotFoundError(DriveWiseError):
    status_code = 404
    default_message = "Resource not found."


class BrochureNotFoundError(NotFoundError):
    default_message = "Brochure not found."


class ChatNotFoundError(NotFoundError):
    default_message = "Chat session not found."


class InvalidFileError(DriveWiseError):
    status_code = 422
    default_message = "The uploaded file is invalid or unsupported."


class FileTooLargeError(DriveWiseError):
    status_code = 413
    default_message = "The uploaded file exceeds the maximum allowed size."


class ParsingError(DriveWiseError):
    status_code = 422
    default_message = "Failed to parse the uploaded PDF."


class EmbeddingError(DriveWiseError):
    status_code = 502
    default_message = "Failed to generate embeddings."


class VectorStoreError(DriveWiseError):
    status_code = 502
    default_message = "Vector store operation failed."


class LLMProviderError(DriveWiseError):
    status_code = 502
    default_message = "The language model provider failed to respond."


class NoRelevantContextError(DriveWiseError):
    """Raised internally when retrieval finds nothing — handled gracefully, not as an HTTP error."""

    status_code = 200
    default_message = "I couldn't find this information in the uploaded brochure."


class RateLimitExceededError(DriveWiseError):
    status_code = 429
    default_message = "Too many requests. Please slow down."
