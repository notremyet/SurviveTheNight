"""Visual novel intro for Survive The Night.

Drop this file beside main.py. Images: assets/intro/1.png ... 3.png
Music: assets/sounds/introsound.mp3
"""
from pathlib import Path
import pygame

BASE = Path(__file__).resolve().parent

SCENES = [
    (
        "A young boy slowly opened his eyes, only to find himself lying in a bedroom he had never seen before. "
        "He tried to remember how he had arrived at this unfamiliar house, but his mind was completely blank. "
        "The silence surrounding him felt strangely unnatural, as though the entire world had suddenly stopped moving. "
        "Confused and uneasy, he slowly sat up on the bed, unaware of the nightmare waiting beyond the walls."
    ),
    (
        "Hoping to find someone who could explain what was happening, he cautiously turned his attention toward the bedroom window. "
        "Outside, several figures wandered aimlessly through the darkness, moving in ways that no ordinary human ever would. "
        "As he looked more closely, a terrifying realization began to settle in: the people outside were no longer human. "
        "The familiar world he remembered had transformed into something completely unrecognizable."
    ),
    (
        "Before he could fully understand the horrifying scene outside, an unexpected sound suddenly broke the silence around him. "
        "Slow, heavy footsteps echoed through the hallway, growing louder as something moved somewhere inside the house. "
        "His heart began racing when he realized that he was not alone, and whatever was approaching might already know he was there. "
        "There was no time to hesitate; he needed to search for a way out of this unfamiliar house before it was too late."
    ),
]


class IntroScene:
    def __init__(self, size):
        self.size = size
        self.active = False
        self.index = 0
        self.images = []
        self.chars_visible = 0.0
        self.chars_per_second = 48.0
        self.last_tick = 0
        self.font = None
        self.ui_font = None
        self.skip_rect = pygame.Rect(size[0] - 125, 22, 102, 42)
        self._music_started = False
        self._wrapped = []
        self._line_height = 28

    def _wrap(self, text, max_width):
        """Wrap at word boundaries based on actual font measurements."""
        result = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            if not words:
                result.append('')
                continue
            current = words[0]
            for word in words[1:]:
                candidate = current + ' ' + word
                if self.font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    result.append(current)
                    current = word
            result.append(current)
        return result

    def _layout_scene(self):
        w, h = self.size
        box_h = min(330, max(235, int(h * 0.34)))
        box = pygame.Rect(19, h - box_h - 18, w - 38, box_h)
        text_width = box.width - 56
        available_height = box.height - 105  # leave room for page and continue prompt
        # Choose the largest legible font that fits the current scene vertically.
        for font_size in (23, 22, 21, 20, 19, 18):
            self.font = pygame.font.SysFont('arial', font_size)
            lines = self._wrap(SCENES[self.index], text_width)
            line_height = font_size + 8
            if len(lines) * line_height <= available_height:
                self._wrapped = lines
                self._line_height = line_height
                return
        self._wrapped = self._wrap(SCENES[self.index], text_width)
        self._line_height = 25

    def start(self):
        self.index = 0
        self.active = True
        self.chars_visible = 0.0
        self.last_tick = pygame.time.get_ticks()
        self.images = []
        for i in range(1, 4):
            path = BASE / 'assets' / 'intro' / f'{i}.png'
            try:
                img = pygame.image.load(str(path)).convert()
                self.images.append(pygame.transform.smoothscale(img, self.size))
            except (pygame.error, OSError) as exc:
                print(f'Intro image unavailable: {path}: {exc}')
                self.images.append(None)
        self.ui_font = pygame.font.SysFont('arial', 19, bold=True)
        self._layout_scene()
        self._music_started = False
        music = BASE / 'assets' / 'sounds' / 'introsound.mp3'
        if music.exists():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.stop()
                pygame.mixer.music.load(str(music))
                pygame.mixer.music.set_volume(0.38)
                pygame.mixer.music.play(-1)
                self._music_started = True
            except (pygame.error, OSError) as exc:
                print('Intro music unavailable:', exc)
        else:
            print('Intro music not found:', music)

    def _finish(self):
        self.active = False
        if self._music_started and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self._music_started = False

    def _text(self):
        return SCENES[self.index]

    def _complete(self):
        return self.chars_visible >= len(self._text())

    def next(self):
        if not self._complete():
            self.chars_visible = float(len(self._text()))
            return
        self.index += 1
        if self.index >= len(SCENES):
            self._finish()
        else:
            self.chars_visible = 0.0
            self.last_tick = pygame.time.get_ticks()
            self._layout_scene()

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.skip_rect.collidepoint(event.pos):
                self._finish()
            else:
                self.next()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._finish()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.next()

    def _advance_typewriter(self):
        now = pygame.time.get_ticks()
        elapsed = min((now - self.last_tick) / 1000.0, 0.15)
        self.last_tick = now
        self.chars_visible = min(float(len(self._text())), self.chars_visible + elapsed * self.chars_per_second)

    def draw(self, screen):
        if not self.active:
            return
        self._advance_typewriter()
        w, h = self.size
        image = self.images[self.index] if self.images else None
        if image is None:
            screen.fill((21, 20, 30))
        else:
            screen.blit(image, (0, 0))

        box_h = min(330, max(235, int(h * 0.34)))
        box = pygame.Rect(19, h - box_h - 18, w - 38, box_h)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((12, 13, 24, 229))
        screen.blit(panel, box.topleft)
        pygame.draw.rect(screen, (160, 152, 175), box, 2, border_radius=12)

        # Reveal the original text one character at a time, while displaying
        # pre-wrapped lines without making words jump during typing.
        remaining = int(self.chars_visible)
        x = box.left + 28
        y = box.top + 22
        for line in self._wrapped:
            if remaining <= 0:
                break
            portion = line[:remaining]
            rendered = self.font.render(portion, True, (247, 244, 247))
            screen.blit(rendered, (x, y))
            remaining -= len(line)
            if remaining > 0:
                remaining -= 1  # space between wrapped lines
            y += self._line_height

        hover = self.skip_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (157, 53, 58) if hover else (50, 49, 64), self.skip_rect, border_radius=9)
        pygame.draw.rect(screen, (235, 225, 231), self.skip_rect, 2, border_radius=9)
        skip = self.ui_font.render('SKIP', True, (255, 255, 255))
        screen.blit(skip, skip.get_rect(center=self.skip_rect.center))

        page = self.ui_font.render(f'{self.index + 1} / 3', True, (220, 217, 226))
        screen.blit(page, (box.left + 28, box.bottom - 37))
        if self._complete():
            hint_text = 'CLICK TO START' if self.index == 2 else 'CLICK TO CONTINUE'
            hint = self.ui_font.render(hint_text + '  >', True, (235, 230, 238))
            screen.blit(hint, hint.get_rect(bottomright=(box.right - 25, box.bottom - 17)))
