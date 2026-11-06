
import pygame


class HowToPlay:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

        self.title_font = pygame.font.SysFont("arial", 40, bold=True)
        self.font = pygame.font.SysFont("arial", 22)
        self.small_font = pygame.font.SysFont("arial", 18)

        self.instructions = [
            "OBJECTIVE",
            "Find the key and escape before time runs out.",
            "",
            "CONTROLS",
            "WASD / Arrow Keys : Move",
            "E : Interact with objects",
            "Shift + Movement : Run",
            "",
            "GAME RULES",
            "You have 3 HP and 2 Actions per round.",
            "Walking costs 1 Action.",
            "Running creates noise.",
            "The zombie investigates sounds and chases you.",
            "Survive until you reach the exit!"
        ]

    def draw(self):
        self.screen.fill((25, 25, 35))

        title = self.title_font.render(
            "HOW TO PLAY", True, (255, 255, 255)
        )
        self.screen.blit(
            title,
            title.get_rect(center=(self.width // 2, 100))
        )

        y = 180

        for line in self.instructions:
            color = (220, 60, 70) if line in [
                "OBJECTIVE", "CONTROLS", "GAME RULES"
            ] else (230, 230, 230)

            text = self.font.render(line, True, color)
            self.screen.blit(text, (100, y))
            y += 38

        back = self.small_font.render(
            "Press ESC or BACKSPACE to return",
            True, (180, 180, 180)
        )

        self.screen.blit(
            back,
            back.get_rect(
                center=(self.width // 2, self.height - 50)
            )
        )

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "back"

        return None
