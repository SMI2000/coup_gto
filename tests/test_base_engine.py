import pytest

from coup_gto.engine import GameState, ActionType, Action


def test_setup_two_players_deterministic_seed():
    gs = GameState(num_players=2, seed=42)
    assert gs.num_players == 2
    assert len(gs.players) == 2
    # Each player starts with 2 coins and 2 cards
    for ps in gs.players:
        assert ps.coins == 2
        assert len(ps.hand) == 2
        assert len(ps.revealed) == 0
    # Deck size: 15 - 4 dealt = 11
    assert len(gs.deck) == 11
    # Player 0 starts
    assert gs.current_player == 0


def test_legal_actions_basic():
    gs = GameState(num_players=2, seed=1)
    acts = gs.legal_actions()
    kinds = {a.type for a in acts}
    assert ActionType.INCOME in kinds
    assert ActionType.FOREIGN_AID in kinds
    # Coup should not be legal at 2 coins
    assert ActionType.COUP not in kinds


def test_coup_becomes_legal_at_7():
    gs = GameState(num_players=2, seed=2)
    gs.players[0].coins = 7
    acts = gs.legal_actions()
    kinds = {a.type for a in acts}
    assert ActionType.COUP in kinds
    # Has a target and is unique among actions
    coup_actions = [a for a in acts if a.type == ActionType.COUP]
    assert len(coup_actions) == 1
    assert coup_actions[0].target == 1


def test_mandatory_coup_at_10_only_coup_legal():
    gs = GameState(num_players=2, seed=3)
    gs.players[0].coins = 10
    acts = gs.legal_actions()
    assert len(acts) == 1
    assert acts[0].type == ActionType.COUP
    assert acts[0].target == 1


def test_apply_income_and_turn_progression():
    gs = GameState(num_players=2, seed=4)
    p0_coins = gs.players[0].coins
    gs.apply(Action(actor=0, type=ActionType.INCOME))
    assert gs.players[0].coins == p0_coins + 1
    # Turn should pass to P1
    assert gs.current_player == 1


def test_apply_coup_resolves_and_reveals_one_card():
    gs = GameState(num_players=2, seed=5)
    gs.players[0].coins = 7
    # Ensure coup is legal then apply
    acts = gs.legal_actions()
    coup = [a for a in acts if a.type == ActionType.COUP][0]
    # Track P1 before
    p1_hand_before = list(gs.players[1].hand)
    gs.apply(coup)
    # Actor pays 7
    assert gs.players[0].coins == 0
    # Target loses exactly one card, moved to revealed
    assert len(gs.players[1].hand) == len(p1_hand_before) - 1
    assert len(gs.players[1].revealed) == 1
    # Next player is P1 if still alive
    assert gs.current_player == 1

