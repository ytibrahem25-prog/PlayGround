[app]
title = Ibrahim Amer Minecraft
package.name = ibrahimamerminecraft
package.domain = org.ibrahimamer.minecraft
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0
requirements = python3, ursina, pillow, numpy, panda3d, arabic-reshaper, python-bidi
orientation = landscape
fullscreen = 0
android.api = 31
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET
p4a.bootstrap = sdl2
# SDL2 bootstrap gives touch input as mouse events, so on-screen buttons work.
# NOTE: Ursina/Panda3D on Android needs a device with OpenGL ES 2+. Test with:
#   buildozer android debug
#   buildozer android deploy run
# If Ursina fails on some devices, the voxel logic in world_core.py is
# engine-independent and can be reused with a Kivy renderer.

[buildozer]
log_level = 2
warn_on_root = 1
