import pygame
from pathlib import Path
from settings import *
from map import Board
from player import Player
from furniture import FurnitureManager
from interactables import InteractableManager
from ui import GameUI
from game_logic import GameState

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
house_image = pygame.image.load(str(BASE_DIR / "assets" / "house_map.png")).convert()
house_image = pygame.transform.scale(house_image, (MAP_WIDTH, MAP_HEIGHT))

board = Board()
player = Player(start_cell="B2")
furniture = FurnitureManager(board, reserved={player.cell, "I7"})
interactables = InteractableManager()
ui = GameUI()
game = GameState()

# Objects take priority over the existing furniture if a future placement overlaps.
# Existing fixed placements in furniture.py do not overlap these seven cells.

def get_cell_center(cell):
    x, y = cell_to_xy(cell)
    return (MAP_X + x * TILE_WIDTH + TILE_WIDTH // 2,
            MAP_Y + y * TILE_HEIGHT + TILE_HEIGHT // 2)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:

                # Only allow interaction during Player Turn
                if game.current_turn == "player" and game.actions_left > 0:
                    result = interactables.interact(player.cell)

                    # Successful interactions cost 1 action
                    if result in ("hide", "leave", "chest_open"):
                        game.use_action()

                        print("Interaction:", result)
                        print("Actions left:", game.actions_left)
            elif interactables.hidden_in is None:
                if game.current_turn == "player" and game.actions_left > 0:
                    moved = player.handle_key(event.key, board, furniture)

                    if moved:
                        game.use_action()
                        print("Player moved to:", player.cell)
                        print("Actions left:", game.actions_left)

    screen.fill((20, 18, 28))
    screen.blit(house_image, (MAP_X, MAP_Y))
    furniture.draw(screen, font, map_x=MAP_X, map_y=MAP_Y,
                   tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
    interactables.draw(screen, MAP_X, MAP_Y, TILE_WIDTH, TILE_HEIGHT)
    if interactables.hidden_in is None:
        player.draw(screen, get_cell_center)

    # On-screen interaction hint and feedback.
    msg = font.render(interactables.message, True, (255, 255, 255))
    msg_bg = pygame.Surface(
        (min(WIDTH - 30, msg.get_width() + 20), 36),
        pygame.SRCALPHA
    )
    msg_bg.fill((45, 35, 25, 220))
    hint_x = 15
    hint_y = HEIGHT - 110
    screen.blit(msg_bg, (hint_x, hint_y))
    screen.blit(msg, (hint_x + 10, hint_y + 7))

    ui.draw_hud(
    screen,
    hp=game.hp,
    max_hp=game.max_hp,
    round_number=game.round_number,
    max_rounds=game.max_rounds,
    actions=game.actions_left,
    max_actions=game.max_actions,
    noise=game.noise,
    message=f"{game.current_turn.upper()} TURN - {game.message}"
    )

    pygame.display.flip()
    clock.tick(FPS)
pygame.quit()
