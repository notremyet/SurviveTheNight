
import pygame
from settings import WIDTH, HEIGHT
from ui import GameUI

pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SURVIVE THE NIGHT - UI TEST")

clock = pygame.time.Clock()
ui = GameUI()

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((25, 25, 35))

    ui.draw_hud(
        screen,
        hp=3,
        max_hp=3,
        round_number=1,
        max_rounds=8,
        actions=2,
        max_actions=2,
        noise=0,
        message="Find the key and escape!"
    )

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
