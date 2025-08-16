from dataclasses import dataclass

@dataclass
class Config:
    # Environment
    max_steps_per_episode: int = 200

    # DQN
    gamma: float = 0.99
    learning_rate: float = 1e-3
    batch_size: int = 64
    buffer_size: int = 50_000
    start_learning_after: int = 1_000   #steps to collect before training
    target_update_interval: int = 1_000  #steps to update target network
    train_every: int = 4                #gradient updates every N env steps
    huber_delta: float = 1.0

    # Epsilon-greed schedule
    # TODO: comment what each value does
    eps_start: float = 1.0
    eps_end: float = 0.05
    eps_decay_steps: int = 30_000

    # Network
    hidden_sizes: tuple = (256, 256)

    # Training
    total_steps: int = 80_000
    seed: int = 42
    device: str = "cpu" # "cuda" if you have GPU + torch.cuda.is_available()

    # Rendering / Logging
    render_every_episodes: int = 5  # render during training every N episode
    fps_when_rendering: int = 30
    checkpoint_dir: str = "runs"