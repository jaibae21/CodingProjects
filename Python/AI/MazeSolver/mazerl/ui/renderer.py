import warnings

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
    module="pygame.pkgdata",
)

import pygame

FLOOR = (205, 196, 174)
FLOOR_ALT = (190, 181, 162)
STONE = (70, 76, 84)
STONE_LIGHT = (106, 115, 126)
STONE_DARK = (34, 38, 44)
INK = (22, 25, 29)
BLUE = (55, 130, 230)
BLUE_LIGHT = (130, 190, 255)
GREEN = (65, 215, 125)
GREEN_DARK = (20, 110, 62)

class MazeRender:
    def __init__(self, env, cell_size=40, fps=30, title="Maze RL"):
        pygame.init()
        self.env = env
        self.cell = cell_size
        self.fps = fps
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)

        w = env.W * cell_size
        h = env.H * cell_size + 30  # extra space for HUD
        self.surface = pygame.display.set_mode((w,h))
        pygame.display.set_caption(title)

    def render(self, info_text=""):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            
        grid, agent, goal = self.env.get_grid_layers()
        self.surface.fill(INK)

        for r in range(self.env.H):
            for c in range(self.env.W):
                if grid[r,c] == 1:
                    self._draw_wall(r, c)
                else:
                    self._draw_floor(r, c)

        self._draw_goal(goal)
        self._draw_agent(agent)
        
        hud = self.font.render(info_text, True, (235, 238, 240))
        self.surface.blit(hud, (6, self.env.H * self.cell + 6))

        pygame.display.flip()
        self.clock.tick(self.fps)

    def _cell_rect(self, r, c, inset=0):
        return pygame.Rect(
            c * self.cell + inset,
            r * self.cell + inset,
            self.cell - inset * 2,
            self.cell - inset * 2,
        )

    def _draw_floor(self, r, c):
        rect = self._cell_rect(r, c)
        color = FLOOR if (r + c) % 2 == 0 else FLOOR_ALT
        pygame.draw.rect(self.surface, color, rect)
        pygame.draw.rect(self.surface, (155, 147, 132), rect, 1)

    def _draw_wall(self, r, c):
        rect = self._cell_rect(r, c)
        pygame.draw.rect(self.surface, STONE_DARK, rect)
        top = [
            (rect.left, rect.top),
            (rect.right, rect.top),
            (rect.right - self.cell * 0.18, rect.top + self.cell * 0.18),
            (rect.left + self.cell * 0.18, rect.top + self.cell * 0.18),
        ]
        face = pygame.Rect(rect.left + 4, rect.top + 4, rect.width - 8, rect.height - 8)
        pygame.draw.polygon(self.surface, STONE_LIGHT, top)
        pygame.draw.rect(self.surface, STONE, face, border_radius=max(2, self.cell // 10))
        pygame.draw.line(self.surface, STONE_DARK, rect.bottomleft, rect.bottomright, 3)
        pygame.draw.line(self.surface, STONE_DARK, rect.topright, rect.bottomright, 3)

    def _draw_goal(self, goal):
        cy = goal[0] * self.cell + self.cell // 2
        cx = goal[1] * self.cell + self.cell // 2
        pygame.draw.circle(self.surface, GREEN_DARK, (cx, cy), int(self.cell * 0.38))
        pygame.draw.circle(self.surface, GREEN, (cx, cy), int(self.cell * 0.27))
        pygame.draw.circle(self.surface, (210, 255, 225), (cx - self.cell // 10, cy - self.cell // 10), max(2, self.cell // 12))

    def _draw_agent(self, agent):
        cy = agent[0] * self.cell + self.cell // 2
        cx = agent[1] * self.cell + self.cell // 2
        pygame.draw.circle(self.surface, (21, 61, 120), (cx + 3, cy + 4), int(self.cell * 0.32))
        pygame.draw.circle(self.surface, BLUE, (cx, cy), int(self.cell * 0.32))
        pygame.draw.circle(self.surface, BLUE_LIGHT, (cx - self.cell // 9, cy - self.cell // 10), int(self.cell * 0.11))
