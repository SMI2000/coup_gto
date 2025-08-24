from coup_gto.engine import GameState, ActionType, Action, Role


def step_foreign_aid_no_block():
    gs = GameState(num_players=2, seed=7)
    p0 = 0
    # P0 chooses Foreign Aid
    fa = [a for a in gs.legal_actions() if a.type == ActionType.FOREIGN_AID][0]
    gs.apply(fa)
    # Now pending response by P1: PASS or BLOCK_FOREIGN_AID
    resp = gs.legal_actions()
    kinds = {a.type for a in resp}
    assert ActionType.PASS in kinds
    assert ActionType.BLOCK_FOREIGN_AID in kinds
    # If P1 passes, FA succeeds: P0 +2 coins, then turn advances to P1
    p0_coins_before = gs.players[p0].coins
    p1_pass = [a for a in resp if a.type == ActionType.PASS][0]
    gs.apply(p1_pass)
    assert gs.players[p0].coins == p0_coins_before + 2
    assert gs.pending_action is None
    assert gs.current_player == 1


def test_foreign_aid_pass_succeeds():
    step_foreign_aid_no_block()


def test_foreign_aid_block_challenge_blocker_truthful():
    gs = GameState(num_players=2, seed=8)
    # Force P1 to have a Duke to test truthful reveal path
    # Move a Duke from deck or from P0 to P1 deterministically if needed
    # Simplest: search and swap cards so that P1 has at least one Duke
    def ensure_role(pid, role):
        # if player has role, ok; else swap from deck
        if role not in gs.players[pid].hand:
            # take the first occurrence from deck or opponent
            for idx, r in enumerate(gs.deck):
                if r == role:
                    gs.players[pid].hand[0] = role
                    gs.deck.pop(idx)
                    break
            else:
                # try from opponent
                opp = 1 - pid
                for idx, r in enumerate(gs.players[opp].hand):
                    if r == role:
                        gs.players[opp].hand[idx] = gs.players[pid].hand[0]
                        gs.players[pid].hand[0] = role
                        break
    ensure_role(1, Role.DUKE)

    # P0 plays Foreign Aid
    fa = [a for a in gs.legal_actions() if a.type == ActionType.FOREIGN_AID][0]
    gs.apply(fa)
    # P1 blocks
    block = [a for a in gs.legal_actions() if a.type == ActionType.BLOCK_FOREIGN_AID][0]
    gs.apply(block)
    # P0 challenges
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    p0_hand_before = len(gs.players[0].hand)
    gs.apply(chal)
    # Blocker truthful: P1 reveals+replaces; P0 loses one influence; FA remains blocked
    assert len(gs.players[0].hand) == p0_hand_before - 1
    assert gs.players[0].revealed
    # Coins unchanged for P0
    # Interaction cleared and turn passes to P1
    assert gs.pending_action is None
    assert gs.current_player == 1


def test_foreign_aid_block_challenge_blocker_bluff():
    gs = GameState(num_players=2, seed=9)
    # Ensure P1 does NOT have a Duke
    def remove_role(pid, role):
        if role in gs.players[pid].hand:
            # replace with a non-role from deck
            replacement = None
            for idx, r in enumerate(gs.deck):
                if r != role:
                    replacement = r
                    gs.deck.pop(idx)
                    break
            if replacement is None:
                # swap with opponent if needed
                opp = 1 - pid
                for idx, r in enumerate(gs.players[opp].hand):
                    if r != role:
                        gs.players[opp].hand[idx], gs.players[pid].hand[0] = gs.players[pid].hand[0], gs.players[opp].hand[idx]
                        return
            for i, r in enumerate(gs.players[pid].hand):
                if r == role:
                    gs.players[pid].hand[i] = replacement
                    return
    remove_role(1, Role.DUKE)

    # P0 plays Foreign Aid
    fa = [a for a in gs.legal_actions() if a.type == ActionType.FOREIGN_AID][0]
    gs.apply(fa)
    # P1 blocks
    block = [a for a in gs.legal_actions() if a.type == ActionType.BLOCK_FOREIGN_AID][0]
    gs.apply(block)
    # P0 challenges
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    p1_hand_before = len(gs.players[1].hand)
    p0_coins_before = gs.players[0].coins
    gs.apply(chal)
    # Blocker bluffed: P1 loses one influence; P0 gains +2 coins from FA
    assert len(gs.players[1].hand) == p1_hand_before - 1
    assert gs.players[0].coins == p0_coins_before + 2
    # Interaction cleared and turn passes to P1
    assert gs.pending_action is None
    assert gs.current_player == 1
