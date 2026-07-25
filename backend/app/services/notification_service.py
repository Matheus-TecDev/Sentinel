from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.core.enums import AlertChannelType, NotificationEventType, NotificationStatus
from app.models.alert import AlertChannel
from app.models.incident import Incident
from app.models.notification import NotificationLog
from app.models.service import MonitoredService
from app.repositories.alert_repository import AlertChannelRepository
from app.repositories.notification_repository import NotificationLogRepository
from app.repositories.service_repository import ServiceRepository
from app.services.alert_service import mask_target

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationContext:
    service: MonitoredService
    incident: Incident
    event_type: NotificationEventType


class NotificationService:
    def __init__(self) -> None:
        self.channels = AlertChannelRepository()
        self.notifications = NotificationLogRepository()
        self.services = ServiceRepository()

    async def notify_incident_event(
        self,
        db: Session,
        incident: Incident,
        event_type: NotificationEventType,
    ) -> list[NotificationLog]:
        service = self.services.get(db, incident.service_id)
        if service is None:
            return []

        context = NotificationContext(service=service, incident=incident, event_type=event_type)
        logs: list[NotificationLog] = []

        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0), follow_redirects=True) as client:
            for channel in self.channels.active_for_service(db, incident.service_id):
                if not self._should_notify(channel, incident, event_type):
                    continue
                status, error_message = await self._send(client, channel, context)
                logs.append(
                    self.notifications.create(
                        db,
                        {
                            "service_id": incident.service_id,
                            "incident_id": incident.id,
                            "channel_type": channel.type,
                            "target": channel.target,
                            "event_type": event_type,
                            "status": status,
                            "error_message": error_message,
                        },
                    )
                )
                if status == NotificationStatus.FAILED:
                    logger.warning(
                        "Alert delivery failed service_id=%s incident_id=%s channel_type=%s target=%s error=%s",
                        incident.service_id,
                        incident.id,
                        channel.type.value,
                        mask_target(channel.target),
                        error_message,
                    )

        return logs

    def _should_notify(
        self,
        channel: AlertChannel,
        incident: Incident,
        event_type: NotificationEventType,
    ) -> bool:
        if event_type == NotificationEventType.INCIDENT_RESOLVED:
            return channel.notify_on_recovery
        if incident.reason == "Serviço degradado":
            return channel.notify_on_degraded
        return channel.notify_on_offline

    async def _send(
        self,
        client: httpx.AsyncClient,
        channel: AlertChannel,
        context: NotificationContext,
    ) -> tuple[NotificationStatus, str | None]:
        if channel.type == AlertChannelType.EMAIL:
            return NotificationStatus.FAILED, "SMTP ainda não implementado nesta fase"

        try:
            if channel.type == AlertChannelType.DISCORD:
                response = await client.post(channel.target, json=self._discord_payload(context))
            else:
                response = await client.post(channel.target, json=self._webhook_payload(context))
            if response.status_code >= 400:
                return NotificationStatus.FAILED, f"Destino retornou HTTP {response.status_code}"
            return NotificationStatus.SENT, None
        except httpx.HTTPError as exc:
            return NotificationStatus.FAILED, str(exc)

    def _webhook_payload(self, context: NotificationContext) -> dict:
        incident = context.incident
        service = context.service
        return {
            "source": "sentinel",
            "event_type": context.event_type.value,
            "service": {
                "id": service.id,
                "name": service.name,
                "environment": service.environment.value,
                "owner": service.owner,
            },
            "incident": {
                "id": incident.id,
                "status": incident.status.value,
                "reason": incident.reason,
                "last_error_message": incident.last_error_message,
                "started_at": incident.started_at.isoformat(),
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "duration_seconds": incident.duration_seconds,
            },
            "message": self._message(context),
        }

    def _discord_payload(self, context: NotificationContext) -> dict:
        color = 15158332 if context.event_type == NotificationEventType.INCIDENT_OPENED else 3066993
        return {
            "content": self._message(context),
            "embeds": [
                {
                    "title": "Sentinel",
                    "description": context.incident.reason,
                    "color": color,
                    "fields": [
                        {"name": "Serviço", "value": context.service.name, "inline": True},
                        {"name": "Ambiente", "value": context.service.environment.value, "inline": True},
                        {"name": "Incidente", "value": str(context.incident.id), "inline": True},
                    ],
                }
            ],
        }

    def _message(self, context: NotificationContext) -> str:
        if context.event_type == NotificationEventType.INCIDENT_RESOLVED:
            return f"Serviço recuperado: {context.service.name}"
        status_label = "degradado" if context.incident.reason == "Serviço degradado" else "offline"
        return f"Incidente aberto: {context.service.name} está {status_label}"
