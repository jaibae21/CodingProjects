import pygame

WHITE = (245, 245, 245)
BLACK = (30, 30, 30)
GREY = (130, 130, 130)
BLUE = (66, 135, 245)
GREEN = (50, 180, 75)

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
        self.surface = pygame.display.set_mod((w,h))
        pygame.display.set_caption(title)

    def render(self, info_text=""):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            
        grid, agent, goal = self.env.get_grid_layers()
        self.surface.fill(WHITE)

        # Draw grid
        for r in range(self.env.H):
            for c in range(self.env.W):
                x = c * self.cell
                y = r * self.cell
                rect = pygame.Rect(x, y, self.cell, self.cell)
                if grid[r,c] == 1:
                    pygame.draw.rect(self.surface, BLACK, rect)
                else:
                    pygame.draw.rect(self.surface, GREY, rect, 1)

        # Agent + Goal
        pygame.draw.rect( self.surface, GREEN, 
                         pygame.Rect(goal[1] * self.cell, goal[0] * self.cell, self.cell, self.cell)
                         )
        pygame.draw.rect( self.surface, BLUE, 
                         pygame.Rect(agent[1] * self.cell, agent[0] * self.cell, self.cell, self.cell)
                         )
        
        # HUD
        hud = self.font.render(info_text, True, BLACK)
        self.surface.blit(hud, (6, self.env.H * self.cell + 6))

        pygame.display.flip()
        self.clock.tick(self.fps)
