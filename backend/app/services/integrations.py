from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.db.base import Notification, new_id
from app.domain.enums import NotificationChannel


class MockNotifier:
    def __init__(self, session: Session, clock: Clock) -> None:
        self.session = session
        self.clock = clock

    def send(
        self,
        employee_id: str,
        recipient: str,
        subject: str,
        body: str,
        *,
        task_id: str | None = None,
    ) -> Notification:
        notification = Notification(
            id=new_id(),
            ts=self.clock.now(),
            employee_id=employee_id,
            to_role_or_user=recipient,
            channel=NotificationChannel.EMAIL,
            subject=subject,
            body=body,
            related_task_id=task_id,
            status="PENDING",
        )
        self.session.add(notification)
        self.session.commit()
        return notification
