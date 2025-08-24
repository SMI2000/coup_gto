# Coup GTO (Base Game, 2-Player First)

This project explores Game Theory Optimal (GTO) strategies for the card game Coup, starting with the base game and 2 players. The architecture is designed to be extensible to expansions (e.g., Reformation, Inquisitor) and higher player counts.

## Status
- Initial rules and engine scaffolding for base game.
- Deterministic game setup and minimal action resolution (Income, Foreign Aid with Duke block, Coup with mandatory rule at 10+ coins).
- Unit tests to anchor behavior.

## Project Structure
- `coup_gto/rules/base.py` — Configurable base game rules (roles, actions, blocks, costs, deck composition).
- `coup_gto/engine/state.py` — Game state, setup, legal action generation, and minimal resolution.
- `coup_gto/engine/actions.py` — Action and enums for action types and roles.
- `tests/` — Pytest unit tests for correctness of core rules.

## Getting Started
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Next Steps
- Add full challenge and block resolution with reveal/replace mechanics.
- Implement Ambassador exchange and Captain steal interactions fully.
- Introduce CFR/MCCFR solver modules and evaluation tooling.
- Generalize to N-player and add expansion variants.
