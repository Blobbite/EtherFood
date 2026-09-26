from pathlib import Path
from PIL import Image
import argparse
import os

FRAMES = 6
COLUMNS = 2
ROWS = 3
KEYWORD = "spritesheet.png"


def get_common_content_box(frames):
    """
    Find the smallest common rectangle that contains all visible pixels
    across all frames.

    Only fully transparent outer borders are removed.
    Every frame receives the exact same crop so animation alignment
    is preserved.
    """
    left = None
    top = None
    right = None
    bottom = None

    for frame in frames:
        alpha = frame.getchannel("A")
        bbox = alpha.getbbox()

        if bbox is None:
            continue

        frame_left, frame_top, frame_right, frame_bottom = bbox

        if left is None:
            left = frame_left
            top = frame_top
            right = frame_right
            bottom = frame_bottom
        else:
            left = min(left, frame_left)
            top = min(top, frame_top)
            right = max(right, frame_right)
            bottom = max(bottom, frame_bottom)

    if left is None:
        return None

    return left, top, right, bottom


def get_output_paths(png_path: Path):
    """
    Return both possible output paths for one source spritesheet.
    """
    normal_output = png_path.with_name(
        f"{png_path.stem}_2x3.png"
    )
    optimized_output = png_path.with_name(
        f"{png_path.stem}_2x3_o.png"
    )

    return normal_output, optimized_output


def processed_output_exists(png_path: Path):
    """
    Check whether this source file was already processed.

    If either the normal 2x3 output or optimized 2x3 output exists
    in the same directory, the source is considered processed.
    """
    normal_output, optimized_output = get_output_paths(png_path)

    existing = []

    if normal_output.exists():
        existing.append(normal_output)

    if optimized_output.exists():
        existing.append(optimized_output)

    return existing


def find_spritesheets(start_dir: Path):
    """
    Recursively find matching PNG files while completely ignoring
    directories whose names start with a dot, for example:

        .git
        .godot
        .workspace
        .cache

    Hidden directories are pruned before os.walk enters them.
    """
    files = []

    for root, dirs, filenames in os.walk(start_dir):
        # Never descend into directories whose names start with '.'.
        dirs[:] = [
            directory
            for directory in dirs
            if not directory.startswith(".")
        ]

        root_path = Path(root)

        for filename in filenames:
            if filename.lower().endswith(KEYWORD):
                files.append(root_path / filename)

    return sorted(files)


def convert_to_2x3(png_path: Path, optimize: bool):
    existing_outputs = processed_output_exists(png_path)

    if existing_outputs:
        print(f"[SKIP] {png_path}")
        print(
            "       Existing output: "
            + ", ".join(path.name for path in existing_outputs)
        )
        print()
        return

    try:
        with Image.open(png_path) as source:
            image = source.convert("RGBA")
    except Exception as e:
        print(f"[ERROR] Cannot open: {png_path}")
        print(f"        {e}")
        print()
        return

    if image.width % FRAMES != 0:
        print(f"[SKIP] {png_path}")
        print(
            f"       Width {image.width} is not divisible by {FRAMES}"
        )
        print()
        return

    frame_width = image.width // FRAMES
    frame_height = image.height

    frames = []

    for i in range(FRAMES):
        left = i * frame_width

        frame = image.crop(
            (
                left,
                0,
                left + frame_width,
                frame_height,
            )
        )

        frames.append(frame)

    original_frame_width = frame_width
    original_frame_height = frame_height

    crop_left = 0
    crop_top = 0
    crop_right = original_frame_width
    crop_bottom = original_frame_height

    if optimize:
        crop_box = get_common_content_box(frames)

        if crop_box is None:
            print(f"[SKIP] {png_path}")
            print("       All frames are fully transparent")
            print()
            return

        crop_left, crop_top, crop_right, crop_bottom = crop_box

        frames = [
            frame.crop(crop_box)
            for frame in frames
        ]

        frame_width = crop_right - crop_left
        frame_height = crop_bottom - crop_top

    atlas_width = frame_width * COLUMNS
    atlas_height = frame_height * ROWS

    atlas = Image.new(
        "RGBA",
        (atlas_width, atlas_height),
        (0, 0, 0, 0),
    )

    for i, frame in enumerate(frames):
        column = i % COLUMNS
        row = i // COLUMNS

        x = column * frame_width
        y = row * frame_height

        atlas.paste(frame, (x, y))

    normal_output, optimized_output = get_output_paths(png_path)
    output_path = optimized_output if optimize else normal_output

    try:
        atlas.save(
            output_path,
            "PNG",
            optimize=True,
            compress_level=9,
        )
    except Exception as e:
        print(f"[ERROR] Cannot save: {output_path}")
        print(f"        {e}")
        print()
        return

    print(f"[OK] {png_path}")
    print(f"     Source:       {image.width}x{image.height}")
    print(
        f"     Frame:        "
        f"{original_frame_width}x{original_frame_height}"
    )

    if optimize:
        original_area = (
            original_frame_width
            * original_frame_height
        )

        optimized_area = (
            frame_width
            * frame_height
        )

        reduction = (
            1 - optimized_area / original_area
        ) * 100

        print(
            f"     Optimized:    "
            f"{frame_width}x{frame_height}"
        )

        print(
            f"     Crop:         "
            f"L={crop_left} "
            f"T={crop_top} "
            f"R={original_frame_width - crop_right} "
            f"B={original_frame_height - crop_bottom}"
        )

        print(
            f"     Area saved:   "
            f"{reduction:.1f}%"
        )

    print(
        f"     Output:       "
        f"{atlas_width}x{atlas_height}"
    )

    print(
        f"     Saved as:     "
        f"{output_path.name}"
    )

    print()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Recursively finds PNG files ending in "
            "'spritesheet.png' and converts their "
            "6 horizontal frames into a 2x3 sprite sheet. "
            "Directories whose names start with '.' are ignored."
        )
    )

    parser.add_argument(
        "--optimize",
        action="store_true",
        help=(
            "Remove the common fully transparent outer border "
            "from all 6 frames before creating the 2x3 sheet. "
            "Frame alignment is preserved."
        ),
    )

    args = parser.parse_args()

    start_dir = Path.cwd()

    files = find_spritesheets(start_dir)

    if not files:
        print(
            f"[INFO] No files ending in "
            f"'{KEYWORD}' were found."
        )
        return

    print(
        f"[INFO] Found {len(files)} spritesheet(s)."
    )
    print(
        "[INFO] Directories starting with '.' are ignored."
    )

    if args.optimize:
        print(
            "[INFO] Transparent-border optimization enabled."
        )

    print()

    for png_path in files:
        convert_to_2x3(
            png_path,
            optimize=args.optimize,
        )

    print("[DONE] Processing complete.")


if __name__ == "__main__":
    main()
