
import unittest
from unittest.mock import MagicMock

from events import EventSystem
from items import ItemType


class TestEventSystem(unittest.TestCase):

    def setUp(self):
        # Fake zombie system for testing
        self.zombies = MagicMock()
        self.zombies.spawns = [
            {"cell": "G5", "patrol": ["G5"]},
            {"cell": "E7", "patrol": ["E7"]}
        ]
        self.zombies.occupied.return_value = False
        self.zombies._static_blocked.return_value = False

        # Fake search system
        self.search_system = MagicMock()
        self.search_system.random_item_card.return_value = {
            "item": ItemType.MEDKIT,
            "message": "Medkit"
        }

        # Fake existing door system
        self.lock_door = MagicMock(return_value="D3")

        self.events = EventSystem(
            zombies=self.zombies,
            search_system=self.search_system,
            lock_random_door=self.lock_door,
            alarm_cell="B2",
            seed=42
        )

    def test_event_1_spawn_zombie(self):
        result = self.events.roll_event("B2", dice=1)

        self.assertEqual(result["event"], "spawn_zombie")
        self.assertTrue(result["success"])

    def test_event_2_zombie_move(self):
        self.zombies.zombies = []

        result = self.events.roll_event("B2", dice=2)

        self.assertEqual(result["event"], "zombie_move")
        self.assertTrue(result["success"])
        self.assertEqual(result["moved"], 0)

    def test_event_3_lock_door(self):
        result = self.events.roll_event("B2", dice=3)

        self.assertEqual(result["event"], "lock_door")
        self.assertTrue(result["success"])
        self.lock_door.assert_called_once()

    def test_event_4_nothing(self):
        result = self.events.roll_event("B2", dice=4)

        self.assertEqual(result["event"], "nothing")
        self.assertTrue(result["success"])

    def test_event_5_random_item(self):
        result = self.events.roll_event("B2", dice=5)

        self.assertEqual(result["event"], "random_item")
        self.assertEqual(
            result["item_result"]["item"],
            ItemType.MEDKIT
        )
        self.search_system.random_item_card.assert_called_once()

    def test_event_6_alarm(self):
        result = self.events.roll_event("B2", dice=6)

        self.assertEqual(result["event"], "alarm")
        self.assertEqual(result["noise"], 2)

        self.zombies.make_noise.assert_called_once_with(
            "B2", 2, "alarm"
        )

    def test_invalid_dice(self):
        for dice in (0, 7, -1, 2.5, True):
            with self.subTest(dice=dice):
                with self.assertRaises(ValueError):
                    self.events.roll_event("B2", dice=dice)


if __name__ == "__main__":
    unittest.main()
