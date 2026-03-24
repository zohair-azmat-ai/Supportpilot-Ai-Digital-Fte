"""Import all models so Alembic can detect them during autogeneration."""

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.customer import Customer, CustomerIdentifier
from app.models.knowledge_base import KnowledgeBase
from app.models.agent_metrics import AgentMetrics
from app.models.system_event import SystemEvent

__all__ = [
    "User",
    "Conversation",
    "Message",
    "Ticket",
    "Customer",
    "CustomerIdentifier",
    "KnowledgeBase",
    "AgentMetrics",
    "SystemEvent",
]
