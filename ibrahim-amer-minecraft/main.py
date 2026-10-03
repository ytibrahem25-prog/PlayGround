# -*- coding: utf-8 -*-
"""Ibrahim Amer Minecraft — 3D voxel game (Kivy, desktop + Android APK).
Game name: Ibrahim Amer Minecraft | (c) Ibrahim Amer
Controls (mobile): left D-pad = move, drag screen = look, Jump/Break/Place buttons.
Controls (desktop): WASD/arrows move, Space jump, drag mouse look,
  left-click break, right-click place, 1-5 select block, B break, P place.
"""
import math
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Quad, Rectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from world import (VoxelWorld, GRASS, DIRT, STONE, WOOD, LEAVES,
                   BLOCK_NAMES, BLOCK_COLORS, view_direction, move_axis)
from renderer import project, cube_faces, FACE_SHADE, FACE_NEIGHBOUR

GAME_TITLE = "Ibrahim Amer Minecraft"
COPYRIGHT = "© Ibrahim Amer"

SELECTABLE = [GRASS, DIRT, STONE, WOOD, LEAVES]
RENDER_DIST = 11
WALK_SPEED = 4.6
JUMP_VEL = 8.2
GRAVITY = -23.0
EYE = 1.62


class GameView(Widget):
    def __init__(self, hud_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.world = VoxelWorld(sx=24, sy=14, sz=24)
        self.world.generate(seed=7)
        cx, cz = self.world.sx / 2, self.world.sz / 2
        top = self.world.column_height(int(cx), int(cz))
        self.pos_p = [cx + 0.5, float(top + 1), cz + 0.5]
        self.vel_y = 0.0
        self.on_ground = False
        self.yaw = math.pi * 0.25
        self.pitch = -0.08
        self.move = {"f": False, "b": False, "l": False, "r": False}
        self.keys = set()
        self.selected = GRASS
        self.target_hit = None
        self.target_prev = None
        self.hud_callback = hud_callback
        # look-drag state
        self._drag = None  # (touch_id, x, y, time, moved)
        self._mouse_down = None
        Clock.schedule_interval(self.update, 1.0 / 30.0)

    # ---------- actions ----------
    def break_block(self):
        if self.target_hit:
            x, y, z = self.target_hit
            # don't delete the floor under bedrock level y=0? allow all but keep y>=0
            self.world.set(x, y, z, 0)
            self.target_hit = None

    def place_block(self):
        if self.target_prev is not None:
            x, y, z = self.target_prev
            if self.world.get(x, y, z) != 0:
                return
            # avoid placing inside the player
            px, py, pz = self.pos_p
            if (math.floor(px - 0.3) <= x <= math.floor(px + 0.3)
                    and math.floor(py) <= y <= math.floor(py + 1.8)
                    and math.floor(pz - 0.3) <= z <= math.floor(pz + 0.3)):
                # check real overlap
                if (x + 1 > px - 0.3 and x < px + 0.3
                        and y + 1 > py and y < py + 1.8
                        and z + 1 > pz - 0.3 and z < pz + 0.3):
                    return
            self.world.set(x, y, z, self.selected)

    def eye_pos(self):
        return (self.pos_p[0], self.pos_p[1] + EYE, self.pos_p[2])

    # ---------- input: touch look ----------
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        # mouse (desktop): left=maybe break, right=maybe place, drag=look
        if "button" in touch.profile and touch.button in ("left", "right"):
            self._mouse_down = (touch.button, touch.x, touch.y, time.time(), 0.0)
            touch.grab(self)
            return True
        # finger: start look-drag
        self._drag = (touch.uid, touch.x, touch.y)
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        if self._mouse_down is not None and "button" in touch.profile:
            _, x0, y0, _, _ = self._mouse_down
            dx, dy = touch.x - x0, touch.y - y0
            btn, ox, oy, t0, moved = self._mouse_down
            self._mouse_down = (btn, touch.x, touch.y, t0, moved + abs(dx) + abs(dy))
            self.yaw += dx * 0.006
            self.pitch = max(-1.45, min(1.45, self.pitch + dy * 0.006))
            return True
        if self._drag is not None:
            _, px, py = self._drag
            dx, dy = touch.x - px, touch.y - py
            self._drag = (touch.uid, touch.x, touch.y)
            self.yaw += dx * 0.0075
            self.pitch = max(-1.45, min(1.45, self.pitch + dy * 0.0075))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        if self._mouse_down is not None and "button" in touch.profile:
            btn, _, _, t0, moved = self._mouse_down
            self._mouse_down = None
            if moved < 14 and time.time() - t0 < 0.4:
                if btn == "left":
                    self.break_block()
                elif btn == "right":
                    self.place_block()
            touch.ungrab(self)
            return True
        if self._drag is not None:
            self._drag = None
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    # ---------- per-frame update + render ----------
    def update(self, dt):
        dt = min(dt, 0.05)
        self._physics(dt)
        self._update_target()
        self._render()
        if self.hud_callback:
            self.hud_callback()

    def _input_dir(self):
        f = (self.move["f"] or "w" in self.keys or "up" in self.keys)
        b = (self.move["b"] or "s" in self.keys or "down" in self.keys)
        l = (self.move["l"] or "a" in self.keys or "left" in self.keys)
        r = (self.move["r"] or "d" in self.keys or "right" in self.keys)
        return (1 if f else 0) - (1 if b else 0), (1 if r else 0) - (1 if l else 0)

    def _physics(self, dt):
        fw, st = self._input_dir()
        sy, cyw = math.sin(self.yaw), math.cos(self.yaw)
        # forward = (-sin yaw, -cos yaw), right = (cos yaw, -sin yaw)
        mx = (-sy) * fw + cyw * st
        mz = (-cyw) * fw + (-sy) * st
        n = math.hypot(mx, mz)
        if n > 0:
            mx, mz = mx / n * WALK_SPEED * dt, mz / n * WALK_SPEED * dt
        else:
            mx = mz = 0.0
        # split into substeps to avoid tunnelling
        steps = 2
        for _ in range(steps):
            self.pos_p = move_axis(self.world, self.pos_p, mx / steps, 0, 0)
            self.pos_p = move_axis(self.world, self.pos_p, 0, 0, mz / steps)
        # gravity / jump
        self.vel_y += GRAVITY * dt
        self.vel_y = max(self.vel_y, -25)
        old_y = self.pos_p[1]
        new_p = move_axis(self.world, self.pos_p, 0, self.vel_y * dt, 0)
        if new_p[1] >= old_y - 1e-6 and self.vel_y <= 0 and self._is_supported(new_p):
            # landed (blocked downward)
            pass
        self.pos_p = new_p
        # ground check: probe slightly below feet
        below = self.world.is_solid(math.floor(self.pos_p[0]),
                                    math.floor(self.pos_p[1] - 0.05),
                                    math.floor(self.pos_p[2]))
        # also check corners
        if not below:
            below = self._is_supported(self.pos_p)
        if below and self.vel_y < 0:
            # snap feet to top of block
            top = math.floor(self.pos_p[1] - 0.05) + 1
            if self.pos_p[1] < top + 0.05:
                self.pos_p[1] = float(top)
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = self.vel_y == 0 and below
        # void safety
        if self.pos_p[1] < 0:
            self.pos_p[1] = 0
            self.vel_y = 0
            self.on_ground = True
        # keep inside borders
        self.pos_p[0] = max(1.0, min(self.world.sx - 1.0, self.pos_p[0]))
        self.pos_p[2] = max(1.0, min(self.world.sz - 1.0, self.pos_p[2]))

    def _is_supported(self, p):
        for ox in (-0.3, 0.3):
            for oz in (-0.3, 0.3):
                if self.world.is_solid(math.floor(p[0] + ox),
                                       math.floor(p[1] - 0.05),
                                       math.floor(p[2] + oz)):
                    return True
        return False

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_VEL
            self.on_ground = False

    def _update_target(self):
        o = self.eye_pos()
        d = view_direction(self.yaw, self.pitch)
        hit, prev = self.world.raycast(o, d, max_dist=6.0)
        self.target_hit, self.target_prev = hit, prev

    # ---------- rendering ----------
    def _render(self):
        w, h = self.width, self.height
        if w < 10 or h < 10:
            return
        cx, cyy = w / 2.0, h / 2.0
        focal = min(w, h) * 1.1
        ex, ey, ez = self.eye_pos()
        faces = []
        px, pz = self.pos_p[0], self.pos_p[2]
        r2 = RENDER_DIST * RENDER_DIST
        for (x, y, z), bid in self.world.blocks.items():
            dx, dz = (x + 0.5) - px, (z + 0.5) - pz
            if dx * dx + dz * dz > r2 + 4:
                continue
            base = BLOCK_COLORS.get(bid, (1, 1, 1))
            corners = cube_faces(x, y, z)
            for fname, pts in corners.items():
                ox, oy, oz = FACE_NEIGHBOUR[fname]
                if self.world.is_solid(x + ox, y + oy, z + oz):
                    continue
                # backface cull: face centre vs camera
                fcx = sum(p[0] for p in pts) / 4.0
                fcy = sum(p[1] for p in pts) / 4.0
                fcz = sum(p[2] for p in pts) / 4.0
                proj = []
                ok = True
                depth = 0.0
                for (wx, wy, wz) in pts:
                    pr = project(wx, wy, wz, ex, ey, ez,
                                 self.yaw, self.pitch, cx, cyy, focal)
                    if pr is None:
                        ok = False
                        break
                    proj.append(pr)
                    depth += pr[2]
                if not ok:
                    continue
                depth /= 4.0
                shade = FACE_SHADE[fname]
                if fname == "top" and bid == GRASS:
                    col = (0.30 * shade + 0.08, 0.72 * shade + 0.08, 0.24 * shade)
                else:
                    col = (base[0] * shade, base[1] * shade, base[2] * shade)
                flat = []
                for (sx_, syy, _) in proj:
                    flat += [sx_, syy]
                faces.append((depth, col, flat))
                if len(faces) > 1600:
                    break
            if len(faces) > 1600:
                break
        faces.sort(key=lambda f: f[0], reverse=True)

        self.canvas.clear()
        with self.canvas:
            # sky
            Color(0.52, 0.78, 0.95, 1)
            Rectangle(pos=self.pos, size=self.size)
            # sun
            Color(1, 0.95, 0.7, 1)
            Rectangle(pos=(self.x + w * 0.78, self.y + h * 0.78),
                      size=(min(w, h) * 0.08, min(w, h) * 0.08))
            for depth, col, flat in faces:
                Color(col[0], col[1], col[2], 1)
                Quad(points=flat)
            # target highlight
            if self.target_hit:
                hx, hy, hz = self.target_hit
                corners = cube_faces(hx, hy, hz)
                Color(1, 1, 1, 1)
                for fname, pts in corners.items():
                    prs = [project(wx, wy, wz, ex, ey, ez, self.yaw,
                                   self.pitch, cx, cyy, focal)
                           for (wx, wy, wz) in pts]
                    if all(p is not None for p in prs):
                        Line(points=[c for p in prs + [prs[0]] for c in p[:2]],
                             width=1.5)


class MinecraftApp(App):
    title = GAME_TITLE

    def build(self):
        Window.clearcolor = (0.52, 0.78, 0.95, 1)
        root = FloatLayout()
        self.view = GameView(hud_callback=self.refresh_hud, size_hint=(1, 1))
        root.add_widget(self.view)

        # ---- top bar ----
        top = BoxLayout(size_hint=(1, None), height=44, pos_hint={"top": 1},
                        padding=6, spacing=6)
        top.add_widget(Label(text=GAME_TITLE, bold=True, color=(0.1, 0.15, 0.2, 1),
                             size_hint_x=0.55, halign="left"))
        self.info = Label(text="", color=(0.15, 0.2, 0.25, 1), size_hint_x=0.45,
                          font_size=13)
        top.add_widget(self.info)
        root.add_widget(top)

        # ---- crosshair ----
        root.add_widget(Label(text="+", font_size=30, color=(1, 1, 1, 1),
                              size_hint=(None, None), size=(40, 40),
                              pos_hint={"center_x": 0.5, "center_y": 0.5}))
        self.hint = Label(text="", font_size=12, color=(1, 1, 1, 1),
                          size_hint=(1, None), height=22, pos_hint={"top": 0.93})
        root.add_widget(self.hint)

        # ---- left D-pad ----
        pad = FloatLayout(size_hint=(None, None), size=(190, 190),
                          pos_hint={"x": 0.02, "y": 0.16})
        btn = dict(font_size=22, size_hint=(None, None), size=(58, 58),
                   background_color=(0, 0, 0, 0.35), color=(1, 1, 1, 1))
        b_up = Button(text="▲", pos_hint={"center_x": 0.5, "center_y": 0.78}, **btn)
        b_dn = Button(text="▼", pos_hint={"center_x": 0.5, "center_y": 0.22}, **btn)
        b_lf = Button(text="◀", pos_hint={"center_x": 0.22, "center_y": 0.5}, **btn)
        b_rt = Button(text="▶", pos_hint={"center_x": 0.78, "center_y": 0.5}, **btn)
        for b, k in ((b_up, "f"), (b_dn, "b"), (b_lf, "l"), (b_rt, "r")):
            b.bind(on_press=self._mk_move(k, True), on_release=self._mk_move(k, False))
            pad.add_widget(b)
        root.add_widget(pad)

        # ---- right action buttons ----
        acts = FloatLayout(size_hint=(None, None), size=(200, 260),
                           pos_hint={"right": 0.98, "y": 0.14})
        ab = dict(font_size=16, size_hint=(None, None), size=(88, 58), color=(1, 1, 1, 1))
        b_jump = Button(text="⬆ قفز", pos_hint={"center_x": 0.5, "center_y": 0.82},
                        background_color=(0.2, 0.6, 0.25, 0.85), **ab)
        b_brk = Button(text="⛏ كسر", pos_hint={"center_x": 0.26, "center_y": 0.45},
                       background_color=(0.75, 0.3, 0.2, 0.85), **ab)
        b_plc = Button(text="🧱 وضع", pos_hint={"center_x": 0.76, "center_y": 0.45},
                       background_color=(0.25, 0.45, 0.8, 0.85), **ab)
        b_jump.bind(on_press=lambda *_: self.view.jump())
        b_brk.bind(on_press=lambda *_: self.view.break_block())
        b_plc.bind(on_press=lambda *_: self.view.place_block())
        acts.add_widget(b_jump)
        acts.add_widget(b_brk)
        acts.add_widget(b_plc)
        root.add_widget(acts)

        # ---- block selector (bottom centre) ----
        bar = BoxLayout(size_hint=(None, None), size=(330, 56),
                        pos_hint={"center_x": 0.5, "y": 0.015}, spacing=6)
        self.bar_buttons = {}
        for bid in SELECTABLE:
            b = Button(text=BLOCK_NAMES[bid][:4], font_size=13)
            c = BLOCK_COLORS[bid]
            b.background_color = (c[0], c[1], c[2], 1)
            b.bind(on_press=self._mk_select(bid))
            self.bar_buttons[bid] = b
            bar.add_widget(b)
        root.add_widget(bar)

        # ---- copyright ----
        root.add_widget(Label(text=COPYRIGHT, font_size=13, color=(1, 1, 1, 1),
                              size_hint=(None, None), size=(200, 24),
                              pos_hint={"right": 0.99, "top": 0.99}))

        self._bind_keyboard()
        self.refresh_hud()
        return root

    def _mk_move(self, key, val):
        def _cb(*_):
            self.view.move[key] = val
        return _cb

    def _mk_select(self, bid):
        def _cb(*_):
            self.view.selected = bid
            self.refresh_hud()
        return _cb

    def _bind_keyboard(self):
        Window.bind(on_key_down=self._key(True), on_key_up=self._key(False))

    def _key(self, down):
        def _cb(win, code, *args):
            name = None
            if len(args) >= 1 and isinstance(args[0], str):
                name = args[0].lower()
            mapping = {276: "left", 275: "right", 273: "up", 274: "down",
                       32: "space", 119: "w", 97: "a", 115: "s", 100: "d",
                       98: "b", 112: "p"}
            key = mapping.get(code, name)
            if key in ("w", "a", "s", "d", "up", "down", "left", "right"):
                if down:
                    self.view.keys.add(key)
                else:
                    self.view.keys.discard(key)
                return True
            if down and key == "space":
                self.view.jump()
                return True
            if down and key == "b":
                self.view.break_block()
                return True
            if down and key == "p":
                self.view.place_block()
                return True
            if down and key in ("1", "2", "3", "4", "5"):
                self.view.selected = SELECTABLE[int(key) - 1]
                self.refresh_hud()
                return True
            return False
        return _cb

    def refresh_hud(self):
        v = self.view
        tgt = "aim: %s" % (BLOCK_NAMES.get(v.world.get(*v.target_hit), "?")
                           if v.target_hit else "—")
        sel = BLOCK_NAMES.get(v.selected, "?")
        self.info.text = "[%s] %s | %.0f,%.0f,%.0f" % (sel, tgt, *v.pos_p)
        self.hint.text = ("WASD move • Space jump • drag look • L-click break • "
                          "R-click place • 1-5 blocks" if not self._is_touch()
                          else "D-pad move • drag look • ⛏/🧱 act • bottom bar blocks")
        for bid, b in self.bar_buttons.items():
            c = BLOCK_COLORS[bid]
            sel_ = (bid == v.selected)
            b.background_color = (c[0], c[1], c[2], 1 if sel_ else 0.55)
            b.text = ("▶ " if sel_ else "") + BLOCK_NAMES[bid][:4]

    @staticmethod
    def _is_touch():
        try:
            from kivy.utils import platform
            return platform == "android"
        except Exception:
            return False


if __name__ == "__main__":
    MinecraftApp().run()
