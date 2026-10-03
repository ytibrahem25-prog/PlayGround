"""
Ibrahim Amer Minecraft - core voxel logic (headless, testable without window).
Used by main.py (Ursina 3D) and unit checks.
"""
import math
import random

GAME_TITLE = "Ibrahim Amer Minecraft"
COPYRIGHT = "© Ibrahim Amer"

# Block IDs
GRASS = 1
DIRT = 2
STONE = 3
WOOD = 4
LEAVES = 5
BEDROCK = 6

BLOCK_NAMES_AR = {
    GRASS: "عشب Grass",
    DIRT: "تراب Dirt",
    STONE: "حجر Stone",
    WOOD: "خشب Wood",
    LEAVES: "أوراق Leaves",
    BEDROCK: "أساس Bedrock",
}

# Fallback display colors (R,G,B 0-255)
BLOCK_COLORS = {
    GRASS: (102, 204, 51),
    DIRT: (139, 90, 43),
    STONE: (140, 140, 140),
    WOOD: (120, 72, 20),
    LEAVES: (34, 139, 34),
    BEDROCK: (40, 40, 40),
}

BUILDABLE_BLOCKS = [GRASS, DIRT, STONE, WOOD]  # hotbar (as required)


def hash2(x, z, seed=1337):
    """Deterministic pseudo-random 0..1 from int coords."""
    h = (x * 374761393 + z * 668265263 + seed * 974634) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return h / 4294967295.0


def smooth_noise(x, z):
    """Bilinear interpolated value noise for terrain."""
    xi, zi = math.floor(x), math.floor(z)
    xf, zf = x - xi, z - zi
    # smoothstep
    u = xf * xf * (3 - 2 * xf)
    v = zf * zf * (3 - 2 * zf)
    a = hash2(xi, zi)
    b = hash2(xi + 1, zi)
    c = hash2(xi, zi + 1)
    d = hash2(xi + 1, zi + 1)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def terrain_height(x, z, seed=7):
    """Terrain height 1..~8. Deterministic so desktop & android match."""
    base = 3
    h = (smooth_noise(x * 0.15 + seed, z * 0.15) - 0.5) * 6
    h += (smooth_noise(x * 0.45, z * 0.45 + seed) - 0.5) * 2
    return max(1, int(round(base + h)))


def column_blocks(x, z, seed=7):
    """Return list of (y, block_id) for a ground column at x,z."""
    h = terrain_height(x, z, seed)
    col = []
    for y in range(h + 1):  # y=0..h
        if y == 0:
            col.append((y, BEDROCK))
        elif y == h:
            col.append((y, GRASS))
        elif y >= h - 2:
            col.append((y, DIRT))
        else:
            col.append((y, STONE))
    return col


class VoxelStore:
    """Simple dict-backed voxel world. Key=(x,y,z) -> block_id."""

    def __init__(self):
        self.blocks = {}

    def generate(self, size=32, seed=7, with_trees=True, tree_seed=42):
        self.blocks.clear()
        half = size // 2
        for x in range(-half, half):
            for z in range(-half, half):
                for (y, b) in column_blocks(x, z, seed):
                    self.blocks[(x, y, z)] = b
        if with_trees:
            rng = random.Random(tree_seed)
            for _ in range(max(3, size // 8)):
                tx = rng.randint(-half + 2, half - 3)
                tz = rng.randint(-half + 2, half - 3)
                self.plant_tree(tx, terrain_height(tx, tz, seed) + 1, tz)
        return self

    def plant_tree(self, x, y_base, z):
        trunk_h = 4
        for i in range(trunk_h):
            self.blocks[(x, y_base + i, z)] = WOOD
        top = y_base + trunk_h
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(-1, 2):
                    if abs(dx) == 2 and abs(dz) == 2:
                        continue
                    p = (x + dx, top + dy, z + dz)
                    if p not in self.blocks:
                        self.blocks[p] = LEAVES
        self.blocks[(x, top + 1, z)] = LEAVES

    def get(self, pos):
        return self.blocks.get(tuple(pos))

    def can_break(self, pos):
        b = self.get(pos)
        return b is not None and b != BEDROCK

    def break_block(self, pos):
        """Return True if removed."""
        pos = tuple(pos)
        if self.can_break(pos):
            del self.blocks[pos]
            return True
        return False

    def place_block(self, pos, block_id):
        """Return True if placed (empty cell only)."""
        pos = tuple(pos)
        if pos in self.blocks:
            return False
        if block_id not in BLOCK_NAMES_AR:
            return False
        self.blocks[pos] = block_id
        return True

    def count(self):
        return len(self.blocks)
