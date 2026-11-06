

import pygame
from settings import COLS, ROWS, cell_to_xy, xy_to_cell


class Player:
    def __init__(self, start_cell="B2"):
        self.cell = start_cell
        self.color = (70, 180, 255)
        self.radius = 16

    def move(self, dx, dy, board, furniture=None):
        x, y = cell_to_xy(self.cell)

        nx = x + dx
        ny = y + dy

        # Prevent moving outside the board
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            return False

        next_cell = xy_to_cell((nx, ny))

        # Check walls and locked doors
        if not board.can_step(self.cell, next_cell):
            return False

        # Check furniture collision
        if furniture is not None:
            if furniture.is_blocked(next_cell):
                return False

        # Move player
        self.cell = next_cell
        return True

    def handle_key(self, key, board, furniture=None):
        directions = {
            pygame.K_w: (0, -1),
            pygame.K_UP: (0, -1),
            pygame.K_s: (0, 1),
            pygame.K_DOWN: (0, 1),
            pygame.K_a: (-1, 0),
            pygame.K_LEFT: (-1, 0),
            pygame.K_d: (1, 0),
            pygame.K_RIGHT: (1, 0),
        }

        if key in directions:
            dx, dy = directions[key]
            return self.move(dx, dy, board, furniture)

        return False

    def draw(self, surface, get_cell_center):
        px, py = get_cell_center(self.cell)

        # Player body
        pygame.draw.circle(
            surface,
            self.color,
            (px, py),
            self.radius
        )

        # White outline
        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (px, py),
            self.radius,
            2
        )
