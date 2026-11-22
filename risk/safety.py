"""Machine à états de sécurité. Fail closed."""
from enum import IntEnum

class State(IntEnum):
    NORMAL = 0
    ENTRY_LOCK = 1
    EXIT_ONLY = 2
    HALT = 3

class SafetyController:
    def __init__(self, db):
        self.db = db
        prev = State[db.get_config("safety_state", "ENTRY_LOCK")]
        self._state = max(prev, State.ENTRY_LOCK)
        self._persist("startup")
    @property
    def state(self): return self._state
    def _persist(self, why, actor="system"):
        self.db.set_config("safety_state", self._state.name)
        self.db.audit(actor, "safety_state", {"state": self._state.name, "why": why})
    def escalate(self, new: State, why: str, actor="system"):
        if new > self._state:
            self._state = new; self._persist(why, actor)
    def unlock(self, new: State, actor_id: int, owner_id: int, why="human"):
        if actor_id != owner_id: raise PermissionError("déverrouillage réservé au propriétaire")
        self._state = new; self._persist(why, f"human:{actor_id}")
    def allows(self, side: str) -> bool:
        if self._state == State.HALT: return False
        if self._state in (State.ENTRY_LOCK, State.EXIT_ONLY): return side == "sell"
        return True
