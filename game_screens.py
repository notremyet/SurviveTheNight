import pygame
from pathlib import Path
from PIL import Image, ImageSequence

class GameEndScreen:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

        # Load animated WIN background
        gif_path = Path(__file__).resolve().parent / "assets" / "win.gif"

        self.win_bg_frames = []
        gif = Image.open(gif_path)

        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert("RGB")
            frame = frame.resize((self.width, self.height))

            surface = pygame.image.fromstring(
                frame.tobytes(),
                frame.size,
                "RGB"
            )
            self.win_bg_frames.append(surface)

        self.win_frame_delay = 300
        self.win_animation_start = pygame.time.get_ticks()

        # Load animated GAME OVER background
        lose_path = Path(__file__).resolve().parent / "assets" / "lose.gif"

        self.lose_bg_frames = []
        lose_gif = Image.open(lose_path)

        for frame in ImageSequence.Iterator(lose_gif):
            frame = frame.convert("RGB")
            frame = frame.resize((self.width, self.height))

            surface = pygame.image.fromstring(
                frame.tobytes(), frame.size, "RGB"
            )
            self.lose_bg_frames.append(surface)

        self.lose_frame_delay = 350
        self.lose_animation_start = pygame.time.get_ticks()

        font_path = "assets/PressStart2P.ttf"

        self.title_font = pygame.font.Font(font_path, 40)
        self.font = pygame.font.Font(font_path, 18)
        self.small_font = pygame.font.Font(font_path, 12)

        self.status = "won"
        self.reason = ""

        self.buttons = {
            "menu": pygame.Rect(
                self.width // 2 - 140, 440, 280, 55
            ),
            "quit": pygame.Rect(
                self.width // 2 - 140, 515, 280, 55
            )
        }

        self.selected = 0
        self.options = ["menu", "quit"]

    def set_result(self, status, reason=""):
        if status not in ("won", "lost"):
            raise ValueError("Status must be 'won' or 'lost'")

        self.status = status
        self.reason = reason
        self.win_animation_start = pygame.time.get_ticks()
        self.lose_animation_start = pygame.time.get_ticks()

    def draw(self):
        if self.status == "won" and self.win_bg_frames:
            elapsed = pygame.time.get_ticks() - self.win_animation_start
            index = (elapsed // self.win_frame_delay) % len(self.win_bg_frames)
            self.screen.blit(self.win_bg_frames[index], (0, 0))

        elif self.status == "lost" and self.lose_bg_frames:
            elapsed = pygame.time.get_ticks() - self.lose_animation_start
            index = (elapsed // self.lose_frame_delay) % len(self.lose_bg_frames)
            self.screen.blit(self.lose_bg_frames[index], (0, 0))

        else:
            self.screen.fill((20, 18, 28))

        if self.status == "won":
            title_text = "YOU SURVIVED!"
            title_color = (100, 210, 120)
            subtitle = "You escaped the house!"
        else:
            title_text = "GAME OVER"
            title_color = (220, 65, 70)
            subtitle = "You did not survive the night."

        title = self.title_font.render(
            title_text, True, title_color
        )
        self.screen.blit(
            title,
            title.get_rect(
                center=(self.width // 2, 190)
            )
        )

        subtitle_surface = self.font.render(
            subtitle, True, (230, 230, 230)
        )
        self.screen.blit(
            subtitle_surface,
            subtitle_surface.get_rect(
                center=(self.width // 2, 275)
            )
        )

        if self.reason:
            reason_surface = self.small_font.render(
                self.reason, True, (180, 180, 180)
            )
            self.screen.blit(
                reason_surface,
                reason_surface.get_rect(
                    center=(self.width // 2, 325)
                )
            )

        for i, option in enumerate(self.options):
            rect = self.buttons[option]
            selected = i == self.selected

            color = (170, 45, 55) if selected else (45, 42, 52)
            border = (255, 255, 255) if selected else (110, 100, 110)

            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, border, rect, 2)

            label = "MAIN MENU" if option == "menu" else "QUIT"
            text = self.font.render(label, True, (255, 255, 255))

            self.screen.blit(
                text, text.get_rect(center=rect.center)
            )

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % 2

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % 2

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.select_option()

        elif event.type == pygame.MOUSEMOTION:
            for i, option in enumerate(self.options):
                if self.buttons[option].collidepoint(event.pos):
                    self.selected = i

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for i, option in enumerate(self.options):
                    if self.buttons[option].collidepoint(event.pos):
                        self.selected = i
                        return self.select_option()

        return None

    def select_option(self):
        if self.options[self.selected] == "menu":
            return "menu"

        return "quit"
