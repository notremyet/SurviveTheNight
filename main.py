"""Survive The Night: Player + Zombie + Chest/Inventory integration.

Uses the team's existing Player, ActionSystem, ZombieManager and LootSystem.
Game Master events and item-use UI are separate integration steps.
"""
import math
import random
from pathlib import Path

import pygame

from settings import *
from map import Board, DOORS, edge
from player import Player
from furniture import FurnitureManager
from interactables import InteractableManager
from action_system import ActionSystem
from pathfinding import find_path, reachable_cells
from items import ItemType, LootSystem, SearchSystem, get_item_name
from inventory import Inventory
from zombie import ZombieManager, DEFAULT_SPAWNS
from ui import GameUI
from game_logic import GameState
from screen_manager import ScreenManager
from events import EventSystem
from item_use_ui import ItemUsePanel
from item_animations import ItemUseAnimation

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SURVIVE THE NIGHT")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20)

# Fit the complete map between the top HUD and bottom status/inventory bar.
TILE_WIDTH = TILE_HEIGHT = min(90, (WIDTH - 40) // COLS, (HEIGHT - 190) // ROWS)
MAP_WIDTH, MAP_HEIGHT = COLS * TILE_WIDTH, ROWS * TILE_HEIGHT
MAP_X = (WIDTH - MAP_WIDTH) // 2
MAP_Y = 85 + max(0, (HEIGHT - 85 - 100 - MAP_HEIGHT) // 2)
BASE_DIR = Path(__file__).resolve().parent
house_image = pygame.image.load(str(BASE_DIR / "assets" / "house_map.png")).convert()
house_image = pygame.transform.scale(house_image, (MAP_WIDTH, MAP_HEIGHT))

# Game Master event artwork and locked-door overlay.
# Initialise these containers BEFORE loading the image assets.
event_card_images = {}
lock_overlay = None
event_asset_dir = BASE_DIR / "assets" / "Itemcard"
for dice_number in range(1, 7):
    event_path = event_asset_dir / f"e{dice_number}.png"
    if event_path.exists():
        event_card_images[dice_number] = pygame.image.load(str(event_path)).convert_alpha()
lock_path = event_asset_dir / "lock.png"
if lock_path.exists():
    lock_overlay = pygame.image.load(str(lock_path)).convert_alpha()

ui = GameUI()
item_use_panel = ItemUsePanel()
item_use_animation = ItemUseAnimation(BASE_DIR)
inventory_open = False
inventory_closed_for_round = False
end_turn_button = pygame.Rect(WIDTH - 182, HEIGHT - 57, 158, 35)
screen_manager = ScreenManager(screen)
game = None
end_screen_shown = False
paused = False
pause_selected = 0
pause_instructions = False
event_phase = "player"       # player -> roll -> rolling -> reveal
event_result = None
event_reveal_until = 0
dice_roll_started = 0
dice_result_until = 0
rolled_dice_value = None
DICE_ROLL_DURATION = 1900
ZOMBIE_TO_EVENT_DELAY = 2200  # pause after zombie actions before the event phase
DEATH_SCREEN_DELAY = 1800  # show the fatal hit before opening Game Over
death_pause_started_at = None
DICE_RESULT_HOLD = 1500

EXIT_CELL = "I7"
hide_animation_until = 0
pending_movement_noise = None
goal_hint = ""
goal_hint_until = 0

# Temporary loot reveal shown after searching a chest.
loot_reveal_item = None
loot_reveal_until = 0
pending_event_loot = None
loot_reveal_source = "chest"
loot_reveal_received = False
LOOT_REVEAL_DURATION = 3800

ITEM_CARD_INFO = {
    ItemType.KEY: ("Key", "Unlocks the exit so you can escape."),
    ItemType.MEDKIT: ("Medkit", "Restores 1 HP when used."),
    ItemType.NOISE_MAKER: ("Noise Maker", "Creates a sound to distract the zombie."),
    ItemType.NOTHING: ("Nothing", "This chest had no useful item."),
}

def show_loot_reveal(item, source="chest", received=False):
    global loot_reveal_item, loot_reveal_until
    global loot_reveal_source, loot_reveal_received
    loot_reveal_item = item
    loot_reveal_source = source
    loot_reveal_received = received
    loot_reveal_until = pygame.time.get_ticks() + LOOT_REVEAL_DURATION

def draw_loot_reveal(surface):
    if loot_reveal_item is None or pygame.time.get_ticks() >= loot_reveal_until:
        return

    title, description = ITEM_CARD_INFO.get(
        loot_reveal_item, ("Unknown Item", "You found an item.")
    )
    if loot_reveal_source == "event":
        if loot_reveal_item == ItemType.NOTHING:
            description = "Nothing drawn. No item added to inventory."
        elif loot_reveal_received:
            description = "Added to your inventory. Press I to check."
        else:
            description = "Item was not added to inventory."
    asset_names = {
        ItemType.KEY: "key.png",
        ItemType.MEDKIT: "medkit.png",
        ItemType.NOISE_MAKER: "noisemaker.png",
        ItemType.NOTHING: "nothing.png",
    }
    image_path = BASE_DIR / "assets" / "Itemcard" / asset_names.get(
        loot_reveal_item, "nothing.png"
    )

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 105))
    surface.blit(shade, (0, 0))

    card_width, card_height = 360, 300
    card = pygame.Rect((WIDTH-card_width)//2, (HEIGHT-card_height)//2,
                       card_width, card_height)
    pygame.draw.rect(surface, (25, 23, 34), card, border_radius=18)
    pygame.draw.rect(surface, (225, 180, 65), card, 3, border_radius=18)

    title_font = pygame.font.SysFont("arial", 30, bold=True)
    body_font = pygame.font.SysFont("arial", 19)
    heading = title_font.render("EVENT REWARD" if loot_reveal_source == "event" else "CHEST SEARCH", True, (255, 217, 65))
    surface.blit(heading, heading.get_rect(center=(WIDTH//2, card.y+35)))

    try:
        item_image = pygame.image.load(str(image_path)).convert_alpha()
        item_image = pygame.transform.smoothscale(item_image, (112, 112))
        surface.blit(item_image, item_image.get_rect(center=(WIDTH//2, card.y+135)))
    except (pygame.error, FileNotFoundError):
        fallback = body_font.render("Item image unavailable", True, (190,190,195))
        surface.blit(fallback, fallback.get_rect(center=(WIDTH//2, card.y+130)))

    name_surface = title_font.render(title, True, (245,245,245))
    surface.blit(name_surface, name_surface.get_rect(center=(WIDTH//2, card.y+215)))

    words, lines, current = description.split(), [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if body_font.size(candidate)[0] <= card_width-36:
            current = candidate
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    for index, line in enumerate(lines[:2]):
        line_surface = body_font.render(line, True, (205,205,215))
        surface.blit(line_surface, line_surface.get_rect(
            center=(WIDTH//2, card.y+255+index*23)
        ))

def draw_dice_modal(surface, rolling=False, face=None):
    """Centered Game Master modal with an animated die and a visible 1-6 result."""
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 175))
    surface.blit(shade, (0, 0))

    panel_w, panel_h = 430, 390
    panel = pygame.Rect((WIDTH-panel_w)//2, (HEIGHT-panel_h)//2,
                        panel_w, panel_h)
    pygame.draw.rect(surface, (25, 23, 34), panel, border_radius=20)
    pygame.draw.rect(surface, (230, 185, 75), panel, 3, border_radius=20)

    heading_font = pygame.font.SysFont("arial", 30, bold=True)
    hint_font = pygame.font.SysFont("arial", 19)
    heading = heading_font.render("GAME MASTER EVENT", True, (255, 218, 95))
    surface.blit(heading, heading.get_rect(center=(WIDTH//2, panel.y+48)))

    die_size = 116
    die = pygame.Surface((die_size, die_size), pygame.SRCALPHA)
    die_rect = pygame.Rect(5, 5, die_size-10, die_size-10)
    pygame.draw.rect(die, (247, 242, 226), die_rect, border_radius=20)
    pygame.draw.rect(die, (70, 55, 42), die_rect, 5, border_radius=20)

    # Standard die pip layout, indexed by the final rolled number.
    pip_layout = {
        1: [(0.50, 0.50)],
        2: [(0.30, 0.30), (0.70, 0.70)],
        3: [(0.30, 0.30), (0.50, 0.50), (0.70, 0.70)],
        4: [(0.30, 0.30), (0.70, 0.30), (0.30, 0.70), (0.70, 0.70)],
        5: [(0.30, 0.30), (0.70, 0.30), (0.50, 0.50),
            (0.30, 0.70), (0.70, 0.70)],
        6: [(0.30, 0.25), (0.70, 0.25), (0.30, 0.50),
            (0.70, 0.50), (0.30, 0.75), (0.70, 0.75)],
    }

    if rolling:
        # Show changing faces while spinning.
        elapsed = pygame.time.get_ticks() - dice_roll_started
        shown_face = (int(elapsed / 85) % 6) + 1
        angle = (elapsed * 1.15) % 360
        pulse = 1.0 + 0.06 * math.sin(elapsed / 48.0)
        hint = "Rolling..."
    else:
        shown_face = face if face in range(1, 7) else 1
        angle = 0
        pulse = 1.0
        hint = f"Dice result: {shown_face}" if face else "Click the die to roll"

    for px, py in pip_layout[shown_face]:
        pygame.draw.circle(
            die, (45, 39, 36),
            (int(die_size*px), int(die_size*py)), 8
        )

    if rolling:
        die = pygame.transform.smoothscale(
            die, (int(die_size*pulse), int(die_size*pulse))
        )
        rendered_die = pygame.transform.rotozoom(die, angle, 1.0)
    else:
        rendered_die = die

    surface.blit(rendered_die, rendered_die.get_rect(
        center=(WIDTH//2, panel.y+190)
    ))
    hint_surface = hint_font.render(hint, True, (235, 235, 240))
    surface.blit(hint_surface, hint_surface.get_rect(
        center=(WIDTH//2, panel.bottom-48)
    ))
    return pygame.Rect(WIDTH//2-82, panel.y+112, 164, 164)

def draw_event_reveal(surface):
    if event_result is None:
        return
    dice = event_result["dice"]
    image = event_card_images.get(dice)
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 165))
    surface.blit(shade, (0, 0))
    panel = pygame.Rect(WIDTH//2-220, HEIGHT//2-255, 440, 510)
    pygame.draw.rect(surface, (25,23,34), panel, border_radius=18)
    pygame.draw.rect(surface, (230,185,75), panel, 3, border_radius=18)
    if image:
        max_size = (350, 350)
        scaled = pygame.transform.smoothscale(image, max_size)
        surface.blit(scaled, scaled.get_rect(center=(WIDTH//2, HEIGHT//2-35)))
    else:
        title = pygame.font.SysFont("arial", 34, bold=True).render(f"EVENT {dice}", True, (255,220,100))
        surface.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2-80)))
    msg = str(event_result.get("message", "Event resolved"))
    font_obj = pygame.font.SysFont("arial", 20, bold=True)
    words, lines, current = msg.split(), [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if font_obj.size(candidate)[0] <= 390:
            current = candidate
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    for i, line in enumerate(lines[:3]):
        text_surface = font_obj.render(line, True, (245,245,245))
        surface.blit(text_surface, text_surface.get_rect(center=(WIDTH//2, panel.bottom-70+i*25)))


def draw_locked_door_overlays(surface):
    if lock_overlay is None:
        return
    size = max(24, int(TILE_WIDTH * 0.42))
    sprite = pygame.transform.smoothscale(lock_overlay, (size, size))
    for a, b in board.locked:
        ax, ay = cell_to_xy(a)
        bx, by = cell_to_xy(b)
        center = (MAP_X + (ax+bx+1)*TILE_WIDTH//2,
                  MAP_Y + (ay+by+1)*TILE_HEIGHT//2)
        surface.blit(sprite, sprite.get_rect(center=center))


def set_goal_hint(text, duration=2600):
    global goal_hint, goal_hint_until
    goal_hint = text
    goal_hint_until = pygame.time.get_ticks() + duration

def reset_game():
    """Create a fresh game world whenever START GAME is selected."""
    global board, player, furniture, interactables, actions, zombies
    global inventory, loot_system, search_system, escaped
    global round_noise, noise_origin, game, end_screen_shown
    global hide_animation_until, pending_movement_noise, paused, pause_selected, pause_instructions
    global goal_hint, goal_hint_until, loot_reveal_item, loot_reveal_until
    global event_phase, event_result, event_reveal_until, event_system, pending_event_loot
    global dice_roll_started, dice_result_until, rolled_dice_value
    global inventory_open, inventory_closed_for_round
    global loot_reveal_source, loot_reveal_received

    board = Board()
    player = Player(start_cell="B2")
    furniture = FurnitureManager(board, reserved={player.cell, EXIT_CELL})
    interactables = InteractableManager()
    actions = ActionSystem()
    zombies = ZombieManager(board, furniture, spawns=[DEFAULT_SPAWNS[0]])
    # Keep the full spawn table available to Event 1, while starting with one zombie.
    zombies.spawns = DEFAULT_SPAWNS
    inventory = Inventory()
    inventory_open = False
    inventory_closed_for_round = False
    item_use_panel.message = "UP/DOWN select; ENTER/SPACE use; I/ESC close."
    item_use_panel.selected_index = 0
    item_use_animation.reset()
    loot_system = LootSystem()
    search_system = SearchSystem(loot_system, inventory)

    def lock_random_door():
        available_doors = [edge(a, b) for a, b in DOORS
                           if edge(a, b) not in board.locked]
        if not available_doors:
            return None
        chosen = random.choice(available_doors)
        board.locked.add(chosen)
        return chosen

    event_system = EventSystem(
        zombies=zombies,
        search_system=search_system,
        lock_random_door=lock_random_door,
        alarm_cell=lambda: player.cell,
    )

    escaped = False
    round_noise = 0
    noise_origin = player.cell
    game = GameState()
    end_screen_shown = False
    hide_animation_until = 0
    pending_movement_noise = None
    goal_hint = ""
    goal_hint_until = 0
    loot_reveal_item = None
    loot_reveal_until = 0
    pending_event_loot = None
    loot_reveal_source = "chest"
    loot_reveal_received = False
    paused = False
    pause_selected = 0
    pause_instructions = False


def place_noise_maker():
    if player.is_dead or player.is_moving or zombies.busy:
        return None
    return inventory.place_noise_maker(player.cell)


def activate_remote(remote_id):
    if player.is_dead or player.is_moving or zombies.busy:
        return False
    return inventory.activate_noise_maker(remote_id)


def use_inventory_slot(index):
    """The item-use rules; a future UI can call this without changing Inventory."""
    if not inventory_open or player.is_dead or player.is_moving:
        return
    owned = inventory.get_items()
    if not 0 <= index < len(owned):
        return
    item = owned[index]
    if item == ItemType.MEDKIT:
        if inventory.use_medkit_on_player(player):
            item_use_animation.start("medkit")
            item_use_panel.message = "Medkit used: +1 HP."
        else:
            item_use_panel.message = "Cannot use Medkit: HP already full."
    elif item == ItemType.NOISE_MAKER:
        remote_id = place_noise_maker()
        if remote_id is None:
            item_use_panel.message = "Cannot place Noise Maker right now."
        else:
            player.play_action("noise", duration_ms=550)
            item_use_animation.start("place_noise_maker")
            item_use_panel.message = f"Noise Maker placed at {player.cell}. Remote {remote_id} ready."
    elif isinstance(item, dict) and item.get("type") == "remote":
        if activate_remote(item.get("id")):
            player.play_action("noise", duration_ms=550)  # Fallback until remote artwork exists.
            item_use_animation.start("activate_remote")
            item_use_panel.message = "Remote activated. Zombie hears it this turn."
        else:
            item_use_panel.message = "This Remote cannot be activated."
    elif item == ItemType.KEY:
        item_use_panel.message = "Keep the Key and press E at exit I7."
    item_use_panel.clamp_selection(len(inventory.get_items()))


def close_inventory_phase():
    global inventory_open
    # Close Bag never ends the turn; the player decides when to press End Turn.
    inventory_open = False


def finish_player_turn():
    global inventory_closed_for_round
    if (not inventory_open and event_phase == "player" and game is not None
            and game.status == "playing" and not player.is_dead
            and not player.is_moving and not zombies.busy
            and actions.round_finished()):
        inventory_closed_for_round = True
        return True
    return False


def draw_end_turn_button(surface):
    if event_phase != "player" or game is None or game.status != "playing":
        return
    ready = actions.round_finished() and not player.is_moving and not inventory_open
    fill = (219, 173, 67) if ready else (65, 64, 75)
    pygame.draw.rect(surface, fill, end_turn_button, border_radius=8)
    pygame.draw.rect(surface, (245, 225, 152) if ready else (115, 112, 120),
                     end_turn_button, 2, border_radius=8)
    button_font = pygame.font.SysFont("arial", 16, bold=True)
    label = "END TURN" if ready else "END TURN (2 actions)"
    rendered = button_font.render(label, True, (28, 25, 31) if ready else (200, 200, 205))
    surface.blit(rendered, rendered.get_rect(center=end_turn_button.center))


def sync_game_state():
    """Mirror the live gameplay systems into GameState for HUD/end screens.

    ActionSystem remains authoritative for actions/rounds; Player remains
    authoritative for HP. GameState owns the overall playing/won/lost status.
    """
    game.hp = player.hp
    game.max_hp = player.max_hp
    game.round_number = actions.round
    game.actions_left = actions.remaining
    game.max_actions = actions.MAX_ACTIONS
    game.noise = round_noise

    if game.status == "playing":
        game.current_turn = (
            "zombie" if actions.round_finished() or zombies.busy else "player"
        )
        if player.is_dead:
            game.lose_game("You were caught by the zombie!")


def get_cell_center(cell):
    x, y = cell_to_xy(cell)
    return (MAP_X + x * TILE_WIDTH + TILE_WIDTH // 2,
            MAP_Y + y * TILE_HEIGHT + TILE_HEIGHT // 2)


YELLOW = (255, 217, 65)
WHITE_GLOW = (242, 248, 255)


def draw_move_highlights(surface, origin):
    if (player.is_dead or player.is_moving or zombies.busy or
            interactables.hidden_in is not None or not actions.can_act()):
        return
    reachable = reachable_cells(board, furniture, origin, max_steps=2)
    ticks = pygame.time.get_ticks()
    pulse = 0.72 + 0.28 * (1 + math.sin(ticks / 270.0)) / 2
    for cell, distance in reachable.items():
        if distance not in (1, 2) or zombies.occupied(cell):
            continue
        path = find_path(board, furniture, origin, cell, max_steps=distance)
        if not path or any(zombies.occupied(step) for step in path[1:]):
            continue
        gx, gy = cell_to_xy(cell)
        rect = pygame.Rect(MAP_X + gx * TILE_WIDTH, MAP_Y + gy * TILE_HEIGHT,
                           TILE_WIDTH, TILE_HEIGHT)
        color = YELLOW if distance == 1 else WHITE_GLOW
        layer = pygame.Surface((TILE_WIDTH, TILE_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(layer, (*color, int(23 * pulse)),
                         layer.get_rect().inflate(-7, -7), border_radius=6)
        for inset, alpha, width in ((3, 65, 8), (5, 140, 4), (7, 245, 2)):
            pygame.draw.rect(layer, (*color, int(alpha * pulse)),
                             layer.get_rect().inflate(-inset * 2, -inset * 2),
                             width, border_radius=5)
        surface.blit(layer, rect.topleft)


hide_animation_until = 0
pending_movement_noise = None
running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif (screen_manager.current_screen == "game" and game is not None
              and game.status == "playing" and inventory_open and not paused):
            # Modal takes priority over movement, chest search and pause hotkeys.
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_i, pygame.K_ESCAPE):
                    close_inventory_phase()
                elif event.key in (pygame.K_UP, pygame.K_DOWN):
                    item_use_panel.move_selection(
                        -1 if event.key == pygame.K_UP else 1,
                        len(inventory.get_items()),
                    )
                elif pygame.K_1 <= event.key <= pygame.K_4:
                    # Optional number shortcuts select a slot; they do NOT use it.
                    target_index = event.key - pygame.K_1
                    if target_index < len(inventory.get_items()):
                        item_use_panel.selected_index = target_index
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    # Inventory is modal: ENTER uses the selected item,
                    # never ends the turn, rolls the die or closes the bag.
                    if inventory.get_items():
                        use_inventory_slot(item_use_panel.selected_index)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                picked = item_use_panel.hit_test(event.pos, len(inventory.get_items()))
                if picked == "close":
                    close_inventory_phase()
                elif isinstance(picked, int):
                    item_use_panel.selected_index = picked
                    use_inventory_slot(picked)
            continue

        elif screen_manager.current_screen == "game" and game is not None and game.status == "playing" and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            paused = not paused
            pause_instructions = False
            continue

        elif screen_manager.current_screen == "game" and paused:
            if event.type == pygame.KEYDOWN:
                if pause_instructions:
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN):
                        pause_instructions = False
                else:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        pause_selected = (pause_selected - 1) % 4
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        pause_selected = (pause_selected + 1) % 4
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if pause_selected == 0:
                            paused = False
                        elif pause_selected == 1:
                            pause_instructions = True
                        elif pause_selected == 2:
                            paused = False
                            game = None
                            screen_manager.current_screen = "menu"
                        elif pause_selected == 3:
                            running = False
            continue

        elif screen_manager.current_screen != "game":
            result = screen_manager.handle_event(event)
            if result == "quit":
                running = False
            elif result == "start":
                reset_game()
            continue

        elif game is not None and game.status in ("won", "lost"):
            result = screen_manager.handle_event(event)
            if result == "quit":
                running = False
            elif result == "menu":
                game = None
            continue

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                zombies.debug = not zombies.debug
                continue

            # ENTER performs exactly ONE step in the current Event modal.
            # Inventory and pause are handled above and always take priority.
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if event_phase == "roll" and game.status == "playing":
                    dice_roll_started = pygame.time.get_ticks()
                    event_phase = "rolling"
                    continue
                if event_phase == "reveal":
                    event_reveal_until = pygame.time.get_ticks()
                    continue
                if event_phase == "event_loot":
                    loot_reveal_until = pygame.time.get_ticks()
                    continue

            if game.status != "playing" or escaped or player.is_dead or zombies.busy or event_phase != "player":
                continue

            # Key is checked only when the player presses E while standing at the exit.
            if event.key == pygame.K_e and player.cell == EXIT_CELL and not player.is_moving:
                if inventory.has_key():
                    escaped = True
                    game.win_game()
                    interactables.message = "Escaped!"
                    if not end_screen_shown:
                        screen_manager.show_victory("You found the key and escaped!")
                        end_screen_shown = True
                else:
                    interactables.message = "Exit locked: Key required"
                    set_goal_hint("The exit is locked. Search the chests and find the key first.")
                continue

            if event.key == pygame.K_i:
                # Bag opens only on request, before/between/after the two actions.
                if (not player.is_moving and not inventory_closed_for_round
                        and pygame.time.get_ticks() >= loot_reveal_until):
                    inventory_open = True
                    item_use_panel.clamp_selection(len(inventory.get_items()))
                    item_use_panel.message = "UP/DOWN select; ENTER/SPACE use; I/ESC close."
                continue

            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                finish_player_turn()  # Requires 2 actions; never forces bag open.
                continue

            elif event.key == pygame.K_e and not player.is_moving:
                if interactables.hidden_in is not None:
                    result = interactables.interact(player.cell)
                    if result == "leave":
                        hide_animation_until = 0
                        player.play_action("hide", duration_ms=450)
                        set_goal_hint("You left the wardrobe. Keep moving toward the exit.")
                else:
                    obj = interactables.by_cell.get(player.cell)

                    # Give clear feedback when the player tries to reuse a searched chest.
                    if obj is not None and obj.kind == "chest" and obj.opened:
                        interactables.message = "This chest has already been searched."
                        set_goal_hint("This chest has already been searched. Try another chest.")
                        continue

                    needs_action = (obj is not None and
                                    (obj.kind == "wardrobe" or not obj.opened))
                    if needs_action and not actions.can_act():
                        interactables.message = "No actions remaining"
                        set_goal_hint("You have used all actions this turn. Wait for your next turn.")
                    else:
                        result = interactables.interact(player.cell)
                        if result == "chest_open":
                            actions.spend("Search")
                            player.play_action("search", duration_ms=650)
                            round_noise += 1
                            noise_origin = player.cell
                            loot_result = search_system.search_chest(result)
                            if loot_result is not None:
                                found_item = loot_result.get("item")
                                loot_message = loot_result.get("message", "You found an item.")
                                interactables.message = "Chest opened - " + loot_message
                                if found_item is not None:
                                    show_loot_reveal(found_item)
                                    item_title = ITEM_CARD_INFO.get(found_item, (loot_message, ""))[0]
                                    if found_item == ItemType.NOTHING:
                                        set_goal_hint("This chest had nothing useful inside.")
                                    else:
                                        set_goal_hint("You found a " + item_title + "!")
                                else:
                                    set_goal_hint("The supplies have been exhausted.")
                                print("Chest loot:", loot_message)
                            else:
                                set_goal_hint("This chest is empty. Search another chest.")
                        elif result == "chest_already_open":
                            interactables.message = "Chest already opened"
                            set_goal_hint("This chest has already been searched. Try another chest.")
                        elif result == "hide":
                            actions.spend("Hide")
                            player.play_action("hide", duration_ms=550)
                            hide_animation_until = pygame.time.get_ticks() + 550
                            set_goal_hint("You are hiding. Press E again to leave the wardrobe.")
                        elif result == "leave":
                            set_goal_hint("You left the wardrobe.")
                        elif result is None:
                            set_goal_hint("Nothing to interact with here. Move onto a chest, wardrobe, or exit.")

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if event_phase == "reveal":
                # Restore the earlier mouse behavior: click anywhere on the event
                # card (or the screen), not a newly added Continue button.
                event_reveal_until = pygame.time.get_ticks()
                continue
            if event_phase == "event_loot":
                # Likewise, dismiss the Event 5 reward without a separate button.
                loot_reveal_until = pygame.time.get_ticks()
                continue
            if event_phase == "roll" and game is not None and game.status == "playing":
                dice_rect = pygame.Rect(WIDTH//2-82, HEIGHT//2-82, 164, 164)
                if dice_rect.collidepoint(event.pos):
                    dice_roll_started = pygame.time.get_ticks()
                    event_phase = "rolling"
                continue
            if event_phase != "player":
                continue
            if game.status != "playing" or escaped or player.is_dead or zombies.busy:
                continue
            if end_turn_button.collidepoint(event.pos):
                finish_player_turn()
                continue
            if interactables.hidden_in is not None:
                interactables.message = "Press E to leave the wardrobe first"
            elif player.is_moving:
                pass
            elif not actions.can_act():
                interactables.message = "No actions remaining"
            else:
                mx, my = event.pos
                if MAP_X <= mx < MAP_X + MAP_WIDTH and MAP_Y <= my < MAP_Y + MAP_HEIGHT:
                    gx = (mx - MAP_X) // TILE_WIDTH
                    gy = (my - MAP_Y) // TILE_HEIGHT
                    target = xy_to_cell((gx, gy))
                    reachable = reachable_cells(board, furniture, player.cell, max_steps=2)
                    distance = reachable.get(target)
                    if distance in (1, 2):
                        style = "walk" if distance == 1 else "run"
                        path = find_path(board, furniture, player.cell,
                                         target, max_steps=distance)
                        if path and not any(zombies.occupied(step) for step in path[1:]):
                            if player.start_route(path, style):
                                actions.spend(style.capitalize())
                                pending_movement_noise = (target, style)
                                interactables.message = f"{style.capitalize()}: {' -> '.join(path)}"
                        else:
                            interactables.message = "A zombie is blocking the path"
                    else:
                        interactables.message = "Click a glowing tile (yellow: walk, white: run)"

    if screen_manager.current_screen == "game" and game is not None and game.status == "playing" and not paused:
        player.update(dt)
        zombies.update(dt)

    # A move's sound is made at the final destination once the animation ends.
    if game is not None and not paused and pending_movement_noise is not None and not player.is_moving:
        destination, style = pending_movement_noise
        if style == "run":
            round_noise += 2
            noise_origin = destination
        # Walking adds no noise and does not reset round_noise.
        pending_movement_noise = None

    # The bag never opens automatically. The player presses I at any point;
    # after two actions they can use items, then press Enter / END TURN.

    # Player (two actions) -> Zombie Turn -> next Player round.
    # Game Master events will be inserted between the last two steps later.
    if (game is not None and not paused and game.status == "playing" and not escaped and not player.is_dead
            and not player.is_moving and not zombies.busy and actions.round_finished()
            and event_phase == "player" and inventory_closed_for_round):
        # One accumulated sound value for the entire Player Turn.
        # Normal turns use it from the last noisy action's location.
        if round_noise > 0:
            zombies.make_noise(noise_origin, round_noise, "player_actions")

        # A Remote redirects THIS SAME sound value to the planted maker.
        # Its priority is resolved by the Zombie AI (not by sound strength).
        activated = [m for m in inventory.get_placed_noise_makers()
                     if m["activated"] and not m["used_this_turn"]]
        for maker in activated:
            if round_noise > 0:
                zombies.make_noise(maker["cell"], round_noise, "noise_maker")
        inventory.end_turn_noise()  # mark activated makers as used

        # If multiple remotes are active, the first one activated has priority;
        # preserve the others as sounds (the current rules do not define ties).
        primary = (activated[0]["cell"], round_noise) if activated and round_noise > 0 else None
        combat_events = zombies.take_turn(
            player.cell, interactables.hidden_in is not None,
            priority_noise=primary,
        )
        inventory.finish_zombie_turn()  # remove used makers
        round_noise = 0                 # next round starts quiet
        noise_origin = player.cell
        total_damage = sum(ev.damage for ev in combat_events if ev.kind == "attack")
        if total_damage:
            lost = player.take_damage(total_damage)
            if lost:
                interactables.message = f"Zombie attack! -{lost} HP"
        elif any(ev.kind == "spotted" for ev in combat_events):
            interactables.message = "A zombie spotted you!"
        elif any(ev.kind == "heard" for ev in combat_events):
            interactables.message = "Something heard that..."
        # Complete the round through GameState, then reset ActionSystem only
        # if the game is still active. This also enforces the 8-round limit.
        if player.is_dead:
            # Keep the map visible briefly after the fatal zombie hit.
            event_phase = "death_pause"
            death_pause_started_at = pygame.time.get_ticks()
            interactables.message = "The zombie caught you..."
        else:
            # GameState requires the Zombie Turn state before it can advance.
            game.current_turn = "zombie"
            game.end_zombie_turn()
            if game.status == "lost" and not end_screen_shown:
                game.message = "TIME_LIMIT"
                screen_manager.show_game_over("TIME_LIMIT")
                end_screen_shown = True
            elif game.status == "playing":
                # Keep the board visible while zombies finish their movement/attack.
                # The dice prompt appears only after the zombie phase is complete.
                event_phase = "zombie"
                zombie_phase_finished_at = None

    # Give the fatal hit a moment on screen before showing Game Over.
    if (event_phase == "death_pause"
            and death_pause_started_at is not None
            and pygame.time.get_ticks() - death_pause_started_at >= DEATH_SCREEN_DELAY):
        game.lose_game("HP_DEPLETED")
        if not end_screen_shown:
            screen_manager.show_game_over("HP_DEPLETED")
            end_screen_shown = True
        death_pause_started_at = None

    # Let the player clearly see the zombie phase, then pause briefly after
    # the final zombie animation before showing the Game Master dice prompt.
    if (event_phase == "zombie" and game is not None
            and game.status == "playing" and not zombies.busy):
        event_phase = "zombie_pause"
        zombie_phase_finished_at = pygame.time.get_ticks()

    if (event_phase == "zombie_pause"
            and zombie_phase_finished_at is not None
            and pygame.time.get_ticks() - zombie_phase_finished_at >= ZOMBIE_TO_EVENT_DELAY):
        event_phase = "roll"
        zombie_phase_finished_at = None

    if (event_phase == "rolling" and
            pygame.time.get_ticks() - dice_roll_started >= DICE_ROLL_DURATION):
        # Choose and resolve the event once; keep its matching die face visible briefly.
        rolled_dice_value = random.randint(1, 6)
        event_result = event_system.roll_event(
            player.cell,
            interactables.hidden_in is not None,
            dice=rolled_dice_value,
        )
        if event_result.get("dice") == 2:
            extra_damage = sum(
                ev.damage for ev in event_result.get("combat_events", [])
                if ev.kind == "attack"
            )
            if extra_damage:
                player.take_damage(extra_damage)
        elif event_result.get("dice") == 5:
            item_result = event_result.get("item_result") or {}
            found = item_result.get("item")
            received = bool(item_result.get("added_to_inventory", False))
            if found is None:
                event_result["message"] = "Random Item: supply pool exhausted."
            elif found == ItemType.NOTHING:
                event_result["message"] = "Random Item: Nothing (no item added)."
                pending_event_loot = (found, False)
            else:
                event_result["message"] = (
                    f"Random Item: {get_item_name(found)} "
                    + ("ADDED TO INVENTORY" if received else "NOT ADDED")
                )
                pending_event_loot = (found, received)

        event_phase = "dice_result"
        dice_result_until = pygame.time.get_ticks() + DICE_RESULT_HOLD

    if (event_phase == "dice_result" and
            pygame.time.get_ticks() >= dice_result_until):
        event_phase = "reveal"
        event_reveal_until = pygame.time.get_ticks() + 4200

    if event_phase == "reveal" and pygame.time.get_ticks() >= event_reveal_until:
        event_result = None
        rolled_dice_value = None
        if pending_event_loot is not None:
            # Give the event card its own screen time, then reveal its reward.
            reward_item, reward_received = pending_event_loot
            show_loot_reveal(reward_item, source="event", received=reward_received)
            pending_event_loot = None
            event_phase = "event_loot"
        else:
            event_phase = "player"
            if player.is_dead:
                game.lose_game("HP_DEPLETED")
                if not end_screen_shown:
                    screen_manager.show_game_over("HP_DEPLETED")
                    end_screen_shown = True
            else:
                actions.next_round()
                inventory_closed_for_round = False
                # Unused Remotes remain in the bag. The player may press I
                # before taking actions, but there is no forced popup.
            round_noise = 0

    if (event_phase == "event_loot"
            and pygame.time.get_ticks() >= loot_reveal_until):
        loot_reveal_item = None
        event_phase = "player"
        if player.is_dead:
            game.lose_game("HP_DEPLETED")
            if not end_screen_shown:
                screen_manager.show_game_over("HP_DEPLETED")
                end_screen_shown = True
        else:
            actions.next_round()
            inventory_closed_for_round = False
            # Remote stays available via I; never open the bag automatically.
        round_noise = 0

    if screen_manager.current_screen == "game" and game is not None:
        screen.fill((20, 18, 28))
        screen.blit(house_image, (MAP_X, MAP_Y))
        furniture.draw(screen, font, map_x=MAP_X, map_y=MAP_Y,
                       tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
        interactables.draw(screen, MAP_X, MAP_Y, TILE_WIDTH, TILE_HEIGHT)
        draw_locked_door_overlays(screen)
        zombies.draw_overlay(screen, get_cell_center)
        if not player.is_dead:
            draw_move_highlights(screen, player.cell)
        if (interactables.hidden_in is None or
                pygame.time.get_ticks() < hide_animation_until):
            player.draw(screen, get_cell_center)
        zombies.draw(screen, get_cell_center)

        # Keep GameState synchronized with the systems that own live gameplay data.
        sync_game_state()
        if game.status == "won":
            hud_message = "YOU ESCAPED! You survived the night!"
        elif game.status == "lost":
            hud_message = game.message
        elif game.current_turn == "zombie" or event_phase in ("zombie", "zombie_pause"):
            hud_message = "ZOMBIE TURN - Stay quiet and survive!"
        else:
            hud_message = "PLAYER TURN - Find the key and escape!"

        raw_items = inventory.get_items()
        visible_items = []
        for item in raw_items:
            if isinstance(item, dict):
                visible_items.append(item.get("name") or item.get("type") or f"Remote {item.get('id', '?')}")
            else:
                visible_items.append(get_item_name(item))

        if goal_hint and pygame.time.get_ticks() < goal_hint_until:
            current_goal = goal_hint
        elif inventory.has_key():
            current_goal = "You have the key! Find the exit and press E to escape."
        else:
            current_goal = "Search the chests for a key, then find the exit."
        ui.draw_hud(
            screen,
            hp=game.hp,
            max_hp=game.max_hp,
            round_number=game.round_number,
            max_rounds=game.max_rounds,
            actions=game.actions_left,
            max_actions=game.max_actions,
            noise=game.noise,
            message=hud_message,
            items=visible_items,
            goal=current_goal,
        )
        # Draw on top of the existing HUD without changing teammates' ui.py.
        if not paused and event_phase == "player" and game.status == "playing":
            draw_end_turn_button(screen)

        loot_popup_active = (
            loot_reveal_item is not None
            and pygame.time.get_ticks() < loot_reveal_until
        )

        if paused:
            ui.draw_pause(screen, pause_selected, pause_instructions)
        elif loot_popup_active:
            # Finish the chest/item popup first; do not show Game Master behind it.
            draw_loot_reveal(screen)
        elif event_phase == "roll":
            draw_dice_modal(screen, rolling=False)
        elif event_phase == "rolling":
            draw_dice_modal(screen, rolling=True)
        elif event_phase == "dice_result":
            draw_dice_modal(screen, rolling=False, face=rolled_dice_value)
        elif event_phase == "reveal":
            draw_event_reveal(screen)

        if inventory_open and game.status == "playing" and not paused:
            item_use_panel.draw(screen, inventory.get_items(), player.hp, player.max_hp,
                                player.cell, round_noise)
            item_use_animation.draw(screen)

        if game.status in ("won", "lost"):
            screen_manager.draw()
    else:
        screen_manager.draw()

    pygame.display.flip()

pygame.quit()
