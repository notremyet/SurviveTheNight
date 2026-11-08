import pygame
from pathlib import Path
from settings import COLS, ROWS, cell_to_xy, xy_to_cell

# Image names in assets/characters/player/
SPRITE_NUMBERS = {
    "right": {"hurt": 7, "run": 8, "walk": 9, "idle": 10},
    "down":  {"hurt": 11, "run": 12, "walk": 13, "idle": 14},
    "left":  {"hurt": 15, "run": 16, "walk": 17, "idle": 18},
    "up":    {"hurt": 19, "run": 20, "walk": 21, "idle": 22},
}
SPECIAL_NUMBERS = {"hide": 3, "noise": 4, "medkit": 5, "search": 6}
INJURED_NUMBERS = {"right": 24, "down": 25, "left": 26, "up": 27}

class Player:
    def __init__(self, start_cell="B2"):
        self.cell = start_cell
        self.color = (70, 180, 255)
        self.max_hp = 3
        self.hp = self.max_hp
        self.invulnerable_until = 0
        self.hurt_flash_until = 0
        self.radius = 16
        self.direction = "down"
        self.action = "idle"
        self.action_until = 0
        self.sprite_size = (66, 78)
        self.sprites = {}
        self._load_sprites()
        self.route = []
        self.visual_position = None
        self.segment_start = None
        self.segment_target = None
        self.segment_progress = 0.0
        self.segment_duration = 0.18
        self.moving_style = "walk"

    def _load_sprites(self):
        folder = Path(__file__).resolve().parent / "assets" / "characters" / "player"
        numbers = set(SPECIAL_NUMBERS.values()) | set(INJURED_NUMBERS.values())
        for actions in SPRITE_NUMBERS.values():
            numbers.update(actions.values())
        for number in numbers:
            path = folder / f"player_{number}.png"
            if not path.exists():
                print(f"Player sprite missing: {path}")
                continue
            img = pygame.image.load(str(path)).convert_alpha()
            if number == SPECIAL_NUMBERS["search"]:
                # Search artwork includes a chest and is wider than other poses.
                # Keep its original aspect ratio AND fit inside one 90x90 tile.
                max_width, max_height = 84, 78
                original_width, original_height = img.get_size()
                scale = min(max_width / original_width,
                            max_height / original_height)
                fitted_size = (max(1, round(original_width * scale)),
                               max(1, round(original_height * scale)))
                self.sprites[number] = pygame.transform.smoothscale(img, fitted_size)
            else:
                self.sprites[number] = pygame.transform.smoothscale(img, self.sprite_size)
          
    def move(self, dx, dy, board, furniture=None):
        x, y = cell_to_xy(self.cell)
        nx, ny = x + dx, y + dy
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            return False
        next_cell = xy_to_cell((nx, ny))
        if not board.can_step(self.cell, next_cell):
            return False
        if furniture is not None and furniture.is_blocked(next_cell):
            return False
        self.cell = next_cell
        return True

    def handle_key(self, key, board, furniture=None, running=None):
        """Walk one cell, or run up to two cells in a straight line.

        Returns True only if the player actually moved. Running cannot
        jump over a wall, locked door, or blocking furniture.
        """
        directions = {
            pygame.K_w: (0, -1, "up"), pygame.K_UP: (0, -1, "up"),
            pygame.K_s: (0, 1, "down"), pygame.K_DOWN: (0, 1, "down"),
            pygame.K_a: (-1, 0, "left"), pygame.K_LEFT: (-1, 0, "left"),
            pygame.K_d: (1, 0, "right"), pygame.K_RIGHT: (1, 0, "right"),
        }
        if key not in directions:
            return False
        dx, dy, self.direction = directions[key]
        if running is None:
            running = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        steps = 2 if running else 1
        moved = False
        for _ in range(steps):
            if not self.move(dx, dy, board, furniture):
                break
            moved = True
        if moved:
            self.action = "run" if running else "walk"
            self.action_until = pygame.time.get_ticks() + 230
        return moved

    def start_route(self, path, style="walk"):
        """Animate a prevalidated path; each click costs one action."""
        if self.route or self.segment_target is not None or len(path) < 2 or path[0] != self.cell:
            return False
        self.route = list(path[1:])
        self.visual_position = tuple(float(v) for v in cell_to_xy(self.cell))
        self.moving_style = style
        self.segment_duration = 0.13 if style == "run" else 0.23
        self.action = style
        self.action_until = 0
        self._begin_segment()
        return True

    def _begin_segment(self):
        if not self.route:
            self.segment_target = None
            self.segment_start = None
            self.action = "idle"
            self.action_until = 0
            return
        target = self.route.pop(0)
        self.segment_start = self.visual_position
        self.segment_target = target
        tx, ty = cell_to_xy(target)
        sx, sy = self.segment_start
        if tx > sx: self.direction = "right"
        elif tx < sx: self.direction = "left"
        elif ty > sy: self.direction = "down"
        elif ty < sy: self.direction = "up"
        self.segment_progress = 0.0

    @property
    def is_moving(self):
        return self.segment_target is not None

    def update(self, dt):
        if not self.is_moving:
            return
        self.segment_progress = min(1.0, self.segment_progress + dt / self.segment_duration)
        tx, ty = cell_to_xy(self.segment_target)
        sx, sy = self.segment_start
        t = self.segment_progress
        self.visual_position = (sx + (tx - sx) * t, sy + (ty - sy) * t)
        if t >= 1.0:
            self.cell = self.segment_target
            self.visual_position = (float(tx), float(ty))
            self._begin_segment()

    @property
    def is_dead(self):
        return self.hp <= 0

    def take_damage(self, amount=1, invulnerability_ms=700):
        """Call ONCE for a successful zombie attack. Returns actual HP lost."""
        now = pygame.time.get_ticks()
        if self.is_dead or now < self.invulnerable_until:
            return 0
        lost = min(self.hp, max(0, int(amount)))
        if not lost:
            return 0
        self.hp -= lost
        self.invulnerable_until = now + invulnerability_ms
        self.hurt_flash_until = now + 550
        self.play_action("hurt", duration_ms=550)
        return lost

    def heal(self, amount=1):
        """Free-action Medkit hook; caller handles inventory."""
        if self.is_dead:
            return 0
        gained = min(self.max_hp - self.hp, max(0, int(amount)))
        self.hp += gained
        if gained:
            self.play_action("medkit", duration_ms=550)
        return gained

    def play_action(self, action, duration_ms=500):
        # For future Search/Hide/Medkit/Noise Maker integration.
        if action not in SPECIAL_NUMBERS and action != "hurt":
            return False
        self.action = action
        self.action_until = pygame.time.get_ticks() + duration_ms
        return True

    def draw(self, surface, get_cell_center):
        if not self.is_moving and pygame.time.get_ticks() >= self.action_until:
            self.action = "idle"
        if self.action in SPECIAL_NUMBERS:
            number = SPECIAL_NUMBERS[self.action]
        elif self.action == "hurt":
            number = SPRITE_NUMBERS[self.direction]["hurt"]
        else:
            number = SPRITE_NUMBERS[self.direction].get(self.action,
                                                        SPRITE_NUMBERS[self.direction]["idle"])
        if self.is_moving and self.visual_position is not None:
            # Render at fractional tile coordinates for smooth travel.
            base_x, base_y = get_cell_center("A1")
            tile_x = get_cell_center("B1")[0] - base_x
            tile_y = get_cell_center("A2")[1] - base_y
            px = round(base_x + self.visual_position[0] * tile_x)
            py = round(base_y + self.visual_position[1] * tile_y)
        else:
            px, py = get_cell_center(self.cell)
        # Flash briefly after a hit, without changing the existing sprite set.
        if pygame.time.get_ticks() < self.hurt_flash_until and (pygame.time.get_ticks() // 90) % 2:
            return
        sprite = self.sprites.get(number)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=(px, py)))
        else:
            pygame.draw.circle(surface, self.color, (px, py), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (px, py), self.radius, 2)
