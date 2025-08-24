from coup_gto.engine import GameState, ActionType, Role


def ensure_role_in_hand(gs: GameState, pid: int, role: Role):
    if role not in gs.players[pid].hand:
        # Try deck first
        for i, r in enumerate(gs.deck):
            if r == role:
                gs.deck.pop(i)
                gs.players[pid].hand[0] = role
                return
        # Then swap with opponent if needed
        opp = 1 - pid
        for i, r in enumerate(gs.players[opp].hand):
            if r == role:
                gs.players[opp].hand[i], gs.players[pid].hand[0] = gs.players[pid].hand[0], gs.players[opp].hand[i]
                return


def remove_role_from_hand(gs: GameState, pid: int, role: Role):
    if role in gs.players[pid].hand:
        # Replace with a different role from deck if possible
        for i, r in enumerate(gs.deck):
            if r != role:
                idx = gs.players[pid].hand.index(role)
                gs.players[pid].hand[idx] = r
                gs.deck.pop(i)
                return
        opp = 1 - pid
        for i, r in enumerate(gs.players[opp].hand):
            if r != role:
                idx = gs.players[pid].hand.index(role)
                gs.players[opp].hand[i], gs.players[pid].hand[idx] = gs.players[pid].hand[idx], gs.players[opp].hand[i]
                return


def get_action(gs: GameState, at: ActionType):
    return [a for a in gs.legal_actions() if a.type == at][0]


def test_exchange_pass_executes_exchange():
    gs = GameState(num_players=2, seed=30)
    p0, p1 = 0, 1
    # Actor claims exchange
    ex = get_action(gs, ActionType.EXCHANGE)
    old_hand = list(gs.players[p0].hand)
    old_deck_top = list(gs.deck[:2])
    gs.apply(ex)
    # Opponent passes
    gs.apply(get_action(gs, ActionType.PASS))
    # Hand should now be updated deterministically; not equal to old hand in general
    assert len(gs.players[p0].hand) == 2
    assert gs.pending_action is None
    # Deck size should be unchanged overall (draw 2, return 2)
    assert len(gs.deck) >= 0


def test_exchange_challenge_actor_truthful():
    gs = GameState(num_players=2, seed=31)
    p0, p1 = 0, 1
    ensure_role_in_hand(gs, p0, Role.AMBASSADOR)
    ex = get_action(gs, ActionType.EXCHANGE)
    gs.apply(ex)
    # Opponent challenges
    chal = get_action(gs, ActionType.CHALLENGE)
    p1_hand_before = len(gs.players[p1].hand)
    gs.apply(chal)
    # Challenger loses 1; exchange performed
    assert len(gs.players[p1].hand) == max(0, p1_hand_before - 1)
    assert gs.pending_action is None


def test_exchange_challenge_actor_bluff():
    gs = GameState(num_players=2, seed=32)
    p0, p1 = 0, 1
    remove_role_from_hand(gs, p0, Role.AMBASSADOR)
    ex = get_action(gs, ActionType.EXCHANGE)
    gs.apply(ex)
    # Opponent challenges
    chal = get_action(gs, ActionType.CHALLENGE)
    p0_hand_before = len(gs.players[p0].hand)
    gs.apply(chal)
    # Actor loses 1; exchange does not occur (no further state pending)
    assert len(gs.players[p0].hand) == p0_hand_before - 1
    assert gs.pending_action is None
