"""Offline knowledge system implementation."""
from .store import StoreMixin
from .answer import AnswerMixin
from .conflicts import ConflictsMixin

class Knowledge(StoreMixin, AnswerMixin, ConflictsMixin):
    """Snapshot-scoped deterministic knowledge system."""
