import argparse
import json
import os
import sys
from datetime import datetime

from coup_gto.solver import MCCFRSolver
from coup_gto.engine import GameState


def _ensure_out_dir(out_dir: str) -> str:
    if not out_dir:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = os.path.join("runs", ts)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def cmd_train(args: argparse.Namespace) -> int:
    solver = MCCFRSolver(
        seed=args.seed,
        max_depth=args.max_depth,
        debug=args.debug,
        traversal_mode=args.traversal_mode,
        log_infoset_hash=args.log_infoset_hash,
    )
    out_dir = _ensure_out_dir(args.out)

    # Minimal metrics collection
    meta = {
        "cmd": "train",
        "iterations": args.iterations,
        "seed": args.seed,
        "game_seed": args.game_seed,
        "max_depth": args.max_depth,
        "traversal_mode": args.traversal_mode,
        "debug": args.debug,
    }

    print(json.dumps({"event": "train_start", **meta}))

    # Chunked training with progress logs
    total = args.iterations
    interval = getattr(args, "log_interval", 0) or 0
    if interval <= 0 or interval >= total:
        solver.iterate(iterations=total, game_seed=args.game_seed)
        print(json.dumps({"event": "train_progress", "completed": total, "total": total}))
    else:
        done = 0
        while done < total:
            step = min(interval, total - done)
            solver.iterate(iterations=step, game_seed=args.game_seed)
            done += step
            print(json.dumps({"event": "train_progress", "completed": done, "total": total}))
    print(json.dumps({"event": "train_end", **meta}))

    # Simple checkpoint: just dump node count for now (placeholder for future strategy export)
    ckpt_path = os.path.join(out_dir, "checkpoint.json")
    solver.save_checkpoint(ckpt_path)
    print(f"Saved checkpoint to {ckpt_path}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    solver = MCCFRSolver(
        seed=args.seed,
        max_depth=args.max_depth,
        debug=args.debug,
        traversal_mode=args.traversal_mode,
        log_infoset_hash=args.log_infoset_hash,
    )
    out_dir = _ensure_out_dir(args.out) if args.out else None
    if args.checkpoint:
        solver.load_checkpoint(args.checkpoint)

    print(json.dumps({
        "event": "eval_start",
        "episodes": args.episodes,
        "seed": args.seed,
        "max_depth": args.max_depth,
        "traversal_mode": args.traversal_mode,
    }))
    val = solver.evaluate(episodes=args.episodes, seed=args.eval_seed)
    result = {"event": "eval_result", "avg_utility_p0": val}
    print(json.dumps(result))

    if out_dir:
        with open(os.path.join(out_dir, "eval.json"), "w", encoding="utf-8") as f:
            json.dump(result, f)
        print(f"Saved eval to {out_dir}/eval.json")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    solver = MCCFRSolver(
        seed=args.seed,
        max_depth=args.max_depth,
        debug=args.debug,
        traversal_mode=args.traversal_mode,
        log_infoset_hash=args.log_infoset_hash,
    )
    if args.checkpoint:
        solver.load_checkpoint(args.checkpoint)
    gs = GameState(num_players=2, seed=args.game_seed)
    acts = solver.action_probabilities(gs)
    data = [
        {"action": a.type.name, "target": a.target, "prob": p}
        for a, p in acts
    ]
    print(json.dumps({"event": "inspect", "actions": data}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coup_gto", description="Coup GTO MCCFR utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=0)
    common.add_argument("--max-depth", type=int, default=300)
    common.add_argument("--traversal-mode", choices=["sampled", "full"], default="sampled")
    common.add_argument("--debug", action="store_true")
    common.add_argument("--log-infoset-hash", action="store_true")

    # train
    pt = sub.add_parser("train", parents=[common], help="Run MCCFR iterations")
    pt.add_argument("--iterations", type=int, default=1000)
    pt.add_argument("--game-seed", type=int, default=42)
    pt.add_argument("--out", type=str, default="")
    pt.add_argument("--log-interval", type=int, default=10, help="Emit a progress log every N iterations")
    pt.set_defaults(func=cmd_train)

    # eval
    pe = sub.add_parser("eval", parents=[common], help="Evaluate average strategies via self-play")
    pe.add_argument("--episodes", type=int, default=100)
    pe.add_argument("--eval-seed", type=int, default=7)
    pe.add_argument("--out", type=str, default="")
    pe.add_argument("--checkpoint", type=str, default="")
    pe.set_defaults(func=cmd_eval)

    # inspect
    pi = sub.add_parser("inspect", parents=[common], help="Show action probabilities at initial state")
    pi.add_argument("--game-seed", type=int, default=3)
    pi.add_argument("--checkpoint", type=str, default="")
    pi.set_defaults(func=cmd_inspect)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
