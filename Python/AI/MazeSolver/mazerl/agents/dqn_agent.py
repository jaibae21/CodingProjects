from __future__ import annotations
import os
import numpy as np
import torch
import torch.nn.functional as F
from .base_agent import BaseAgent
from .networks import DQNNet
from .replay_buffer import ReplayBuffer

class DQNAgent(BaseAgent):
    """"
    DQN with 
    - Experience Replay
    - Target Network
    - Epsilon-greedy exploration

    Core update (per sample):
    y = r + gamma * max_a' Q_target(s', a') * (1 - done)
    loss = Huber(Q(s, a), y)
    """

    def __init__(self, obs_size, n_actions, config):
        super().__init__(obs_size, n_actions)
        self.cfg = config
        device = torch.device(config.device)

        self.policy = DQNNet(obs_size, n_actions, config.hidden_sizes).to(device)
        self.target = DQNNet(obs_size, n_actions, config.hidden_sizes).to(device)
        self.target.load_state_dict(self.policy.state_dict())
        self.target.eval()

        self.optim = torch.optim.Adam(self.policy.parameters(), lr=config.learning_rate)
        self.memory = ReplayBuffer(config.buffer_size, obs_size)
        self.device = device
        self.global_step = 0

    def epsilon_by_step(self, step: int) -> float:
        # Linear decay from eps_start -> eps_end over eps_decay_steps
        eps = self.cfg.eps_end + (self.cfg.eps_start - self.cfg.eps_end) * \
            max(0.0, (self.cfg.eps_decay_steps - step) / self.cfg.eps_decay_steps)
        return float(eps)
    
    def act(self, state: np.ndarray, step: int) -> int:
        eps = self.epsilon_by_step(step)
        if np.random.rand() < eps:
            return np.random.randint(self.n_actions)
        with torch.no_grad():
            s = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            q = self.policy(s)
            return int(torch.argmax(q, dim=1).item())
        
    def observe(self, s, a, r, s2, d, step):
        self.global_step += 1
        self.memory.add(s, a, r, s2, float(d))

        if self.global_step < self.cfg.start_learning_after:
            return
    
        if self.global_step % self.cfg.train_every != 0:
            return
        
        self._train_step()

        if self.global_step % self.cfg.target_update_interval == 0:
            self.target.load_state_dict(self.policy.state_dict())

    def _train_step(self):
        if len(self.memory) < self.cfg.batch_size:
            return
        
        s, a, r, s2, d = self.memory.sample(self.cfg.batch_size)

        s = torch.tensor(s, dtype=torch.float32, device=self.device)
        a = torch.tensor(a, dtype=torch.int64, device=self.device)
        r = torch.tensor(r, dtype=torch.float32, device=self.device)
        s2 = torch.tensor(s2, dtype=torch.float32, device=self.device)
        d = torch.tensor(d, dtype=torch.float32, device=self.device)

        # Q(s,a)
        q_values = self.policy(s).gather(1, a)

        # y = r + gamma * max_a' Q_target(s',a') * (1 - done)
        with torch.no_grad():
            next_q = self.target(s2).max(dim=1, keepdim=True)[0]
            target = r + self.cfg.gamma * next_q * (1.0 -d)
        
        # Huber loss (smooth L1) is robust to outliers vs MSE
        loss = F.smooth_l1_loss(q_values, target, beta=self.cfg.huber_delta)

        self.optim.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 10.0)
        self.optim.step()

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save({
            "model": self.policy.state_dict(),
            "cfg": vars(self.cfg),
            "step": self.global_step,
        }, path)

    def load(self, path: str):
        ckpt = torch.load(path, map_location=self.device)
        self.policy.load_state_dict(ckpt["model"])
        self.target.load_state_dict(ckpt["model"])
        self.global_step = ckpt.get("step", 0)