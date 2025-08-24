from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from coup_gto.engine.actions import ActionType, Role


@dataclass(frozen=True)
class BaseRules:
    # Core numeric params
    starting_coins: int = 2
    cards_per_player: int = 2
    coup_cost: int = 7
    assassinate_cost: int = 3
    mandatory_coup_threshold: int = 10

    # Deck composition
    deck_counts: Dict[Role, int] = None  # set in __post_init__ for immutability

    # Block graph (who can block what) — reference only for now
    blocks: Dict[ActionType, Tuple[Role, ...]] = None

    # Claimed-action mapping (for reference)
    claims: Dict[ActionType, Role] = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "deck_counts",
            {
                Role.DUKE: 3,
                Role.ASSASSIN: 3,
                Role.CAPTAIN: 3,
                Role.AMBASSADOR: 3,
                Role.CONTESSA: 3,
            },
        )
        object.__setattr__(
            self,
            "blocks",
            {
                ActionType.FOREIGN_AID: (Role.DUKE,),
                ActionType.ASSASSINATE: (Role.CONTESSA,),
                ActionType.STEAL: (Role.CAPTAIN, Role.AMBASSADOR),
            },
        )
        object.__setattr__(
            self,
            "claims",
            {
                ActionType.TAX: Role.DUKE,
                ActionType.ASSASSINATE: Role.ASSASSIN,
                ActionType.STEAL: Role.CAPTAIN,
                ActionType.EXCHANGE: Role.AMBASSADOR,
            },
        )

    def full_deck(self) -> List[Role]:
        deck: List[Role] = []
        for role, cnt in self.deck_counts.items():
            deck.extend([role] * cnt)
        return deck
