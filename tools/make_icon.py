"""Generate the multi-size PMAI application icon with only the standard library.

The icon is written as a Windows .ico containing uncompressed 32-bit images,
which keeps the generator dependency-free and the result compatible with
PyInstaller, Explorer, and older Windows shell versions.
"""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "assets" / "pmai.ico"
DEFAULT_SIZES = (16, 24, 32, 48, 64, 128, 256)

RGB = tuple[int, int, int]

BACKGROUND_START: RGB = (0x6D, 0x74, 0xF0)
BACKGROUND_END: RGB = (0x3D, 0x35, 0xB5)
LINK: RGB = (0xDF, 0xE7, 0xFF)
CARD: RGB = (0xFF, 0xFF, 0xFF)
MENU: RGB = (0xF5, 0x9E, 0x0B)
FIELDS: RGB = (0x60, 0xA5, 0xFA)

# x0, y0, x1, y1, corner radius, header color
CARDS = (
    (0.155, 0.285, 0.435, 0.715, 0.055, MENU),
    (0.585, 0.155, 0.845, 0.445, 0.055, FIELDS),
    (0.585, 0.555, 0.845, 0.845, 0.055, FIELDS),
)

# x0, y0, x1, y1
LINK_SEGMENTS = (
    (0.435, 0.500, 0.515, 0.500),
    (0.515, 0.500, 0.585, 0.300),
    (0.515, 0.500, 0.585, 0.700),
)
LINK_HALF_WIDTH = 0.018
HEADER_HEIGHT = 0.060


def _inside_rounded_rect(
    x: float,
    y: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    radius: float,
) -> bool:
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    center_x = min(max(x, x0 + radius), x1 - radius)
    center_y = min(max(y, y0 + radius), y1 - radius)
    dx = x - center_x
    dy = y - center_y
    return dx * dx + dy * dy <= radius * radius


def _on_segment(
    x: float,
    y: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    half_width: float,
) -> bool:
    dx = x1 - x0
    dy = y1 - y0
    length_squared = dx * dx + dy * dy
    if length_squared == 0.0:
        return math.hypot(x - x0, y - y0) <= half_width
    t = ((x - x0) * dx + (y - y0) * dy) / length_squared
    t = min(1.0, max(0.0, t))
    nearest_x = x0 + t * dx
    nearest_y = y0 + t * dy
    return (x - nearest_x) ** 2 + (y - nearest_y) ** 2 <= half_width * half_width


def _mix(first: RGB, second: RGB, amount: float) -> RGB:
    return (
        round(first[0] + (second[0] - first[0]) * amount),
        round(first[1] + (second[1] - first[1]) * amount),
        round(first[2] + (second[2] - first[2]) * amount),
    )


def _sample(x: float, y: float) -> RGB | None:
    if not _inside_rounded_rect(x, y, 0.015, 0.015, 0.985, 0.985, 0.225):
        return None

    gradient = min(1.0, max(0.0, (x * 0.6 + y * 0.4 - 0.1) / 0.9))
    color = _mix(BACKGROUND_START, BACKGROUND_END, gradient)

    distance = math.hypot(x - 0.28, y - 0.16)
    if distance < 0.75:
        bloom = (1.0 - distance / 0.75) ** 2 * 0.16
        color = _mix(color, (255, 255, 255), bloom)

    for x0, y0, x1, y1 in LINK_SEGMENTS:
        if _on_segment(x, y, x0, y0, x1, y1, LINK_HALF_WIDTH):
            color = LINK
            break

    for x0, y0, x1, y1, radius, header_color in CARDS:
        if _inside_rounded_rect(x, y, x0, y0, x1, y1, radius):
            if y < y0 + HEADER_HEIGHT:
                color = header_color
            else:
                color = CARD
            break

    return color


def _supersample(size: int) -> int:
    if size <= 64:
        return 4
    if size <= 128:
        return 3
    return 2


def _render(size: int, supersample: int) -> bytes:
    pixels = bytearray(size * size * 4)
    sample_count = supersample * supersample
    step = 1.0 / (size * supersample)

    for pixel_y in range(size):
        for pixel_x in range(size):
            red = green = blue = covered = 0
            for sample_y in range(supersample):
                y = (pixel_y * supersample + sample_y + 0.5) * step
                for sample_x in range(supersample):
                    x = (pixel_x * supersample + sample_x + 0.5) * step
                    color = _sample(x, y)
                    if color is not None:
                        red += color[0]
                        green += color[1]
                        blue += color[2]
                        covered += 1

            if covered:
                index = (pixel_y * size + pixel_x) * 4
                pixels[index] = red // covered
                pixels[index + 1] = green // covered
                pixels[index + 2] = blue // covered
                pixels[index + 3] = round(255 * covered / sample_count)

    return bytes(pixels)


def _dib(rgba: bytes, size: int) -> bytes:
    header = struct.pack(
        "<IiiHHIIiiII",
        40,           # BITMAPINFOHEADER size
        size,         # width
        size * 2,     # height includes the XOR image and the AND mask
        1,            # planes
        32,           # bits per pixel
        0,            # BI_RGB
        len(rgba),    # image size
        0, 0, 0, 0,   # resolution and palette
    )

    bgra = bytearray(len(rgba))
    bgra[0::4] = rgba[2::4]
    bgra[1::4] = rgba[1::4]
    bgra[2::4] = rgba[0::4]
    bgra[3::4] = rgba[3::4]

    stride = size * 4
    pixels = b"".join(
        bytes(bgra[row * stride : (row + 1) * stride])
        for row in range(size - 1, -1, -1)
    )

    mask_stride = ((size + 31) // 32) * 4
    mask = bytes(mask_stride * size)
    return header + pixels + mask


def build_icon(sizes: tuple[int, ...], output: Path) -> None:
    images = [(size, _render(size, _supersample(size))) for size in sizes]
    payloads = [(size, _dib(rgba, size)) for size, rgba in images]

    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = 6 + 16 * len(payloads)
    directory = bytearray()
    data = bytearray()

    for size, payload in payloads:
        dimension = 0 if size == 256 else size
        directory += struct.pack(
            "<BBBBHHII",
            dimension,
            dimension,
            0,
            0,
            1,
            32,
            len(payload),
            offset,
        )
        data += payload
        offset += len(payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header + directory + data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--sizes",
        default=",".join(str(size) for size in DEFAULT_SIZES),
        help="comma-separated square sizes (default: 16,24,32,48,64,128,256)",
    )
    args = parser.parse_args(argv)

    try:
        sizes = tuple(
            sorted({int(part.strip()) for part in args.sizes.split(",") if part.strip()})
        )
    except ValueError:
        parser.error("--sizes must be a comma-separated list of integers")
    if not sizes or any(size < 8 or size > 256 for size in sizes):
        parser.error("icon sizes must be between 8 and 256 pixels")

    output = args.output.expanduser()
    if not output.is_absolute():
        output = Path.cwd() / output

    build_icon(sizes, output)
    size_kb = output.stat().st_size / 1024
    joined_sizes = ", ".join(str(size) for size in sizes)
    print(f"Wrote {output} ({size_kb:.1f} KB; sizes: {joined_sizes})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
