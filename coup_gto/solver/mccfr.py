from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import math
import random

from coup_gto.engine.actions import Action, ActionType
from coup_gto.engine.state import GameState


def action_key(a: Action) -> str:
    t = a.type.name
    tgt = "-" if a.target is None else str(a.target)
    return f"{t}:{tgt}"


def infoset_key(gs: GameState, player: int) -> str:
    # 2-player encoding: public state + acting player's private info if player == gs.current_player
    # Public: current_player, coins, revealed, pending flags
    pub = []
    pub.append(str(gs.current_player))
    pub.append(
        f"c:{gs.players[0].coins},{gs.players[1].coins}"
    )
    pub.append(
        "r0:" + ",".join(sorted([r.name for r in gs.players[0].revealed]))
    )
    pub.append(
        "r1:" + ",".join(sorted([r.name for r in gs.players[1].revealed]))
    )
    # Pending interaction summary
    pa = gs.pending_action
    if pa is None:
        pub.append("pa:None")
    else:
        pub.append(f"pa:{pa.type.name}:{pa.actor}:{-1 if pa.target is None else pa.target}")
    pub.append(
        "pr:" + ("None" if gs.pending_block_role is None else gs.pending_block_role.name)
    )
    pub.append(
        "pb:" + ("None" if gs.pending_blocker is None else str(gs.pending_blocker))
    )
    pub.append(
        "ar:" + ("None" if gs.awaiting_response_from is None else str(gs.awaiting_response_from))
    )
    pub.append(
        "cr:" + ("None" if gs.pending_claim_role is None else gs.pending_claim_role.name)
    )

    parts = ["|".join(pub)]

    # Private info for perspective player: their hand (sorted), only to ensure perfect recall on own info
    hand = sorted([r.name for r in gs.players[player].hand])
    parts.append("h:" + ",".join(hand))

    return "||".join(parts)


@dataclass
class NodeStats:
    # Per-action accumulators keyed by action_key
    regret_sum: Dict[str, float] = field(default_factory=dict)
    strategy_sum: Dict[str, float] = field(default_factory=dict)

    def get_strategy(self, legal: List[Action], realization_weight: float) -> List[float]:
        # Regret-matching over current legal actions
        keys = [action_key(a) for a in legal]
        regrets = [max(0.0, self.regret_sum.get(k, 0.0)) for k in keys]
        normalizer = sum(regrets)
        if normalizer > 1e-12:
            strat = [r / normalizer for r in regrets]
        else:
            # Uniform if no positive regret
            n = len(legal)
            strat = [1.0 / n for _ in range(n)] if n > 0 else []
        # Accumulate average strategy with current reach weight
        for k, p in zip(keys, strat):
            self.strategy_sum[k] = self.strategy_sum.get(k, 0.0) + realization_weight * p
        return strat

    def get_average_strategy(self, legal: List[Action]) -> List[float]:
        keys = [action_key(a) for a in legal]
        vals = [self.strategy_sum.get(k, 0.0) for k in keys]
        s = sum(vals)
        if s > 1e-12:
            return [v / s for v in vals]
        # Default to uniform
        n = len(legal)
        return [1.0 / n for _ in range(n)] if n > 0 else []


