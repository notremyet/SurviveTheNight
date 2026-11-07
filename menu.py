
from PIL import Image, ImageSequence
import pygame
import os


class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

        # Load animated GIF background
        gif = Image.open("assets/pixelmenu.gif")
        self.bg_frames = []

        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert("RGB")
            frame = frame.resize((self.width, self.height))

            surface = pygame.image.fromstring(
                frame.tobytes(), frame.size, "RGB"
            )
            self.bg_frames.append(surface)

        self.frame_index = 0
        self.last_frame_time = pygame.time.get_ticks()
        self.frame_delay = 180

        # Load pixel font if available
        font_path = "assets/PressStart2P.ttf"

        if os.path.exists(font_path):
            self.title_font = pygame.font.Font(font_path, 42)
            self.button_font = pygame.font.Font(font_path, 14)
        else:
            self.title_font = pygame.font.SysFont(
                "monospace", 38, bold=True
            )
            self.button_font = pygame.font.SysFont(
                "monospace", 23, bold=True
            )

        self.small_font = pygame.font.Font(font_path, 13)

        # Menu buttons
        self.options = ["start", "how_to_play", "quit"]
        self.labels = [
            "START GAME",
            "HOW TO PLAY",
            "QUIT"
        ]

        self.selected = 0

        self.buttons = []

        button_width = 320
        button_height = 65
        center_x = self.width // 2
        start_y = 330

        for i in range(3):
            rect = pygame.Rect(
                center_x - button_width // 2,
                start_y + i * 85,
                button_width,
                button_height
            )
            self.buttons.append(rect)

    def draw_background(self):
        now = pygame.time.get_ticks()

        if now - self.last_frame_time >= self.frame_delay:
            self.frame_index = (
                self.frame_index + 1
            ) % len(self.bg_frames)

            self.last_frame_time = now

        self.screen.blit(
            self.bg_frames[self.frame_index], (0, 0)
        )

    def draw(self):
        # Draw animated background first
        self.draw_background()

        # Game title
        title = self.title_font.render(
            "SURVIVE THE NIGHT",
            True,
            (245, 245, 245)
        )

        title_rect = title.get_rect(
            center=(self.width // 2, 180)
        )

        self.screen.blit(title, title_rect)

        by_text = self.small_font.render(
            "by LOL",
            True,
            (180, 180, 190)
        )

        by_rect = by_text.get_rect(
            center=(self.width // 2, title_rect.bottom + 65)
        )

        self.screen.blit(by_text, by_rect)

        # Draw menu buttons
        for i, rect in enumerate(self.buttons):

            selected = (i == self.selected)

            if selected:
                text_color = (235, 65, 75)
                border_color = (235, 65, 75)
                background = (35, 20, 30)
            else:
                text_color = (205, 205, 210)
                border_color = (100, 100, 115)
                background = (25, 25, 38)

            pygame.draw.rect(
                self.screen,
                background,
                rect,
                border_radius=5
            )

            pygame.draw.rect(
                self.screen,
                border_color,
                rect,
                width=3,
                border_radius=5
            )

            text = self.button_font.render(
                self.labels[i],
                True,
                text_color
            )

            text_rect = text.get_rect(
                center=rect.center
            )

            self.screen.blit(text, text_rect)

        # Keyboard hint
        hint = self.small_font.render(
            "Use UP / DOWN and ENTER to select",
            True,
            (170, 170, 180)
        )

        self.screen.blit(
            hint,
            hint.get_rect(
                center=(self.width // 2, 700)
            )
        )

    def handle_event(self, event):

        if event.type == pygame.KEYDOWN:

            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (
                    self.selected - 1
                ) % len(self.options)

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (
                    self.selected + 1
                ) % len(self.options)

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.options[self.selected]

        elif event.type == pygame.MOUSEMOTION:

            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    self.selected = i

        elif event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:
                for i, rect in enumerate(self.buttons):
                    if rect.collidepoint(event.pos):
                        self.selected = i
                        return self.options[i]

        return None
