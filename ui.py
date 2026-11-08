import pygame
from settings import WIDTH, HEIGHT


class GameUI:
    def __init__(self):
        self.font = pygame.font.SysFont("arial", 21, bold=True)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.title_font = pygame.font.SysFont("arial", 24, bold=True)
        self.body_font = pygame.font.SysFont("arial", 18)
        self.colors = {
            "panel": (22, 22, 29), "border": (100, 95, 100),
            "white": (240, 240, 240), "red": (210, 55, 65),
            "gray": (145, 145, 150), "green": (100, 180, 110),
            "yellow": (255, 217, 65), "muted": (180, 178, 188),
        }

    def draw_panel(self, screen, rect, fill=None):
        pygame.draw.rect(screen, fill or self.colors["panel"], rect, border_radius=10)
        pygame.draw.rect(screen, self.colors["border"], rect, 2, border_radius=10)

    def draw_text(self, screen, text, x, y, font=None, color=None):
        surface = (font or self.font).render(str(text), True, color or self.colors["white"])
        screen.blit(surface, (x, y))
        return surface.get_rect(topleft=(x, y))

    def draw_hud(self, screen, hp=3, max_hp=3, round_number=1,
                 max_rounds=12, actions=2, max_actions=2, noise=0,
                 message="Find the key and escape!", items=None, goal=None):
        # Top bar
        top = pygame.Rect(15, 10, WIDTH - 30, 65)
        self.draw_panel(screen, top)
        self.draw_text(screen, "HP", 30, 20)
        for i in range(max_hp):
            color = self.colors["red"] if i < hp else self.colors["gray"]
            pygame.draw.circle(screen, color, (85 + i * 27, 35), 9)
        round_surface = self.title_font.render(
            f"ROUND {round_number}/{max_rounds}", True, self.colors["white"])
        screen.blit(round_surface, round_surface.get_rect(center=(WIDTH // 2, 42)))
        action_surface = self.font.render(
            f"ACTIONS: {actions}/{max_actions}", True, self.colors["white"])
        screen.blit(action_surface, (WIDTH - action_surface.get_width() - 32, 25))

        # Bottom bar: live noise/goal on left, inventory slots on right.
        bottom_y = HEIGHT - 82
        bottom = pygame.Rect(15, bottom_y, WIDTH - 30, 67)
        self.draw_panel(screen, bottom)
        self.draw_text(screen, f"NOISE: {noise}", 30, bottom_y + 10,
                       self.small_font, self.colors["yellow"])
        self.draw_text(screen, "GOAL", 155, bottom_y + 10,
                       self.small_font, self.colors["yellow"])
        goal_text = goal or "Search chests, find the key and escape through I7."
        # Keep goal text inside its allocated area, away from END TURN.
        def fit_text(text, font, max_width):
            text = str(text)
            if font.size(text)[0] <= max_width:
                return text
            while text and font.size(text + "...")[0] > max_width:
                text = text[:-1]
            return text.rstrip() + "..."

        self.draw_text(screen, fit_text(goal_text, self.small_font, WIDTH - 425),
                       205, bottom_y + 10, self.small_font, self.colors["white"])
        self.draw_text(screen, "INVENTORY", 30, bottom_y + 37,
                       self.small_font, self.colors["muted"])
        items = items or []
        item_text = "  |  ".join(str(item) for item in items[:5]) if items else "Empty"
        self.draw_text(screen, fit_text(item_text, self.small_font, 355),
                       135, bottom_y + 37, self.small_font, self.colors["white"])
        # Reserve the bottom-right 185 pixels for the END TURN button.
        if message:
            msg_text = fit_text(message, self.small_font, 290)
            msg = self.small_font.render(msg_text, True, self.colors["green"])
            screen.blit(msg, (500, bottom_y + 39))

    def draw_pause(self, screen, selected=0, show_instructions=False):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 190))
        screen.blit(shade, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 220,
                            520, 440 if show_instructions else 360)
        self.draw_panel(screen, panel)
        title = "HOW TO PLAY" if show_instructions else "PAUSED"
        title_surface = self.title_font.render(title, True, self.colors["yellow"])
        screen.blit(title_surface, title_surface.get_rect(
            center=(WIDTH // 2, panel.y + 45)))
        if show_instructions:
            lines = [
                "Click a yellow tile: walk 1 tile",
                "Click a white tile: run 2 tiles",
                "Stand on a chest and press E: search",
                "Stand at a wardrobe and press E: hide",
                "Press E again to leave a wardrobe",
                "Find the key, reach exit I7, then press E",
                "Press ESC to return to the pause menu",
            ]
            y = panel.y + 100
            for line in lines:
                self.draw_text(screen, line, panel.x + 35, y, self.body_font)
                y += 36
            self.draw_text(screen, "ESC  -  BACK", panel.x + 35,
                           panel.bottom - 45, self.small_font, self.colors["yellow"])
        else:
            options = ["RESUME", "HOW TO PLAY", "MAIN MENU", "QUIT"]
            y = panel.y + 110
            for i, label in enumerate(options):
                color = self.colors["yellow"] if i == selected else self.colors["white"]
                text = self.title_font.render(label, True, color)
                screen.blit(text, text.get_rect(center=(WIDTH // 2, y)))
                y += 65
            self.draw_text(screen, "UP / DOWN to select  -  ENTER to confirm",
                           panel.x + 45, panel.bottom - 38,
                           self.small_font, self.colors["muted"])