class MCCFRSolver:
    def __init__(self, seed: int = 0, max_depth: int = 300, debug: bool = False):
        self.nodes: Dict[str, NodeStats] = {}
        self.rng = random.Random(seed)
        self.max_depth = max_depth
        self.debug = debug

    def iterate(self, iterations: int = 1, game_seed: Optional[int] = None):
        for _ in range(iterations):
            # Run two traversals, one for each player as the updating player
            for updating_player in (0, 1):
                gs = GameState(num_players=2, seed=game_seed if game_seed is not None else self.rng.randrange(1 << 30))
                self._mccfr_traverse(gs, updating_player, reach_prob_other=1.0, reach_prob_updating=1.0, depth=0)

    def _mccfr_traverse(self, gs: GameState, updating_player: int, *, reach_prob_other: float, reach_prob_updating: float, depth: int) -> float:
        # Depth cap to prevent runaway recursion in long interactions
        if depth >= self.max_depth:
            if self.debug:
                try:
                    key_dbg = infoset_key(gs, gs.current_player)
                except Exception:
                    key_dbg = "<infoset_error>"
                print(f"[MCCFR] depth cap reached at depth={depth}, infoset={key_dbg}")
            return 0.0
        # Terminal check
        w = gs.winner()
        if w is not None:
            # Utility +1 for win, -1 for loss for updating player
            return 1.0 if w == updating_player else -1.0

        current = gs.current_player
        legal = gs.legal_actions()

        # Chance events are embedded in apply() via RNG when drawing/shuffling.
        # This scaffolding treats all non-player-stochasticity as part of environment.

        key = infoset_key(gs, current if current == updating_player else updating_player)
        node = self.nodes.setdefault(key, NodeStats())

        # If it's the updating player's decision, sample a single action to avoid exponential branching
        if current == updating_player:
            strategy = node.get_strategy(legal, realization_weight=reach_prob_other)
            idx = self._sample_from_dist(strategy) if legal else 0
            a = legal[idx]
            gs_next = self._clone_and_apply(gs, a)
            u = self._mccfr_traverse(
                gs_next,
                updating_player,
                reach_prob_other=reach_prob_other,
                reach_prob_updating=reach_prob_updating * strategy[idx],
                depth=depth + 1,
            )
            # Use the sampled utility as node utility for this visit
            node_utility = u
            # Minimal regret update: only touch the sampled action (keeps storage bounded, OK for smoke tests)
            k = action_key(a)
            node.regret_sum[k] = node.regret_sum.get(k, 0.0) + reach_prob_other * (u - node_utility)
            return node_utility
        else:
            # Sample opponent action according to their current average strategy (or current strategy)
            # Use current-strategy for traversal
            opp_strategy = node.get_strategy(legal, realization_weight=0.0)
            idx = self._sample_from_dist(opp_strategy)
            a = legal[idx]
            gs_next = self._clone_and_apply(gs, a)
            return self._mccfr_traverse(
                gs_next,
                updating_player,
                reach_prob_other=reach_prob_other * opp_strategy[idx],
                reach_prob_updating=reach_prob_updating,
                depth=depth + 1,
            )

    def _clone_and_apply(self, gs: GameState, a: Action) -> GameState:
        # Use engine-provided clone to preserve internal state safely
        gs2: GameState = gs.clone()
        gs2.apply(a)
        return gs2

    def _sample_from_dist(self, dist: List[float]) -> int:
        r = self.rng.random()
        c = 0.0
        for i, p in enumerate(dist):
            c += p
            if r <= c:
                return i
        return len(dist) - 1

    def action_probabilities(self, gs: GameState) -> List[Tuple[Action, float]]:
        legal = gs.legal_actions()
        key = infoset_key(gs, gs.current_player)
        node = self.nodes.get(key)
        if node is None:
            # uniform
            n = len(legal)
            probs = [1.0 / n for _ in range(n)] if n else []
        else:
            probs = node.get_average_strategy(legal)
        return list(zip(legal, probs))

    def evaluate(self, episodes: int = 100, seed: Optional[int] = None) -> float:
        # Self-play using average strategies; return avg utility for player 0
        rng = random.Random(seed)
        total = 0.0
        for _ in range(episodes):
            gs = GameState(num_players=2, seed=rng.randrange(1 << 30))
            steps = 0
            while gs.winner() is None and steps < self.max_depth:
                acts = self.action_probabilities(gs)
                if not acts:
                    break
                actions, probs = zip(*acts)
                idx = self._sample_from_dist(list(probs))
                gs.apply(actions[idx])
                steps += 1
            w = gs.winner()
            total += 1.0 if w == 0 else -1.0
        return total / max(1, episodes)
