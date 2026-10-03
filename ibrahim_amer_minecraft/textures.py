"""Procedural Minecraft-style textures (no external assets needed)."""
import os
import random

SIZE = 32

TEXTURE_FILES = {
    "grass_top": "grass_top.png",
    "grass_side": "grass_side.png",
    "dirt": "dirt.png",
    "stone": "stone.png",
    "wood_side": "wood_side.png",
    "wood_top": "wood_top.png",
    "leaves": "leaves.png",
    "bedrock": "bedrock.png",
}


def _noise_fill(base, vary, rng, size=SIZE):
    px = []
    for _ in range(size * size):
        d = rng.randint(-vary, vary)
        px.append(tuple(max(0, min(255, c + d)) for c in base))
    return px


def generate_textures(asset_dir="assets"):
    """Create PNGs in asset_dir. Returns dict name->filepath. Pure stdlib + PIL."""
    os.makedirs(asset_dir, exist_ok=True)
    try:
        from PIL import Image
    except ImportError:
        return {}  # caller falls back to plain colors

    rng = random.Random(2026)
    out = {}

    def save(name, pixels, size=SIZE):
        img = Image.new("RGB", (size, size))
        img.putdata(pixels)
        path = os.path.join(asset_dir, TEXTURE_FILES[name])
        img.save(path)
        out[name] = path
        return path

    # grass top: green noise
    save("grass_top", _noise_fill((106, 190, 48), 18, rng))
    # dirt: brown noise
    dirt_px = _noise_fill((134, 96, 67), 20, rng)
    save("dirt", dirt_px)
    # grass side: dirt + green top strip
    img_side = list(dirt_px)
    top_green = _noise_fill((106, 190, 48), 14, rng)
    for y in range(7):
        for x in range(SIZE):
            img_side[y * SIZE + x] = top_green[y * SIZE + x]
    save("grass_side", img_side)
    # stone
    save("stone", _noise_fill((136, 136, 136), 12, rng))
    # wood side: vertical stripes
    wood = []
    for y in range(SIZE):
        for x in range(SIZE):
            stripe = 14 if (x % 6 < 2) else 0
            v = 104 - stripe + rng.randint(-8, 8)
            wood.append((max(0, v - 20), max(0, v - 50), max(0, v - 80)))
    save("wood_side", wood)
    # wood top: rings
    rings = []
    for y in range(SIZE):
        for x in range(SIZE):
            d = abs(x - SIZE // 2) + abs(y - SIZE // 2)
            c = 150 if (d % 4 < 2) else 110
            c += rng.randint(-8, 8)
            rings.append((c, c - 45, c - 85))
    save("wood_top", rings)
    # leaves: dark green with holes
    leaves = []
    for _ in range(SIZE * SIZE):
        if rng.random() < 0.12:
            leaves.append((20, 60, 20))
        else:
            leaves.append((34 + rng.randint(-12, 18), 139 + rng.randint(-25, 15), 34 + rng.randint(-10, 10)))
    save("leaves", leaves)
    # bedrock
    save("bedrock", _noise_fill((60, 60, 60), 25, rng))
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    print(generate_textures(os.path.join(here, "assets")))
