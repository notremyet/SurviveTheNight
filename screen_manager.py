
from menu import MainMenu
from how_to_play import HowToPlay
from game_screens import GameEndScreen


class ScreenManager:
    def __init__(self, screen):
        self.screen = screen

        self.menu = MainMenu(screen)
        self.how_to_play = HowToPlay(screen)
        self.end_screen = GameEndScreen(screen)

        self.current_screen = "menu"

    def handle_event(self, event):
        if self.current_screen == "menu":
            result = self.menu.handle_event(event)

            if result == "start":
                self.current_screen = "game"
                return "start"

            elif result == "how_to_play":
                self.current_screen = "how_to_play"

            elif result == "quit":
                return "quit"

        elif self.current_screen == "how_to_play":
            result = self.how_to_play.handle_event(event)

            if result == "back":
                self.current_screen = "menu"

        elif self.current_screen in ("victory", "game_over"):
            result = self.end_screen.handle_event(event)

            if result == "menu":
                self.current_screen = "menu"
                return "menu"

            elif result == "quit":
                return "quit"

        return None

    def show_victory(self, reason=""):
        self.end_screen.set_result("won", reason)
        self.current_screen = "victory"

    def show_game_over(self, reason=""):
        self.end_screen.set_result("lost", reason)
        self.current_screen = "game_over"

    def draw(self):
        if self.current_screen == "menu":
            self.menu.draw()

        elif self.current_screen == "how_to_play":
            self.how_to_play.draw()

        elif self.current_screen in ("victory", "game_over"):
            self.end_screen.draw()
