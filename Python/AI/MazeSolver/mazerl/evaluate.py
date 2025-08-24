import argparse
from .config import Config
from .utils.seeding import set_seed
from .envs.maze_env import MazeEnv
from .agents.dqn_agent import DQNAgent
from .ui.renderer import MazeRender

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="Path to save model .pt")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    cfg = Config()
    if args.device is not None:
        cfg.device = args.device

    set_seed(cfg.seed)
    env = MazeEnv(max_steps=cfg.max_steps_per_episode, seed=cfg.seed)
    agent = DQNAgent(env.obs_size, env.action_space_n, cfg)
    agent.load(args.checkpoint)

    renderer = MazeRender(env, fps=cfg.fps_when_rendering, title="Evaluate")

    for ep in range(1, args.episode + 1):
        s = env.reset()
        done = False
        ep_ret = 0.0
        steps = 0
        while not done:
            # Greedy (no epsilon) action
            a = agent.act(s, step=10**9)    # large step -> eps ~ eps_end
            s, r, done, _ = env.step(a)
            ep_ret += r
            steps += 1
            renderer.render(info_text=f"Eval Ep {ep} | steps {steps} | R {ep_ret:.2f}")
    
    print("Evaluation complete")

if __name__ == "__main__":
    main()