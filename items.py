import random
from enum import Enum

class ItemType(Enum):
    KEY = "key"
    MEDKIT = "medkit"
    NOISE_MAKER = "noise_maker"
    NOTHING = "nothing"

ITEM_NAMES = {
    ItemType.KEY: "Key",
    ItemType.MEDKIT: "Medkit",
    ItemType.NOISE_MAKER: "Noise Maker",
    ItemType.NOTHING: "Nothing",
}

class LootSystem:
    def __init__(self):
        # จำนวนผลการสุ่มทั้งหมดในเกม
        self.remaining_loot = (
            [ItemType.KEY] * 1
            + [ItemType.MEDKIT] * 2
            + [ItemType.NOISE_MAKER] * 2
            + [ItemType.NOTHING] * 2
        )

    def random_loot(self):
        # ถ้าสุ่มครบทั้ง 7 ครั้งแล้ว
        if not self.remaining_loot:
            return None

        # สุ่มจากผลที่ยังเหลืออยู่
        item = random.choice(self.remaining_loot)

        # นำผลที่สุ่มได้ออกจากกอง
        self.remaining_loot.remove(item)

        return item

def get_item_name(item):
    return ITEM_NAMES.get(item, "Unknown Item")

    
class SearchSystem:
    def __init__(self, loot_system, inventory):
        self.loot_system = loot_system
        self.inventory = inventory

    def draw_item(self):
        item = self.loot_system.random_loot()

        if item is None:
            return {"item": None, "message": "Supply exhausted", "added_to_inventory": False}

        added = False
        if item != ItemType.NOTHING:
            added = self.inventory.add_item(item)

        return {
            "item": item,
            "message": get_item_name(item),
            "added_to_inventory": added,
        }

    def search_chest(self, interaction_result):
        if interaction_result != "chest_open":
            return None
        return self.draw_item()

    def random_item_card(self):
        return self.draw_item()