from coup_gto.solver import MCCFRSolver
from coup_gto.engine import GameState


def test_mccfr_runs_iterations_and_evaluates():
    # Keep test ultra-lightweight and enable debug to diagnose any loops
    solver = MCCFRSolver(seed=123, max_depth=60, debug=True)
    # Run a minimal number of iterations to ensure no crashes
    solver.iterate(iterations=1, game_seed=42)
    # Evaluate should return a finite value in [-1, 1]
    val = solver.evaluate(episodes=1, seed=7)
    assert -1.0 <= val <= 1.0


def test_action_probabilities_outputs_distribution():
    solver = MCCFRSolver(seed=1, max_depth=60)
    gs = GameState(num_players=2, seed=3)
    acts = solver.action_probabilities(gs)
    assert acts, "Should return at least one action"
    # Probabilities sum to 1
    s = sum(p for _, p in acts)
    assert abs(s - 1.0) < 1e-6
