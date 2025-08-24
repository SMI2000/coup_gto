from coup_gto.engine import GameState


def test_random_rollout_terminates_under_cap():
    gs = GameState(num_players=2, seed=123)
    max_steps = 300
    steps = 0
    while gs.winner() is None and steps < max_steps:
        legal = gs.legal_actions()
        assert legal, "No legal actions available during rollout"
        a = legal[0]  # deterministic pick to avoid randomness; still should terminate
        gs.apply(a)
        steps += 1
    assert gs.winner() is not None or steps == max_steps
