import pygame
from PIL import Image, ImageSequence
import os


class HowToPlay:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = screen.get_size()

        # Load a separate animated background for the How To Play screen
        gif_path = "assets/pixelhowtoplay.gif"
        gif = Image.open(gif_path)
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
        self.frame_delay = 220

        # Load the same pixel font used by the main menu
        font_path = "assets/PressStart2P.ttf"

        if os.path.exists(font_path):
            self.title_font = pygame.font.Font(font_path, 24)
            self.section_font = pygame.font.Font(font_path, 15)
            self.font = pygame.font.Font(font_path, 13)
            self.small_font = pygame.font.Font(font_path, 8)
        else:
            # Fallback fonts if PressStart2P.ttf has not been added yet
            self.title_font = pygame.font.SysFont("monospace", 32, bold=True)
            self.section_font = pygame.font.SysFont("monospace", 18, bold=True)
            self.font = pygame.font.SysFont("monospace", 16)
            self.small_font = pygame.font.SysFont("monospace", 13)

        self.instructions = [
            ("OBJECTIVE", [
                "Find the key and escape before time runs out."
            ]),
            ("CONTROLS", [
                "WASD / Arrow Keys : Move",
                "E : Interact with objects",
                "Shift + Movement : Run"
            ]),
            ("GAME RULES", [
                "You have 3 HP and 2 Actions per round.",
                "Walking costs 1 Action.",
                "Running creates noise.",
                "The zombie investigates sounds and chases you.",
                "Survive until you reach the exit!"
            ])
        ]

        self.colors = {
            "white": (245, 242, 235),
            "red": (235, 75, 80),
            "muted": (185, 185, 195)
        }

        # Dark transparent layer helps the text stay readable
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.overlay.fill((8, 8, 20, 70))

    def draw_background(self):
        now = pygame.time.get_ticks()

        if now - self.last_frame_time >= self.frame_delay:
            self.frame_index = (
                self.frame_index + 1
            ) % len(self.bg_frames)
            self.last_frame_time = now

        self.screen.blit(self.bg_frames[self.frame_index], (0, 0))
        self.screen.blit(self.overlay, (0, 0))

    def draw(self):
        self.draw_background()

        # Screen title
        title = self.title_font.render(
            "HOW TO PLAY", True, self.colors["white"]
        )
        title_rect = title.get_rect(
            center=(self.width // 2, 90)
        )
        self.screen.blit(title, title_rect)

        # Instruction sections
        x = 75
        y = 165

        for heading, lines in self.instructions:
            heading_surface = self.section_font.render(
                heading, True, self.colors["red"]
            )
            self.screen.blit(heading_surface, (x, y))
            y += 30

            for line in lines:
                line_surface = self.font.render(
                    line, True, self.colors["white"]
                )
                self.screen.blit(line_surface, (x, y))
                y += 30

            y += 22

        # Return hint
        back = self.small_font.render(
            "PRESS ESC OR BACKSPACE TO RETURN",
            True,
            self.colors["muted"]
        )
        self.screen.blit(
            back,
            back.get_rect(
                center=(self.width // 2, self.height - 45)
            )
        )

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "back"

        return None
