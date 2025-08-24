from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class Role(Enum):
    DUKE = "Duke"
    ASSASSIN = "Assassin"
    CAPTAIN = "Captain"
    AMBASSADOR = "Ambassador"
    CONTESSA = "Contessa"


class ActionType(Enum):
    INCOME = auto()
    FOREIGN_AID = auto()
    COUP = auto()
    TAX = auto()
    STEAL = auto()
    ASSASSINATE = auto()
    EXCHANGE = auto()
    # Interaction/response actions
    PASS = auto()
    BLOCK_FOREIGN_AID = auto()
    BLOCK_ASSASSINATE = auto()
    BLOCK_STEAL_CAPTAIN = auto()
    BLOCK_STEAL_AMBASSADOR = auto()
    CHALLENGE = auto()


@dataclass(frozen=True)
class Action:
    actor: int
    type: ActionType
    target: Optional[int] = None

    cost: int = 0  # paid from actor when applying; set by rules/state for convenience

    def __str__(self) -> str:
        if self.target is None:
            return f"P{self.actor}:{self.type.name}"
        return f"P{self.actor}:{self.type.name}->P{self.target}"
