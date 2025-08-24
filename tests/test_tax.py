from coup_gto.engine import GameState, ActionType, Action, Role


def test_tax_pass_succeeds():
    gs = GameState(num_players=2, seed=10)
    p0 = 0
    # P0 chooses TAX
    tax = [a for a in gs.legal_actions() if a.type == ActionType.TAX][0]
    coins_before = gs.players[p0].coins
    gs.apply(tax)
    # P1 can CHALLENGE or PASS
    resp = gs.legal_actions()
    kinds = {a.type for a in resp}
    assert ActionType.CHALLENGE in kinds and ActionType.PASS in kinds
    # Choose PASS -> TAX succeeds
    p1_pass = [a for a in resp if a.type == ActionType.PASS][0]
    gs.apply(p1_pass)
    assert gs.players[p0].coins == coins_before + 3
    assert gs.pending_action is None
    assert gs.current_player == 1


def test_tax_challenge_actor_truthful():
    gs = GameState(num_players=2, seed=11)
    # Ensure P0 has a Duke
    if Role.DUKE not in gs.players[0].hand:
        # Swap from deck
        for i, r in enumerate(gs.deck):
            if r == Role.DUKE:
                gs.deck.pop(i)
                gs.players[0].hand[0] = Role.DUKE
                break
    # P0 claims TAX
    tax = [a for a in gs.legal_actions() if a.type == ActionType.TAX][0]
    p0_coins_before = gs.players[0].coins
    p1_hand_before = len(gs.players[1].hand)
    gs.apply(tax)
    # P1 challenges
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    gs.apply(chal)
    # Actor truthful: P1 loses one influence, P0 gains +3
    assert len(gs.players[1].hand) == p1_hand_before - 1
    assert gs.players[0].coins == p0_coins_before + 3
    assert gs.pending_action is None
    assert gs.current_player == 1


def test_tax_challenge_actor_bluff():
    gs = GameState(num_players=2, seed=12)
    # Ensure P0 does NOT have a Duke
    if Role.DUKE in gs.players[0].hand:
        # Replace with a non-Duke from deck
        replacement = None
        for i, r in enumerate(gs.deck):
            if r != Role.DUKE:
                replacement = r
                gs.deck.pop(i)
                break
        for j, r in enumerate(gs.players[0].hand):
            if r == Role.DUKE:
                gs.players[0].hand[j] = replacement
                break
    # P0 claims TAX
    tax = [a for a in gs.legal_actions() if a.type == ActionType.TAX][0]
    p0_coins_before = gs.players[0].coins
    p0_hand_before = len(gs.players[0].hand)
    gs.apply(tax)
    # P1 challenges
    chal = [a for a in gs.legal_actions() if a.type == ActionType.CHALLENGE][0]
    gs.apply(chal)
    # Actor bluffed: P0 loses one influence, no coins gained
    assert len(gs.players[0].hand) == p0_hand_before - 1
    assert gs.players[0].coins == p0_coins_before
    assert gs.pending_action is None
    assert gs.current_player == 1
