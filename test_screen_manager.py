
import pygame
import sys

from screen_manager import ScreenManager

pygame.init()

screen = pygame.display.set_mode((1000, 800))
pygame.display.set_caption("Screen Manager Test")

clock = pygame.time.Clock()
manager = ScreenManager(screen)

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        result = manager.handle_event(event)

        if result == "start":
            print("Game started!")

        elif result == "menu":
            print("Returned to Main Menu!")

        elif result == "quit":
            running = False

    manager.draw()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
