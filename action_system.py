"""Player actions and round lifecycle. Zombie/Event hooks can be added later."""
class ActionSystem:
    MAX_ACTIONS = 2

    def __init__(self):
        self.round = 1
        self.remaining = self.MAX_ACTIONS
        self.last_action = "Ready"
        self.completed_rounds = 0

    def can_act(self):
        return self.remaining > 0

    def spend(self, name):
        if not self.can_act():
            return False
        self.remaining -= 1
        self.last_action = name
        return True

    def round_finished(self):
        return self.remaining == 0

    def next_round(self):
        """Called after the future Zombie Turn and Event Phase."""
        self.completed_rounds += 1
        self.round += 1
        self.remaining = self.MAX_ACTIONS
        self.last_action = "Ready"
