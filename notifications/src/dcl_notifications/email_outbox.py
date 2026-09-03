from email.message import EmailMessage
from hashlib import sha256
from pathlib import Path

from dcl_notifications.model import EmailNotification


class DirectoryEmailOutbox:
    def __init__(self, directory: str | Path, sender: str) -> None:
        self._directory = Path(directory)
        self._sender = sender

    def deliver(self, notification: EmailNotification) -> bool:
        self._directory.mkdir(parents=True, exist_ok=True)
        digest = sha256(notification.idempotency_key.encode("utf-8")).hexdigest()
        destination = self._directory / f"{notification.kind}-{digest}.eml"

        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = ", ".join(notification.recipients)
        message["Subject"] = notification.subject
        message["X-DCL-Notification-Key"] = notification.idempotency_key
        message["X-DCL-Notification-Kind"] = notification.kind
        message.set_content(notification.body)

        if destination.exists():
            return False
        destination.write_text(message.as_string(), encoding="utf-8")
        return True
