
import pygame
import sys

from game_screens import GameEndScreen

pygame.init()

screen = pygame.display.set_mode((1000, 800))
pygame.display.set_caption("SURVIVE THE NIGHT - End Screens")

clock = pygame.time.Clock()

end_screen = GameEndScreen(screen)

# Change between "won" and "lost" to test each screen.
#end_screen.set_result(
#    "won",
#    "You found the key and reached the exit!"
#)

end_screen.set_result(
    "lost",
    "You ran out of HP!"
)

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        result = end_screen.handle_event(event)

        if result == "menu":
            print("Return to Main Menu selected!")
            running = False

        elif result == "quit":
            running = False

    end_screen.draw()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
