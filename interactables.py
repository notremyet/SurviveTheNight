from dataclasses import dataclass
from pathlib import Path
import pygame
from settings import cell_to_xy

WARDROBE_CELLS = ("D2", "A5", "D7")
CHEST_CELLS = ("A2", "G1", "D5", "F7")

@dataclass
class Interactable:
    kind: str
    cell: str
    opened: bool = False

class InteractableManager:
    def __init__(self):
        self.items = ([Interactable("wardrobe", cell) for cell in WARDROBE_CELLS]
                      + [Interactable("chest", cell) for cell in CHEST_CELLS])
        self.by_cell = {obj.cell: obj for obj in self.items}
        self.hidden_in = None
        self.message = "Stand on a chest or wardrobe and press E"
        self.images = {}
        asset_dir = Path(__file__).resolve().parent / "assets" / "interactables"
        for kind in ("wardrobe", "chest"):
            for state in ("open", "closed"):
                path = asset_dir / f"{kind}_{state}.png"
                if not path.exists():
                    raise FileNotFoundError(f"Missing interaction sprite: {path}")
                sprite = pygame.image.load(str(path)).convert_alpha()
                visible = sprite.get_bounding_rect(min_alpha=10)
                if visible.width and visible.height:
                    sprite = sprite.subsurface(visible).copy()
                self.images[(kind, state)] = sprite

    def is_blocked(self, cell):
        # Interactable tiles must be walkable so players can stand on them.
        return False

    def interact(self, player_cell):
        # While hidden, E closes the wardrobe and reveals the player.
        if self.hidden_in is not None:
            obj = self.by_cell[self.hidden_in]
            obj.opened = False
            self.hidden_in = None
            self.message = "Left wardrobe"
            return "leave"

        obj = self.by_cell.get(player_cell)
        if obj is None:
            self.message = "Stand on an object to interact"
            return None

        if obj.kind == "wardrobe":
            obj.opened = True
            self.hidden_in = obj.cell
            self.message = "Hiding in wardrobe - press E to leave"
            return "hide"

        # A chest can only be opened once; it stays open permanently.
        if obj.opened:
            self.message = "Chest already opened"
            return "chest_already_open"
        obj.opened = True
        self.message = "Chest opened - loot system can be added later"
        return "chest_open"

    def draw(self, surface, map_x, map_y, tile_width=90, tile_height=90):
        for obj in self.items:
            x, y = cell_to_xy(obj.cell)
            cx = map_x + (x + 0.5) * tile_width
            cy = map_y + (y + 0.5) * tile_height
            sprite = self.images[(obj.kind, "open" if obj.opened else "closed")]
            factor = 0.78 if obj.kind == "wardrobe" else 0.62
            max_w, max_h = tile_width * factor, tile_height * factor
            ratio = min(max_w / sprite.get_width(), max_h / sprite.get_height())
            size = (max(1, round(sprite.get_width() * ratio)),
                    max(1, round(sprite.get_height() * ratio)))
            scaled = pygame.transform.smoothscale(sprite, size)
            surface.blit(scaled, scaled.get_rect(center=(round(cx), round(cy))))
