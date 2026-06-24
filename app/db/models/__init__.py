# Import all models vào đây để Alembic autogenerate nhận diện được đầy đủ.
from app.db.models.auth import User, UserSession
from app.db.models.conversation import Artifact, ChatSession, ExecutionLog, Message, ToolCall
from app.db.models.intelligence import ModelRegistry, ModelScore, ModelUsageLog, RoutingRule
from app.db.models.soul import LearnedPattern, SoulKnowledge, SoulUpdateCandidate
from app.db.models.episode import Episode
from app.db.models.meeting import AgentRole, MeetingMember, MeetingReport, MeetingRoom, MeetingTurn

__all__ = [
    # Auth
    "User", "UserSession",
    # Conversation
    "ChatSession", "Message", "ToolCall", "Artifact", "ExecutionLog",
    # Intelligence
    "ModelRegistry", "ModelUsageLog", "ModelScore", "RoutingRule",
    # Soul
    "SoulKnowledge", "LearnedPattern", "SoulUpdateCandidate",
    # Episode
    "Episode",
    # Meeting
    "AgentRole", "MeetingRoom", "MeetingMember", "MeetingTurn", "MeetingReport",
]
