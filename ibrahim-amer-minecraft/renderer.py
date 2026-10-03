"""3D -> 2D projection helpers (pure Python, no Kivy dependency)."""
import math


def project(wx, wy, wz, cam_x, cam_eye, cam_z, yaw, pitch, cx, cy, focal):
    """Transform world point to screen. Returns (sx, sy, depth) or None if behind."""
    dx = wx - cam_x
    dy = wy - cam_eye
    dz = wz - cam_z
    cyaw = math.cos(yaw)
    syaw = math.sin(yaw)
    # yaw rotation (yaw=0 looks toward -Z)
    xc = dx * cyaw + dz * syaw
    zc = -dx * syaw - dz * cyaw
    # pitch rotation
    cp = math.cos(pitch)
    sp = math.sin(pitch)
    yc = dy * cp - zc * sp
    zc2 = dy * sp + zc * cp
    if zc2 < 0.15:
        return None
    return (cx + (xc / zc2) * focal, cy + (yc / zc2) * focal, zc2)


def cube_faces(x, y, z):
    """Return dict face_name -> 4 corner points for unit cube at (x,y,z)."""
    x0, y0, z0 = x, y, z
    x1, y1, z1 = x + 1, y + 1, z + 1
    return {
        "top": [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        "bottom": [(x0, y0, z0), (x0, y0, z1), (x1, y0, z1), (x1, y0, z0)],
        "north": [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],  # -Z
        "south": [(x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1)],  # +Z
        "west": [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],   # -X
        "east": [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)],   # +X
    }


# face shading multipliers
FACE_SHADE = {
    "top": 1.0,
    "bottom": 0.45,
    "north": 0.72,
    "south": 0.72,
    "west": 0.82,
    "east": 0.82,
}

# which neighbour must be air for a face to be visible
FACE_NEIGHBOUR = {
    "top": (0, 1, 0),
    "bottom": (0, -1, 0),
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
}
