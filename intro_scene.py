"""Visual novel intro for Survive The Night.

Images: assets/intro/1.png ... 3.png
Music: assets/sounds/introsound.mp3
"""
from pathlib import Path
import pygame

BASE = Path(__file__).resolve().parent

SCENES = [
    ("A young boy woke up in a strange bedroom with no memory "
     "of how he got there. The house was unusually quiet, "
     "making him feel that something was wrong."),
    ("He looked out the window and saw people wandering "
     "through the dark streets. As he watched them move, "
     "he realized they were zombies and the world had changed."),
    ("Suddenly, he heard strange footsteps coming from another "
     "room. Realizing he was not alone in the house, "
     "he knew he had to find a way out before it was too late."),
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
        self._line_height = 25

    def _box(self):
        w, h = self.size
        box_h = min(165, max(118, int(h * 0.17)))
        return pygame.Rect(19, h - box_h - 18, w - 38, box_h)

    def _wrap(self, text, max_width):
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
        box = self._box()
        text_width = box.width - 56
        available_height = box.height - 60
        for font_size in (23, 22, 21, 20, 19, 18, 17, 16):
            self.font = pygame.font.SysFont('arial', font_size)
            lines = self._wrap(SCENES[self.index], text_width)
            line_height = font_size + 5
            if len(lines) * line_height <= available_height:
                self._wrapped = lines
                self._line_height = line_height
                return
        self._wrapped = self._wrap(SCENES[self.index], text_width)
        self._line_height = 21

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
        image = self.images[self.index] if self.images else None
        if image is None:
            screen.fill((21, 20, 30))
        else:
            screen.blit(image, (0, 0))

        box = self._box()
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((12, 13, 24, 229))
        screen.blit(panel, box.topleft)
        pygame.draw.rect(screen, (160, 152, 175), box, 2, border_radius=12)

        remaining = int(self.chars_visible)
        x = box.left + 28
        y = box.top + 14
        for line in self._wrapped:
            if remaining <= 0:
                break
            portion = line[:remaining]
            rendered = self.font.render(portion, True, (247, 244, 247))
            screen.blit(rendered, (x, y))
            remaining -= len(line)
            if remaining > 0:
                remaining -= 1
            y += self._line_height

        hover = self.skip_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (157, 53, 58) if hover else (50, 49, 64), self.skip_rect, border_radius=9)
        pygame.draw.rect(screen, (235, 225, 231), self.skip_rect, 2, border_radius=9)
        skip = self.ui_font.render('SKIP', True, (255, 255, 255))
        screen.blit(skip, skip.get_rect(center=self.skip_rect.center))

        page = self.ui_font.render(f'{self.index + 1} / 3', True, (220, 217, 226))
        screen.blit(page, (box.left + 28, box.bottom - 30))
        if self._complete():
            hint_text = 'CLICK TO START' if self.index == 2 else 'CLICK TO CONTINUE'
            hint = self.ui_font.render(hint_text + '  >', True, (235, 230, 238))
            screen.blit(hint, hint.get_rect(bottomright=(box.right - 25, box.bottom - 12)))
