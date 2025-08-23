from abc import ABC, abstractmethod
import numpy as np

class BaseAgent(ABC):
    def __init__(self, obs_size: int, n_actions: int):
        self.obs_size = obs_size
        self.n_actions = n_actions

    @abstractmethod
    def act(self, stat: np.ndarray, step: int) -> int:
        ...
    
    @abstractmethod
    def observe(self, s, a, r, s2, d, step: int):
        ...

    @abstractmethod
    def save(self, path: str):
        ...
    
    @abstractmethod
    def load(self, path: str):
        ...
