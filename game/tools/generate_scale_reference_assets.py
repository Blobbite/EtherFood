#!/usr/bin/env python3
"""Generate EtherFood's deterministic Visual Lab prototype PNG assets.

The generator uses only Python's standard library. It performs no network
access and deliberately draws on a two-world-pixel grid without antialiasing.
Run with ``--check`` to verify that committed PNGs match the deterministic
output byte for byte. The separately documented cloudy fog textures are not
regenerated here because their source was created with the built-in image tool.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from collections.abc import Callable, Iterable
from pathlib import Path

Color = tuple[int, int, int, int]
Point = tuple[int, int]

TRANSPARENT: Color = (0, 0, 0, 0)
INK: Color = (20, 29, 34, 255)
INK_SOFT: Color = (31, 43, 45, 255)
GROUND: Color = (39, 64, 58, 255)
GROUND_DARK: Color = (29, 49, 48, 255)
GROUND_LIGHT: Color = (53, 81, 67, 255)
MOSS: Color = (73, 101, 70, 255)
STONE_DARK: Color = (56, 59, 57, 255)
STONE: Color = (104, 101, 85, 255)
STONE_LIGHT: Color = (156, 145, 111, 255)
WOOD_DARK: Color = (55, 34, 27, 255)
WOOD: Color = (105, 61, 34, 255)
WOOD_LIGHT: Color = (157, 99, 48, 255)
GOLD_DARK: Color = (119, 82, 35, 255)
GOLD: Color = (213, 169, 73, 255)
SKIN_DARK: Color = (112, 67, 51, 255)
SKIN: Color = (187, 126, 78, 255)
SKIN_LIGHT: Color = (220, 166, 102, 255)
GREEN_DEEP: Color = (25, 62, 48, 255)
GREEN_DARK: Color = (34, 84, 53, 255)
GREEN: Color = (61, 119, 66, 255)
GREEN_LIGHT: Color = (119, 158, 79, 255)
GREEN_BRIGHT: Color = (151, 181, 72, 255)
PURPLE_DEEP: Color = (46, 29, 53, 255)
PURPLE_DARK: Color = (75, 35, 71, 255)
PURPLE: Color = (112, 48, 83, 255)
RED: Color = (142, 57, 65, 255)
RED_LIGHT: Color = (185, 76, 72, 255)
STEEL_DARK: Color = (54, 64, 70, 255)
STEEL: Color = (103, 116, 116, 255)
STEEL_LIGHT: Color = (162, 161, 139, 255)
CREAM: Color = (218, 204, 151, 255)
ASH: Color = (82, 79, 73, 255)
SOIL: Color = (74, 62, 47, 255)
SOIL_LIGHT: Color = (111, 91, 61, 255)
SCALE = 2
WORLD_STATE_SOURCE_WIDTH = 720
WORLD_STATE_SOURCE_HEIGHT = 405
OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "assets"
    / "prototypes"
    / "scale_references"
)
WORLD_STATE_OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "assets"
    / "prototypes"
    / "world_states"
)


class Canvas:
    """Tiny deterministic RGBA raster canvas with hard-edged primitives."""

    def __init__(self, width: int, height: int, fill: Color = TRANSPARENT) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(fill * (width * height))

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 4
            self.pixels[offset : offset + 4] = bytes(color)

    def get_pixel(self, x: int, y: int) -> Color:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return TRANSPARENT
        offset = (y * self.width + x) * 4
        return tuple(self.pixels[offset : offset + 4])  # type: ignore[return-value]

    def rect(self, x: int, y: int, width: int, height: int, color: Color) -> None:
        for draw_y in range(max(0, y), min(self.height, y + height)):
            for draw_x in range(max(0, x), min(self.width, x + width)):
                self.set_pixel(draw_x, draw_y, color)

    def polygon(self, points: Iterable[Point], color: Color) -> None:
        vertices = tuple(points)
        min_x = max(0, min(point[0] for point in vertices))
        max_x = min(self.width - 1, max(point[0] for point in vertices))
        min_y = max(0, min(point[1] for point in vertices))
        max_y = min(self.height - 1, max(point[1] for point in vertices))
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if _point_in_polygon(x + 0.5, y + 0.5, vertices):
                    self.set_pixel(x, y, color)

    def disc(
        self,
        center_x: int,
        center_y: int,
        radius_x: int,
        radius_y: int,
        color: Color,
    ) -> None:
        for y in range(center_y - radius_y, center_y + radius_y + 1):
            for x in range(center_x - radius_x, center_x + radius_x + 1):
                normalized_x = ((x - center_x) / max(1, radius_x)) ** 2
                normalized_y = ((y - center_y) / max(1, radius_y)) ** 2
                if normalized_x + normalized_y <= 1.0:
                    self.set_pixel(x, y, color)

    def line(self, start: Point, end: Point, color: Color, width: int = 1) -> None:
        x_0, y_0 = start
        x_1, y_1 = end
        delta_x = abs(x_1 - x_0)
        step_x = 1 if x_0 < x_1 else -1
        delta_y = -abs(y_1 - y_0)
        step_y = 1 if y_0 < y_1 else -1
        error = delta_x + delta_y
        while True:
            self.rect(x_0 - width // 2, y_0 - width // 2, width, width, color)
            if x_0 == x_1 and y_0 == y_1:
                break
            doubled_error = 2 * error
            if doubled_error >= delta_y:
                error += delta_y
                x_0 += step_x
            if doubled_error <= delta_x:
                error += delta_x
                y_0 += step_y

    def upscale(self, factor: int) -> "Canvas":
        scaled = Canvas(self.width * factor, self.height * factor)
        for y in range(self.height):
            for x in range(self.width):
                offset = (y * self.width + x) * 4
                color = tuple(self.pixels[offset : offset + 4])
                scaled.rect(x * factor, y * factor, factor, factor, color)  # type: ignore[arg-type]
        return scaled

    def blit(self, source: "Canvas", left: int, top: int) -> None:
        for source_y in range(source.height):
            for source_x in range(source.width):
                source_offset = (source_y * source.width + source_x) * 4
                color = tuple(source.pixels[source_offset : source_offset + 4])
                if color[3] != 0:
                    self.set_pixel(left + source_x, top + source_y, color)  # type: ignore[arg-type]

    def png_bytes(self) -> bytes:
        signature = b"\x89PNG\r\n\x1a\n"
        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 6, 0, 0, 0)
        scanlines = bytearray()
        row_size = self.width * 4
        for y in range(self.height):
            scanlines.append(0)
            start = y * row_size
            scanlines.extend(self.pixels[start : start + row_size])
        return signature + _png_chunk(b"IHDR", header) + _png_chunk(
            b"IDAT", zlib.compress(bytes(scanlines), level=9)
        ) + _png_chunk(b"IEND", b"")

    def alpha_bounds(self) -> tuple[int, int, int, int] | None:
        visible: list[tuple[int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if self.pixels[(y * self.width + x) * 4 + 3] != 0:
                    visible.append((x, y))
        if not visible:
            return None
        return (
            min(point[0] for point in visible),
            min(point[1] for point in visible),
            max(point[0] for point in visible),
            max(point[1] for point in visible),
        )


def _point_in_polygon(x: float, y: float, points: tuple[Point, ...]) -> bool:
    inside = False
    previous_x, previous_y = points[-1]
    for current_x, current_y in points:
        crosses = (current_y > y) != (previous_y > y)
        if crosses:
            edge_x = (previous_x - current_x) * (y - current_y) / (
                previous_y - current_y
            ) + current_x
            if x < edge_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(payload, checksum)
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _finish_sprite(
    image: Canvas,
    detail_painter: Callable[[Canvas], None] | None = None,
) -> Canvas:
    """Add half-grid detail while retaining hard, uniformly scaled pixels."""

    detailed = image.upscale(2)
    if detail_painter is not None:
        detail_painter(detailed)
    finished = detailed.upscale(SCALE)
    _add_pixel_texture(finished)
    return finished


def _add_pixel_texture(image: Canvas) -> None:
    """Break broad color fields into deterministic one-pixel material clusters."""

    highlights: dict[Color, Color] = {
        WOOD_DARK: WOOD,
        WOOD: WOOD_LIGHT,
        STONE_DARK: STONE,
        STONE: STONE_LIGHT,
        STEEL_DARK: STEEL,
        STEEL: STEEL_LIGHT,
        GREEN_DEEP: GREEN_DARK,
        GREEN_DARK: GREEN,
        GREEN: GREEN_LIGHT,
        PURPLE_DEEP: PURPLE_DARK,
        PURPLE_DARK: PURPLE,
        PURPLE: RED,
        SKIN_DARK: SKIN,
        SKIN: SKIN_LIGHT,
        GROUND_DARK: GROUND,
        GROUND: GROUND_LIGHT,
    }
    shadows: dict[Color, Color] = {
        WOOD: WOOD_DARK,
        WOOD_LIGHT: WOOD,
        STONE: STONE_DARK,
        STONE_LIGHT: STONE,
        STEEL: STEEL_DARK,
        STEEL_LIGHT: STEEL,
        GREEN_DARK: GREEN_DEEP,
        GREEN: GREEN_DARK,
        GREEN_LIGHT: GREEN,
        GREEN_BRIGHT: GREEN_LIGHT,
        PURPLE_DARK: PURPLE_DEEP,
        PURPLE: PURPLE_DARK,
        RED: PURPLE_DARK,
        SKIN: SKIN_DARK,
        SKIN_LIGHT: SKIN,
    }
    original = bytes(image.pixels)

    def original_pixel(x: int, y: int) -> Color:
        offset = (y * image.width + x) * 4
        return tuple(original[offset : offset + 4])  # type: ignore[return-value]

    for y in range(1, image.height - 1):
        for x in range(1, image.width - 1):
            color = original_pixel(x, y)
            if color[3] != 255 or color in (INK, INK_SOFT):
                continue
            if original_pixel(x - 1, y) != color or original_pixel(x + 1, y) != color:
                continue
            value = (x * 47 + y * 71 + x * y * 3) % 113
            if value == 3 and color in highlights:
                image.set_pixel(x, y, highlights[color])
            elif value == 79 and color in shadows:
                image.set_pixel(x, y, shadows[color])


def hero_idle_down() -> Canvas:
    image = Canvas(14, 20)
    image.polygon(
        [(4, 1), (5, 0), (9, 0), (11, 2), (12, 6), (10, 9), (4, 9), (2, 6), (3, 2)],
        INK,
    )
    image.polygon(
        [(4, 2), (6, 1), (9, 1), (11, 3), (11, 6), (9, 8), (4, 8), (3, 6), (3, 3)],
        WOOD_DARK,
    )
    image.rect(4, 2, 6, 2, WOOD)
    image.rect(4, 4, 7, 2, SKIN)
    image.rect(5, 4, 3, 1, SKIN_LIGHT)
    image.rect(5, 6, 5, 2, SKIN_DARK)
    image.rect(6, 6, 1, 1, INK)
    image.rect(9, 6, 1, 1, INK)
    image.polygon(
        [
            (2, 8),
            (4, 7),
            (10, 7),
            (12, 8),
            (13, 12),
            (12, 16),
            (10, 17),
            (4, 17),
            (1, 15),
            (1, 11),
        ],
        INK,
    )
    image.polygon(
        [(3, 9), (5, 8), (9, 8), (11, 9), (11, 15), (9, 16), (4, 16), (2, 14), (2, 11)],
        STEEL_DARK,
    )
    image.rect(4, 9, 6, 2, STEEL)
    image.rect(3, 10, 2, 5, WOOD)
    image.rect(10, 10, 2, 5, WOOD_DARK)
    image.rect(5, 11, 4, 1, GOLD)
    image.rect(5, 12, 5, 4, PURPLE_DARK)
    image.rect(6, 12, 1, 3, RED)
    image.rect(4, 16, 3, 2, INK)
    image.rect(8, 16, 3, 2, INK)
    image.rect(4, 17, 2, 3, WOOD_DARK)
    image.rect(9, 17, 2, 3, WOOD_DARK)
    image.rect(4, 19, 2, 1, STEEL_LIGHT)
    image.rect(9, 19, 2, 1, STEEL_LIGHT)
    image.set_pixel(11, 9, STEEL_LIGHT)
    def paint_details(detailed: Canvas) -> None:
        # Hair reads as a rounded crown seen from above, with light from NW.
        detailed.rect(9, 2, 9, 2, WOOD_LIGHT)
        detailed.rect(7, 4, 3, 3, WOOD)
        detailed.rect(18, 5, 3, 4, INK_SOFT)
        detailed.line((8, 8), (11, 5), SKIN_LIGHT)
        detailed.rect(11, 12, 2, 1, CREAM)
        detailed.rect(18, 12, 2, 1, CREAM)
        detailed.rect(14, 15, 4, 1, SKIN_LIGHT)
        # Shoulder plates, leather seams and a compact adventurer silhouette.
        detailed.rect(4, 19, 3, 3, STEEL)
        detailed.rect(21, 19, 3, 3, STEEL_DARK)
        detailed.rect(6, 18, 2, 1, STEEL_LIGHT)
        detailed.rect(9, 20, 10, 2, STEEL)
        detailed.rect(10, 23, 8, 1, GOLD_DARK)
        detailed.rect(9, 25, 2, 6, PURPLE_DEEP)
        detailed.rect(18, 25, 2, 6, PURPLE_DEEP)
        detailed.rect(13, 24, 2, 7, RED_LIGHT)
        detailed.rect(5, 26, 2, 3, WOOD_LIGHT)
        detailed.rect(22, 26, 2, 3, WOOD_DARK)
        detailed.rect(10, 32, 3, 2, GOLD_DARK)
        detailed.rect(17, 32, 3, 2, GOLD_DARK)
        detailed.rect(8, 37, 4, 1, STEEL)
        detailed.rect(18, 37, 4, 1, STEEL_DARK)

    return _finish_sprite(image, paint_details)


def small_enemy() -> Canvas:
    image = Canvas(17, 14)
    image.rect(4, 12, 4, 2, INK)
    image.rect(10, 12, 4, 2, INK)
    image.polygon(
        [
            (1, 7),
            (4, 5),
            (5, 2),
            (6, 2),
            (7, 0),
            (9, 2),
            (11, 0),
            (12, 3),
            (13, 5),
            (16, 7),
            (15, 11),
            (12, 12),
            (5, 12),
            (1, 10),
        ],
        INK,
    )
    image.disc(9, 5, 4, 4, GREEN)
    image.rect(6, 2, 5, 2, GREEN_LIGHT)
    image.rect(5, 4, 7, 3, GREEN_DARK)
    image.rect(6, 6, 2, 1, INK)
    image.rect(10, 6, 2, 1, INK)
    image.set_pixel(7, 6, GOLD)
    image.set_pixel(10, 6, GOLD)
    image.polygon(
        [(2, 7), (5, 6), (8, 8), (11, 7), (15, 8), (14, 10), (11, 11), (6, 11), (2, 10)],
        GREEN_DARK,
    )
    image.rect(5, 8, 8, 2, RED)
    image.rect(7, 9, 4, 3, WOOD_DARK)
    image.set_pixel(5, 7, GREEN_LIGHT)
    image.rect(4, 13, 4, 1, WOOD_DARK)
    image.rect(10, 13, 4, 1, WOOD_DARK)

    def paint_details(detailed: Canvas) -> None:
        # Long ears, brow and tiny tusks make the top-down goblin readable.
        detailed.polygon([(1, 12), (7, 9), (6, 15), (2, 17)], GREEN)
        detailed.polygon([(32, 12), (25, 9), (26, 15), (31, 17)], GREEN_DARK)
        detailed.rect(10, 7, 9, 2, GREEN_LIGHT)
        detailed.rect(11, 11, 4, 2, INK)
        detailed.rect(20, 11, 4, 2, INK)
        detailed.set_pixel(13, 11, GOLD)
        detailed.set_pixel(21, 11, GOLD)
        detailed.rect(14, 15, 7, 2, GREEN_DEEP)
        detailed.set_pixel(13, 16, CREAM)
        detailed.set_pixel(21, 16, CREAM)
        detailed.rect(6, 18, 4, 2, RED_LIGHT)
        detailed.rect(23, 18, 4, 2, RED)
        detailed.rect(11, 19, 12, 2, WOOD)
        detailed.rect(15, 19, 3, 2, GOLD)
        detailed.rect(8, 24, 5, 2, WOOD)
        detailed.rect(21, 24, 5, 2, WOOD_DARK)

    return _finish_sprite(image, paint_details)


def door_entrance() -> Canvas:
    image = Canvas(21, 28)
    image.polygon([(2, 0), (18, 0), (21, 8), (18, 12), (2, 12), (0, 8)], INK)
    image.polygon([(3, 1), (17, 1), (19, 7), (17, 9), (3, 9), (1, 7)], WOOD_DARK)
    image.polygon([(4, 2), (16, 2), (18, 7), (16, 8), (3, 8)], WOOD)
    image.line((4, 3), (17, 7), WOOD_LIGHT)
    image.line((8, 1), (6, 8), INK_SOFT)
    image.line((14, 1), (15, 8), INK_SOFT)
    image.rect(1, 9, 19, 17, INK)
    image.rect(2, 10, 17, 15, STONE_DARK)
    image.rect(3, 11, 4, 4, STONE)
    image.rect(14, 11, 4, 4, STONE)
    image.rect(2, 16, 5, 4, STONE)
    image.rect(14, 16, 5, 4, STONE)
    image.rect(3, 21, 4, 3, STONE_LIGHT)
    image.rect(14, 21, 4, 3, STONE)
    image.rect(6, 11, 9, 15, INK)
    image.rect(7, 12, 7, 14, WOOD_DARK)
    image.rect(8, 13, 5, 13, WOOD)
    image.line((10, 13), (10, 25), WOOD_LIGHT)
    image.rect(12, 19, 1, 1, GOLD)
    image.rect(5, 26, 11, 2, INK)
    image.rect(6, 26, 9, 1, STONE_LIGHT)
    def paint_details(detailed: Canvas) -> None:
        # Roof cap and masonry share the same NW lighting as every actor.
        detailed.rect(8, 3, 13, 2, WOOD_LIGHT)
        detailed.rect(23, 4, 8, 2, WOOD)
        detailed.rect(6, 10, 5, 2, GOLD_DARK)
        detailed.rect(30, 12, 5, 2, WOOD_DARK)
        for x, y in ((5, 23), (29, 23), (4, 34), (31, 35), (7, 44), (29, 45)):
            detailed.rect(x, y, 5, 2, STONE_LIGHT)
            detailed.rect(x + 4, y + 2, 3, 1, STONE_DARK)
        detailed.line((14, 25), (14, 50), WOOD_LIGHT)
        detailed.line((21, 25), (21, 50), WOOD_DARK)
        detailed.rect(15, 32, 11, 2, INK_SOFT)
        detailed.rect(23, 38, 2, 2, GOLD)
        detailed.rect(11, 52, 20, 2, STONE_LIGHT)
        detailed.rect(14, 54, 15, 1, CREAM)
        detailed.rect(2, 17, 4, 2, INK_SOFT)
        detailed.rect(36, 17, 3, 2, INK_SOFT)

    return _finish_sprite(image, paint_details)


def house_wall() -> Canvas:
    image = Canvas(75, 36)
    image.polygon([(4, 0), (70, 0), (75, 17), (70, 23), (4, 23), (0, 17)], INK)
    image.polygon([(5, 1), (69, 1), (73, 16), (69, 20), (4, 20), (2, 16)], WOOD_DARK)
    image.polygon([(6, 2), (68, 2), (71, 15), (68, 18), (4, 18)], WOOD)
    for x in range(8, 69, 10):
        image.line((x, 2), (x - 3, 18), INK_SOFT)
        image.line((x + 1, 3), (x + 7, 3), WOOD_LIGHT)
    image.rect(2, 19, 71, 5, INK)
    image.rect(3, 20, 69, 2, WOOD_LIGHT)
    image.rect(2, 23, 71, 12, INK)
    image.rect(3, 23, 69, 11, STONE_DARK)
    for x in range(4, 70, 9):
        color = STONE if x % 18 == 4 else STONE_LIGHT
        image.rect(x, 24, 7, 4, color)
    for x in range(0, 72, 10):
        color = STONE_LIGHT if x % 20 == 0 else STONE
        image.rect(x + 3, 29, 8, 4, color)
    image.rect(48, 24, 12, 9, INK)
    image.rect(50, 25, 8, 6, PURPLE_DEEP)
    image.rect(51, 25, 3, 2, STEEL_LIGHT)
    image.rect(54, 28, 4, 3, STEEL_DARK)
    image.rect(1, 34, 73, 2, INK)
    image.rect(3, 34, 69, 1, STONE_LIGHT)
    image.rect(0, 35, 75, 1, STONE_DARK)
    def paint_details(detailed: Canvas) -> None:
        # Individual shingles and chipped mortar avoid a flat facade read.
        for row, y in enumerate((5, 13, 21, 29)):
            start = 5 if row % 2 == 0 else 10
            for x in range(start, 142, 14):
                detailed.rect(x, y, 10, 2, WOOD_LIGHT if row < 2 else WOOD)
                detailed.rect(x + 9, y + 2, 2, 7, INK_SOFT)
                detailed.set_pixel(x + 2, y + 4, GOLD_DARK)
        detailed.rect(5, 41, 138, 2, CREAM)
        detailed.rect(4, 45, 140, 3, WOOD_DARK)
        for row, y in enumerate((49, 59)):
            offset = 4 if row == 0 else 12
            for x in range(offset, 143, 18):
                detailed.rect(x, y, 13, 2, STONE_LIGHT)
                detailed.rect(x + 12, y + 2, 2, 7, INK_SOFT)
        detailed.rect(100, 50, 15, 2, STEEL_LIGHT)
        detailed.rect(101, 55, 4, 3, PURPLE)
        detailed.rect(111, 58, 3, 4, PURPLE_DEEP)
        for x in (19, 47, 73, 132):
            detailed.rect(x, 64, 9, 2, MOSS)
            detailed.set_pixel(x + 2, 62, GREEN_LIGHT)
        detailed.rect(2, 69, 146, 2, STONE_DARK)

    return _finish_sprite(image, paint_details)


def large_enemy() -> Canvas:
    image = Canvas(43, 32)
    image.rect(9, 28, 9, 4, INK)
    image.rect(25, 28, 9, 4, INK)
    image.polygon(
        [
            (8, 10),
            (13, 5),
            (16, 5),
            (17, 1),
            (20, 0),
            (25, 1),
            (26, 5),
            (31, 6),
            (36, 10),
            (41, 17),
            (40, 25),
            (34, 29),
            (27, 29),
            (22, 27),
            (17, 29),
            (9, 29),
            (3, 25),
            (2, 17),
        ],
        INK,
    )
    image.disc(21, 8, 8, 7, PURPLE_DEEP)
    image.polygon([(16, 3), (20, 1), (25, 2), (27, 6), (25, 12), (17, 12), (14, 7)], PURPLE)
    image.rect(16, 4, 7, 3, RED)
    image.rect(17, 4, 5, 1, RED_LIGHT)
    image.rect(16, 8, 3, 2, INK)
    image.rect(24, 8, 3, 2, INK)
    image.set_pixel(17, 8, GOLD)
    image.set_pixel(25, 8, GOLD)
    image.rect(19, 11, 6, 2, INK)
    image.disc(10, 17, 8, 8, PURPLE_DARK)
    image.disc(33, 17, 8, 8, PURPLE_DARK)
    image.rect(4, 17, 7, 7, RED)
    image.rect(32, 17, 7, 7, RED)
    image.rect(8, 12, 8, 3, STEEL)
    image.rect(28, 12, 7, 3, STEEL_DARK)
    image.polygon([(14, 12), (29, 12), (33, 19), (29, 27), (14, 27), (10, 19)], STEEL_DARK)
    image.polygon([(16, 13), (27, 13), (30, 19), (27, 25), (16, 25), (13, 19)], PURPLE)
    image.rect(15, 15, 13, 2, RED)
    image.rect(19, 16, 5, 8, PURPLE_DEEP)
    image.rect(10, 27, 9, 3, PURPLE_DEEP)
    image.rect(24, 27, 9, 3, PURPLE_DEEP)
    image.rect(10, 31, 8, 1, STEEL_LIGHT)
    image.rect(26, 31, 8, 1, STEEL_LIGHT)
    image.set_pixel(12, 11, STEEL_LIGHT)
    def paint_details(detailed: Canvas) -> None:
        # Helmet crown and shoulder plates establish the shared overhead view.
        detailed.rect(36, 3, 13, 3, PURPLE)
        detailed.rect(33, 7, 5, 7, STEEL)
        detailed.rect(50, 8, 5, 7, STEEL_DARK)
        detailed.rect(31, 14, 7, 3, PURPLE)
        detailed.rect(49, 14, 7, 3, PURPLE_DARK)
        detailed.rect(34, 17, 6, 2, INK)
        detailed.rect(48, 17, 6, 2, INK)
        detailed.set_pixel(37, 17, GOLD)
        detailed.set_pixel(50, 17, GOLD)
        detailed.rect(39, 22, 10, 2, INK)
        detailed.rect(17, 26, 12, 3, STEEL_LIGHT)
        detailed.rect(58, 27, 11, 3, STEEL)
        detailed.rect(20, 32, 4, 13, RED_LIGHT)
        detailed.rect(65, 33, 4, 12, RED)
        detailed.rect(29, 29, 30, 3, STEEL)
        detailed.rect(30, 36, 28, 2, PURPLE_DARK)
        detailed.rect(32, 48, 24, 3, WOOD_DARK)
        detailed.rect(41, 47, 6, 5, GOLD)
        detailed.rect(21, 54, 13, 3, PURPLE)
        detailed.rect(53, 54, 13, 3, PURPLE_DARK)
        detailed.rect(20, 61, 14, 2, STEEL)
        detailed.rect(53, 61, 14, 2, STEEL_DARK)

    return _finish_sprite(image, paint_details)


def tree() -> Canvas:
    image = Canvas(41, 48)
    image.disc(20, 38, 14, 5, INK_SOFT)
    image.rect(17, 31, 8, 15, INK)
    image.polygon(
        [(18, 29), (24, 29), (24, 43), (29, 47), (24, 47), (21, 44), (17, 48), (11, 47), (17, 42)],
        WOOD_DARK,
    )
    image.rect(19, 29, 4, 15, WOOD)
    image.rect(19, 31, 1, 10, WOOD_LIGHT)
    image.disc(10, 21, 10, 12, INK)
    image.disc(29, 21, 11, 13, INK)
    image.disc(20, 10, 13, 10, INK)
    image.disc(20, 25, 15, 13, INK)
    image.disc(10, 20, 8, 10, GREEN_DARK)
    image.disc(29, 20, 9, 11, GREEN_DEEP)
    image.disc(20, 10, 11, 9, GREEN_DARK)
    image.disc(20, 25, 13, 11, GREEN)
    image.disc(12, 13, 7, 7, GREEN)
    image.disc(28, 10, 7, 7, GREEN_DEEP)
    image.disc(8, 25, 6, 7, GREEN_DEEP)
    image.disc(32, 27, 6, 7, GREEN_DARK)
    image.disc(16, 6, 5, 4, GREEN_LIGHT)
    image.disc(9, 16, 4, 4, GREEN_LIGHT)
    image.disc(20, 19, 6, 5, GREEN_LIGHT)
    image.disc(28, 25, 4, 4, GREEN)
    image.rect(19, 0, 4, 2, GREEN_DARK)
    image.set_pixel(12, 9, GREEN_LIGHT)
    image.set_pixel(25, 6, MOSS)
    image.set_pixel(16, 21, GREEN_DEEP)
    image.set_pixel(29, 17, GREEN_LIGHT)
    image.rect(15, 47, 5, 1, WOOD_LIGHT)
    image.rect(23, 47, 6, 1, WOOD_DARK)
    def paint_details(detailed: Canvas) -> None:
        # Small angular leaf clusters provide texture without gradients.
        highlight_clusters = (
            (25, 8),
            (34, 5),
            (18, 20),
            (42, 18),
            (56, 14),
            (12, 33),
            (29, 34),
            (48, 31),
            (63, 39),
            (21, 49),
            (42, 50),
            (54, 58),
        )
        for index, (x, y) in enumerate(highlight_clusters):
            color = GREEN_BRIGHT if index % 3 == 0 else GREEN_LIGHT
            detailed.rect(x, y, 5, 3, color)
            detailed.rect(x - 2, y + 2, 3, 3, color)
            detailed.set_pixel(x + 5, y + 4, GREEN)
        shadow_clusters = ((9, 44), (18, 60), (35, 64), (57, 51), (66, 31), (50, 8))
        for x, y in shadow_clusters:
            detailed.rect(x, y, 6, 3, GREEN_DEEP)
            detailed.rect(x + 2, y + 3, 5, 2, GREEN_DARK)
        detailed.rect(37, 63, 3, 21, WOOD_LIGHT)
        detailed.rect(43, 65, 3, 20, WOOD_DARK)
        detailed.line((39, 73), (30, 92), WOOD)
        detailed.line((45, 76), (55, 92), WOOD_DARK)
        detailed.rect(29, 93, 12, 2, WOOD_LIGHT)
        detailed.rect(48, 93, 11, 2, WOOD)
        detailed.rect(16, 78, 10, 2, INK_SOFT)
        detailed.rect(58, 78, 9, 2, INK_SOFT)

    return _finish_sprite(image, paint_details)


def scale_ground() -> Canvas:
    image = Canvas(600, 80, GROUND)
    image.polygon(
        [
            (0, 49),
            (82, 46),
            (158, 50),
            (232, 47),
            (315, 52),
            (402, 48),
            (490, 51),
            (600, 46),
            (600, 74),
            (500, 71),
            (410, 75),
            (315, 71),
            (226, 76),
            (134, 72),
            (60, 75),
            (0, 71),
        ],
        GROUND_DARK,
    )
    for tile_y in range(3, 77, 8):
        for tile_x in range(4, 596, 11):
            value = (tile_x * 37 + tile_y * 61 + tile_x * tile_y) % 17
            if value in (0, 3):
                image.rect(tile_x, tile_y, 2, 1, GROUND_LIGHT)
                image.set_pixel(tile_x - 1, tile_y + 1, MOSS)
            elif value == 7:
                image.rect(tile_x, tile_y, 3, 1, GROUND_DARK)
            elif value == 11:
                image.set_pixel(tile_x, tile_y, MOSS)
                image.set_pixel(tile_x + 1, tile_y - 1, GROUND_LIGHT)
    stones = ((35, 61), (112, 54), (205, 68), (288, 58), (374, 66), (457, 56), (548, 69))
    for stone_x, stone_y in stones:
        image.rect(stone_x, stone_y, 5, 3, STONE_DARK)
        image.rect(stone_x + 1, stone_y, 3, 1, STONE)
        image.set_pixel(stone_x + 1, stone_y + 1, STONE_LIGHT)
    grass_tufts = (
        (19, 18),
        (74, 30),
        (146, 14),
        (263, 29),
        (351, 17),
        (431, 35),
        (527, 21),
        (579, 33),
    )
    for grass_x, grass_y in grass_tufts:
        image.line((grass_x, grass_y + 2), (grass_x - 1, grass_y), MOSS)
        image.line((grass_x + 1, grass_y + 2), (grass_x + 2, grass_y), GROUND_LIGHT)
    detailed = image.upscale(2)
    # A deterministic half-grid pass produces worn grass, moss and grit.
    for y in range(7, detailed.height - 5, 13):
        for x in range(9, detailed.width - 8, 17):
            value = (x * 19 + y * 31 + x * y) % 23
            if value in (1, 6, 14):
                detailed.rect(x, y, 3, 1, GROUND_LIGHT)
                detailed.set_pixel(x - 1, y + 1, MOSS)
            elif value in (4, 19):
                detailed.rect(x, y, 4, 1, GROUND_DARK)
                detailed.set_pixel(x + 1, y + 1, INK_SOFT)
    for stone_x, stone_y in ((83, 40), (333, 87), (581, 34), (877, 96), (1118, 51)):
        detailed.rect(stone_x, stone_y, 7, 3, STONE_DARK)
        detailed.rect(stone_x + 1, stone_y, 4, 1, STONE_LIGHT)
    return detailed.upscale(SCALE)


def world_ground(damaged: bool) -> Canvas:
    """Create the shared 1440 by 810 world-preview ground footprint."""

    base = (32, 54, 51, 255) if damaged else (43, 76, 53, 255)
    image = Canvas(WORLD_STATE_SOURCE_WIDTH, WORLD_STATE_SOURCE_HEIGHT, base)
    dark = (24, 42, 42, 255) if damaged else (32, 62, 45, 255)
    light = (50, 70, 59, 255) if damaged else (67, 99, 58, 255)
    moss = (62, 72, 51, 255) if damaged else (82, 118, 57, 255)

    # Identical patch footprints; only their health and palette change.
    image.polygon(
        [(8, 31), (83, 15), (151, 37), (139, 79), (59, 87), (12, 66)],
        dark,
    )
    image.polygon(
        [(205, 29), (297, 17), (348, 53), (329, 112), (235, 117), (197, 77)],
        dark,
    )
    # The right half forms a continuous forest floor while the middle remains
    # open enough for long movement, zoom and collision passes.
    image.polygon(
        [(418, 12), (556, 5), (704, 31), (716, 146), (641, 191), (477, 171)],
        dark,
    )
    image.polygon(
        [(438, 211), (574, 174), (713, 208), (719, 397), (524, 399), (416, 323)],
        dark,
    )
    image.polygon(
        [(235, 214), (362, 181), (454, 221), (438, 324), (291, 337), (213, 286)],
        (29, 47, 45, 255) if damaged else (48, 82, 54, 255),
    )
    for y in range(5, WORLD_STATE_SOURCE_HEIGHT - 5, 9):
        for x in range(4, WORLD_STATE_SOURCE_WIDTH - 4, 11):
            value = (x * 23 + y * 41 + x * y) % 29
            if value in (0, 5, 17):
                image.rect(x, y, 2, 1, light)
                image.set_pixel(x - 1, y + 1, moss)
            elif value in (8, 21):
                image.rect(x, y, 3, 1, dark)
    return image.upscale(SCALE)


def world_ground_detail(damaged: bool) -> Canvas:
    """Overlay paired stones plus cracks or new grass on the same positions."""

    image = Canvas(WORLD_STATE_SOURCE_WIDTH, WORLD_STATE_SOURCE_HEIGHT)
    stones = (
        (27, 171),
        (207, 146),
        (338, 125),
        (177, 52),
        (312, 178),
        (402, 352),
        (469, 88),
        (553, 286),
        (631, 61),
        (683, 341),
    )
    for index, (x, y) in enumerate(stones):
        stone = ASH if damaged else STONE
        image.polygon(
            [
                (x - 7, y),
                (x - 2, y - 5),
                (x + 7, y - 3),
                (x + 6, y + 4),
                (x - 4, y + 5),
            ],
            INK_SOFT,
        )
        image.polygon(
            [
                (x - 5, y - 1),
                (x - 1, y - 4),
                (x + 5, y - 2),
                (x + 4, y + 2),
                (x - 3, y + 3),
            ],
            stone,
        )
        image.line((x - 3, y - 2), (x + 2, y - 3), STONE_LIGHT, 1)
        if not damaged and index % 2 == 0:
            image.line((x - 7, y + 3), (x - 9, y - 2), GREEN_LIGHT, 1)

    if damaged:
        cracks = (
            ((15, 110), (37, 118), (31, 132), (52, 142), (46, 158)),
            ((184, 59), (199, 70), (192, 85), (211, 94), (203, 108)),
            ((302, 122), (314, 132), (308, 144), (325, 153)),
            ((431, 236), (453, 246), (445, 264), (472, 278), (465, 295)),
            ((596, 102), (611, 117), (605, 133), (629, 145), (621, 163)),
            ((655, 315), (674, 327), (669, 345), (696, 358)),
        )
        for points in cracks:
            for start, end in zip(points, points[1:]):
                image.line(start, end, (14, 25, 27, 255), 2)
            branch_x, branch_y = points[2]
            image.line((branch_x, branch_y), (branch_x + 9, branch_y + 5), INK_SOFT)
    else:
        for x, y in (
            (33, 119),
            (200, 88),
            (316, 142),
            (73, 148),
            (252, 47),
            (418, 272),
            (489, 122),
            (542, 345),
            (614, 191),
            (689, 304),
        ):
            image.line((x, y + 4), (x - 2, y - 3), GREEN, 2)
            image.line((x + 1, y + 4), (x + 5, y - 4), GREEN_LIGHT, 2)
            image.set_pixel(x + 2, y, GREEN_BRIGHT)
    return image.upscale(SCALE)


def world_path(damaged: bool) -> Canvas:
    image = Canvas(WORLD_STATE_SOURCE_WIDTH, WORLD_STATE_SOURCE_HEIGHT)
    path_dark = (58, 51, 45, 255) if damaged else (91, 78, 54, 255)
    path = (77, 66, 53, 255) if damaged else (127, 105, 66, 255)
    path_light = (100, 82, 59, 255) if damaged else (157, 130, 77, 255)
    footprint = [
        (112, 139),
        (137, 133),
        (156, 150),
        (180, 162),
        (218, 226),
        (244, 310),
        (240, 405),
        (145, 405),
        (153, 315),
        (145, 244),
        (111, 201),
        (102, 159),
    ]
    image.polygon(footprint, path_dark)
    inner = [
        (116, 141),
        (135, 137),
        (154, 153),
        (176, 166),
        (210, 230),
        (236, 313),
        (232, 405),
        (153, 405),
        (161, 316),
        (153, 247),
        (118, 199),
        (108, 158),
    ]
    image.polygon(inner, path)
    # A broad branch links the house path to the sawmill yard and makes the
    # enlarged preview useful for horizontal and diagonal camera movement.
    branch = [
        (141, 157),
        (170, 149),
        (211, 158),
        (253, 177),
        (305, 190),
        (365, 199),
        (417, 224),
        (405, 269),
        (351, 254),
        (299, 236),
        (247, 221),
        (201, 201),
        (164, 187),
    ]
    branch_inner = [
        (147, 161),
        (170, 155),
        (207, 165),
        (248, 183),
        (302, 197),
        (361, 206),
        (408, 229),
        (399, 260),
        (354, 247),
        (302, 229),
        (250, 214),
        (204, 194),
        (167, 181),
    ]
    image.polygon(branch, path_dark)
    image.polygon(branch_inner, path)
    path_stones = (
        (121, 148),
        (139, 151),
        (128, 166),
        (153, 169),
        (139, 184),
        (171, 190),
        (127, 201),
        (164, 251),
        (193, 292),
        (176, 346),
        (214, 382),
        (207, 176),
        (259, 195),
        (315, 211),
        (370, 228),
    )
    for x, y in path_stones:
        image.rect(x, y, 6, 2, path_dark)
        image.rect(x + 1, y, 3, 1, path_light)
    if damaged:
        image.line((143, 158), (151, 165), INK_SOFT)
        image.line((151, 165), (146, 174), INK_SOFT)
    else:
        image.rect(112, 155, 3, 1, MOSS)
        image.rect(182, 199, 3, 1, GREEN_LIGHT)
    return image.upscale(SCALE)


def world_sawmill(damaged: bool) -> Canvas:
    """Draw paired open-sided sawmills on one shared 480 by 320 canvas."""

    image = Canvas(240, 160)
    shadow = (13, 25, 24, 165)
    yard = (59, 51, 43, 255) if damaged else (91, 76, 50, 255)
    image.polygon(
        [(6, 37), (72, 13), (184, 24), (232, 57), (220, 145), (37, 151), (8, 118)],
        shadow,
    )
    image.polygon(
        [(14, 79), (72, 57), (211, 72), (218, 139), (42, 145), (14, 116)],
        yard,
    )

    # Open mill shed: the common silhouette and machinery anchors stay fixed
    # so state toggles compare repair, material and atmosphere only.
    image.polygon([(10, 34), (71, 9), (145, 22), (145, 82), (72, 105), (10, 86)], INK)
    image.polygon(
        [(14, 35), (72, 13), (141, 25), (141, 78), (72, 100), (14, 82)],
        WOOD_DARK,
    )
    image.polygon([(18, 74), (73, 91), (136, 72), (136, 118), (74, 137), (18, 116)], INK)
    image.polygon(
        [(22, 77), (73, 95), (132, 77), (132, 114), (74, 132), (22, 112)],
        WOOD,
    )
    for x in range(26, 130, 14):
        image.line((x, 80), (x, 113), WOOD_LIGHT if not damaged else ASH)
    for post_x in (18, 70, 136):
        image.rect(post_x, 66, 5, 61, INK)
        image.rect(post_x + 1, 68, 3, 57, WOOD)

    # Circular saw, drive housing and feed table make the structure readable
    # as a sawmill even at the wide camera profile.
    image.disc(158, 91, 26, 26, INK)
    image.disc(158, 91, 22, 22, STEEL_DARK if damaged else STEEL)
    image.disc(158, 91, 12, 12, yard)
    image.disc(158, 91, 4, 4, INK)
    for start, end in (
        ((158, 62), (158, 69)),
        ((158, 113), (158, 121)),
        ((129, 91), (137, 91)),
        ((179, 91), (187, 91)),
        ((138, 71), (144, 77)),
        ((172, 106), (178, 112)),
        ((137, 111), (143, 105)),
        ((173, 76), (179, 70)),
    ):
        image.line(start, end, STEEL_LIGHT if not damaged else ASH, 3)
    image.rect(142, 122, 33, 18, INK)
    image.rect(146, 125, 25, 12, STEEL_DARK)

    # Log conveyor and stacked timber occupy the same footprint in both states.
    image.polygon([(177, 44), (230, 55), (224, 75), (173, 64)], INK)
    image.polygon([(180, 47), (227, 57), (222, 70), (177, 61)], WOOD)
    for x in range(183, 224, 10):
        image.line((x, 49), (x - 4, 65), WOOD_LIGHT, 2)
    for index, (x, y) in enumerate(((181, 121), (192, 132), (204, 120), (216, 133))):
        image.line((x, y), (x + 21, y + 4), INK, 8)
        image.line((x + 1, y - 1), (x + 20, y + 3), WOOD_DARK, 5)
        image.disc(x + 21, y + 4, 3, 3, WOOD_LIGHT if index % 2 == 0 else WOOD)

    if damaged:
        image.polygon([(14, 35), (48, 23), (60, 43), (43, 56), (14, 49)], (14, 25, 25, 255))
        image.polygon([(96, 18), (141, 25), (141, 51), (121, 48), (108, 34)], (14, 24, 24, 255))
        image.line((31, 30), (55, 58), ASH, 4)
        image.line((99, 20), (127, 49), WOOD_DARK, 4)
        image.line((85, 78), (117, 119), ASH, 4)
        image.line((185, 47), (219, 71), WOOD_DARK, 3)
        image.line((133, 80), (181, 105), (118, 55, 48, 255), 3)
        image.rect(149, 83, 18, 3, (113, 59, 43, 255))
    else:
        for y in range(29, 76, 10):
            image.line((17, y), (70, y + 16), GOLD_DARK)
            image.line((75, y + 15), (137, y), WOOD_LIGHT)
        image.rect(68, 12, 5, 88, INK_SOFT)
        image.rect(70, 14, 2, 83, WOOD_LIGHT)
        image.rect(151, 88, 14, 3, STEEL_LIGHT)
        image.rect(150, 126, 18, 2, STEEL)
        for x, y in ((25, 119), (55, 132), (111, 122)):
            image.rect(x, y, 7, 2, GREEN)
            image.set_pixel(x + 2, y - 1, GREEN_LIGHT)
    return image.upscale(SCALE)


def world_building(damaged: bool) -> Canvas:
    """Draw paired top-down buildings on one shared 300 by 260 canvas."""

    image = Canvas(150, 130)
    image.polygon([(5, 14), (75, 2), (148, 16), (148, 109), (76, 128), (4, 111)], (13, 24, 25, 150))
    image.polygon([(2, 89), (75, 105), (145, 89), (145, 112), (76, 129), (2, 112)], INK)
    image.polygon([(4, 90), (75, 105), (143, 90), (143, 110), (76, 126), (4, 110)], STONE_DARK)

    # Shared roof silhouette and ridge establish the invariant perspective.
    roof_left = [(2, 10), (75, 0), (75, 105), (4, 89)]
    roof_right = [(75, 0), (147, 11), (143, 90), (75, 105)]
    image.polygon(roof_left, INK)
    image.polygon(roof_right, INK)
    image.polygon([(4, 12), (73, 3), (73, 101), (7, 86)], WOOD_DARK)
    image.polygon([(77, 3), (144, 13), (140, 87), (77, 101)], WOOD)

    for y in range(12, 92, 11):
        stagger = 0 if (y // 11) % 2 == 0 else 6
        image.line((7, y), (72, y + 9), GOLD_DARK, 1)
        image.line((78, y + 9), (141, y), WOOD_LIGHT, 1)
        for x in range(10 + stagger, 142, 14):
            image.line((x, y), (x - 2, min(101, y + 10)), INK_SOFT, 1)
    image.rect(73, 2, 5, 101, INK_SOFT)
    image.rect(74, 3, 2, 97, WOOD_LIGHT if not damaged else ASH)

    # Masonry on the short southern wall.
    for row, y in enumerate((94, 104, 114)):
        offset = 4 if row % 2 == 0 else 11
        for x in range(offset, 142, 18):
            image.rect(x, y, 14, 2, STONE)
            image.rect(x + 13, y + 2, 2, 6, INK_SOFT)
            image.rect(x + 2, y, 6, 1, STONE_LIGHT)

    # Same entrance cutout; state changes blockage and finish only.
    image.rect(80, 103, 29, 25, INK)
    image.rect(83, 106, 23, 21, WOOD_DARK)
    for x in (86, 94, 102):
        image.rect(x, 108, 2, 18, WOOD)
        image.rect(x, 108, 1, 15, WOOD_LIGHT)

    if damaged:
        # Jagged missing roof sections expose a dark interior and snapped beams.
        image.polygon([(5, 12), (34, 8), (43, 23), (31, 39), (6, 32)], (15, 26, 27, 255))
        image.polygon([(104, 7), (145, 13), (143, 44), (124, 39), (114, 23)], (14, 24, 25, 255))
        image.polygon([(47, 48), (72, 39), (90, 53), (82, 72), (58, 68)], (12, 22, 23, 255))
        image.line((17, 11), (39, 35), ASH, 3)
        image.line((118, 12), (139, 38), WOOD_DARK, 3)
        image.line((51, 46), (84, 68), WOOD_DARK, 3)
        image.line((78, 107), (110, 126), WOOD_LIGHT, 4)
        image.line((79, 126), (110, 105), WOOD, 4)
        image.rect(33, 82, 7, 4, ASH)
        image.rect(119, 89, 9, 4, ASH)
    else:
        image.rect(83, 103, 23, 3, WOOD_LIGHT)
        image.rect(81, 126, 27, 3, INK)
        image.rect(83, 126, 23, 2, STONE_LIGHT)
        image.rect(102, 116, 2, 2, GOLD)
        # Moss and a few repaired brass roof pins add life without changing shape.
        for x, y in ((9, 87), (24, 91), (124, 88), (138, 86)):
            image.rect(x, y, 7, 2, GREEN)
            image.set_pixel(x + 2, y - 1, GREEN_LIGHT)
        for x, y in ((35, 31), (61, 76), (97, 25), (126, 65)):
            image.rect(x, y, 2, 2, GOLD)
    return image.upscale(SCALE)


def world_tree(damaged: bool) -> Canvas:
    image = Canvas(84, 84)
    image.disc(42, 67, 37, 10, (13, 25, 24, 150))
    image.polygon(
        [
            (36, 45),
            (48, 45),
            (48, 70),
            (59, 80),
            (50, 81),
            (42, 73),
            (34, 82),
            (23, 80),
            (35, 69),
        ],
        INK,
    )
    image.polygon(
        [
            (38, 44),
            (46, 44),
            (46, 69),
            (54, 77),
            (49, 78),
            (42, 71),
            (34, 79),
            (28, 78),
            (38, 67),
        ],
        WOOD_DARK,
    )
    image.rect(39, 45, 4, 27, WOOD)
    image.rect(39, 47, 1, 18, WOOD_LIGHT)
    if damaged:
        branches = (
            ((42, 48), (36, 26), (43, 8), (54, 1)),
            ((44, 50), (60, 37), (75, 38), (83, 28)),
            ((39, 51), (25, 42), (11, 46), (1, 36)),
            ((43, 55), (55, 61), (65, 72), (78, 75)),
        )
        for points in branches:
            for index, (start, end) in enumerate(zip(points, points[1:])):
                image.line(start, end, INK if index == 0 else WOOD_DARK, 6 - index)
                image.line(start, end, WOOD if index == 0 else ASH, 3 - min(index, 1))
        image.line((37, 28), (25, 17), ASH, 2)
        image.line((61, 37), (68, 22), WOOD_DARK, 2)
        image.rect(40, 51, 2, 3, INK_SOFT)
    else:
        # Overlapping hard-edged clusters create a deep overhead crown.
        clusters = (
            (22, 22, 19, 18, GREEN_DARK),
            (43, 14, 22, 18, GREEN),
            (62, 25, 20, 20, GREEN_DEEP),
            (18, 44, 18, 18, GREEN_DEEP),
            (42, 40, 25, 23, GREEN),
            (66, 47, 17, 18, GREEN_DARK),
        )
        for x, y, radius_x, radius_y, color in clusters:
            image.disc(x, y, radius_x, radius_y, INK)
            image.disc(x, y - 1, radius_x - 2, radius_y - 2, color)
        leaf_highlights = (
            (15, 15),
            (34, 7),
            (52, 13),
            (25, 30),
            (44, 28),
            (61, 34),
            (34, 48),
            (53, 49),
        )
        for x, y in leaf_highlights:
            image.rect(x, y, 7, 4, GREEN_LIGHT)
            image.rect(x + 2, y - 2, 4, 3, GREEN_BRIGHT)
            image.set_pixel(x + 7, y + 3, MOSS)
    return image.upscale(SCALE)


def world_plant(damaged: bool) -> Canvas:
    image = Canvas(32, 28)
    image.disc(16, 21, 15, 5, (14, 26, 24, 130))
    if damaged:
        dry_stems = (
            ((16, 21), (5, 11)),
            ((16, 21), (12, 4)),
            ((16, 21), (24, 5)),
            ((16, 21), (29, 14)),
        )
        for start, end in dry_stems:
            image.line(start, end, WOOD_DARK, 3)
            image.line(start, end, ASH, 1)
        image.rect(4, 10, 5, 3, SOIL_LIGHT)
        image.rect(22, 4, 5, 3, SOIL)
    else:
        leaves = ((6, 12), (11, 7), (17, 5), (23, 8), (27, 13), (20, 16), (12, 17))
        for index, (x, y) in enumerate(leaves):
            image.disc(x, y, 6, 4, INK)
            image.disc(x, y - 1, 4, 3, GREEN if index % 2 else GREEN_DARK)
            image.rect(x - 2, y - 2, 3, 1, GREEN_LIGHT)
    return image.upscale(SCALE)


def comparison_preview() -> Canvas:
    """Compose the scale row for local visual review, with the hero on its marker."""

    preview = Canvas(2560, 520, (15, 24, 28, 255))
    ground_top = 120
    baseline_y = ground_top + 240
    preview.blit(scale_ground(), 80, ground_top)
    preview.rect(80, baseline_y - 2, 2400, 4, GOLD_DARK)
    anchored_assets = (
        (small_enemy(), 80 + 180),
        (hero_idle_down(), 80 + 520),
        (door_entrance(), 80 + 840),
        (house_wall(), 80 + 1250),
        (large_enemy(), 80 + 1730),
        (tree(), 80 + 2180),
    )
    for asset, center_x in anchored_assets:
        preview.blit(asset, center_x - asset.width // 2, baseline_y - asset.height)
    return preview


AssetFactory = Callable[[], Canvas]
ASSETS: dict[str, tuple[AssetFactory, int]] = {
    "hero_idle_down.png": (hero_idle_down, 80),
    "small_enemy.png": (small_enemy, 56),
    "door_entrance.png": (door_entrance, 112),
    "house_wall.png": (house_wall, 144),
    "large_enemy.png": (large_enemy, 128),
    "tree.png": (tree, 192),
    "scale_ground.png": (scale_ground, 320),
}
WORLD_STATE_ASSETS: dict[str, AssetFactory] = {
    "damaged_ground.png": lambda: world_ground(True),
    "restored_ground.png": lambda: world_ground(False),
    "damaged_ground_detail.png": lambda: world_ground_detail(True),
    "restored_ground_detail.png": lambda: world_ground_detail(False),
    "damaged_path.png": lambda: world_path(True),
    "restored_path.png": lambda: world_path(False),
    "damaged_building.png": lambda: world_building(True),
    "restored_building.png": lambda: world_building(False),
    "dead_tree.png": lambda: world_tree(True),
    "living_tree.png": lambda: world_tree(False),
    "dead_plant.png": lambda: world_plant(True),
    "living_plant.png": lambda: world_plant(False),
    "damaged_sawmill.png": lambda: world_sawmill(True),
    "restored_sawmill.png": lambda: world_sawmill(False),
}
STATIC_WORLD_STATE_ASSETS: dict[str, tuple[tuple[int, int], int]] = {
    "damaged_fog.png": ((1440, 810), 250_000),
    "restored_fog.png": ((1440, 810), 250_000),
}


def _png_dimensions(payload: bytes) -> tuple[int, int] | None:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", payload[16:24])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed files without modifying them",
    )
    parser.add_argument(
        "--preview-output",
        type=Path,
        help="write a local scale-row preview to the selected path",
    )
    arguments = parser.parse_args()
    mismatches: list[str] = []
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORLD_STATE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename, (factory, expected_visible_height) in ASSETS.items():
        image = factory()
        bounds = image.alpha_bounds()
        if bounds is None or bounds[1] != 0 or bounds[3] + 1 != expected_visible_height:
            raise RuntimeError(
                f"{filename}: visible alpha height must be {expected_visible_height}, got {bounds}"
            )
        output = image.png_bytes()
        destination = OUTPUT_DIR / filename
        if arguments.check:
            if not destination.exists() or destination.read_bytes() != output:
                mismatches.append(filename)
            continue
        destination.write_bytes(output)
        print(f"generated {destination.relative_to(Path.cwd())}")

    for filename, factory in WORLD_STATE_ASSETS.items():
        output = factory().png_bytes()
        destination = WORLD_STATE_OUTPUT_DIR / filename
        if arguments.check:
            if not destination.exists() or destination.read_bytes() != output:
                mismatches.append(filename)
            continue
        destination.write_bytes(output)
        print(f"generated {destination.relative_to(Path.cwd())}")

    for filename, (expected_dimensions, maximum_size) in STATIC_WORLD_STATE_ASSETS.items():
        destination = WORLD_STATE_OUTPUT_DIR / filename
        payload = destination.read_bytes() if destination.exists() else b""
        if (
            _png_dimensions(payload) != expected_dimensions
            or len(payload) > maximum_size
        ):
            mismatches.append(filename)

    if mismatches:
        print("outdated generated assets: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    if arguments.check:
        asset_count = len(ASSETS) + len(WORLD_STATE_ASSETS)
        fog_count = len(STATIC_WORLD_STATE_ASSETS)
        print(
            f"verified {asset_count} deterministic Visual Lab assets "
            f"and {fog_count} optimized fog textures"
        )
    if arguments.preview_output is not None:
        arguments.preview_output.write_bytes(comparison_preview().png_bytes())
        print(f"generated visual review at {arguments.preview_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
