from coup_gto.engine import GameState, ActionType, Role


def ensure_role_in_hand(gs: GameState, pid: int, role: Role):
    if role not in gs.players[pid].hand:
        for i, r in enumerate(gs.deck):
            if r == role:
                gs.deck.pop(i)
                gs.players[pid].hand[0] = role
                return
        opp = 1 - pid
        for i, r in enumerate(gs.players[opp].hand):
            if r == role:
                gs.players[opp].hand[i], gs.players[pid].hand[0] = gs.players[pid].hand[0], gs.players[opp].hand[i]
                return


def remove_role_from_hand(gs: GameState, pid: int, role: Role):
    if role in gs.players[pid].hand:
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


def test_steal_pass_transfers_up_to_two():
    gs = GameState(num_players=2, seed=20)
    p0, p1 = 0, 1
    gs.players[p0].coins = 0
    gs.players[p1].coins = 2
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    # Target passes
    gs.apply(get_action(gs, ActionType.PASS))
    assert gs.players[p0].coins == 2
    assert gs.players[p1].coins == 0
    assert gs.pending_action is None


def test_steal_pass_transfers_only_available():
    gs = GameState(num_players=2, seed=21)
    p0, p1 = 0, 1
    gs.players[p0].coins = 1
    gs.players[p1].coins = 1
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    gs.apply(get_action(gs, ActionType.PASS))
    assert gs.players[p0].coins == 2  # +1
    assert gs.players[p1].coins == 0


def test_steal_challenge_actor_truthful():
    gs = GameState(num_players=2, seed=22)
    p0, p1 = 0, 1
    ensure_role_in_hand(gs, p0, Role.CAPTAIN)
    start0, start1 = gs.players[p0].coins, gs.players[p1].coins
    gs.players[p1].coins = 2
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    # Target challenges claim
    chal = get_action(gs, ActionType.CHALLENGE)
    gs.apply(chal)
    # Truthful: challenger loses 1 influence, and transfer occurs
    assert gs.players[p0].coins == start0 + 2
    assert gs.players[p1].coins == 0
    assert gs.pending_action is None


def test_steal_challenge_actor_bluff():
    gs = GameState(num_players=2, seed=23)
    p0, p1 = 0, 1
    remove_role_from_hand(gs, p0, Role.CAPTAIN)
    start0, start1 = gs.players[p0].coins, gs.players[p1].coins
    gs.players[p1].coins = 2
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    chal = get_action(gs, ActionType.CHALLENGE)
    gs.apply(chal)
    # Bluff: actor loses 1 influence, no transfer
    assert gs.players[p0].coins == start0
    assert gs.players[p1].coins == 2
    assert gs.pending_action is None


def test_steal_block_captain_truthful():
    gs = GameState(num_players=2, seed=24)
    p0, p1 = 0, 1
    gs.players[p1].coins = 2
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    ensure_role_in_hand(gs, p1, Role.CAPTAIN)
    block = get_action(gs, ActionType.BLOCK_STEAL_CAPTAIN)
    gs.apply(block)
    # Actor challenges block
    chal = get_action(gs, ActionType.CHALLENGE)
    gs.apply(chal)
    # Truthful block: actor loses 1; no transfer
    assert gs.players[p1].coins == 2
    assert gs.pending_action is None


def test_steal_block_captain_bluff():
    gs = GameState(num_players=2, seed=25)
    p0, p1 = 0, 1
    gs.players[p1].coins = 2
    start0 = gs.players[p0].coins
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    remove_role_from_hand(gs, p1, Role.CAPTAIN)
    block = get_action(gs, ActionType.BLOCK_STEAL_CAPTAIN)
    gs.apply(block)
    # Actor challenges block
    chal = get_action(gs, ActionType.CHALLENGE)
    gs.apply(chal)
    # Bluff block: blocker loses 1; transfer proceeds
    assert gs.players[p0].coins == start0 + 2
    assert gs.players[p1].coins == 0
    assert gs.pending_action is None


def test_steal_block_ambassador_truthful():
    gs = GameState(num_players=2, seed=26)
    p0, p1 = 0, 1
    gs.players[p1].coins = 2
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    ensure_role_in_hand(gs, p1, Role.AMBASSADOR)
    block = get_action(gs, ActionType.BLOCK_STEAL_AMBASSADOR)
    gs.apply(block)
    # Actor challenges block
    chal = get_action(gs, ActionType.CHALLENGE)
    gs.apply(chal)
    assert gs.players[p1].coins == 2
    assert gs.pending_action is None


def test_steal_block_ambassador_bluff():
    gs = GameState(num_players=2, seed=27)
    p0, p1 = 0, 1
    gs.players[p1].coins = 2
    start0 = gs.players[p0].coins
    steal = get_action(gs, ActionType.STEAL)
    gs.apply(steal)
    remove_role_from_hand(gs, p1, Role.AMBASSADOR)
    block = get_action(gs, ActionType.BLOCK_STEAL_AMBASSADOR)
    gs.apply(block)
    # Actor challenges block
    chal = get_action(gs, ActionType.CHALLENGE)
    gs.apply(chal)
    assert gs.players[p0].coins == start0 + 2
    assert gs.players[p1].coins == 0
    assert gs.pending_action is None
