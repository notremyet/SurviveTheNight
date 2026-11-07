import pygame
from pathlib import Path

from settings import *
from map import Board
from player import Player
from furniture import FurnitureManager
from interactables import InteractableManager
from action_system import ActionSystem
from pathfinding import find_path, reachable_cells

# Item & Inventory System
from items import LootSystem, SearchSystem, get_item_name
from inventory import Inventory


pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SURVIVE THE NIGHT")

clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20)

TILE_WIDTH = 90
TILE_HEIGHT = 90

MAP_WIDTH = COLS * TILE_WIDTH
MAP_HEIGHT = ROWS * TILE_HEIGHT

MAP_X = (WIDTH - MAP_WIDTH) // 2
MAP_Y = (HEIGHT - MAP_HEIGHT) // 2

BASE_DIR = Path(__file__).resolve().parent

house_image = pygame.image.load(
    str(BASE_DIR / "assets" / "house_map.png")
).convert()

house_image = pygame.transform.scale(
    house_image,
    (MAP_WIDTH, MAP_HEIGHT)
)


# ----------------------------
# Game Objects
# ----------------------------

board = Board()

player = Player(start_cell="B2")

furniture = FurnitureManager(
    board,
    reserved={player.cell, "I7"}
)

interactables = InteractableManager()
actions = ActionSystem()


# ----------------------------
# Item & Inventory Setup
# ----------------------------

inventory = Inventory()

loot_system = LootSystem()

search_system = SearchSystem(
    loot_system,
    inventory
)


def get_cell_center(cell):
    x, y = cell_to_xy(cell)

    return (
        MAP_X + x * TILE_WIDTH + TILE_WIDTH // 2,
        MAP_Y + y * TILE_HEIGHT + TILE_HEIGHT // 2
    )


# ----------------------------
# Main Game Loop
# ----------------------------

# Glowing movement targets: yellow = walk 1 tile; white = run 2 tiles.
YELLOW = (255, 217, 65)
WHITE_GLOW = (242, 248, 255)

