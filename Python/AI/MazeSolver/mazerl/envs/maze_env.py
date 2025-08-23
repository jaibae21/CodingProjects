from __future__ import annotations
import numpy as np
from typing import Tuple, List
from .levels import DEFAULT_LEVEL

class MazeEnv:
    """
    Tiny Gym-lie gird environment for maze navigation

    Observation: 
        Flattened float32 vector of shape(H*W*3)
        Channels: [walls, agent, goal] as one hot planes

    Actions: 0=up, 1=down, 2=left, 3=Right
    Reward:
        -0.01 per step (time penalty)
        -0.05 if run into a wall (no move)
        +1.0 if goal reached (episode terminates)
    
    Episode terminates on reaching goal or max_steps
    """

    ACTIONS = {
        0: (-1,0),  # up
        1: (1,0),   # Down
        2: (0,-1),   # Left
        3: (0,1),    #Right
    }

    def __init__(self, level: List[str] = None, max_steps: int = 200, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.level = level or DEFAULT_LEVEL
        self.max_steps = max_steps
        self._parse_level(self.level)
        self.reset()

    def _parse_level(self, level: List[str]):
        h = len(level)
        w = len(level[0])
        self.H, self.W = h,w

        grid = np.zeros((h,w), dtype=np.int8)   # 0 empty, 1 wall
        self.start = None
        self.goal = None

        for r, row in enumerate(level):
            if len(row) != w:
                raise ValueError("All level rows must have equal length")
            for c, ch in enumerate(row):
                if ch == '#':
                    grid[r,c] = 1
                elif ch == 'S':
                    self.start = (r,c)
                elif ch == 'G':
                    self.goal = (r,c)
                elif ch == '.':
                    pass
                else:
                    raise ValueError(f"Unknown char in level: '{ch}'")
                
        if self.start is None or self.goal is None:
            raise ValueError("Level must contain 'S' and 'G'")
        self.grid = grid

    @property
    def action_space_n(self) -> int:
        return 4
    
    @property
    def obs_size(self) -> int:
        # 3 channels (walls/agent/goal) * H * W
        return self.H * self.W * 3
    
    def reset(self) -> np.ndarray:
        self.agent = tuple(self.start)
        self.steps = 0
        return self._obs()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        self.steps += 1
        dr, dc = self.ACTIONS[action]
        nr, nc = self.agent[0] + dr, self.agent[1] + dc

        reward = -0.01  # time penalty
        done = False
        
        if not (0 <= nr < self.H and 0 <= nc < self.W) or self.grid[nr, nc] == 1:
            # bump wall or boundary -> stay put and small penalty
            reward -= 0.05
            nr, nc = self.agent
        else:
            self.agent = (nr, nc)

        if self.agent == self.goal:
            reward += 1.0
            done = True
        
        if self.steps >= self.max_steps:
            done = True
        
        return self._obs(), reward, done, {}
    
    def _obs(self) -> np.ndarray:
        walls = self.grid.astype(np.float32)
        agent = np.zeros_like(walls, dtype=np.float32)
        goal = np.zeros_like(walls, dtype=np.float32)
        agent[self.agent] = 1.0
        goal[self.goal] = 1.0
        stacked = np.stack([walls, agent, goal], axis=0) # (3, H, W)
        return stacked.flatten().astype(np.float32)
    
    # Convience used by renderer
    def get_grid_layers(self):
        return self.grid, self.agent, self.goal