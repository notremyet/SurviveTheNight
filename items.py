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
