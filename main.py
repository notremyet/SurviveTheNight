import pygame
from pathlib import Path
from settings import *
from map import Board
from player import Player
from furniture import FurnitureManager
from interactables import InteractableManager
from zombie import ZombieManager, NOISE_WALK, NOISE_RUN, NOISE_SEARCH

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
zombies = ZombieManager(board, furniture)

# Objects take priority over the existing furniture if a future placement overlaps.
# Existing fixed placements in furniture.py do not overlap these seven cells.

def get_cell_center(cell):
    x, y = cell_to_xy(cell)
    return (MAP_X + x * TILE_WIDTH + TILE_WIDTH // 2,
            MAP_Y + y * TILE_HEIGHT + TILE_HEIGHT // 2)


class Blockers:
    """The player cannot walk through blocking furniture or zombies."""
    def is_blocked(self, cell):
        return furniture.is_blocked(cell) or zombies.occupied(cell)


blockers = Blockers()

# --- TEMP: rounds and HP for testing the zombies. Replace with person 1's
# --- Player HP / 2-actions-per-round and person 4's HUD when they are merged.
ACTIONS_PER_ROUND = 2
MAX_HP = 3
actions_left = ACTIONS_PER_ROUND
round_no = 1
player_hp = MAX_HP
game_over = False


def spend_action():
    """Use one action. When the player is out of actions, the zombies move."""
    global actions_left, round_no, player_hp, game_over
    actions_left -= 1
    if actions_left > 0:
        return
    hidden = interactables.hidden_in is not None
    events = zombies.take_turn(player.cell, hidden)
    kinds = {ev.kind for ev in events}
    player_hp = max(0, player_hp - sum(ev.damage for ev in events if ev.kind == "attack"))
    if player_hp <= 0:
        game_over = True
        interactables.message = "You were bitten. Game over."
        return
    if "attack" in kinds:
        interactables.message = "A zombie bit you!"
    elif "spotted" in kinds:
        interactables.message = "A zombie spotted you!"
    elif "heard" in kinds:
        interactables.message = "Something heard that..."
    round_no += 1
    actions_left = ACTIONS_PER_ROUND


def draw_temp_hud():
    noise = {0: "quiet", 1: "low", 2: "medium", 3: "loud"}.get(zombies.noise_level, "VERY LOUD")
    status = (f"HP {player_hp}/{MAX_HP}    Round {round_no}    "
              f"Actions {actions_left}/{ACTIONS_PER_ROUND}    Noise: {noise}")
    keys = "Move WASD   Run Shift+WASD   E interact   Space wait   F1 AI debug"
    screen.blit(font.render(status, True, (255, 255, 255)), (MAP_X, HEIGHT - 70))
    screen.blit(font.render(keys, True, (170, 170, 185)), (MAP_X, HEIGHT - 42))
    if game_over:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((60, 0, 0, 150))
        screen.blit(shade, (0, 0))
        big = pygame.font.SysFont("arial", 56, bold=True).render("GAME OVER", True, (255, 255, 255))
        screen.blit(big, big.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
# --- end TEMP


running = True
while running:
    dt = clock.tick(FPS) / 1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                zombies.debug = not zombies.debug
            elif game_over or zombies.busy:
                pass  # wait for the zombie animation to finish
            elif event.key == pygame.K_SPACE:
                actions_left = 1
                spend_action()
            elif event.key == pygame.K_e:
                result = interactables.interact(player.cell)
                if result == "chest_open":
                    zombies.make_noise(player.cell, NOISE_SEARCH, "search")
                if result in ("hide", "leave", "chest_open"):
                    spend_action()
            elif interactables.hidden_in is None:
                run = bool(event.mod & pygame.KMOD_SHIFT)
                moved = player.handle_key(event.key, board, blockers)
                if moved:
                    if run:
                        player.handle_key(event.key, board, blockers)
                    zombies.make_noise(player.cell, NOISE_RUN if run else NOISE_WALK,
                                       "run" if run else "walk")
                    print("Player moved to:", player.cell)
                    spend_action()

    zombies.update(dt)

    screen.fill((20, 18, 28))
    screen.blit(house_image, (MAP_X, MAP_Y))
    furniture.draw(screen, font, map_x=MAP_X, map_y=MAP_Y,
                   tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
    interactables.draw(screen, MAP_X, MAP_Y, TILE_WIDTH, TILE_HEIGHT)
    zombies.draw_overlay(screen, get_cell_center)
    if interactables.hidden_in is None:
        player.draw(screen, get_cell_center)
    zombies.draw(screen, get_cell_center)

    # On-screen interaction hint and feedback.
    msg = font.render(interactables.message, True, (255, 255, 255))
    msg_bg = pygame.Surface((min(WIDTH, msg.get_width() + 20), 32), pygame.SRCALPHA)
    msg_bg.fill((0, 0, 0, 180))
    screen.blit(msg_bg, (10, 8))
    screen.blit(msg, (20, 12))
    draw_temp_hud()

    pygame.display.flip()
pygame.quit()
