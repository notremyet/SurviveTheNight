"""Item-use panel, deliberately separate from the team's ui.py.

The player opens the bag on demand using I during Player Turn.
It never opens automatically when actions are exhausted.
"""
import pygame

from items import ItemType, get_item_name


class ItemUsePanel:
    def __init__(self):
        self.font = pygame.font.SysFont("arial", 23, bold=True)
        self.small = pygame.font.SysFont("arial", 18)
        self.message = "Choose an item to use, then Close Bag."
        self.rows = []
        self.selected_index = 0
        self.close_rect = pygame.Rect(0, 0, 1, 1)

    def clamp_selection(self, count):
        if count <= 0:
            self.selected_index = 0
        else:
            self.selected_index = min(self.selected_index, count - 1)

    def move_selection(self, direction, count):
        if count <= 0:
            self.selected_index = 0
            return
        self.selected_index = (self.selected_index + direction) % count

    def hit_test(self, pos, count):
        if self.close_rect.collidepoint(pos):
            return "close"
        for i, rect in enumerate(self.rows[:count]):
            if rect.collidepoint(pos):
                return i
        return None

    def draw(self, surface, items, hp, max_hp, player_cell, noise):
        self.clamp_selection(len(items))
        w, h = surface.get_size()
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 185))
        surface.blit(shade, (0, 0))
        panel_width = min(650, w - 50)
        panel_height = min(590, h - 60)
        box = pygame.Rect((w-panel_width)//2, (h-panel_height)//2,
                          panel_width, panel_height)
        pygame.draw.rect(surface, (28, 27, 38), box, border_radius=12)
        pygame.draw.rect(surface, (235, 206, 105), box, 3, border_radius=12)

        def label(t, x, y, color=(240, 240, 245), font=None):
            image = (font or self.small).render(t, True, color)
            surface.blit(image, (x, y))

        label("INVENTORY - USE ITEMS", box.x+28, box.y+22, (255, 221, 118), self.font)
        label(f"HP {hp}/{max_hp}    Cell {player_cell}    Noise {noise}",
              box.x+28, box.y+58)
        label("UP/DOWN: Select   ENTER/SPACE: Use   Mouse: Click to use",
              box.x+28, box.y+92, (183, 186, 198))

        self.rows = []
        for i, item in enumerate(items[:9]):
            top = box.y + 133 + i * 41
            if top + 36 > box.bottom - 105:
                break
            rect = pygame.Rect(box.x+28, top, box.width-56, 36)
            self.rows.append(rect)
            selected = (i == self.selected_index)
            pygame.draw.rect(surface, (81, 72, 51) if selected else (54, 52, 69),
                             rect, border_radius=6)
            if selected:
                pygame.draw.rect(surface, (255, 221, 118), rect, 2, border_radius=6)
            if isinstance(item, dict) and item.get("type") == "remote":
                title = f"Remote #{item.get('id', '?')} - ACTIVATE"
            elif item == ItemType.MEDKIT:
                title = "Medkit - HEAL +1 HP"
            elif item == ItemType.NOISE_MAKER:
                title = "Noise Maker - PLACE HERE (becomes Remote)"
            elif item == ItemType.KEY:
                title = "Key - HOLD for exit (not consumable)"
            else:
                title = get_item_name(item)
            label(f"{'>' if selected else ' '} {i+1}. {title}", rect.x+12, rect.y+6)
        if not items:
            label("Inventory empty", box.x+30, box.y+148, (190, 190, 200))

        msg_y = box.bottom - 98
        label(self.message[:75], box.x+28, msg_y, (168, 219, 163))
        self.close_rect = pygame.Rect(box.right-194, box.bottom-60, 166, 43)
        pygame.draw.rect(surface, (205, 167, 63), self.close_rect, border_radius=8)
        label("CLOSE BAG", self.close_rect.x+24, self.close_rect.y+9,
              (22, 22, 30), self.font)
        label("I / ESC: CLOSE BAG", box.x+28, box.bottom-48, (190, 190, 205))
