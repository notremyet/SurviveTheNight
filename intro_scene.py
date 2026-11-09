
from pathlib import Path
import pygame

SCENES = [
    ("THE AWAKENING", [
        "A young boy slowly opened his eyes in an unfamiliar bedroom.",
        "He couldn't remember how he got there.",
        "The house was silent, and everything felt strangely unfamiliar.",
        "Something was terribly wrong."
    ]),
    ("THE WORLD OUTSIDE", [
        "He turned toward the window, hoping to find someone outside.",
        "But the streets were filled with people wandering aimlessly.",
        "Their movements were unnatural, their faces lifeless.",
        "The world he once knew had become a nightmare."
    ]),
    ("SOMETHING INSIDE", [
        "Still confused, he suddenly heard a strange noise.",
        "Slow, heavy footsteps echoed from another room.",
        "He realized he was not alone inside the house.",
        "He had to find a way out before it was too late."
    ]),
]

class IntroScene:
    def __init__(self, size):
        self.size = size
        self.active = False
        self.index = 0
        self.images = []
        self.title_font = None
        self.body_font = None
        self.small_font = None
        self.skip_rect = pygame.Rect(size[0] - 125, 22, 102, 42)
        self.next_rect = pygame.Rect(size[0] - 145, size[1] - 80, 115, 45)

    def start(self):
        self.index = 0
        self.active = True
        self.images = []
        directory = Path(__file__).resolve().parent / "assets" / "intro"
        for i in range(1, 4):
            path = directory / f"{i}.png"
            try:
                image = pygame.image.load(str(path)).convert()
                self.images.append(pygame.transform.smoothscale(image, self.size))
            except (pygame.error, FileNotFoundError) as exc:
                print(f"Intro image unavailable: {path}: {exc}")
                self.images.append(None)
        self.title_font = pygame.font.SysFont("arial", 23, bold=True)
        self.body_font = pygame.font.SysFont("arial", 21)
        self.small_font = pygame.font.SysFont("arial", 19, bold=True)

    def next(self):
        self.index += 1
        if self.index >= len(SCENES):
            self.active = False

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.skip_rect.collidepoint(event.pos):
                self.active = False
            else:
                self.next()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.next()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.active = False

    def draw(self, screen):
        if not self.active:
            return
        w, h = self.size
        image = self.images[self.index] if self.images else None
        if image is None:
            screen.fill((21, 20, 30))
        else:
            screen.blit(image, (0, 0))
        # Semi-transparent VN dialogue window at bottom.
        box_h = 220
        panel = pygame.Surface((w - 38, box_h), pygame.SRCALPHA)
        panel.fill((12, 13, 24, 222))
        screen.blit(panel, (19, h - box_h - 18))
        pygame.draw.rect(screen, (160, 152, 175), (19, h - box_h - 18, w - 38, box_h), 2, border_radius=12)
        title, lines = SCENES[self.index]
        screen.blit(self.title_font.render(title, True, (255, 216, 116)), (42, h - box_h + 0))
        for j, line in enumerate(lines):
            screen.blit(self.body_font.render(line, True, (245, 242, 244)), (43, h - box_h + 43 + j * 30))
        hover = self.skip_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (157, 53, 58) if hover else (50, 49, 64), self.skip_rect, border_radius=9)
        pygame.draw.rect(screen, (235, 225, 231), self.skip_rect, 2, border_radius=9)
        label = self.small_font.render("SKIP", True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=self.skip_rect.center))
        prompt = "CLICK TO START" if self.index == 2 else "CLICK TO CONTINUE"
        hint = self.small_font.render(prompt + "  >", True, (255, 214, 115))
        screen.blit(hint, hint.get_rect(bottomright=(w - 43, h - 36)))
        page = self.small_font.render(f"{self.index + 1} / 3", True, (220, 217, 226))
        screen.blit(page, (45, h - 43))
