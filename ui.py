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
        # Keep the original horizontal columns; only lift the green turn
        # status from the lower Inventory row to the NOISE/GOAL row.
        def fit_text(text, font, max_width):
            text = str(text)
            if font.size(text)[0] <= max_width:
                return text
            while text and font.size(text + "...")[0] > max_width:
                text = text[:-1]
            return text.rstrip() + "..."

        self.draw_text(screen, fit_text(goal_text, self.small_font, 275),
                       205, bottom_y + 10, self.small_font, self.colors["white"])
        if message:
            # END TURN starts at WIDTH-185; leave a clear gap before it.
            available = max(10, WIDTH - 185 - 500 - 18)
            self.draw_text(screen, fit_text(message, self.small_font, available),
                           500, bottom_y + 10, self.small_font, self.colors["green"])
        self.draw_text(screen, "INVENTORY", 30, bottom_y + 37,
                       self.small_font, self.colors["muted"])
        items = items or []
        item_text = "  |  ".join(str(item) for item in items[:5]) if items else "-"
        self.draw_text(screen, fit_text(item_text, self.small_font, 355),
                       135, bottom_y + 37, self.small_font, self.colors["white"])
        # Reserve the bottom-right 185 pixels for END TURN.
        # The Inventory row (label + items + blank space) is mouse-clickable.

    def pause_layout(self):
        panel = pygame.Rect(WIDTH // 2 - 300, HEIGHT // 2 - 250, 600, 500)
        labels = ["RESTART", "RESUME", "HOW TO PLAY", "MAIN MENU", "QUIT"]
        buttons = [pygame.Rect(panel.left + 52, panel.top + 100 + i * 68,
                               panel.width - 104, 52) for i in range(len(labels))]
        return panel, list(zip(labels, buttons))

    def pause_hit_test(self, pos):
        _, options = self.pause_layout()
        return next((label for label, rect in options if rect.collidepoint(pos)), None)

    def draw_pause(self, screen, selected=0, show_instructions=False):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 195))
        screen.blit(shade, (0, 0))
        panel, options = self.pause_layout()
        self.draw_panel(screen, panel)
        if show_instructions:
            title = pygame.font.SysFont("arial", 36, bold=True).render("HOW TO PLAY", True, self.colors["yellow"])
            screen.blit(title, title.get_rect(center=(WIDTH // 2, panel.top + 48)))
            lines = [
                "Click a yellow tile: walk 1 tile",
                "Click a white tile: run 2 tiles",
                "Stand on a chest and press E: search",
                "Stand at a wardrobe and press E: hide",
                "Press E again to leave a wardrobe",
                "Find the key, reach exit, then press E",
                "Click anywhere or press ESC to go back",
            ]
            for i, line in enumerate(lines):
                text = self.body_font.render(line, True, self.colors["white"])
                screen.blit(text, (panel.left + 35, panel.top + 108 + i * 45))
            return
        title = pygame.font.SysFont("arial", 47, bold=True).render("PAUSE", True, (255, 55, 70))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, panel.top + 47)))
        mouse = pygame.mouse.get_pos()
        for label, rect in options:
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(screen, (82, 66, 77) if hover else (43, 43, 53), rect, border_radius=10)
            if hover:
                pygame.draw.rect(screen, (220, 91, 101), rect, 2, border_radius=10)
            text = self.body_font.render(label, True, (255, 230, 235) if hover else self.colors["white"])
            screen.blit(text, text.get_rect(center=rect.center))
        hint = self.small_font.render("Click an option to select", True, self.colors["muted"])
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, panel.bottom - 22)))
