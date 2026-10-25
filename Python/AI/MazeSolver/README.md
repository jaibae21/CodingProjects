# Maze Solver using DQN and Pygame

# DQN agent you can watch learn in real time

# python -m mazerl.train
# python -m mazerl.evaluate --checkpoint runs/run_YYYYMMDD_HHMMSS/dqn_last.pt

# Training now uses OS-random generated mazes by default.
# Add --seed 42 if you want reproducible maze generation.
# Add --static-level to train on the original hand-authored level.
#
# python -m mazerl.train --maze-rows 21 --maze-cols 21
#
# Each training run is saved under a timestamped folder in runs/.
# Example outputs:
# runs/run_YYYYMMDD_HHMMSS/dqn_final.pt
# runs/run_YYYYMMDD_HHMMSS/train_metrics.csv
# runs/run_YYYYMMDD_HHMMSS/eval_metrics.csv
#
# Headless evaluation:
# python -m mazerl.evaluate --checkpoint runs/run_YYYYMMDD_HHMMSS/dqn_final.pt --episodes 50 --no-render --csv runs/manual_eval.csv
#
# Use mazerl/envs/levels.py to add more levels
# Hyperparameters live in config.py
# Renderer is controlled in train.py to show every N episodes/steps
