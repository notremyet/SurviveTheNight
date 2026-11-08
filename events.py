
import random

from zombie import (
    Zombie,
    ZombieEvent,
    DEFAULT_SPAWNS,
    CHASE,
    ATTACK_DAMAGE,
)


class EventSystem:
    def __init__(
        self,
        zombies,
        search_system,
        lock_random_door,
        alarm_cell,
        seed=None,
    ):
        self.zombies = zombies
        self.search_system = search_system

        # Connect to the game's existing door system.
        self.lock_random_door = lock_random_door

        # Location where the alarm sounds.
        self.alarm_cell = alarm_cell

        self.rng = random.Random(seed)
        self.last_event = None

    # EVENT 1: SPAWN ZOMBIE
    def spawn_zombie(self, player_cell):
        # Reuse spawn specifications from zombie.py.
        spawns = getattr(
            self.zombies,
            "spawns",
            DEFAULT_SPAWNS
        )

        available = [
            spec for spec in spawns
            if spec["cell"] != player_cell
            and not self.zombies.occupied(spec["cell"])
            and not self.zombies._static_blocked(
                spec["cell"]
            )
        ]

        if not available:
            return {
                "success": False,
                "message": "No available zombie spawn"
            }

        spec = self.rng.choice(available)

        zombie = Zombie(**spec)
        zombie.compute_visible(self.zombies.board)

        self.zombies.zombies.append(zombie)

        return {
            "success": True,
            "cell": zombie.cell,
            "message": f"Zombie spawned at {zombie.cell}"
        }

    # EVENT 2: ZOMBIES MOVE +1
    def zombie_extra_move(
        self,
        player_cell,
        player_hidden=False
    ):
        combat_events = []
        moved = 0

        for zombie in self.zombies.zombies:
            if (
                zombie.state == CHASE
                and not player_hidden
                and self.zombies.board.can_step(
                    zombie.cell,
                    player_cell
                )
            ):
                zombie.face(player_cell)
                zombie.lunge = 1.0

                combat_events.append(
                    ZombieEvent(
                        "attack",
                        zombie,
                        ATTACK_DAMAGE
                    )
                )
                continue

            goal = self.zombies._goal(zombie)

            next_cell = self.zombies._next_step(
                zombie,
                goal,
                player_cell
            )

            if next_cell is None:
                continue

            zombie.step_to(next_cell)
            zombie.compute_visible(self.zombies.board)
            moved += 1

        return {
            "success": True,
            "moved": moved,
            "combat_events": combat_events,
            "message": "Zombies move +1"
        }

    # EVENT 3: RANDOM DOOR LOCKED
    def random_door_locked(self):
        # Calls the existing door system.
        result = self.lock_random_door()

        return {
            "success": result is not False
                       and result is not None,
            "door_result": result,
            "message": "Random door locked"
        }

    # EVENT 4: NOTHING
    def nothing(self):
        return {
            "success": True,
            "message": "Nothing happened"
        }

    # EVENT 5: RANDOM ITEM
    def random_item(self):
        result = self.search_system.random_item_card()

        return {
            "success": True,
            "item_result": result,
            "message": f"Random Item: {result['message']}"
        }

    # EVENT 6: ALARM NOISE +2
    def alarm(self):
        cell = (
            self.alarm_cell()
            if callable(self.alarm_cell)
            else self.alarm_cell
        )

        # The main game queues this event sound for the next Zombie Turn.
        # Do not inject it directly here: this event occurs AFTER the zombie phase.

        return {
            "success": True,
            "cell": cell,
            "noise": 2,
            "message": "Alarm noise +2"
        }

    # GAME MASTER: ROLL 1-6
    def roll_event(
        self,
        player_cell,
        player_hidden=False,
        dice=None
    ):
        if dice is None:
            dice = self.rng.randint(1, 6)

        if type(dice) is not int or not 1 <= dice <= 6:
            raise ValueError("Dice must be 1-6")

        if dice == 1:
            event = "spawn_zombie"
            result = self.spawn_zombie(player_cell)

        elif dice == 2:
            event = "zombie_move"
            result = self.zombie_extra_move(
                player_cell,
                player_hidden
            )

        elif dice == 3:
            event = "lock_door"
            result = self.random_door_locked()

        elif dice == 4:
            event = "nothing"
            result = self.nothing()

        elif dice == 5:
            event = "random_item"
            result = self.random_item()

        else:
            event = "alarm"
            result = self.alarm()

        self.last_event = {
            "dice": dice,
            "event": event,
            **result
        }

        return self.last_event
