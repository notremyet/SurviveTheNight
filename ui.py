
import pygame
from settings import WIDTH, HEIGHT


class GameUI:
    def __init__(self):
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.title_font = pygame.font.SysFont("arial", 26, bold=True)

        self.colors = {
            "panel": (22, 22, 29),
            "border": (100, 95, 100),
            "white": (240, 240, 240),
            "red": (210, 55, 65),
            "gray": (145, 145, 150),
            "green": (100, 180, 110),
        }

    def draw_panel(self, screen, rect):
        pygame.draw.rect(
            screen,
            self.colors["panel"],
            rect,
            border_radius=10
        )
        pygame.draw.rect(
            screen,
            self.colors["border"],
            rect,
            width=2,
            border_radius=10
        )

    def draw_text(self, screen, text, x, y, font=None, color=None):
        if font is None:
            font = self.font

        if color is None:
            color = self.colors["white"]

        surface = font.render(str(text), True, color)
        screen.blit(surface, (x, y))

    def draw_hud(
        self,
        screen,
        hp=3,
        max_hp=3,
        round_number=1,
        max_rounds=8,
        actions=2,
        max_actions=2,
        noise=0,
        message="Find the key and escape!"
    ):
        # Top HUD
        top_panel = pygame.Rect(15, 10, WIDTH - 30, 65)
        self.draw_panel(screen, top_panel)

        # HP
        self.draw_text(screen, "HP", 30, 20)
        for i in range(max_hp):
            color = self.colors["red"] if i < hp else self.colors["gray"]
            pygame.draw.circle(
                screen, color, (85 + i * 27, 35), 9
            )

        # Round
        self.draw_text(
            screen,
            f"ROUND {round_number}/{max_rounds}",
            WIDTH // 2 - 80,
            27,
            self.title_font
        )

        # Actions
        self.draw_text(
            screen,
            f"ACTIONS: {actions}/{max_actions}",
            WIDTH - 235,
            27
        )

        # Bottom HUD
        bottom_panel = pygame.Rect(15, HEIGHT - 65, WIDTH - 30, 50)
        self.draw_panel(screen, bottom_panel)

        self.draw_text(
            screen,
            f"NOISE: {noise}",
            30,
            HEIGHT - 52,
            self.small_font
        )

        self.draw_text(
            screen,
            message,
            WIDTH // 2 - 170,
            HEIGHT - 52,
            self.small_font,
            self.colors["green"]
        )
