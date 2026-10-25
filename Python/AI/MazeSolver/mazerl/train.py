import os
import time
import argparse
from tqdm import trange
import numpy as np
from .config import Config
from .utils.seeding import set_seed
from .envs.maze_env import MazeEnv
from .agents.dqn_agent import DQNAgent
from .eval_utils import run_greedy_evaluation
from .metrics import CsvLogger, EpisodeMetrics, EvalMetrics

def run_training(cfg: Config):
    set_seed(cfg.seed)
    run_name = cfg.run_name or time.strftime("run_%Y%m%d_%H%M%S")
    run_dir = os.path.join(cfg.checkpoint_dir, run_name)
    os.makedirs(run_dir, exist_ok=True)
    train_metrics_path = cfg.train_metrics_path or os.path.join(run_dir, "train_metrics.csv")
    eval_metrics_path = cfg.eval_metrics_path or os.path.join(run_dir, "eval_metrics.csv")

    env = MazeEnv(
        max_steps=cfg.max_steps_per_episode,
        seed=cfg.seed,
        random_maze=cfg.random_maze,
        maze_rows=cfg.maze_rows,
        maze_cols=cfg.maze_cols,
        randomize_on_reset=cfg.randomize_maze_each_episode,
    )
    agent = DQNAgent(env.obs_size, env.action_space_n, cfg)
    train_logger = CsvLogger(
        train_metrics_path,
        ["episode", "step", "return", "length", "success", "epsilon", "loss"],
    )
    eval_logger = CsvLogger(
        eval_metrics_path,
        ["step", "episode", "episodes", "success_rate", "avg_return", "avg_length"],
    )

    # Render only on some episodes to speed training
    renderer = None

    total_steps = 0
    episode = 0
    ep_returns = []

    with trange(cfg.total_steps, desc="Training", unit="step") as tbar:
        while total_steps < cfg.total_steps:
            s = env.reset()
            done = False
            ep_ret = 0.0
            ep_len = 0
            episode += 1

            # Turn on renderer for this episode
            do_render = cfg.render_every_episodes > 0 and episode % cfg.render_every_episodes == 0
            if do_render and renderer is None:
                from .ui.renderer import MazeRender

                renderer = MazeRender(env, fps=cfg.fps_when_rendering, title="Training")

            while not done and total_steps < cfg.total_steps:
                a = agent.act(s, agent.global_step)
                s2, r, done, _ = env.step(a)
                agent.observe(s, a, r, s2, done, agent.global_step)
                s = s2
                ep_ret += r
                ep_len += 1
                total_steps += 1
                tbar.update(1)

                if do_render and renderer is not None:
                    info = f"Ep {episode} | step {total_steps} | eps {agent.epsilon_by_step(agent.global_step):.2f} | R {ep_ret:.2f}"
                    renderer.render(info_text=info)
            
            ep_returns.append(ep_ret)
            success = int(env.agent == env.goal)
            train_logger.write(EpisodeMetrics(
                episode=episode,
                step=total_steps,
                return_=ep_ret,
                length=ep_len,
                success=success,
                epsilon=agent.epsilon_by_step(agent.global_step),
                loss=agent.last_loss,
            ))

            if cfg.eval_every_episodes > 0 and episode % cfg.eval_every_episodes == 0:
                eval_env = MazeEnv(
                    max_steps=cfg.max_steps_per_episode,
                    seed=cfg.seed,
                    random_maze=cfg.random_maze,
                    maze_rows=cfg.maze_rows,
                    maze_cols=cfg.maze_cols,
                    randomize_on_reset=cfg.randomize_maze_each_episode,
                )
                eval_stats = run_greedy_evaluation(agent, eval_env, cfg.eval_episodes)
                eval_logger.write(EvalMetrics(
                    step=total_steps,
                    episode=episode,
                    episodes=cfg.eval_episodes,
                    success_rate=eval_stats["success_rate"],
                    avg_return=eval_stats["avg_return"],
                    avg_length=eval_stats["avg_length"],
                ))

            if episode % 10 == 0:
                avg_r = np.mean(ep_returns[-10:])
                tbar.set_postfix_str(
                    f"Last10R={avg_r:.3f} success={success} loss={agent.last_loss}"
                )
                # Save rolling checkpoint
                agent.save(os.path.join(run_dir, "dqn_last.pt"))

    # Final save
    agent.save(os.path.join(run_dir, "dqn_final.pt"))
    print(f"\nTraining complete. Run saved to {run_dir}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default=None, help="'cpu' or 'cuda'")
    parser.add_argument("--seed", type=int, default=None, help="Set for reproducible mazes; omit for OS-random mazes")
    parser.add_argument("--static-level", action="store_true", help="Use the original hand-authored level")
    parser.add_argument("--maze-rows", type=int, default=None)
    parser.add_argument("--maze-cols", type=int, default=None)
    parser.add_argument("--eval-every-episodes", type=int, default=None)
    parser.add_argument("--eval-episodes", type=int, default=None)
    parser.add_argument("--render-every-episodes", type=int, default=None)
    parser.add_argument("--total-steps", type=int, default=None)
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    cfg = Config()
    if args.device is not None:
        cfg.device = args.device
    if args.seed is not None:
        cfg.seed = args.seed
    if args.static_level:
        cfg.random_maze = False
        cfg.randomize_maze_each_episode = False
    if args.maze_rows is not None:
        cfg.maze_rows = args.maze_rows
    if args.maze_cols is not None:
        cfg.maze_cols = args.maze_cols
    if args.eval_every_episodes is not None:
        cfg.eval_every_episodes = args.eval_every_episodes
    if args.eval_episodes is not None:
        cfg.eval_episodes = args.eval_episodes
    if args.render_every_episodes is not None:
        cfg.render_every_episodes = args.render_every_episodes
    if args.total_steps is not None:
        cfg.total_steps = args.total_steps
    if args.checkpoint_dir is not None:
        cfg.checkpoint_dir = args.checkpoint_dir
    if args.run_name is not None:
        cfg.run_name = args.run_name

    run_training(cfg)

if __name__ == "__main__":
    main()
