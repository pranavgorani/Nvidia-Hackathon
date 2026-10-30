import uuid
import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditEvent

logger = logging.getLogger(__name__)

class AuditService:
    async def log_event(
        self,
        organization_id: str,
        action_type: str,
        outcome: str,
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        error_category: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> AuditEvent:
        """
        Records an append-only audit log entry.
        Never stores secret API keys or authentication credentials.
        """
        # Redact any accidental sensitive keys in details
        safe_details = {}
        if details:
            for k, v in details.items():
                if any(secret_term in k.lower() for secret_term in ["token", "key", "password", "secret"]):
                    safe_details[k] = "[REDACTED]"
                else:
                    safe_details[k] = v

        event = AuditEvent(
            organization_id=organization_id,
            workflow_id=workflow_id,
            step_id=step_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action_type=action_type,
            tool_name=tool_name,
            resource_type=resource_type,
            resource_id=resource_id,
            approval_id=approval_id,
            outcome=outcome,
            error_category=error_category,
            details_json=safe_details,
            correlation_id=correlation_id or str(uuid.uuid4())
        )
        if session:
            session.add(event)
            await session.commit()
            await session.refresh(event)

        logger.info(
            f"AUDIT: [{outcome.upper()}] {action_type} by actor={actor_email or actor_id or 'system'} "
            f"org={organization_id} tool={tool_name} res={resource_type}:{resource_id}"
        )
        return event

audit_service = AuditService()

