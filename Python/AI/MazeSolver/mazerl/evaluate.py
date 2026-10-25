import argparse
import csv
import os
import torch
from .config import Config
from .utils.seeding import set_seed
from .envs.maze_env import MazeEnv
from .agents.dqn_agent import DQNAgent
from .eval_utils import run_greedy_evaluation


def apply_checkpoint_config(cfg: Config, checkpoint_path: str) -> Config:
    ckpt = torch.load(checkpoint_path, map_location=cfg.device)
    saved_cfg = ckpt.get("cfg", {})
    for key in ("random_maze", "randomize_maze_each_episode", "maze_rows", "maze_cols", "max_steps_per_episode", "hidden_sizes"):
        if key in saved_cfg:
            setattr(cfg, key, saved_cfg[key])
    return cfg

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="Path to save model .pt")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--device", default=None)
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--csv", default=None, help="Optional path to append evaluation results")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    cfg = Config()
    if args.device is not None:
        cfg.device = args.device
    cfg = apply_checkpoint_config(cfg, args.checkpoint)
    if args.device is not None:
        cfg.device = args.device
    if args.seed is not None:
        cfg.seed = args.seed

    set_seed(cfg.seed)
    env = MazeEnv(
        max_steps=cfg.max_steps_per_episode,
        seed=cfg.seed,
        random_maze=cfg.random_maze,
        maze_rows=cfg.maze_rows,
        maze_cols=cfg.maze_cols,
        randomize_on_reset=cfg.randomize_maze_each_episode,
    )
    agent = DQNAgent(env.obs_size, env.action_space_n, cfg)
    agent.load(args.checkpoint)

    renderer = None
    if not args.no_render:
        from .ui.renderer import MazeRender

        renderer = MazeRender(env, fps=cfg.fps_when_rendering, title="Evaluate")

    stats = run_greedy_evaluation(agent, env, args.episodes, renderer=renderer)
    print(
        f"Evaluation complete: success_rate={stats['success_rate']:.2%}, "
        f"avg_return={stats['avg_return']:.3f}, avg_length={stats['avg_length']:.1f}"
    )

    if args.csv is not None:
        os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
        needs_header = not os.path.exists(args.csv) or os.path.getsize(args.csv) == 0
        with open(args.csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["checkpoint", "episodes", "success_rate", "avg_return", "avg_length"])
            if needs_header:
                writer.writeheader()
            writer.writerow({"checkpoint": args.checkpoint, **stats})

if __name__ == "__main__":
    main()
