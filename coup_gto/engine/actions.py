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
    # Claimed actions (not yet implemented in engine resolution)
    TAX = auto()  # Duke: take 3
    ASSASSINATE = auto()  # Assassin: pay 3, target loses 1 influence
    STEAL = auto()  # Captain: steal 2
    EXCHANGE = auto()  # Ambassador: draw 2, choose 2 to keep
    # Interaction/response actions
    PASS = auto()
    BLOCK_FOREIGN_AID = auto()
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
