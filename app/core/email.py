import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    """Delivery channel for verification codes (email/SMS providers implement this)."""

    def send_verification_code(self, email: str, code: str) -> None: ...


class ConsoleEmailSender:
    """Dev implementation: prints the code to the application log/console.

    SIMPLIFICATION: with more time, add an SMTP/provider implementation
    (e.g. aiosmtplib or a transactional API) selected via settings, with retries
    and delivery via a Celery queue.
    """

    def send_verification_code(self, email: str, code: str) -> None:
        logger.warning("[DEV] Verification code for %s: %s", email, code)
        print(f"[DEV] Verification code for {email}: {code}")


def get_email_sender() -> EmailSender:
    """FastAPI dependency; override in tests or when a real provider exists."""
    return ConsoleEmailSender()
