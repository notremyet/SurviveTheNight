import random
from dataclasses import dataclass
from pathlib import Path
import pygame

from settings import COLS, ROWS, cell_to_xy, xy_to_cell
from map import DOORS
COLORS = {
    "bed": (170, 70, 80),
    "car": (200, 50, 50),
    "sofa": (155, 105, 65),
    "fridge": (195, 210, 220),
    "plant": (65, 155, 80),
    "table": (155, 105, 65),
    "lamp": (245, 205, 100),
    "bookshelf": (125, 80, 50),
}

ROOM_CELLS = {
    "bedroom": [
        f"{c}{r}" for c in "ABCD" for r in (1, 2)
    ],
    "living": [
        f"{c}{r}" for c in "FGHIJ" for r in (1, 2)
    ],
    "kitchen": [
        f"{c}{r}" for c in "ABCD" for r in (3, 4, 5)
    ],
    "garage": [
        f"{c}{r}" for c in "ABCDE" for r in (6, 7)
    ],
}

ROOM_MAP = {
    cell: room
    for room, cells in ROOM_CELLS.items()
    for cell in cells
}


@dataclass
class Furniture:
    name: str
    cells: tuple
    blocking: bool
    color: tuple
    anchor: str = "center"


class FurnitureManager:

    def __init__(self, board, reserved=None, seed=None):
        self.board = board
        self.items = []
        self.blocked_cells = set()
        self.occupied_cells = set()
        self.reserved = set(reserved or [])
        self.rng = random.Random(seed)

        # Reserve door cells and their immediate approaches.
        self.door_cells = set()
        for a, b in DOORS:
            self.door_cells.update((a, b))

        self.reserved.update(self.door_cells)


        self.images = {}
        assets_path = (
            Path(__file__).resolve().parent
            / "assets"
            / "furniture"
        )

        for name in COLORS:
            image_path = assets_path / f"{name}.png"

            if image_path.exists():
                image = pygame.image.load(str(image_path)).convert_alpha()
                # Crop transparent padding so the actual object appears larger.
                visible = image.get_bounding_rect(min_alpha=10)
                if visible.width > 0 and visible.height > 0:
                    image = image.subsurface(visible).copy()
                self.images[name] = image
        self.generate()

    def can_place(self, cells):
        cells = tuple(cells)

        if not cells:
            return False

        for cell in cells:
            if not self.board.inside(cell):
                return False

            if cell in self.reserved:
                return False

            if cell in self.occupied_cells:
                return False

        return True

    def place(self, name, cells, blocking=True,
              anchor="center"):
        cells = tuple(cells)

        if not self.can_place(cells):
            return False

        item = Furniture(
            name=name,
            cells=cells,
            blocking=blocking,
            color=COLORS[name],
            anchor=anchor
        )

        self.items.append(item)
        self.occupied_cells.update(cells)

        if blocking:
            self.blocked_cells.update(cells)

        return True

    def shuffle_place(self, name, candidates,
                      blocking=True):
        candidates = list(candidates)
        self.rng.shuffle(candidates)

        for cells, anchor in candidates:
            if self.place(
                name, cells, blocking, anchor
            ):
                return True

        return False

    def room_wall_sides(self, cell, room):
        """
        Identify walls at the boundary of a room.
        Door openings are not considered walls.
        """
        allowed = set(ROOM_CELLS[room])
        x, y = cell_to_xy(cell)

        directions = {
            "top": (0, -1),
            "bottom": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }

        sides = []

        for side, (dx, dy) in directions.items():
            nx, ny = x + dx, y + dy

            if not (0 <= nx < COLS and
                    0 <= ny < ROWS):
                sides.append(side)
                continue

            other = xy_to_cell((nx, ny))

            if other not in allowed:
                if not self.board.can_step(
                    cell, other, ignore_locks=True
                ):
                    sides.append(side)

        return sides

    def wall_candidates(self, room):
        candidates = []

        for cell in ROOM_CELLS[room]:
            for side in self.room_wall_sides(
                cell, room
            ):
                candidates.append(((cell,), side))

        return candidates

    def place_bed(self):
        # Bed: one tile, against bedroom walls.
        return self.shuffle_place(
            "bed",
            self.wall_candidates("bedroom"),
            True
        )

    def place_fridge(self):
        # Fridge: one tile, against kitchen walls.
        return self.shuffle_place(
            "fridge",
            self.wall_candidates("kitchen"),
            True
        )

    def place_car(self):
        # Vertical cars must be at the left edge.
        # Horizontal cars stay on the left side,
        # away from the E6/F6 garage entrance.
        candidates = [
            (("A6", "A7"), "vertical"),
            (("A6", "B6"), "horizontal"),
            (("B6", "C6"), "horizontal"),
            (("A7", "B7"), "horizontal"),
            (("B7", "C7"), "horizontal"),
        ]

        return self.shuffle_place(
            "car", candidates, True
        )

    def place_sofa(self):
        allowed = set(ROOM_CELLS["living"])
        candidates = []

        for cell in sorted(allowed):
            x, y = cell_to_xy(cell)

            for dx, dy, orientation in (
                (1, 0, "horizontal"),
                (0, 1, "vertical")
            ):
                nx, ny = x + dx, y + dy

                if not (0 <= nx < COLS and
                        0 <= ny < ROWS):
                    continue

                other = xy_to_cell((nx, ny))

                if other not in allowed:
                    continue

                if not self.board.can_step(
                    cell, other, ignore_locks=True
                ):
                    continue

                first_sides = self.room_wall_sides(
                    cell, "living"
                )
                second_sides = self.room_wall_sides(
                    other, "living"
                )

                # Sofa must run along a wall.
                if orientation == "horizontal":
                    sides = ("top", "bottom")
                else:
                    sides = ("left", "right")

                for side in sides:
                    if (side in first_sides and
                            side in second_sides):
                        candidates.append(
                            ((cell, other), side)
                        )

        return self.shuffle_place(
            "sofa", candidates, True
        )

    def place_wall_decoration(self, name):
        candidates = []

        for room in ROOM_CELLS:
            candidates.extend(
                self.wall_candidates(room)
            )

        return self.shuffle_place(
            name, candidates, False
        )

    def place_table(self):
        # Prefer living room, then bedroom/kitchen.
        rooms = ["living", "bedroom", "kitchen"]

        for room in rooms:
            candidates = [
                ((cell,), "center")
                for cell in ROOM_CELLS[room]
            ]

            if self.shuffle_place(
                "table", candidates, False
            ):
                return True

        return False

    def place_plant(self):
        # Prefer corners or walls.
        candidates = []

        for room in ROOM_CELLS:
            for cell in ROOM_CELLS[room]:
                sides = self.room_wall_sides(
                    cell, room
                )

                if len(sides) >= 2:
                    candidates.append(
                        ((cell,), sides[0])
                    )

        if not candidates:
            for room in ROOM_CELLS:
                candidates.extend(
                    self.wall_candidates(room)
                )

        return self.shuffle_place(
            "plant", candidates, False
        )

    def paths_remain_open(self):
        """
        Check that all originally reachable cells
        remain reachable after blocking furniture.
        """
        available = {
            xy_to_cell((x, y))
            for y in range(ROWS)
            for x in range(COLS)
            if self.board.inside(
                xy_to_cell((x, y))
            )
        }

        walkable = available - self.blocked_cells

        if not walkable:
            return False

        # Check connectivity of each original
        # board component independently.
        unseen = set(available)

        while unseen:
            start = min(unseen)
            original = {start}
            queue = [start]
            unseen.remove(start)

            while queue:
                current = queue.pop()

                for neighbor in self.board.neighbors(
                    current, ignore_locks=True
                ):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        original.add(neighbor)
                        queue.append(neighbor)

            remaining = original & walkable

            if not remaining:
                continue

            visited = set()
            queue = [min(remaining)]
            visited.add(queue[0])

            while queue:
                current = queue.pop()

                for neighbor in self.board.neighbors(
                    current, ignore_locks=True
                ):
                    if (neighbor in remaining and
                            neighbor not in visited):
                        visited.add(neighbor)
                        queue.append(neighbor)

            if visited != remaining:
                return False

        return True

    
    def generate(self):
        # Fixed furniture placement; sofa, table, and car block movement.
        self.items.clear()
        self.blocked_cells.clear()
        self.occupied_cells.clear()

        self.place("bed", ("A1",), True)
        self.place("fridge", ("A3",), True)
        # Sofa against the upper living-room wall.
        self.place("sofa", ("H1", "I1"), True, "top")
        # Table in D3.
        self.place("table", ("D3",), True, "center")
        # Car centered across B7 and C7.
        self.place("car", ("B7", "C7"), True, "horizontal")
        self.place("plant", ("J1",), False, "right")
        self.place("plant", ("G3",), False, "right")
        # Lamps removed.

    def is_blocked(self, cell):
        return cell in self.blocked_cells

    def draw(self, surface, font,
             map_x=0, map_y=0,
             tile_width=90, tile_height=90):

        for item in self.items:
            rects = []

            for cell in item.cells:
                x, y = cell_to_xy(cell)

                rects.append(
                    pygame.Rect(
                        map_x + x * tile_width,
                        map_y + y * tile_height,
                        tile_width,
                        tile_height
                    )
                )

            left = min(r.left for r in rects)
            top = min(r.top for r in rects)
            right = max(r.right for r in rects)
            bottom = max(r.bottom for r in rects)

            bounds = pygame.Rect(
                left, top,
                right - left,
                bottom - top
            )

            # ===== VISUAL SIZE (independent from collision) =====
            # Each value is a fraction of the furniture's grid footprint.
            size_scale = {
                "bed": (0.95, 0.95),
                "fridge": (0.82, 0.82),
                "sofa": (0.83, 0.83),
                "car": (0.83, 0.83),
                "table": (0.75, 0.68),
                "plant": (0.62, 0.62),
                "lamp": (0.55, 0.55),
                "bookshelf": (0.85, 0.85),
            }
            scale_x, scale_y = size_scale.get(item.name, (0.90, 0.90))
            rect = pygame.Rect(
                0, 0,
                max(1, round(bounds.width * scale_x)),
                max(1, round(bounds.height * scale_y)),
            )
            rect.center = bounds.center

            # Keep wall decorations aligned to their specified wall.
            inset = 3
            if item.name in ("lamp", "bookshelf", "plant", "sofa"):
                if item.anchor == "top":
                    rect.top = bounds.top + inset
                elif item.anchor == "bottom":
                    rect.bottom = bounds.bottom - inset
                elif item.anchor == "left":
                    rect.left = bounds.left + inset
                elif item.anchor == "right":
                    rect.right = bounds.right - inset

            # Draw PNG furniture sprite when available.
            image = self.images.get(item.name)

            if image is not None:
                # Rotate a wide sprite when its furniture occupies vertical tiles.
                if len(item.cells) == 2 and bounds.height > bounds.width:
                    if image.get_width() > image.get_height():
                        image = pygame.transform.rotate(image, 90)
                elif len(item.cells) == 2 and bounds.width > bounds.height:
                    if image.get_height() > image.get_width():
                        image = pygame.transform.rotate(image, 90)

                # Fit inside the assigned rectangle without stretching.
                iw, ih = image.get_size()
                scale = min(rect.width / iw, rect.height / ih)
                size = (max(1, round(iw * scale)), max(1, round(ih * scale)))
                sprite = pygame.transform.smoothscale(image, size)
                surface.blit(sprite, sprite.get_rect(center=rect.center))
            else:
                # Show a placeholder when the corresponding PNG is missing.
                pygame.draw.rect(surface, item.color, rect, border_radius=6)
