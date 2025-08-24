from coup_gto.solver import MCCFRSolver
from coup_gto.engine import GameState

def test_full_branch_traversal_smoke():
    # Very small iterate to ensure full mode runs without blowing up
    solver = MCCFRSolver(seed=1, max_depth=15, traversal_mode="full", debug=False)
    solver.iterate(iterations=1, game_seed=5)
    # Inspect probabilities at root to ensure node storage occurred or at least callable
    gs = GameState(num_players=2, seed=11)
    probs = solver.action_probabilities(gs)
    assert isinstance(probs, list)
    assert len(probs) > 0
