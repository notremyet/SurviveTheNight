import pygame
from pathlib import Path

from settings import *
from map import Board
from player import Player
from furniture import FurnitureManager
from interactables import InteractableManager

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

running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:

            # E: Interact with Chest / Wardrobe
            if event.key == pygame.K_e:

                interaction_result = interactables.interact(
                    player.cell
                )

                # Draw loot only when chest opens
                loot_result = search_system.search_chest(
                    interaction_result
                )

                if loot_result is not None:

                    interactables.message = (
                        "Chest opened - "
                        + loot_result["message"]
                    )

                    print(
                        "Chest loot:",
                        loot_result["message"]
                    )

            # I: Show Inventory in Terminal
            elif event.key == pygame.K_i:

                current_items = inventory.get_items()

                print("\n=== INVENTORY ===")

                if not current_items:
                    print("Empty")

                else:
                    for item in current_items:
                        print(get_item_name(item))

                print("=================\n")

            # Movement
            elif interactables.hidden_in is None:

                moved = player.handle_key(
                    event.key,
                    board,
                    furniture
                )

                if moved:
                    print(
                        "Player moved to:",
                        player.cell
                    )

    # ----------------------------
    # Drawing
    # ----------------------------

    screen.fill((20, 18, 28))

    screen.blit(
        house_image,
        (MAP_X, MAP_Y)
    )

    furniture.draw(
        screen,
        font,
        map_x=MAP_X,
        map_y=MAP_Y,
        tile_width=TILE_WIDTH,
        tile_height=TILE_HEIGHT
    )

    interactables.draw(
        screen,
        MAP_X,
        MAP_Y,
        TILE_WIDTH,
        TILE_HEIGHT
    )

    if interactables.hidden_in is None:
        player.draw(
            screen,
            get_cell_center
        )

    # Show interaction / item message
    msg = font.render(
        interactables.message,
        True,
        (255, 255, 255)
    )

    msg_bg = pygame.Surface(
        (min(WIDTH, msg.get_width() + 20), 32),
        pygame.SRCALPHA
    )

    msg_bg.fill((0, 0, 0, 180))

    screen.blit(
        msg_bg,
        (10, 8)
    )

    screen.blit(
        msg,
        (20, 12)
    )

    pygame.display.flip()

    clock.tick(FPS)


pygame.quit()
