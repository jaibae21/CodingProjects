from __future__ import annotations

import numpy as np

from .envs.maze_env import MazeEnv


def run_greedy_evaluation(agent, env: MazeEnv, episodes: int, renderer=None, label="Eval") -> dict:
    returns = []
    lengths = []
    successes = []

    for ep in range(1, episodes + 1):
        state = env.reset()
        done = False
        episode_return = 0.0
        steps = 0

        while not done:
            action = agent.act(state, step=agent.global_step, greedy=True)
            state, reward, done, _ = env.step(action)
            episode_return += reward
            steps += 1

            if renderer is not None:
                renderer.render(info_text=f"{label} Ep {ep} | steps {steps} | R {episode_return:.2f}")

        returns.append(episode_return)
        lengths.append(steps)
        successes.append(int(env.agent == env.goal))

    return {
        "episodes": episodes,
        "success_rate": float(np.mean(successes)) if successes else 0.0,
        "avg_return": float(np.mean(returns)) if returns else 0.0,
        "avg_length": float(np.mean(lengths)) if lengths else 0.0,
    }
