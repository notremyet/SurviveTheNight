
import pygame


class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

        self.font = pygame.font.SysFont("arial", 28)
        self.title_font = pygame.font.SysFont("arial", 50, bold=True)

        self.options = ["START GAME", "HOW TO PLAY", "QUIT"]
        self.selected = 0

    def draw(self):
        self.screen.fill((25, 25, 35))

        title = self.title_font.render(
            "SURVIVE THE NIGHT", True, (255, 255, 255)
        )
        self.screen.blit(
            title,
            title.get_rect(center=(self.width // 2, 180))
        )

        for i, option in enumerate(self.options):
            color = (220, 60, 70) if i == self.selected else (180, 180, 180)

            text = self.font.render(option, True, color)
            rect = text.get_rect(
                center=(self.width // 2, 350 + i * 80)
            )
            self.screen.blit(text, rect)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.select_option()

        if event.type == pygame.MOUSEMOTION:
            for i, option in enumerate(self.options):
                text = self.font.render(option, True, (255, 255, 255))
                rect = text.get_rect(
                    center=(self.width // 2, 350 + i * 80)
                )
                if rect.collidepoint(event.pos):
                    self.selected = i

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for i, option in enumerate(self.options):
                    text = self.font.render(option, True, (255, 255, 255))
                    rect = text.get_rect(
                        center=(self.width // 2, 350 + i * 80)
                    )
                    if rect.collidepoint(event.pos):
                        self.selected = i
                        return self.select_option()

        return None

    def select_option(self):
        if self.selected == 0:
            return "start"

        if self.selected == 1:
            return "how_to_play"

        if self.selected == 2:
            return "quit"
