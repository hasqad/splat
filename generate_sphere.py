"""
Generates a half-red, half-blue sphere as a Gaussian Splatting .ply file.
Top half (y > 0) = red, bottom half (y < 0) = blue.

Usage: python generate_sphere.py
Output: sphere.ply
"""

import struct
import math

NUM_SPLATS = 50000
RADIUS     = 1.5
SCALE_TAN  = 0.09        # tangential scale (along surface)
SCALE_RAD  = 0.005       # radial scale (into/out of sphere surface, very thin)
OPACITY    = 0.95        # 0.0 - 1.0

SH_C0 = 0.28209479177387814

# Colors as linear 0-1 floats (R, G, B)
RED  = (0.95, 0.05, 0.05)
BLUE = (0.05, 0.25, 0.95)

def to_f_dc(r, g, b):
    """Convert linear RGB to spherical harmonics DC coefficients."""
    return ((r - 0.5) / SH_C0,
            (g - 0.5) / SH_C0,
            (b - 0.5) / SH_C0)

def fibonacci_sphere(n, radius):
    golden = (1 + math.sqrt(5)) / 2
    pts = []
    for i in range(n):
        theta = math.acos(1 - 2 * (i + 0.5) / n)
        phi   = 2 * math.pi * i / golden
        x = radius * math.sin(theta) * math.cos(phi)
        y = radius * math.sin(theta) * math.sin(phi)
        z = radius * math.cos(theta)
        pts.append((x, y, z))
    return pts


def normal_to_quaternion(nx, ny, nz):
    """Quaternion (w,x,y,z) that rotates the local Z-axis to align with (nx,ny,nz).
    This lets scale_2 control thickness in the normal direction."""
    if nz < -0.9999:
        return (0.0, 1.0, 0.0, 0.0)  # 180° around X
    cos_half = math.sqrt((1.0 + nz) / 2.0)
    sin_theta = math.sqrt(max(0.0, 1.0 - nz * nz))
    if sin_theta < 1e-10:
        return (1.0, 0.0, 0.0, 0.0)  # identity
    sin_half = math.sqrt(max(0.0, (1.0 - nz) / 2.0))
    return (cos_half, -ny * sin_half / sin_theta, nx * sin_half / sin_theta, 0.0)


if __name__ == "__main__":
    print(f"Generating {NUM_SPLATS} splats (radius={RADIUS})...")
    pts = fibonacci_sphere(NUM_SPLATS, RADIUS)

    log_tan = math.log(SCALE_TAN)
    log_rad = math.log(SCALE_RAD)
    opacity_logit = math.log(OPACITY / (1 - OPACITY))  # logit

    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {NUM_SPLATS}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property float nx\n"
        "property float ny\n"
        "property float nz\n"
        "property float f_dc_0\n"
        "property float f_dc_1\n"
        "property float f_dc_2\n"
        "property float opacity\n"
        "property float scale_0\n"
        "property float scale_1\n"
        "property float scale_2\n"
        "property float rot_0\n"
        "property float rot_1\n"
        "property float rot_2\n"
        "property float rot_3\n"
        "end_header\n"
    ).encode("ascii")

    with open("sphere.ply", "wb") as f:
        f.write(header)
        for (x, y, z) in pts:
            length = math.sqrt(x*x + y*y + z*z)
            nx, ny, nz = x/length, y/length, z/length

            color = RED if y > 0 else BLUE
            dc0, dc1, dc2 = to_f_dc(*color)

            row = struct.pack(
                "<17f",
                x, y, z,
                nx, ny, nz,
                dc0, dc1, dc2,
                opacity_logit,
                log_tan, log_tan, log_rad,
                qw, qx, qy, qz,       # quaternion aligning Z with surface normal
            )
            f.write(row)

    import os
    size_kb = os.path.getsize("sphere.ply") / 1024
    print(f"Saved sphere.ply ({size_kb:.0f} KB)")
    print("Drag sphere.ply into the viewer to test!")