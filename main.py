import pygame
from pathlib import Path
from settings import *
from map import Board
from player import Player
from furniture import FurnitureManager
from interactables import InteractableManager
from action_system import ActionSystem
from pathfinding import find_path, reachable_cells
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
actions = ActionSystem()
zombies = ZombieManager(board, furniture)

# Objects take priority over the existing furniture if a future placement overlaps.
# Existing fixed placements in furniture.py do not overlap these seven cells.

def get_cell_center(cell):
    x, y = cell_to_xy(cell)
    return (MAP_X + x * TILE_WIDTH + TILE_WIDTH // 2,
            MAP_Y + y * TILE_HEIGHT + TILE_HEIGHT // 2)

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

# Zombie phase state: one zombie phase per completed player round.
zombie_phase_started = False
game_over = False


def finish_player_round():
    """Run the zombie phase once after the player spends both actions."""
    global zombie_phase_started, game_over

    if not actions.round_finished() or player.is_moving or zombie_phase_started:
        return

    zombie_phase_started = True
    hidden = interactables.hidden_in is not None
    events = zombies.take_turn(player.cell, hidden)

    # Player owns the single source of truth for health.
    for ev in events:
        if ev.kind == "attack":
            lost = player.take_damage(ev.damage)
            if lost:
                interactables.message = f"Zombie attack! -{lost} HP"
        elif ev.kind == "spotted":
            interactables.message = "A zombie spotted you!"
        elif ev.kind == "heard":
            interactables.message = "Something heard that..."
        elif ev.kind == "lost":
            interactables.message = "The zombie lost sight of you."


def draw_hud():
    noise = {
        0: "Quiet", 1: "Low", 2: "Medium", 3: "Loud",
        4: "Very loud", 5: "Very loud", 6: "Very loud"
    }.get(zombies.noise_level, "Very loud")
    status = (
        f"Round {actions.round}  |  Actions {actions.remaining}/2  |  "
        f"Last: {actions.last_action}  |  Noise: {noise}"
    )
    hud = font.render(status, True, (255, 235, 165))
    hud_bg = pygame.Surface((min(WIDTH - 20, hud.get_width() + 20), 34), pygame.SRCALPHA)
    hud_bg.fill((0, 0, 0, 190))
    screen.blit(hud_bg, (10, HEIGHT - 44))
    screen.blit(hud, (20, HEIGHT - 39))

    hp_font = pygame.font.SysFont("segoeuisymbol", 29)
    for i in range(player.max_hp):
        heart = hp_font.render(
            "♥", True,
            (239, 69, 88) if i < player.hp else (82, 77, 88)
        )
        screen.blit(heart, (WIDTH - 135 + i * 39, 8))
    hp_label = font.render(f"HP {player.hp}/{player.max_hp}", True, (255, 255, 255))
    screen.blit(hp_label, (WIDTH - 130, 44))

    if player.is_dead:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 195))
        screen.blit(veil, (0, 0))
        title_font = pygame.font.SysFont("arial", 54, bold=True)
        title = title_font.render("GAME OVER", True, (245, 75, 85))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2)))


running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            continue

        # During the zombie phase, wait for its animations to finish.
        if zombie_phase_started or player.is_dead:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                zombies.debug = not zombies.debug
            continue

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                zombies.debug = not zombies.debug

            elif event.key == pygame.K_SPACE:
                if not player.is_moving and actions.spend("Wait"):
                    interactables.message = "You wait and listen..."

            elif event.key == pygame.K_e and not player.is_moving:
                if interactables.hidden_in is not None:
                    # Leaving a wardrobe is free.
                    interactables.interact(player.cell)
                    player.play_action("hide", duration_ms=450)
                else:
                    obj = interactables.by_cell.get(player.cell)
                    needs_action = (
                        obj is not None and
                        (obj.kind == "wardrobe" or not obj.opened)
                    )
                    if needs_action and not actions.can_act():
                        interactables.message = "No actions remaining"
                    else:
                        result = interactables.interact(player.cell)
                        if result == "chest_open":
                            if actions.spend("Search"):
                                player.play_action("search", duration_ms=650)
                                zombies.make_noise(player.cell, NOISE_SEARCH, "search")
                        elif result == "hide":
                            if actions.spend("Hide"):
                                player.play_action("hide", duration_ms=550)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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

                    if zombies.occupied(target):
                        interactables.message = "A zombie is blocking that tile"
                    else:
                        reachable = reachable_cells(
                            board, furniture, player.cell, max_steps=2
                        )
                        distance = reachable.get(target)
                        if distance in (1, 2):
                            style = "walk" if distance == 1 else "run"
                            path = find_path(
                                board, furniture, player.cell, target,
                                max_steps=distance
                            )
                            if path and player.start_route(path, style):
                                if actions.spend(style.capitalize()):
                                    loudness = NOISE_WALK if style == "walk" else NOISE_RUN
                                    zombies.make_noise(player.cell, loudness, style)
                                    interactables.message = (
                                        f"{style.capitalize()}: {' -> '.join(path)}"
                                    )
                        else:
                            interactables.message = (
                                "Click a glowing tile (yellow: walk, white: run)"
                            )

    player.update(dt)
    zombies.update(dt)

    # Start zombie turn only after the player's movement animation has ended.
    finish_player_round()

    # The next player round begins only after all zombie animations finish.
    if zombie_phase_started and not zombies.busy and not player.is_dead:
        actions.next_round()
        zombie_phase_started = False


    screen.fill((20, 18, 28))
    screen.blit(house_image, (MAP_X, MAP_Y))
    furniture.draw(screen, font, map_x=MAP_X, map_y=MAP_Y,
                   tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
    interactables.draw(screen, MAP_X, MAP_Y, TILE_WIDTH, TILE_HEIGHT)
    if not player.is_dead:
        draw_move_highlights(screen, player.cell)
    zombies.draw_overlay(screen, get_cell_center)
    if interactables.hidden_in is None:
        player.draw(screen, get_cell_center)
    zombies.draw(screen, get_cell_center)

    # Mouse control legend.
    controls = font.render("Click YELLOW: WALK 1 tile | Click WHITE: RUN 2 tiles | E: interact | SPACE: wait | F1: debug", True, (255, 255, 255))
    legend_bg = pygame.Surface((min(WIDTH - 20, controls.get_width() + 20), 30), pygame.SRCALPHA)
    legend_bg.fill((0, 0, 0, 175))
    screen.blit(legend_bg, (10, HEIGHT - 80))
    screen.blit(controls, (20, HEIGHT - 76))

    # On-screen interaction hint and feedback.
    msg = font.render(interactables.message, True, (255, 255, 255))
    msg_bg = pygame.Surface((min(WIDTH, msg.get_width() + 20), 32), pygame.SRCALPHA)
    msg_bg.fill((0, 0, 0, 180))
    screen.blit(msg_bg, (10, 8))
    screen.blit(msg, (20, 12))
    draw_hud()

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
pygame.quit()
