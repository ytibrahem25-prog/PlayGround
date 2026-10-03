"""Headless tests for Ibrahim Amer Minecraft world logic (no window needed)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from world_core import (
    GAME_TITLE, COPYRIGHT, GRASS, DIRT, STONE, WOOD, LEAVES, BEDROCK,
    BUILDABLE_BLOCKS, VoxelStore, terrain_height, column_blocks,
)


def test_title_and_rights():
    assert GAME_TITLE == "Ibrahim Amer Minecraft", GAME_TITLE
    assert "Ibrahim Amer" in COPYRIGHT, COPYRIGHT
    print("ok title/rights:", GAME_TITLE, "|", COPYRIGHT)


def test_required_blocks():
    assert set(BUILDABLE_BLOCKS) == {GRASS, DIRT, STONE, WOOD}
    print("ok blocks: Grass/Dirt/Stone/Wood present")


def test_terrain_deterministic():
    assert terrain_height(3, 5) == terrain_height(3, 5)
    col = column_blocks(0, 0)
    assert col[0][1] == BEDROCK  # bottom layer unbreakable
    assert col[-1][1] == GRASS   # top layer grass
    print("ok terrain deterministic, height sample:", terrain_height(0, 0))


def test_break_place():
    s = VoxelStore().generate(size=16, seed=7)
    assert s.count() > 200
    # break a grass top block
    h = __import__("world_core").terrain_height(0, 0, 7)
    assert s.break_block((0, h, 0)) is True
    assert s.get((0, h, 0)) is None
    # bedrock cannot be broken
    assert s.break_block((0, 0, 0)) is False
    # place back
    assert s.place_block((0, h, 0), GRASS) is True
    assert s.get((0, h, 0)) == GRASS
    # cannot place on occupied cell
    assert s.place_block((0, h, 0), STONE) is False
    print("ok break/place, total blocks:", s.count())


def test_trees():
    s = VoxelStore().generate(size=32, seed=7)
    woods = [p for p, b in s.blocks.items() if b == WOOD]
    leaves = [p for p, b in s.blocks.items() if b == LEAVES]
    assert len(woods) > 5 and len(leaves) > 10
    print(f"ok trees: wood={len(woods)} leaves={len(leaves)}")


if __name__ == "__main__":
    test_title_and_rights()
    test_required_blocks()
    test_terrain_deterministic()
    test_break_place()
    test_trees()
    print("ALL TESTS PASSED ✔")
