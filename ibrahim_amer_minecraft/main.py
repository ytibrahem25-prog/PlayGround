#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ibrahim Amer Minecraft — 3D voxel game (Desktop + touch-ready for Android APK)
- Ursina Engine based, Minecraft-like: cubes world, move/jump, touch camera,
  break/place blocks, Grass/Dirt/Stone/Wood selection, on-screen mobile buttons.
- Title: Ibrahim Amer Minecraft | Rights: © Ibrahim Amer

Run (desktop):
    pip install -r requirements.txt
    python main.py

Android (APK via buildozer, see buildozer.spec + README_AR.md):
    buildozer android debug
Touch buttons already work with finger taps (tap = click, drag = look around).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from world_core import (
    GAME_TITLE, COPYRIGHT, GRASS, DIRT, STONE, WOOD, LEAVES, BEDROCK,
    BLOCK_NAMES_AR, BUILDABLE_BLOCKS, VoxelStore, terrain_height,
)
from textures import generate_textures

ASSETS = os.path.join(HERE, "assets")
WORLD_SIZE = 32
WORLD_SEED = 7

# ---------------------------------------------------------------- textures
texture_paths = generate_textures(ASSETS)
USE_TEXTURES = bool(texture_paths)

# block -> texture filename (inside assets/)
BLOCK_TEXTURE = {
    GRASS: "grass_side.png",
    DIRT: "dirt.png",
    STONE: "stone.png",
    WOOD: "wood_side.png",
    LEAVES: "leaves.png",
    BEDROCK: "bedrock.png",
}
# fallback flat colors (ursina color)
BLOCK_TINT = {
    GRASS: None, DIRT: None, STONE: None,
    WOOD: None, LEAVES: None, BEDROCK: None,
}

# ---------------------------------------------------------------- ursina app
try:
    from ursina import (
        Ursina, Entity, Button, Text, DirectionalLight, AmbientLight,
        held_keys, mouse, camera, scene, window, color, Vec2, Vec3, destroy, raycast,
    )
    from ursina.prefabs.first_person_controller import FirstPersonController
except ImportError:
    print("ERROR: ursina is not installed.")
    print("Install with:  pip install ursina pillow numpy")
    sys.exit(1)

app = Ursina(title=GAME_TITLE, borderless=False, fullscreen=False)
window.title = GAME_TITLE
window.size = (960, 600)
window.fps_counter.enabled = True
window.exit_button.visible = False

# --- Arabic font + shaping (Panda3D default font has no Arabic glyphs,
# --- and needs reshaping for correct letter connections / RTL order) ---
AR_FONT_ABS = os.path.join(ASSETS, "Amiri-Regular.ttf")
# ursina resolves fonts relative to the asset folder (project dir), so use a
# relative path here; absolute paths are not found by its font search.
AR_FONT = os.path.join("assets", "Amiri-Regular.ttf")

