extends RefCounted

## Builds the Green Hero preview set from the five supplied art variants.
##
## The source sheets stay in test_assets and are sliced at runtime so the
## visual lab can switch quality and frame rate without duplicating resources.

const SOURCE_ROOT := "res://test_assets/characters/heroes/greenhero/spritesheets"
const DIRECTIONS: Array[String] = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
const ACTIONS: Array[String] = ["stand", "slowwalk", "walk", "sneak", "run", "sprint", "jump"]
const FPS_VALUES: Array[int] = [8, 10, 12, 14, 16]
const VARIANT_IDS: Array[String] = [
	"comic_high",
	"comic_mid",
	"comic_low",
	"pixel_high",
	"pixel_low",
]
const GRID_BY_FPS: Dictionary = {
	8: Vector2i(4, 2),
	10: Vector2i(5, 2),
	12: Vector2i(4, 3),
	14: Vector2i(7, 2),
	16: Vector2i(4, 4),
}
const JUMP_SOURCE_CANVAS := Vector2(1436.0, 1254.0)
const JUMP_REFERENCE_HEIGHT := 1205.0
const JUMP_FOOT_ANCHOR := Vector2(718.0, 1224.0)
const WORLD_HEIGHT := 80.0

static var _cache: Dictionary = {}


static func build(
		variant_id: String,
		frame_count: int,
		playback_fps: int = -1,
) -> SpriteFrames:
	var normalized_variant := variant_id if variant_id in VARIANT_IDS else VARIANT_IDS[0]
	var normalized_frames := frame_count if frame_count in FPS_VALUES else FPS_VALUES[0]
	var normalized_fps := (
		playback_fps if playback_fps in FPS_VALUES else normalized_frames
	)
	var cache_key := "%s:%d:%d" % [normalized_variant, normalized_frames, normalized_fps]
	if _cache.has(cache_key):
		return (_cache[cache_key] as SpriteFrames).duplicate(true)

	var frames := SpriteFrames.new()
	frames.remove_animation(&"default")
	var layouts: Dictionary = {}
	var source_paths: Dictionary = {}
	for action in ACTIONS:
		var source_action := "run" if action == "sprint" else action
		var source_fps := 12 if action == "sprint" else normalized_frames
		for direction in DIRECTIONS:
			var animation_name := StringName("%s_%s" % [action, direction])
			source_paths[animation_name] = _source_path(
				source_action,
				normalized_variant,
				source_fps,
				direction,
				action == "jump",
			)
			var layout := _add_animation(
				frames,
				animation_name,
				source_action,
				normalized_variant,
				source_fps,
				direction,
				12 if action == "sprint" else normalized_fps,
				action == "jump",
			)
			if not layout.is_empty():
				layouts[animation_name] = layout

	frames.set_meta(&"animation_layouts", layouts)
	frames.set_meta(&"animation_sources", source_paths)
	frames.set_meta(&"hero_variant", normalized_variant)
	frames.set_meta(&"hero_frames", normalized_frames)
	frames.set_meta(&"hero_fps", normalized_fps)
	_cache[cache_key] = frames
	return frames.duplicate(true)


static func _add_animation(
		frames: SpriteFrames,
		animation_name: StringName,
		action: String,
		variant_id: String,
		source_fps: int,
		direction: String,
		playback_fps: int,
		is_jump: bool,
) -> Dictionary:
	frames.add_animation(animation_name)
	frames.set_animation_loop(animation_name, not is_jump)
	frames.set_animation_speed(animation_name, float(playback_fps))
	var texture_path: String
	var columns: int
	var rows: int
	texture_path = _source_path(action, variant_id, source_fps, direction, is_jump)
	if is_jump:
		columns = 1
		rows = 1
	else:
		var grid := GRID_BY_FPS[source_fps] as Vector2i
		columns = grid.x
		rows = grid.y

	var atlas := load(texture_path) as Texture2D
	if atlas == null:
		push_error("Green Hero source sheet is unavailable: %s" % texture_path)
		return {}
	var cell_size := atlas.get_size() / Vector2(columns, rows)
	var frame_count := columns * rows if not is_jump else 1
	for frame_index in range(frame_count):
		var region := Rect2(
			Vector2(frame_index % columns, frame_index / columns) * cell_size,
			cell_size,
		)
		var frame := AtlasTexture.new()
		frame.atlas = atlas
		frame.region = region
		frame.filter_clip = true
		frames.add_frame(animation_name, frame)

	if is_jump:
		var source_scale := atlas.get_size() / JUMP_SOURCE_CANVAS
		return {
			"scale": Vector2.ONE * WORLD_HEIGHT / (JUMP_REFERENCE_HEIGHT * source_scale.y),
			"offset": Vector2(
				atlas.get_size().x / 2.0 - JUMP_FOOT_ANCHOR.x * source_scale.x,
				atlas.get_size().y / 2.0 - JUMP_FOOT_ANCHOR.y * source_scale.y,
			),
		}
	return {
		"scale": Vector2.ONE / cell_size.y * WORLD_HEIGHT,
		"offset": Vector2(0.0, -cell_size.y / 2.0),
	}


static func _source_path(
		action: String,
		variant_id: String,
		source_fps: int,
		direction: String,
		is_jump: bool,
) -> String:
	if is_jump:
		return "%s/jump/%s/greenhero_hd_jump_%s.png" % [
			SOURCE_ROOT, variant_id, direction,
		]
	var grid := GRID_BY_FPS[source_fps] as Vector2i
	return "%s/%s/%s/spritesheet-fram%d/greenhero_hd_%s_spritesheet_%s_%dx%d_o.png" % [
		SOURCE_ROOT,
		action,
		variant_id,
		source_fps,
		action,
		direction,
		grid.x,
		grid.y,
	]