def draw_move_highlights(surface, origin):
    if player.is_moving or interactables.hidden_in is not None or not actions.can_act():
        return
    reachable = reachable_cells(board, furniture, origin, max_steps=2)
    ticks = pygame.time.get_ticks()
    pulse = 0.72 + 0.28 * (1 + __import__('math').sin(ticks / 270.0)) / 2
    for cell, distance in reachable.items():
        if distance not in (1, 2):
            continue
        gx, gy = cell_to_xy(cell)
        rect = pygame.Rect(MAP_X + gx * TILE_WIDTH, MAP_Y + gy * TILE_HEIGHT,
                           TILE_WIDTH, TILE_HEIGHT)
        color = YELLOW if distance == 1 else WHITE_GLOW
        layer = pygame.Surface((TILE_WIDTH, TILE_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(layer, (*color, int(23 * pulse)), layer.get_rect().inflate(-7, -7), border_radius=6)
        for inset, alpha, width in ((3, 65, 8), (5, 140, 4), (7, 245, 2)):
            pygame.draw.rect(layer, (*color, int(alpha * pulse)),
                             layer.get_rect().inflate(-inset * 2, -inset * 2),
                             width, border_radius=5)
        surface.blit(layer, rect.topleft)

hide_animation_until = 0
feedback_until = 0

def apply_zombie_hit(damage=1):
    """Zombie AI should call this once when an attack lands."""
    lost = player.take_damage(damage)
    if lost:
        interactables.message = f"Zombie attack! -{lost} HP"
    return lost


running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            # Temporary testing key; remove when zombie.py is integrated.
            if event.key == pygame.K_t and not player.is_dead:
                apply_zombie_hit()
            if player.is_dead:
                continue
            if event.key == pygame.K_i:
                current_items = inventory.get_items()
                print("\n=== INVENTORY ===")
                if not current_items:
                    print("Empty")
                else:
                    for item in current_items:
                        print(get_item_name(item))
                print("=================\n")
            elif event.key == pygame.K_e and not player.is_moving:
                # Leaving a wardrobe is free; entering and first chest search cost 1.
                if interactables.hidden_in is not None:
                    result = interactables.interact(player.cell)
                    if result == "leave":
                        hide_animation_until = 0
                        player.play_action("hide", duration_ms=450)
                else:
                    obj = interactables.by_cell.get(player.cell)
                    needs_action = (obj is not None and
                                    (obj.kind == "wardrobe" or not obj.opened))
                    if needs_action and not actions.can_act():
                        interactables.message = "No actions remaining"
                    else:
                        result = interactables.interact(player.cell)
                        if result == "chest_open":
                            actions.spend("Search")
                            player.play_action("search", duration_ms=650)
                            loot_result = search_system.search_chest(result)
                            if loot_result is not None:
                                interactables.message = "Chest opened - " + loot_result["message"]
                                print("Chest loot:", loot_result["message"])
                        elif result == "hide":
                            actions.spend("Hide")
                            player.play_action("hide", duration_ms=550)
                            hide_animation_until = pygame.time.get_ticks() + 550
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not player.is_dead:
            # One left click chooses the action by target glow color.
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
                        path = find_path(board, furniture, player.cell, target, max_steps=distance)
                        if path and player.start_route(path, style):
                            actions.spend(style.capitalize())
                            interactables.message = f"{style.capitalize()}: {' -> '.join(path)}"
                    else:
                        interactables.message = "Click a glowing tile (yellow: walk, white: run)"

    player.update(clock.get_time() / 1000.0)

    # Future integration point: Zombie Turn -> Event Phase -> next round.
    # Currently there is no zombie/event implementation in this project.
    if not player.is_dead and actions.round_finished() and not player.is_moving:
        print(f"Round {actions.round} completed: Zombie/Event phases pending")
        actions.next_round()

    screen.fill((20, 18, 28))
    screen.blit(house_image, (MAP_X, MAP_Y))
    furniture.draw(screen, font, map_x=MAP_X, map_y=MAP_Y,
                   tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
    interactables.draw(screen, MAP_X, MAP_Y, TILE_WIDTH, TILE_HEIGHT)
    if not player.is_dead:
        draw_move_highlights(screen, player.cell)
    if (interactables.hidden_in is None
            or pygame.time.get_ticks() < hide_animation_until):
        player.draw(screen, get_cell_center)

    # Mouse control legend.
    controls = font.render("Click YELLOW: WALK 1 tile | Click WHITE: RUN 2 tiles | E: interact", True, (255, 255, 255))
    legend_bg = pygame.Surface((min(WIDTH - 20, controls.get_width() + 20), 30), pygame.SRCALPHA)
    legend_bg.fill((0, 0, 0, 175))
    screen.blit(legend_bg, (10, HEIGHT - 80))
    screen.blit(controls, (20, HEIGHT - 76))

    # On-screen interaction hint and feedback.
    msg = font.render(interactables.message, True, (255, 255, 255))
    msg_bg = pygame.Surface((min(WIDTH, msg.get_width() + 20), 32), pygame.SRCALPHA)
    msg_bg.fill((0, 0, 0, 180))

    screen.blit(
        msg_bg,
        (10, 8)
    )

    screen.blit(
        msg,
        (20, 12)
    )

    hud = font.render(
        f"Round {actions.round}  |  Actions {actions.remaining}/2  |  Last: {actions.last_action}",
        True, (255, 235, 165)
    )
    hud_bg = pygame.Surface((min(WIDTH - 20, hud.get_width() + 20), 34), pygame.SRCALPHA)
    hud_bg.fill((0, 0, 0, 190))
    screen.blit(hud_bg, (10, HEIGHT - 44))
    screen.blit(hud, (20, HEIGHT - 39))

    # HP hearts: filled = remaining health, dark = lost health.
    hp_font = pygame.font.SysFont("segoeuisymbol", 29)
    for i in range(player.max_hp):
        heart = hp_font.render("♥", True, (239, 69, 88) if i < player.hp else (82, 77, 88))
        screen.blit(heart, (WIDTH - 135 + i * 39, 8))
    hp_label = font.render(f"HP {player.hp}/{player.max_hp}", True, (255, 255, 255))
    screen.blit(hp_label, (WIDTH - 130, 44))
    if player.is_dead:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 195))
        screen.blit(veil, (0, 0))
        title_font = pygame.font.SysFont("arial", 54, bold=True)
        game_over = title_font.render("GAME OVER", True, (245, 75, 85))
        screen.blit(game_over, game_over.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pygame.display.flip()

    clock.tick(FPS)


pygame.quit()
