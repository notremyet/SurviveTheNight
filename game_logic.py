class GameState:
    def __init__(self):
        # Player status
        self.hp = 3
        self.max_hp = 3

        # Round system
        self.round_number = 1
        self.max_rounds = 12

        # Action system
        self.max_actions = 2
        self.actions_left = 2

        # Noise system
        self.noise = 0

        # Game flow
        self.current_turn = "player"
        self.status = "playing"

        # Message shown on HUD
        self.message = "Find the key and escape!"

    def use_action(self):
        """Use one action during the player's turn."""
        if self.status != "playing":
            return False

        if self.current_turn != "player":
            return False

        if self.actions_left <= 0:
            return False

        self.actions_left -= 1

        if self.actions_left == 0:
            self.end_player_turn()

        return True

    def end_player_turn(self):
        """Switch from Player Turn to Zombie Turn."""
        if self.current_turn != "player":
            return

        if self.actions_left == 0:
            self.current_turn = "zombie"
            self.message = "Zombie's turn!"

    def end_zombie_turn(self):
        """Finish Zombie Turn and start the next round."""
        if self.status != "playing":
            return

        if self.current_turn != "zombie":
            return

        self.round_number += 1

        if self.round_number > self.max_rounds:
            self.lose_game("Time is up! You failed to escape.")
            return

        self.actions_left = self.max_actions
        self.noise = 0
        self.current_turn = "player"
        self.message = "Find the key and escape!"

    def add_noise(self, amount):
        self.noise += amount

    def reset_noise(self):
        self.noise = 0

    def take_damage(self, amount=1):
        if self.status != "playing":
            return

        self.hp = max(0, self.hp - amount)

        if self.hp <= 0:
            self.lose_game("You were caught by the zombie!")

    def heal(self, amount=1):
        if self.status != "playing":
            return

        self.hp = min(self.max_hp, self.hp + amount)

    def win_game(self):
        if self.status != "playing":
            return

        self.status = "won"
        self.message = "You escaped! You survived the night!"

    def lose_game(self, reason="Game Over"):
        if self.status != "playing":
            return

        self.status = "lost"
        self.message = reason

    def is_game_over(self):
        return self.status != "playing"