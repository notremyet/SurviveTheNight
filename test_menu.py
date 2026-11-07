
import pygame
import sys

from menu import MainMenu
from how_to_play import HowToPlay

pygame.init()

screen = pygame.display.set_mode((1000, 800))
pygame.display.set_caption("SURVIVE THE NIGHT")

clock = pygame.time.Clock()

menu = MainMenu(screen)
how_to_play = HowToPlay(screen)

current_screen = "menu"
running = True

while running:
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if current_screen == "menu":
            result = menu.handle_event(event)

            if result == "start":
                print("Start Game selected!")
                current_screen = "game"

            elif result == "how_to_play":
                current_screen = "how_to_play"

            elif result == "quit":
                running = False

        elif current_screen == "how_to_play":
            result = how_to_play.handle_event(event)

            if result == "back":
                current_screen = "menu"

    if current_screen == "menu":
        menu.draw()

    elif current_screen == "how_to_play":
        how_to_play.draw()

    elif current_screen == "game":
        screen.fill((20, 18, 28))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
