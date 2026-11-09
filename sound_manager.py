"""Audio manager for Survive The Night."""
from pathlib import Path
import pygame


class SoundManager:
    def __init__(self):
        self.base = Path(__file__).resolve().parent / "assets" / "sounds"
        self.ready = False
        self.effects = {}
        self.music_state = None
        self._music_paused = None
        self.outcome = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.ready = True
            names = ("walk", "run", "chest", "wardrobe", "zombie_step",
                     "zombie_attack", "zombie_detect", "hurt", "noise_maker",
                     "medkit", "item_pickup", "door_lock", "door_unlock",
                     "event", "win", "lose")
            for key in names:
                filename = "player_hurt.wav" if key == "hurt" else key + ".wav"
                path = self.base / filename
                if path.is_file():
                    try:
                        self.effects[key] = pygame.mixer.Sound(str(path))
                    except (pygame.error, OSError) as error:
                        print(f"Sound effect error ({path.name}): {error}")
            for key, vol in (("walk", .22), ("run", .36), ("zombie_step", .28),
                             ("hurt", .65), ("zombie_attack", .65)):
                if key in self.effects:
                    self.effects[key].set_volume(vol)
        except (pygame.error, OSError) as error:
            print("Audio unavailable:", error)

    def play(self, key):
        if self.ready and key in self.effects:
            self.effects[key].play()

    def reset(self):
        self.outcome = None
        self.music_state = None
        self._music_paused = None
        if self.ready:
            pygame.mixer.music.stop()

    def sync(self, screen, paused, status):
        if not self.ready:
            return
        if status in ("won", "lost") and self.outcome != status:
            self.outcome = status
            self.play("win" if status == "won" else "lose")
        target = "game" if screen == "game" and status == "playing" else "menu"
        if status in ("won", "lost"):
            target = "silent"
        if target != self.music_state:
            self.music_state = target
            self._music_paused = None  # New track has no previous pause state.
            pygame.mixer.music.stop()
            if target != "silent":
                path = self.base / ("ambience.ogg" if target == "game" else "menu_music.ogg")
                if path.is_file():
                    try:
                        pygame.mixer.music.load(str(path))
                        pygame.mixer.music.set_volume(.25 if target == "game" else .22)
                        pygame.mixer.music.play(-1)
                    except (pygame.error, OSError) as error:
                        print(f"Music error ({path.name}): {error}")
                else:
                    print(f"Music file not found: {path}")
        # Do not call SDL_mixer pause/unpause every game frame.
        # Only change music state when the user actually toggles pause,
        # or when music has just switched to another track.
        if target == "silent":
            self._music_paused = None
        elif self._music_paused is None:
            if paused:
                pygame.mixer.music.pause()
            self._music_paused = bool(paused)
        elif bool(paused) != self._music_paused:
            if paused:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
            self._music_paused = bool(paused)
