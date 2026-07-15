class DomainError(Exception):
    """Base class for domain errors mapped to HTTP responses in main.py."""

    status_code = 400
    detail = "Bad request"


class EmailAlreadyExistsError(DomainError):
    status_code = 409
    detail = "A user with this email already exists"


class InvalidCredentialsError(DomainError):
    status_code = 401
    detail = "Invalid email or password"


class EmailNotVerifiedError(DomainError):
    status_code = 403
    detail = "Email is not verified"


class InvalidVerificationCodeError(DomainError):
    status_code = 400
    detail = "Invalid or expired verification code"


class UserNotFoundError(DomainError):
    status_code = 404
    detail = "User not found"


class PermissionDeniedError(DomainError):
    status_code = 403
    detail = "Not enough permissions"
