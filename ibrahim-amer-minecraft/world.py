"""Voxel world data + generation + physics helpers.
Pure Python — no Kivy dependency so it can be unit-tested on desktop/CI.
"""
import math
import random

# Block ids
GRASS = 1
DIRT = 2
STONE = 3
WOOD = 4
LEAVES = 5

BLOCK_NAMES = {
    GRASS: "Grass",
    DIRT: "Dirt",
    STONE: "Stone",
    WOOD: "Wood",
    LEAVES: "Leaves",
}

# Base colors (r, g, b) for each block, per face shading is applied in main.py
BLOCK_COLORS = {
    GRASS: (0.38, 0.72, 0.26),
    DIRT: (0.55, 0.38, 0.22),
    STONE: (0.55, 0.55, 0.58),
    WOOD: (0.45, 0.30, 0.15),
    LEAVES: (0.20, 0.55, 0.22),
}


class VoxelWorld:
    def __init__(self, sx=24, sy=12, sz=24):
        self.sx = sx
        self.sy = sy
        self.sz = sz
        self.blocks = {}  # (x, y, z) -> block_id

    # ---- basic access ----
    def get(self, x, y, z):
        return self.blocks.get((int(x), int(y), int(z)), 0)

    def set(self, x, y, z, bid):
        x, y, z = int(x), int(y), int(z)
        if not (0 <= x < self.sx and 0 <= z < self.sz and 0 <= y < self.sy):
            return False
        if bid == 0:
            self.blocks.pop((x, y, z), None)
        else:
            self.blocks[(x, y, z)] = bid
        return True

    def is_solid(self, x, y, z):
        return self.get(x, y, z) != 0

    def is_exposed(self, x, y, z):
        """A block needs rendering only if at least one neighbour is air."""
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                           (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            if not self.is_solid(x + dx, y + dy, z + dz):
                return True
        return False

    # ---- generation ----
    def generate(self, seed=7):
        rnd = random.Random(seed)
        self.blocks.clear()
        for x in range(self.sx):
            for z in range(self.sz):
                h = 2 + int(
                    1.2 * math.sin(x * 0.45) * math.cos(z * 0.45)
                    + 0.8 * math.sin(x * 0.2 + 1.7) * math.sin(z * 0.23 + 0.6)
                )
                h = max(1, min(h, self.sy - 5))
                for y in range(h + 1):
                    if y == h:
                        self.set(x, y, z, GRASS)
                    elif y >= h - 2:
                        self.set(x, y, z, DIRT)
                    else:
                        self.set(x, y, z, STONE)
        # trees
        for _ in range(5):
            tx = rnd.randint(3, self.sx - 4)
            tz = rnd.randint(3, self.sz - 4)
            top = self.column_height(tx, tz)
            if top < 0:
                continue
            trunk = rnd.randint(3, 4)
            for i in range(1, trunk + 1):
                self.set(tx, top + i, tz, WOOD)
            # leaf blob (uses LEAVES)
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    for dy in range(trunk - 2, trunk + 2):
                        if abs(dx) + abs(dz) + abs(dy - trunk + 1) <= 4:
                            lx, ly, lz = tx + dx, top + dy, tz + dz
                            if self.get(lx, ly, lz) == 0 and abs(dx) + abs(dz) > 0 or dy == trunk + 1:
                                if self.get(lx, ly, lz) == 0:
                                    self.set(lx, ly, lz, LEAVES)
            self.set(tx, top + trunk + 1, tz, LEAVES)

    def column_height(self, x, z):
        for y in range(self.sy - 1, -1, -1):
            if self.is_solid(x, y, z):
                return y
        return -1

    # ---- raycast (Amanatides & Woo DDA) ----
    def raycast(self, origin, direction, max_dist=6.0):
        """Return (hit_xyz, prev_empty_xyz) or (None, None)."""
        x, y, z = origin
        dx, dy, dz = direction
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length == 0:
            return None, None
        dx, dy, dz = dx / length, dy / length, dz / length

        ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        step_z = 1 if dz > 0 else -1

        def boundary(v, d, s):
            if d == 0:
                return float("inf")
            if s > 0:
                return (math.floor(v) + 1 - v) / abs(d)
            return (v - math.floor(v)) / abs(d)

        t_max_x = boundary(x, dx, step_x)
        t_max_y = boundary(y, dy, step_y)
        t_max_z = boundary(z, dz, step_z)
        t_delta_x = abs(1.0 / dx) if dx != 0 else float("inf")
        t_delta_y = abs(1.0 / dy) if dy != 0 else float("inf")
        t_delta_z = abs(1.0 / dz) if dz != 0 else float("inf")

        t = 0.0
        prev = (ix, iy, iz)
        while t <= max_dist:
            if self.is_solid(ix, iy, iz):
                return (ix, iy, iz), prev
            prev = (ix, iy, iz)
            if t_max_x < t_max_y and t_max_x < t_max_z:
                ix += step_x
                t = t_max_x
                t_max_x += t_delta_x
            elif t_max_y < t_max_z:
                iy += step_y
                t = t_max_y
                t_max_y += t_delta_y
            else:
                iz += step_z
                t = t_max_z
                t_max_z += t_delta_z
        return None, None


def view_direction(yaw, pitch):
    """yaw=0 looks toward -Z, pitch>0 looks up. Returns unit vector."""
    cp = math.cos(pitch)
    return (
        -math.sin(yaw) * cp,
        math.sin(pitch),
        -math.cos(yaw) * cp,
    )


def move_axis(world, pos, dx, dy, dz, half_w=0.3, height=1.8):
    """Move player AABB along one axis with collision. pos is feet [x,y,z].
    Returns new pos list. Axis move is applied only on the non-zero component.
    """
    nx, ny, nz = pos[0] + dx, pos[1] + dy, pos[2] + dz
    # AABB corners to test
    for ox in (-half_w, half_w):
        for oz in (-half_w, half_w):
            for oy in (0.0, height / 2.0, height):
                bx = math.floor(nx + ox)
                by = math.floor(ny + oy)
                bz = math.floor(nz + oz)
                if world.is_solid(bx, by, bz):
                    return list(pos)  # blocked: cancel whole axis step
    # keep inside world + above void
    if ny < 0:
        ny = 0
    return [nx, ny, nz]
