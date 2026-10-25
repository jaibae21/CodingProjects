# Simple level definitions and random maze generation.
# Legend:
# 'S' = start, 'G' = goal, '#' = wall, '.' = empty
# Keep rectangular (equal line lengths).

from collections import deque

import numpy as np

LEVEL_7x7 = [
    "#######",
    "#S...G#",
    "#.###.#",
    "#...#.#",
    "###.#.#",
    "#.....#",
    "#######",
]

LEVEL_9x9 = [
    "#########",
    "#S....#G#",
    "#.##.#.#.",
    "#.#..#.#.",
    "#.#.##.#.",
    "#.#....#.",
    "#.######.",
    "#.......#",
    "#########",
]

DEFAULT_LEVEL = LEVEL_7x7


def _odd_at_least(value: int, minimum: int = 5) -> int:
    value = max(minimum, int(value))
    return value if value % 2 == 1 else value + 1


def generate_random_maze(rows: int, cols: int, rng: np.random.Generator) -> list[str]:
    """Create a solvable randomized maze using recursive backtracking."""
    rows = _odd_at_least(rows)
    cols = _odd_at_least(cols)

    grid = np.ones((rows, cols), dtype=np.int8)
    start = (1, 1)
    grid[start] = 0

    stack = [start]
    while stack:
        r, c = stack[-1]
        neighbors = []
        for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            nr, nc = r + dr, c + dc
            if 1 <= nr < rows - 1 and 1 <= nc < cols - 1 and grid[nr, nc] == 1:
                neighbors.append((nr, nc, dr // 2, dc // 2))

        if not neighbors:
            stack.pop()
            continue

        nr, nc, wr, wc = neighbors[int(rng.integers(len(neighbors)))]
        grid[r + wr, c + wc] = 0
        grid[nr, nc] = 0
        stack.append((nr, nc))

    goal = _farthest_open_cell(grid, start)
    return _grid_to_level(grid, start, goal)


def _farthest_open_cell(grid: np.ndarray, start: tuple[int, int]) -> tuple[int, int]:
    queue = deque([(start, 0)])
    seen = {start}
    farthest = start
    farthest_dist = 0

    while queue:
        (r, c), dist = queue.popleft()
        if dist > farthest_dist:
            farthest = (r, c)
            farthest_dist = dist

        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            pos = (nr, nc)
            if pos in seen:
                continue
            if 0 <= nr < grid.shape[0] and 0 <= nc < grid.shape[1] and grid[nr, nc] == 0:
                seen.add(pos)
                queue.append((pos, dist + 1))

    return farthest


def _grid_to_level(
    grid: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[str]:
    rows = []
    for r in range(grid.shape[0]):
        chars = []
        for c in range(grid.shape[1]):
            pos = (r, c)
            if pos == start:
                chars.append("S")
            elif pos == goal:
                chars.append("G")
            elif grid[r, c] == 1:
                chars.append("#")
            else:
                chars.append(".")
        rows.append("".join(chars))
    return rows
