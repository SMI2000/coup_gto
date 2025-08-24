from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import random

from coup_gto.engine.actions import Action, ActionType, Role
from coup_gto.rules.base import BaseRules


@dataclass
class PlayerState:
    coins: int
    hand: List[Role] = field(default_factory=list)
    revealed: List[Role] = field(default_factory=list)

    def alive(self) -> bool:
        return len(self.hand) > 0


@dataclass
class GameState:
    num_players: int
    rules: BaseRules = field(default_factory=BaseRules)
    players: List[PlayerState] = field(init=False)
    deck: List[Role] = field(init=False)
    current_player: int = field(init=False, default=0)
    rng: random.Random = field(init=False)

    def __init__(self, num_players: int, seed: Optional[int] = 0, rules: Optional[BaseRules] = None):
        assert 2 <= num_players <= 6, "Coup supports 2-6 players"
        self.num_players = num_players
        self.rules = rules or BaseRules()
        self.rng = random.Random(seed)
        self._setup()

    # --- Setup ---
    def _setup(self) -> None:
        self.players = [PlayerState(coins=self.rules.starting_coins) for _ in range(self.num_players)]
        self.deck = self.rules.full_deck()[:]
        self.rng.shuffle(self.deck)
        # deal cards
        for _ in range(self.rules.cards_per_player):
            for p in range(self.num_players):
                self.players[p].hand.append(self.deck.pop())
        self.current_player = 0

    # --- Utility ---
    def alive_players(self) -> List[int]:
        return [i for i, ps in enumerate(self.players) if ps.alive()]

    def next_player(self) -> None:
        # advance to next alive player
        nxt = (self.current_player + 1) % self.num_players
        while not self.players[nxt].alive():
            nxt = (nxt + 1) % self.num_players
        self.current_player = nxt

    def winner(self) -> Optional[int]:
        alive = self.alive_players()
        if len(alive) == 1:
            return alive[0]
        return None

    # --- Actions ---
    def legal_actions(self) -> List[Action]:
        if self.winner() is not None:
            return []
        actor = self.current_player
        ps = self.players[actor]

        # If at or above mandatory coup threshold, only coup is legal
        if ps.coins >= self.rules.mandatory_coup_threshold:
            return [Action(actor=actor, type=ActionType.COUP, target=self._default_target())]

        actions: List[Action] = []
        # Income
        actions.append(Action(actor=actor, type=ActionType.INCOME))
        # Foreign Aid (block handling not implemented yet)
        actions.append(Action(actor=actor, type=ActionType.FOREIGN_AID))
        # Coup if enough coins
        if ps.coins >= self.rules.coup_cost:
            actions.append(Action(actor=actor, type=ActionType.COUP, target=self._default_target()))
        # Placeholder: claimed actions to be added later
        return actions

    def _default_target(self) -> Optional[int]:
        # For 2 players, the only target is the opponent. For N>2, choose the next alive opponent by default
        for offset in range(1, self.num_players):
            cand = (self.current_player + offset) % self.num_players
            if self.players[cand].alive():
                return cand
        return None

    def apply(self, action: Action) -> None:
        assert action.actor == self.current_player, "Not this player's turn"
        assert action in self._as_set(self.legal_actions()), f"Illegal action: {action}"

        if action.type == ActionType.INCOME:
            self._apply_income(action)
        elif action.type == ActionType.FOREIGN_AID:
            self._apply_foreign_aid(action)
        elif action.type == ActionType.COUP:
            self._apply_coup(action)
        else:
            raise NotImplementedError(f"Action not yet implemented: {action.type}")

        # advance turn if game not over
        if self.winner() is None:
            self.next_player()

    def _apply_income(self, action: Action) -> None:
        self.players[action.actor].coins += 1

    def _apply_foreign_aid(self, action: Action) -> None:
        # Block and challenge not implemented yet
        self.players[action.actor].coins += 2

    def _apply_coup(self, action: Action) -> None:
        assert action.target is not None, "Coup requires a target"
        actor_ps = self.players[action.actor]
        target_ps = self.players[action.target]
        assert actor_ps.coins >= self.rules.coup_cost, "Insufficient coins for coup"
        actor_ps.coins -= self.rules.coup_cost
        # Target chooses a card to lose; until choice system exists, remove the first card deterministically
        if target_ps.hand:
            lost = target_ps.hand.pop(0)
            target_ps.revealed.append(lost)

    @staticmethod
    def _as_set(actions: List[Action]) -> List[Action]:
        # dataclass equality makes list membership fine; keep helper to clarify intent
        return actions
