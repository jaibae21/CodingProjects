import numpy as np
from typing import Tuple

class ReplayBuffer:
    def __init__(self, capacity: int, obs_dim: int):
        self.capacity = capacity
        self.obs_dim = obs_dim
        self.reset()

    def reset(self):
        self.s = np.zeroes((self.capacity, self.obs_dim), dtype=np.float32)
        self.a = np.zeroes((self.capacity, 1), dtype=np.int64)
        self.r = np.zeros((self.capacity, 1), dtype=np.float32)
        self.s2 = np.zeros((self.capacity, self.obs_dim), dtype=np.float32)
        self.d = np.zeros((self.capacity, 1), dtype=np.float32)
        self.idx = 0
        self.full = False

    def __len__(self):
        return self.capacity if self.full else self.idx
    
    def add(self, s, a, r, s2, d):
        self.s[self.idx] = s
        self.a[self.idx] = a
        self.r[self.idx] = r
        self.s2[self.idx] = s2
        self.d[self.idx] = d
        self.idx = (self.idx + 1) % self.capacity
        if self.idx == 0:
            self.full = True

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        max_idx = self.capacity if self.full else self.idx
        idxs = np.random.randint(0, max_idx, size=batch_size)
        return (
            self.s[idxs],
            self.a[idxs],
            self.r[idxs],
            self.s2[idxs], 
            self.d[idxs],
        )