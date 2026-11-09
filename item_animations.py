"""Optional item-use animations; no changes to teammate-owned ui.py/player.py.

Drop transparent frame_01.png, frame_02.png, ... into:
    assets/item_animations/medkit/
    assets/item_animations/place_noise_maker/
    assets/item_animations/activate_remote/

If a folder has no animation frames, the existing player action sprite is
shown as a one-frame fallback for compatibility. All frames are optional.
"""
from pathlib import Path
import pygame


class ItemUseAnimation:
    DURATION_MS = 720
    FRAME_MS = 120
    FALLBACK_PLAYER_SPRITES = {
        "medkit": "player_5.png",
        "place_noise_maker": "player_4.png",
        "activate_remote": "player_4.png",  # Replace with dedicated remote frames later.
    }

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.frames = {}
        self.active_name = None
        self.started_at = 0

    def _load_frames(self, name):
        if name in self.frames:
            return self.frames[name]
        folder = self.base_dir / "assets" / "item_animations" / name
        paths = sorted(folder.glob("frame_*.png")) if folder.is_dir() else []
        if not paths:
            fallback = self.FALLBACK_PLAYER_SPRITES.get(name)
            if fallback:
                path = self.base_dir / "assets" / "characters" / "player" / fallback
                if path.is_file():
                    paths = [path]
        loaded = []
        for path in paths:
            try:
                loaded.append(pygame.image.load(str(path)).convert_alpha())
            except (pygame.error, OSError) as exc:
                print(f"Cannot load item-use animation frame {path}: {exc}")
        self.frames[name] = loaded
        return loaded

    def start(self, name):
        """Call only AFTER the item was successfully used."""
        self.active_name = name
        self.started_at = pygame.time.get_ticks()
        self._load_frames(name)

    def reset(self):
        self.active_name = None

    def draw(self, surface):
        """Draw over the inventory modal, so the animation is clearly visible."""
        if self.active_name is None:
            return
        elapsed = pygame.time.get_ticks() - self.started_at
        if elapsed >= self.DURATION_MS:
            self.active_name = None
            return
        frames = self._load_frames(self.active_name)
        if not frames:
            return  # No image yet: game still runs normally.
        index = min(len(frames) - 1, elapsed // self.FRAME_MS)
        image = frames[index]
        w, h = surface.get_size()
        # Bottom-right within the game window; deliberately separate from team's HUD.
        max_dim = 104
        factor = min(max_dim / max(1, image.get_width()), max_dim / max(1, image.get_height()))
        scaled = pygame.transform.smoothscale(image, (max(1, round(image.get_width() * factor)),
                                                         max(1, round(image.get_height() * factor))))
        surface.blit(scaled, scaled.get_rect(center=(w // 2 + 225, h // 2 - 145)))
