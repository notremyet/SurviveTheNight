from items import ItemType, LootSystem
from inventory import Inventory

def test_inventory():
    inventory = Inventory()

    # 1. Test Key
    inventory.add_item(ItemType.KEY)
    assert inventory.has_key()
    assert not inventory.add_item(ItemType.KEY)
    print("PASS: Key")

    # 2. Test Medkit
    inventory.add_item(ItemType.MEDKIT)
    assert inventory.use_medkit(2) == 3
    assert not inventory.has_item(ItemType.MEDKIT)

    inventory.add_item(ItemType.MEDKIT)
    assert inventory.use_medkit(3) == 3
    assert inventory.has_item(ItemType.MEDKIT)
    print("PASS: Medkit")

    # 3. Test Noise Maker
    inventory.add_item(ItemType.NOISE_MAKER)

    remote_id = inventory.place_noise_maker((4, 5))
    assert remote_id is not None
    assert not inventory.has_item(ItemType.NOISE_MAKER)

    remote = {"type": "remote", "id": remote_id}
    assert remote in inventory.get_items()

    # วางแล้วแต่ยังไม่ Activate ต้องข้ามเทิร์นได้
    assert inventory.end_turn_noise() == []
    inventory.finish_zombie_turn()
    assert len(inventory.get_placed_noise_makers()) == 1

    # Activate แล้ว Remote หายทันที
    assert inventory.activate_noise_maker(remote_id)
    assert remote not in inventory.get_items()

    # Noise Maker ยังอยู่บนแผนที่
    assert len(inventory.get_placed_noise_makers()) == 1

    # Finish Turn ส่งตำแหน่งเสียง
    assert inventory.end_turn_noise() == [(4, 5)]

    # หลัง Zombie Turn จบ Noise Maker หาย
    inventory.finish_zombie_turn()
    assert inventory.get_placed_noise_makers() == []
    print("PASS: Noise Maker & Remote")

    # 4. Test Nothing
    assert not inventory.add_item(ItemType.NOTHING)
    print("PASS: Nothing")

    # 5. Test Loot Pool
    loot = LootSystem()
    results = [loot.random_loot() for _ in range(7)]

    assert results.count(ItemType.KEY) == 1
    assert results.count(ItemType.MEDKIT) == 2
    assert results.count(ItemType.NOISE_MAKER) == 2
    assert results.count(ItemType.NOTHING) == 2
    assert loot.random_loot() is None
    print("PASS: Loot System")

    print("\nALL TESTS PASSED!")


if __name__ == "__main__":
    test_inventory()