def A(s):
    """Prepare Arabic (or mixed) string for in-game display."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(s))
    except Exception:
        return s

try:
    if os.path.isfile(AR_FONT_ABS):
        Text.default_font = AR_FONT
except Exception:
    pass

# Flat day-blue sky via clear color (robust on desktop + mobile GPUs).
# (Ursina's Sky dome is skipped: it fails to render once thousands of voxel
# entities exist in the scene.)
window.color = color.rgb32(115, 185, 235)
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
AmbientLight(color=color.rgba32(180, 180, 180, 255))

# ---------------------------------------------------------------- state
store = VoxelStore().generate(size=WORLD_SIZE, seed=WORLD_SEED, with_trees=True)
selected_block = GRASS
voxel_entities = {}   # (x,y,z) -> Voxel entity
ui_buttons = []       # all touch/UI buttons (to separate world clicks from UI taps)
_forced_keys = set()

HOTBAR_ORDER = [GRASS, DIRT, STONE, WOOD]
HOTBAR_LABEL = {GRASS: A("1 عشب"), DIRT: A("2 تراب"), STONE: A("3 حجر"), WOOD: A("4 خشب")}
HOTBAR_COLOR = {
    GRASS: color.rgb32(106, 190, 48),
    DIRT: color.rgb32(134, 96, 67),
    STONE: color.rgb32(150, 150, 150),
    WOOD: color.rgb32(120, 72, 20),
}


def tex_for(block_id):
    if USE_TEXTURES:
        return BLOCK_TEXTURE.get(block_id)
    return None


class Voxel(Button):
    """One cube in the world. Button gives us hover/click + collider for free."""

    def __init__(self, pos, block_id):
        t = tex_for(block_id)
        tint = BLOCK_TINT.get(block_id) or color.white
        # ursina loads textures from application asset folder; use relative path
        super().__init__(
            parent=scene,
            position=Vec3(*pos),
            model="cube",
            origin_y=0.5,
            texture=t,
            color=tint,
            highlight_color=color.rgb32(255, 255, 200),
            collider="box",
        )
        self.block_id = block_id

    def input(self, key):
        if not self.hovered:
            return
        if ui_hovered():   # tap was on a touch button, not on the world
            return
        if key == "left mouse down":
            do_break(self)
        elif key == "right mouse down":
            do_place(self)


def ui_hovered():
    try:
        return any(b.hovered for b in ui_buttons if b and b.enabled)
    except Exception:
        return False


def touch_held(btn):
    try:
        return bool(btn and btn.enabled and btn.hovered and mouse.left)
    except Exception:
        return False


def add_voxel(pos, block_id):
    pos = tuple(pos)
    if pos in voxel_entities:
        return voxel_entities[pos]
    v = Voxel(pos, block_id)
    voxel_entities[pos] = v
    store.blocks[pos] = block_id
    return v


def remove_voxel(voxel):
    pos = (int(round(voxel.position.x)), int(round(voxel.position.y)), int(round(voxel.position.z)))
    if not store.can_break(pos):
        return False
    destroy(voxel)
    voxel_entities.pop(pos, None)
    store.break_block(pos)
    return True


def do_break(voxel):
    if voxel is None:
        return
    # bedrock is unbreakable
    if voxel.block_id == BEDROCK:
        msg.text = A("لا يمكن كسر طبقة الأساس!")
        return
    if remove_voxel(voxel):
        msg.text = ""


def do_place(hit_voxel):
    """Place selected block adjacent to hit voxel (on the hit face)."""
    global selected_block
    if hit_voxel is None:
        return
    try:
        n = mouse.normal
    except Exception:
        n = None
    if n is None:
        pos = (int(hit_voxel.position.x), int(hit_voxel.position.y + 1), int(hit_voxel.position.z))
    else:
        pos = (
            int(round(hit_voxel.position.x + n.x)),
            int(round(hit_voxel.position.y + n.y)),
            int(round(hit_voxel.position.z + n.z)),
        )
    if pos in voxel_entities:
        return
    # don't place inside the player
    try:
        if player and abs(pos[0] - player.position.x) < 0.7 and abs(pos[2] - player.position.z) < 0.7 \
                and abs(pos[1] - player.position.y) < 1.8:
            msg.text = A("لا يمكن البناء داخل اللاعب!")
            return
    except Exception:
        pass
    add_voxel(pos, selected_block)


# ---------------------------------------------------------------- build world
for (pos, bid) in list(store.blocks.items()):
    v = Voxel(pos, bid)
    voxel_entities[pos] = v

# spawn above center
spawn_y = terrain_height(0, 0, WORLD_SEED) + 3
player = FirstPersonController(model="cube", visible=False)
player.position = Vec3(0, spawn_y, 0)
player.jump_height = 2.2
player.gravity = 1.0
try:
    player.mouse_sensitivity = Vec2(60, 60)
except Exception:
    pass
player.cursor.visible = False
# On Android there is no physical mouse: keep it unlocked so touch-drag look
# (see update()) stays active. On desktop the first world click locks it.
try:
    if bool(os.getenv("ANDROID_ARGUMENT")) or "android" in sys.platform:
        mouse.locked = False
except Exception:
    pass

# ---------------------------------------------------------------- HUD: title / copyright / crosshair / help
title = Text(text=GAME_TITLE, position=(0, 0.46), origin=(0, 0),
             scale=1.4, color=color.azure, background=False)
rights = Text(text=COPYRIGHT, position=(0.5, -0.46), origin=(1, 0),
              scale=0.9, color=color.light_gray)
rights.x = 0.5
crosshair = Text(text="+", position=(0, 0), origin=(0, 0), scale=2, color=color.white)
msg = Text(text="", position=(0, 0.38), origin=(0, 0), scale=1, color=color.yellow)
help_text = Text(
    text=A("WASD حركة | مسافة قفز | كليك يسار كسر | كليك يمين بناء | 1-4 اختيار بلوك"),
    position=(0, -0.42), origin=(0, 0), scale=0.85, color=color.light_gray,
)

selected_label = Text(text=A("البلوك: عشب"), position=(-0.5, 0.42), origin=(-1, 0),
                      scale=1, color=color.white)


def refresh_hotbar():
    for b in hotbar_btns:
        bid = b.block_id
        if bid == selected_block:
            b.color = color.white
            b.scale = (0.12, 0.07)
        else:
            b.color = color.rgb32(210, 210, 210)
            b.scale = (0.11, 0.065)
    _name = {GRASS: "عشب", DIRT: "تراب", STONE: "حجر", WOOD: "خشب"}.get(selected_block, "")
    selected_label.text = A("البلوك: " + _name)


def select_block(bid):
    global selected_block
    if bid in HOTBAR_ORDER:
        selected_block = bid
        refresh_hotbar()


# ---------------------------------------------------------------- touch controls (mobile buttons)
def mk_button(**kw):
    b = Button(**kw)
    ui_buttons.append(b)
    return b


# movement pad (bottom-left) — Arabic words (clearest on mobile).
# NOTE: camera.ui visible x-range is about ±0.62, and semi-transparent UI
# colors render washed-out, so all buttons use OPAQUE colors here.
_DPAD = color.rgb32(40, 40, 40)
btn_fwd = mk_button(text=A("أمام"), position=(-0.40, -0.16), scale=(0.10, 0.07), color=_DPAD)
btn_back = mk_button(text=A("خلف"), position=(-0.40, -0.34), scale=(0.10, 0.07), color=_DPAD)
btn_left = mk_button(text=A("يسار"), position=(-0.51, -0.25), scale=(0.10, 0.07), color=_DPAD)
btn_right = mk_button(text=A("يمين"), position=(-0.29, -0.25), scale=(0.10, 0.07), color=_DPAD)

# actions (bottom-right) — opaque colors (see note above)
btn_jump = mk_button(text=A("قفز"), position=(0.40, -0.25), scale=(0.11, 0.07), color=color.rgb32(46, 139, 46))
btn_break = mk_button(text=A("كسر"), position=(0.28, -0.13), scale=(0.11, 0.07), color=color.rgb32(178, 60, 60))
btn_place = mk_button(text=A("بناء"), position=(0.42, -0.13), scale=(0.11, 0.07), color=color.rgb32(60, 90, 180))

btn_jump.on_click = lambda: (player.jump() if hasattr(player, "jump") else None)
btn_break.on_click = lambda: do_break(mouse.hovered_entity if isinstance(mouse.hovered_entity, Voxel) else None)
btn_place.on_click = lambda: do_place(mouse.hovered_entity if isinstance(mouse.hovered_entity, Voxel) else None)

# hotbar (bottom-center): Grass / Dirt / Stone / Wood
hotbar_btns = []
for i, bid in enumerate(HOTBAR_ORDER):
    t = tex_for(bid)
    b = mk_button(text=HOTBAR_LABEL[bid], position=(-0.195 + i * 0.13, -0.36),
                  scale=(0.11, 0.065), color=color.rgb32(210, 210, 210),
                  texture=t if USE_TEXTURES else None, text_color=color.black)
    b.block_id = bid
    _bid = bid
    b.on_click = (lambda v=_bid: select_block(v))
    hotbar_btns.append(b)
refresh_hotbar()

# look hint (top-right)
look_hint = Text(text=A("اسحب للتدوير"), position=(0.5, 0.42), origin=(1, 0),
                 scale=0.85, color=color.light_gray)

# ---------------------------------------------------------------- input & update
TOUCH_MAP = [(btn_fwd, "w"), (btn_back, "s"), (btn_left, "a"), (btn_right, "d")]


def input(key):
    if key in ("1", "2", "3", "4"):
        select_block(HOTBAR_ORDER[int(key) - 1])
    if key == "escape":
        mouse.locked = False
    if key == "left mouse down" and not ui_hovered():
        # desktop: lock mouse for FPS look on first world click
        try:
            import platform
            on_android = bool(os.getenv("ANDROID_ARGUMENT")) or "android" in sys.platform
            if not on_android and not mouse.locked:
                mouse.locked = True
        except Exception:
            pass


def update():
    # --- touch movement: hold D-pad buttons to walk (merged with WASD) ---
    for btn, key in TOUCH_MAP:
        if touch_held(btn):
            held_keys[key] = 1
            _forced_keys.add(key)
        elif key in _forced_keys:
            held_keys[key] = 0
            _forced_keys.discard(key)

    # --- touch camera: drag on empty world area to look around ---
    try:
        if mouse.left and not ui_hovered():
            vx, vy = mouse.velocity
            if abs(vx) + abs(vy) > 0.0001 and not mouse.locked:
                player.rotation_y += vx * 60
                try:
                    player.camera_pivot.rotation_x -= vy * 60
                    player.camera_pivot.rotation_x = max(-85, min(85, player.camera_pivot.rotation_x))
                except Exception:
                    pass
    except Exception:
        pass


print(f"Starting {GAME_TITLE}  |  {COPYRIGHT}")
print(f"Blocks: {len(voxel_entities)}  |  textures={'png' if USE_TEXTURES else 'flat-color fallback'}")

# Optional test hook: IBRAHIM_SHOT=/tmp/shot.png xvfb-run -a python3 main.py
# takes a screenshot after 5s and quits (used for visual verification).
if os.getenv("IBRAHIM_SHOT"):
    from ursina import invoke, application
    _shot_path = os.getenv("IBRAHIM_SHOT")

    def _take_shot(path=_shot_path):
        try:
            from panda3d.core import Filename
            app.win.saveScreenshot(Filename(path))
            print("screenshot saved:", path)
        except Exception as e:
            print("screenshot failed:", e)
        invoke(application.quit, delay=0.5)

    invoke(_take_shot, delay=5.0)

app.run()
