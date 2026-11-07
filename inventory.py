from items import ItemType

class Inventory:
    def __init__(self):
        self.items = []
        self.placed_noise_makers = []
        self.next_remote_id = 1

    # ---------- Inventory ----------

    def add_item(self, item):
        if item is None or item == ItemType.NOTHING:
            return False

        if item == ItemType.KEY and self.has_item(ItemType.KEY):
            return False

        self.items.append(item)
        return True

    def has_item(self, item):
        return item in self.items

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def get_items(self):
        return self.items.copy()

    # ---------- Medkit ----------

    def use_medkit(self, current_hp):
        if not self.has_item(ItemType.MEDKIT):
            return current_hp

        if current_hp >= 3:
            return current_hp

        self.remove_item(ItemType.MEDKIT)
        return min(current_hp + 1, 3)

    
    def use_medkit_on_player(self, player):
        # Check if Medkit exists
        if not self.has_item(ItemType.MEDKIT):
            return False

        # Cannot heal a dead player
        if player.is_dead:
            return False

        # Do not consume Medkit when HP is full
        if player.hp >= player.max_hp:
            return False

        # Heal the actual Player
        healed = player.heal(1)

        if healed > 0:
            self.remove_item(ItemType.MEDKIT)
            return True

        return False

    # ---------- Key ----------

    def has_key(self):
        return self.has_item(ItemType.KEY)

    # ---------- Noise Maker ----------

    def place_noise_maker(self, player_cell):
        if not self.has_item(ItemType.NOISE_MAKER):
            return None

        if player_cell is None:
            return None

        remote_id = self.next_remote_id
        self.next_remote_id += 1

        # เปลี่ยน Noise Maker ใน Inventory เป็น Remote
        index = self.items.index(ItemType.NOISE_MAKER)
        self.items[index] = {
            "type": "remote",
            "id": remote_id
        }

        # Noise Maker ตัวจริงอยู่บนแผนที่
        self.placed_noise_makers.append({
            "id": remote_id,
            "cell": player_cell,
            "activated": False,
            "used_this_turn": False
        })

        return remote_id

    def activate_noise_maker(self, remote_id):
        for maker in self.placed_noise_makers:
            if maker["id"] != remote_id:
                continue

            if maker["activated"]:
                return False

            remote = {
                "type": "remote",
                "id": remote_id
            }

            if not self.remove_item(remote):
                return False

            # Remote หายทันที
            # แต่ Noise Maker ยังอยู่บนแผนที่
            maker["activated"] = True
            return True

        return False

    def end_turn_noise(self):
        # เรียกตอนกด Finish Turn
        # คืนตำแหน่งเสียงให้ Zombie AI
        noise_cells = []

        for maker in self.placed_noise_makers:
            if maker["activated"] and not maker["used_this_turn"]:
                noise_cells.append(maker["cell"])
                maker["used_this_turn"] = True

        return noise_cells

    def finish_zombie_turn(self):
        # เรียกหลัง Zombie Turn เดินเสร็จ
        # ลบ Noise Maker ที่ใช้แล้วออกจากแผนที่
        self.placed_noise_makers = [
            maker
            for maker in self.placed_noise_makers
            if not maker["used_this_turn"]
        ]

    def get_placed_noise_makers(self):
        # ให้ระบบแผนที่อ่านตำแหน่ง Noise Maker
        return [
            maker.copy()
            for maker in self.placed_noise_makers
        ]
