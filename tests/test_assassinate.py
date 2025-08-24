from coup_gto.engine import GameState, ActionType, Role


def ensure_role_in_hand(gs: GameState, pid: int, role: Role):
    if role not in gs.players[pid].hand:
        # move from deck if available, else swap with opponent
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
        # replace with non-role from deck if possible
        for i, r in enumerate(gs.deck):
            if r != role:
                gs.players[pid].hand[gs.players[pid].hand.index(role)] = r
                gs.deck.pop(i)
                return
        # else swap with opponent
        opp = 1 - pid
        for i, r in enumerate(gs.players[opp].hand):
            if r != role:
                idx = gs.players[pid].hand.index(role)
                gs.players[opp].hand[i], gs.players[pid].hand[idx] = gs.players[pid].hand[idx], gs.players[opp].hand[i]
                return


def test_assassinate_pass_succeeds_and_cost_paid():
    gs = GameState(num_players=2, seed=13)
    p0 = 0
    p1 = 1
    gs.players[p0].coins = 3
    # Declare assassinate
    ass = [a for a in gs.legal_actions() if a.type == ActionType.ASSASSINATE][0]
    gs.apply(ass)
    # Cost deducted immediately
    assert gs.players[p0].coins == 0
    # P1 may pass/block/challenge; choose pass -> P1 loses 1 influence
    resp = [a for a in gs.legal_actions() if a.type == ActionType.PASS][0]
    hand_before = len(gs.players[p1].hand)
    gs.apply(resp)
    assert len(gs.players[p1].hand) == hand_before - 1
    assert gs.pending_action is None
    assert gs.current_player == 1


def test_assassinate_challenge_actor_truthful():
    gs = GameState(num_players=2, seed=14)
    p0 = 0
    p1 = 1
    gs.players[p0].coins = 3
    ensure_role_in_hand(gs, p0, Role.ASSASSIN)
    ass = [a for a in gs.legal_actions() if a.type == ActionType.ASSASSINATE][0]
    gs.apply(ass)
    # P1 challenges claim
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    p1_hand_before = len(gs.players[p1].hand)
    gs.apply(chal)
    # Truthful: P1 loses 1 and target loses another from assassination
    assert len(gs.players[p1].hand) == p1_hand_before - 2 or (p1_hand_before - 1 == 0)
    assert gs.pending_action is None
    # If P1 still alive, turn passes; else game may be over with current player unchanged
    if len(gs.players[p1].hand) > 0:
        assert gs.current_player == 1


def test_assassinate_challenge_actor_bluff():
    gs = GameState(num_players=2, seed=15)
    p0 = 0
    p1 = 1
    gs.players[p0].coins = 3
    remove_role_from_hand(gs, p0, Role.ASSASSIN)
    ass = [a for a in gs.legal_actions() if a.type == ActionType.ASSASSINATE][0]
    gs.apply(ass)
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    p0_hand_before = len(gs.players[p0].hand)
    gs.apply(chal)
    # Bluff: P0 loses 1, assassination fails
    assert len(gs.players[p0].hand) == p0_hand_before - 1
    assert gs.pending_action is None
    assert gs.current_player == 1


def test_assassinate_block_contessa_truthful():
    gs = GameState(num_players=2, seed=16)
    p0 = 0
    p1 = 1
    gs.players[p0].coins = 3
    ensure_role_in_hand(gs, p1, Role.CONTESSA)
    ass = [a for a in gs.legal_actions() if a.type == ActionType.ASSASSINATE][0]
    gs.apply(ass)
    # P1 blocks with Contessa
    block = [a for a in gs.legal_actions() if a.type == ActionType.BLOCK_ASSASSINATE][0]
    gs.apply(block)
    # P0 challenges the block
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    p0_hand_before = len(gs.players[p0].hand)
    gs.apply(chal)
    # Truthful block: P0 loses 1; assassination fails
    assert len(gs.players[p0].hand) == p0_hand_before - 1
    assert gs.pending_action is None
    assert gs.current_player == 1


def test_assassinate_block_contessa_bluff():
    gs = GameState(num_players=2, seed=17)
    p0 = 0
    p1 = 1
    gs.players[p0].coins = 3
    remove_role_from_hand(gs, p1, Role.CONTESSA)
    ass = [a for a in gs.legal_actions() if a.type == ActionType.ASSASSINATE][0]
    gs.apply(ass)
    # P1 blocks
    block = [a for a in gs.legal_actions() if a.type == ActionType.BLOCK_ASSASSINATE][0]
    gs.apply(block)
    # P0 challenges block
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    p1_hand_before = len(gs.players[p1].hand)
    gs.apply(chal)
    # Bluff block: P1 loses 1, assassination succeeds -> P1 loses another
    assert len(gs.players[p1].hand) == max(0, p1_hand_before - 2)
    assert gs.pending_action is None
    if len(gs.players[p1].hand) > 0:
        assert gs.current_player == 1
