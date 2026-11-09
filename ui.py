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

    def pause_hit_test(self, pos, show_instructions=False):
        """Return the clicked pause action, or None."""
        panel = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 220, 520, 440)
        if show_instructions:
            back = pygame.Rect(panel.x + 25, panel.bottom - 60, 190, 45)
            return "BACK" if back.collidepoint(pos) else None
        for i, option in enumerate(("RESTART", "RESUME", "HOW TO PLAY", "MAIN MENU", "QUIT")):
            rect = pygame.Rect(panel.x + 45, panel.y + 77 + i * 65, 430, 50)
            if rect.collidepoint(pos):
                return option
        return None

    def draw_pause(self, screen, selected=0, show_instructions=False):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 190))
        screen.blit(shade, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 220, 520, 440)
        self.draw_panel(screen, panel)
        mouse = pygame.mouse.get_pos()
        if show_instructions:
            heading = self.title_font.render("HOW TO PLAY", True, self.colors["yellow"])
            screen.blit(heading, heading.get_rect(center=(WIDTH // 2, panel.y + 43)))
            lines = [
                "Click a yellow tile: walk 1 tile",
                "Click a white tile: run 2 tiles",
                "Stand on a chest and press E: search",
                "Stand at a wardrobe and press E: hide",
                "Press E again to leave a wardrobe",
                "Find the key, reach exit I7, then press E",
            ]
            for i, line in enumerate(lines):
                self.draw_text(screen, line, panel.x + 35, panel.y + 95 + i * 39, self.body_font)
            back = pygame.Rect(panel.x + 25, panel.bottom - 60, 190, 45)
            hovered = back.collidepoint(mouse)
            pygame.draw.rect(screen, (65, 56, 45) if hovered else (40, 40, 50), back, border_radius=8)
            self.draw_text(screen, "BACK", back.x + 58, back.y + 10,
                           self.title_font, self.colors["yellow"] if hovered else self.colors["white"])
        else:
            pause_font = pygame.font.SysFont("arial", 48, bold=True)
            title = pause_font.render("PAUSE", True, (255, 55, 65))
            screen.blit(title, title.get_rect(center=(WIDTH // 2, panel.y + 43)))
            options = ("RESTART", "RESUME", "HOW TO PLAY", "MAIN MENU", "QUIT")
            for i, label in enumerate(options):
                rect = pygame.Rect(panel.x + 45, panel.y + 77 + i * 65, 430, 50)
                hovered = rect.collidepoint(mouse)
                if hovered:
                    pygame.draw.rect(screen, (58, 49, 45), rect, border_radius=8)
                color = self.colors["yellow"] if hovered else self.colors["white"]
                rendered = self.title_font.render(label, True, color)
                screen.blit(rendered, rendered.get_rect(center=rect.center))
            hint = self.small_font.render("Click an option to select", True, self.colors["muted"])
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, panel.bottom - 18)))
