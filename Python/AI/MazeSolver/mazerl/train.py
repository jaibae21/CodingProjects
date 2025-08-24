import os
import time
import argparse
from tqdm import trange
import numpy as np
from .config import Config
from .utils.seeding import set_seed
from .envs.maze_env import MazeEnv
from .agents.dqn_agent import DQNAgent
from .ui.renderer import MazeRender

def run_training(cfg: Config):
    set_seed(cfg.seed)
    env = MazeEnv(max_steps=cfg.max_steps_per_episode, seed=cfg.seed)
    agent = DQNAgent(env.obs_size, env.action_space_n, cfg)

    # Render only on some episodes to speed training
    renderer = None
    last_render_time = 0.0

    total_steps = 0
    episode = 0
    ep_returns = []

    with trange(cfg.total_steps, desc="Training", unit="step") as tbar:
        while total_steps < cfg.total_steps:
            s = env.reset()
            done = False
            ep_ret = 0.0
            episode += 1

            # Turn on renderer for this episode
            do_render = (episode % cfg.render_every_episodes == 0)
            if do_render and renderer is None:
                renderer = MazeRender(env, fps=cfg.fps_when_rendering, title="Training")

            while not done and total_steps < cfg.total_steps:
                a = agent.act(s, agent.global_step)
                s2, r, done, _ = env.step(a)
                agent.observe(s, a, r, s2, done, agent.global_step)
                s = s2
                ep_ret += r
                total_steps += 1
                tbar.update(1)

                if do_render and renderer is not None:
                    info = f"Ep {episode} | step {total_steps} | eps {agent.epsilon_by_step(agent.global_step):.2f} | R {ep_ret:.2f}"
                    renderer.render(info_text=info)
            
            ep_returns.append(ep_ret)
            if episode % 10 == 0:
                avg_r = np.mean(ep_returns[-10:])
                tbar.set_postfix_str(f"Last10R={avg_r:.3f}")
                # Save rolling checkpoint
                agent.save(os.path.join(cfg.checkpoint_dir, "dqn_last.pt"))

    # Final save
    agent.save(os.path.join(cfg.checkpoint_dir, "dqn_final.pt"))
    print("\nTraining complete.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default=None, help="'cpu' or 'cuda'")
    args = parser.parse_args()

    cfg = Config()
    if args.device is not None:
        cfg.device = args.device

    run_training(cfg)

if __name__ == "__main__":
    main()
