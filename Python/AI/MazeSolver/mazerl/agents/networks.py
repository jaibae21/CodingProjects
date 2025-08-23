import torch
import torch.nn as nn

class DQNNet(nn.Module):
    """"
    Simple MLP for DQN
    Input: flat state vector
    Ouptut: Q values for each action
    """

    def __init__(self, input_dim: int, output_dim: int, hidden_sizes=(256, 256)):
        super().__init__()
        layers = []
        last = input_dim
        for h in hidden_sizes:
            layers += [nn.Linear(last, h), nn.ReLU()]
            last = h
        layers += [nn.Linear(last, output_dim)]
        self.net == nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)