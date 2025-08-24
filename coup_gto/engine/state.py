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

    # Interaction state
    # If not None, an action is awaiting responses (e.g., Foreign Aid block window)
    pending_action: Optional[Action] = field(init=False, default=None)
    # If a block has been declared, track who blocked and the claimed role
    pending_blocker: Optional[int] = field(init=False, default=None)
    pending_block_role: Optional[Role] = field(init=False, default=None)
    # Whose response is awaited (e.g., the original actor deciding to challenge or pass)
    awaiting_response_from: Optional[int] = field(init=False, default=None)
    # If a claim is being challenged (unblocked actions like TAX), track the claimed role
    pending_claim_role: Optional[Role] = field(init=False, default=None)

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
        # If an interaction is pending, return response options
        if self.pending_action is not None:
            return self._legal_responses()

        actor = self.current_player
        ps = self.players[actor]

        # If at or above mandatory coup threshold, only coup is legal
        if ps.coins >= self.rules.mandatory_coup_threshold:
            return [Action(actor=actor, type=ActionType.COUP, target=self._default_target())]

        actions: List[Action] = []
        # Income
        actions.append(Action(actor=actor, type=ActionType.INCOME))
        # Foreign Aid (block/challenge handled via pending interaction)
        actions.append(Action(actor=actor, type=ActionType.FOREIGN_AID))
        # Duke Tax (challengeable claim)
        actions.append(Action(actor=actor, type=ActionType.TAX))
        # Ambassador Exchange (challengeable claim)
        actions.append(Action(actor=actor, type=ActionType.EXCHANGE))
        # Captain Steal (challengeable, blockable by Captain or Ambassador)
        if actor != self._default_target():
            actions.append(Action(actor=actor, type=ActionType.STEAL, target=self._default_target()))
        # Assassin Assassinate (challengeable and blockable by Contessa)
        if ps.coins >= self.rules.assassinate_cost:
            actions.append(Action(actor=actor, type=ActionType.ASSASSINATE, target=self._default_target()))
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
        # If in a response window, the responder may not be the current_player
        legal = self.legal_actions()
        assert action in self._as_set(legal), f"Illegal action: {action}"
        if self.pending_action is None:
            assert action.actor == self.current_player, "Not this player's turn"

        if action.type == ActionType.INCOME:
            self._apply_income(action)
        elif action.type == ActionType.FOREIGN_AID:
            self._start_foreign_aid_interaction(action)
        elif action.type == ActionType.COUP:
            self._apply_coup(action)
        elif action.type == ActionType.PASS:
            self._apply_pass(action)
        elif action.type == ActionType.BLOCK_FOREIGN_AID:
            self._apply_block_foreign_aid(action)
        elif action.type == ActionType.BLOCK_ASSASSINATE:
            self._apply_block_assassinate(action)
        elif action.type == ActionType.BLOCK_STEAL_CAPTAIN:
            self._apply_block_steal_captain(action)
        elif action.type == ActionType.BLOCK_STEAL_AMBASSADOR:
            self._apply_block_steal_ambassador(action)
        elif action.type == ActionType.CHALLENGE:
            self._apply_challenge(action)
        elif action.type == ActionType.TAX:
            self._start_tax_interaction(action)
        elif action.type == ActionType.EXCHANGE:
            self._start_exchange_interaction(action)
        elif action.type == ActionType.STEAL:
            self._start_steal_interaction(action)
        elif action.type == ActionType.ASSASSINATE:
            self._start_assassinate_interaction(action)
        else:
            raise NotImplementedError(f"Action not yet implemented: {action.type}")

        # advance turn if game not over
        if self.winner() is None and self.pending_action is None and self.awaiting_response_from is None:
            self.next_player()

    def _apply_income(self, action: Action) -> None:
        self.players[action.actor].coins += 1

    # --- Interaction: Foreign Aid ---
    def _start_foreign_aid_interaction(self, action: Action) -> None:
        # Start a response window: opponents may block with Duke.
        self.pending_action = action
        # In 2-player, the only potential blocker is the opponent
        self.awaiting_response_from = self._default_target()

    def _legal_responses(self) -> List[Action]:
        assert self.pending_action is not None
        acts: List[Action] = []
        # Foreign Aid response window
        if self.pending_action.type == ActionType.FOREIGN_AID:
            if self.pending_blocker is None:
                # The opponent can pass or declare a block with Duke
                responder = self.awaiting_response_from
                assert responder is not None
                acts.append(Action(actor=responder, type=ActionType.PASS))
                acts.append(Action(actor=responder, type=ActionType.BLOCK_FOREIGN_AID))
            else:
                # A block was declared; the original actor may challenge or pass (accept block)
                actor = self.pending_action.actor
                acts.append(Action(actor=actor, type=ActionType.CHALLENGE))
                acts.append(Action(actor=actor, type=ActionType.PASS))
        # Tax response window (opponent can challenge or pass)
        elif self.pending_action.type == ActionType.TAX:
            responder = self.awaiting_response_from
            assert responder is not None
            acts.append(Action(actor=responder, type=ActionType.CHALLENGE))
            acts.append(Action(actor=responder, type=ActionType.PASS))
        # Exchange response window
        elif self.pending_action.type == ActionType.EXCHANGE:
            responder = self.awaiting_response_from
            assert responder is not None
            acts.append(Action(actor=responder, type=ActionType.CHALLENGE))
            acts.append(Action(actor=responder, type=ActionType.PASS))
        # Steal response window
        elif self.pending_action.type == ActionType.STEAL:
            if self.pending_blocker is None:
                responder = self.awaiting_response_from
                assert responder is not None
                acts.append(Action(actor=responder, type=ActionType.PASS))
                acts.append(Action(actor=responder, type=ActionType.BLOCK_STEAL_CAPTAIN))
                acts.append(Action(actor=responder, type=ActionType.BLOCK_STEAL_AMBASSADOR))
                acts.append(Action(actor=responder, type=ActionType.CHALLENGE))
            else:
                actor = self.pending_action.actor
                acts.append(Action(actor=actor, type=ActionType.CHALLENGE))
                acts.append(Action(actor=actor, type=ActionType.PASS))
        # Assassinate response window
        elif self.pending_action.type == ActionType.ASSASSINATE:
            if self.pending_blocker is None:
                # Target may pass (accept), block (Contessa), or challenge the claim
                responder = self.awaiting_response_from
                assert responder is not None
                acts.append(Action(actor=responder, type=ActionType.PASS))
                acts.append(Action(actor=responder, type=ActionType.BLOCK_ASSASSINATE))
                acts.append(Action(actor=responder, type=ActionType.CHALLENGE))
            else:
                # Block declared; actor may challenge or pass (accept block)
                actor = self.pending_action.actor
                acts.append(Action(actor=actor, type=ActionType.CHALLENGE))
                acts.append(Action(actor=actor, type=ActionType.PASS))
        return acts

    def _apply_pass(self, action: Action) -> None:
        # Handle passes depending on the interaction stage
        assert self.pending_action is not None
        if self.pending_action.type == ActionType.FOREIGN_AID:
            if self.pending_blocker is None:
                # No block declared -> FA succeeds
                self.players[self.pending_action.actor].coins += 2
                self._clear_pending()
            else:
                # Actor accepts the block -> FA fails
                self._clear_pending()
        elif self.pending_action.type == ActionType.TAX:
            # Opponent passed -> TAX succeeds
            self.players[self.pending_action.actor].coins += 3
            self._clear_pending()
        elif self.pending_action.type == ActionType.EXCHANGE:
            # Opponent passed -> perform exchange
            self._perform_exchange(self.pending_action.actor)
            self._clear_pending()
        elif self.pending_action.type == ActionType.STEAL:
            if self.pending_blocker is None:
                # Target accepts; transfer up to 2 coins
                self._apply_steal_transfer()
                self._clear_pending()
            else:
                # Actor accepts block
                self._clear_pending()
        elif self.pending_action.type == ActionType.ASSASSINATE:
            # Pass depends on stage
            if self.pending_blocker is None:
                # Target accepts; assassination succeeds
                target = self.pending_action.target
                assert target is not None
                self._lose_influence(target)
                self._clear_pending()
            else:
                # Actor accepts the block; assassination fails
                self._clear_pending()

    def _apply_block_foreign_aid(self, action: Action) -> None:
        # Opponent claims Duke to block FA
        assert self.pending_action is not None and self.pending_action.type == ActionType.FOREIGN_AID
        assert action.actor != self.pending_action.actor, "Actor cannot block own action"
        self.pending_blocker = action.actor
        self.pending_block_role = Role.DUKE
        # Now the original actor may challenge or pass
        self.awaiting_response_from = self.pending_action.actor

    def _apply_block_assassinate(self, action: Action) -> None:
        # Target claims Contessa to block Assassinate
        assert self.pending_action is not None and self.pending_action.type == ActionType.ASSASSINATE
        assert action.actor == self.pending_action.target, "Only target may block assassination"
        self.pending_blocker = action.actor
        self.pending_block_role = Role.CONTESSA
        self.awaiting_response_from = self.pending_action.actor

    def _apply_block_steal_captain(self, action: Action) -> None:
        assert self.pending_action is not None and self.pending_action.type == ActionType.STEAL
        assert action.actor == self.pending_action.target, "Only target may block steal"
        self.pending_blocker = action.actor
        self.pending_block_role = Role.CAPTAIN
        self.awaiting_response_from = self.pending_action.actor

    def _apply_block_steal_ambassador(self, action: Action) -> None:
        assert self.pending_action is not None and self.pending_action.type == ActionType.STEAL
        assert action.actor == self.pending_action.target, "Only target may block steal"
        self.pending_blocker = action.actor
        self.pending_block_role = Role.AMBASSADOR
        self.awaiting_response_from = self.pending_action.actor

    def _apply_challenge(self, action: Action) -> None:
        assert self.pending_action is not None
        if self.pending_action.type == ActionType.FOREIGN_AID:
            assert self.pending_blocker is not None and self.pending_block_role == Role.DUKE
            challenger = action.actor
            blocker = self.pending_blocker
            # Resolve challenge to block
            if self._player_has_role(blocker, Role.DUKE):
                # Blocker truthful
                self._truthful_reveal(blocker, Role.DUKE)
                self._lose_influence(challenger)
                self._clear_pending()
            else:
                # Blocker bluffed
                self._lose_influence(blocker)
                self.players[self.pending_action.actor].coins += 2
                self._clear_pending()
        elif self.pending_action.type == ActionType.TAX:
            # Opponent challenges the Duke claim
            challenger = action.actor
            actor = self.pending_action.actor
            if self._player_has_role(actor, Role.DUKE):
                # Actor truthful: reveal Duke, challenger loses 1, Tax succeeds
                self._truthful_reveal(actor, Role.DUKE)
                self._lose_influence(challenger)
                self.players[actor].coins += 3
                self._clear_pending()
            else:
                # Actor bluffed: loses 1, Tax fails
                self._lose_influence(actor)
                self._clear_pending()
        elif self.pending_action.type == ActionType.EXCHANGE:
            # Challenge to Ambassador claim
            challenger = action.actor
            actor = self.pending_action.actor
            if self._player_has_role(actor, Role.AMBASSADOR):
                self._truthful_reveal(actor, Role.AMBASSADOR)
                self._lose_influence(challenger)
                self._perform_exchange(actor)
                self._clear_pending()
            else:
                self._lose_influence(actor)
                self._clear_pending()
        elif self.pending_action.type == ActionType.STEAL:
            actor = self.pending_action.actor
            target = self.pending_action.target
            assert target is not None
            if self.pending_blocker is None:
                # Challenge the Captain claim
                challenger = action.actor
                if self._player_has_role(actor, Role.CAPTAIN):
                    self._truthful_reveal(actor, Role.CAPTAIN)
                    self._lose_influence(challenger)
                    self._apply_steal_transfer()
                    self._clear_pending()
                else:
                    self._lose_influence(actor)
                    self._clear_pending()
            else:
                # Challenge the block (either Captain or Ambassador)
                challenger = action.actor
                blocker = self.pending_blocker
                if self.pending_block_role == Role.CAPTAIN:
                    if self._player_has_role(blocker, Role.CAPTAIN):
                        self._truthful_reveal(blocker, Role.CAPTAIN)
                        self._lose_influence(challenger)
                        self._clear_pending()
                    else:
                        self._lose_influence(blocker)
                        self._apply_steal_transfer()
                        self._clear_pending()
                elif self.pending_block_role == Role.AMBASSADOR:
                    if self._player_has_role(blocker, Role.AMBASSADOR):
                        self._truthful_reveal(blocker, Role.AMBASSADOR)
                        self._lose_influence(challenger)
                        self._clear_pending()
                    else:
                        self._lose_influence(blocker)
                        self._apply_steal_transfer()
                        self._clear_pending()
        elif self.pending_action.type == ActionType.ASSASSINATE:
            actor = self.pending_action.actor
            target = self.pending_action.target
            assert target is not None
            if self.pending_blocker is None:
                # Challenge to the assassin claim itself
                challenger = action.actor
                if self._player_has_role(actor, Role.ASSASSIN):
                    # Actor truthful: reveal Assassin, challenger loses 1, assassination succeeds
                    self._truthful_reveal(actor, Role.ASSASSIN)
                    self._lose_influence(challenger)
                    self._lose_influence(target)
                    self._clear_pending()
                else:
                    # Actor bluffed: loses 1, assassination fails (coins not refunded)
                    self._lose_influence(actor)
                    self._clear_pending()
            else:
                # Challenge to the Contessa block
                assert self.pending_block_role == Role.CONTESSA
                challenger = action.actor
                blocker = self.pending_blocker
                if self._player_has_role(blocker, Role.CONTESSA):
                    # Blocker truthful: reveal Contessa, challenger loses 1, assassination fails
                    self._truthful_reveal(blocker, Role.CONTESSA)
                    self._lose_influence(challenger)
                    self._clear_pending()
                else:
                    # Blocker bluffed: blocker loses 1, assassination succeeds (target loses another)
                    self._lose_influence(blocker)
                    self._lose_influence(target)
                    self._clear_pending()

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

    # --- Common helpers ---
    def _player_has_role(self, pid: int, role: Role) -> bool:
        return role in self.players[pid].hand

    def _truthful_reveal(self, pid: int, role: Role) -> None:
        # Reveal role from hand, then shuffle it back into deck and draw a replacement.
        ps = self.players[pid]
        assert role in ps.hand, "Cannot truthfully reveal a role not in hand"
        ps.hand.remove(role)
        # Show and return to deck, shuffle, draw
        self.deck.append(role)
        self.rng.shuffle(self.deck)
        if self.deck:
            ps.hand.append(self.deck.pop())

    def _lose_influence(self, pid: int) -> None:
        ps = self.players[pid]
        if ps.hand:
            lost = ps.hand.pop(0)
            ps.revealed.append(lost)
        
    def _clear_pending(self) -> None:
        self.pending_action = None
        self.pending_blocker = None
        self.pending_block_role = None
        self.awaiting_response_from = None
        self.pending_claim_role = None

    # --- Start interactions for claims ---
    def _start_tax_interaction(self, action: Action) -> None:
        # Start challenge window for claimed Duke Tax
        self.pending_action = action
        self.pending_claim_role = Role.DUKE
        self.awaiting_response_from = self._default_target()

    def _start_assassinate_interaction(self, action: Action) -> None:
        # Pay cost at declaration (not refunded if blocked/challenged)
        actor_ps = self.players[action.actor]
        assert action.target is not None, "Assassinate requires a target"
        assert actor_ps.coins >= self.rules.assassinate_cost, "Insufficient coins for assassinate"
        actor_ps.coins -= self.rules.assassinate_cost
        self.pending_action = action
        self.pending_claim_role = Role.ASSASSIN
        # Target responds first
        self.awaiting_response_from = action.target

    def _start_steal_interaction(self, action: Action) -> None:
        assert action.target is not None, "Steal requires a target"
        self.pending_action = action
        self.pending_claim_role = Role.CAPTAIN
        self.awaiting_response_from = action.target

    def _apply_steal_transfer(self) -> None:
        assert self.pending_action is not None and self.pending_action.type == ActionType.STEAL
        actor = self.pending_action.actor
        target = self.pending_action.target
        assert target is not None
        amt = min(2, self.players[target].coins)
        self.players[target].coins -= amt
        self.players[actor].coins += amt

    def _start_exchange_interaction(self, action: Action) -> None:
        self.pending_action = action
        self.pending_claim_role = Role.AMBASSADOR
        self.awaiting_response_from = self._default_target()

    def _perform_exchange(self, actor: int) -> None:
        # Deterministic: draw top 2 from deck, choose 2 to keep among 4 by sorted name, return others to bottom
        drawn: List[Role] = []
        for _ in range(2):
            if self.deck:
                drawn.append(self.deck.pop(0))
        combined = self.players[actor].hand + drawn
        # keep exactly cards_per_player
        keep_n = self.rules.cards_per_player
        kept = sorted(combined, key=lambda r: r.value)[:keep_n]
        returned = [r for r in combined if r not in kept or kept.count(r) < combined.count(r)]
        # Update hand
        self.players[actor].hand = kept
        # Return others to bottom of deck, preserve current order of 'returned'
        self.deck.extend(returned)

    @staticmethod
    def _as_set(actions: List[Action]) -> List[Action]:
        # dataclass equality makes list membership fine; keep helper to clarify intent
        return actions
