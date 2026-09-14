extends RefCounted

const HERO_SCENE_PATH := "res://scenes/gameplay/hero/hero_character.tscn"
const HERO_SCRIPT := preload("res://scenes/gameplay/hero/hero_character.gd")
const MANIFEST_PATH := (
	"res://tests/assets/characters/heroes/green_hero/ultra/stand_walk_manifest.json"
)
const FRAMES_PATH := (
	"res://tests/assets/characters/heroes/green_hero/ultra/green_hero_stand_walk_ultra.tres"
)
const MOVEMENT_ACTIONS: Array[StringName] = [
	&"gameplay_move_left",
	&"gameplay_move_right",
	&"gameplay_move_up",
	&"gameplay_move_down",
]
const DIRECTION_CASES := [
	{"suffix": "N", "actions": [&"gameplay_move_up"]},
	{
		"suffix": "NO",
		"actions": [&"gameplay_move_up", &"gameplay_move_right"],
	},
	{"suffix": "O", "actions": [&"gameplay_move_right"]},
	{
		"suffix": "SO",
		"actions": [&"gameplay_move_down", &"gameplay_move_right"],
	},
	{"suffix": "S", "actions": [&"gameplay_move_down"]},
	{
		"suffix": "SW",
		"actions": [&"gameplay_move_down", &"gameplay_move_left"],
	},
	{"suffix": "W", "actions": [&"gameplay_move_left"]},
	{
		"suffix": "NW",
		"actions": [&"gameplay_move_up", &"gameplay_move_left"],
	},
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_test_resource_contract()
	for variant in ["hd", "test"]:
		var package_root := "res://tests/assets/characters/heroes/green_hero/%s/" % variant
		_test_resource_contract(
			package_root + "stand_walk_manifest.json",
			package_root + "green_hero_stand_walk_%s.tres" % variant,
		)
	await _test_runtime_animation(tree)
	_release_actions()
	return failures


func _test_resource_contract(
	manifest_path: String = MANIFEST_PATH,
	frames_path: String = FRAMES_PATH,
) -> void:
	var manifest_text := FileAccess.get_file_as_string(manifest_path)
	var parsed_manifest: Variant = JSON.parse_string(manifest_text)
	_expect(parsed_manifest is Dictionary, "stand/walk manifest parses")
	if not parsed_manifest is Dictionary:
		return
	var manifest := parsed_manifest as Dictionary
	var defaults := manifest.get("defaults", {}) as Dictionary
	var source_canvas := manifest.get("source_canvas", []) as Array
	var animations := manifest.get("animations", []) as Array
	var sprite_frames := load(frames_path) as SpriteFrames
	var is_test_package: bool = manifest.get("variant", "") == "test"
	var animation_count := 48 if is_test_package else 16
	_expect(sprite_frames != null, "generated SpriteFrames resource loads")
	_expect(animations.size() == animation_count, "manifest contains its complete pose set")
	if sprite_frames == null or source_canvas.size() != 2:
		return
	if is_test_package:
		_test_test_pose_layout(manifest, sprite_frames)

	var expected_names: Array[StringName] = []
	var texture_paths: Dictionary[String, bool] = {}
	var total_frames := 0
	for animation_value in animations:
		var animation := animation_value as Dictionary
		var animation_canvas := animation.get("source_canvas", source_canvas) as Array
		_test_still_source(manifest, animation)
		var animation_name := StringName(str(animation.get("name", "")))
		expected_names.append(animation_name)
		var columns := int(animation.get("columns", defaults.get("columns", 0)))
		var rows := int(animation.get("rows", defaults.get("rows", 0)))
		var frame_count := int(
			animation.get("frame_count", defaults.get("frame_count", 0))
		)
		var frame_order := animation.get(
			"frame_order",
			defaults.get("frame_order", []),
		) as Array
		var durations := animation.get(
			"frame_durations_ms",
			defaults.get("frame_durations_ms", []),
		) as Array
		var crop := animation.get("crop_rect", []) as Array
		var runtime_file := str(animation.get("runtime_file", ""))
		var expected_atlas_path := "%s/%s" % [
			str(manifest.get("resource_root", "")),
			runtime_file,
		]
		_expect(sprite_frames.has_animation(animation_name), "%s exists" % animation_name)
		if not sprite_frames.has_animation(animation_name):
			continue
		_expect(
			sprite_frames.get_animation_loop(animation_name) == (not is_test_package),
			"%s uses its variant's loop behavior" % animation_name,
		)
		_expect(
			sprite_frames.get_frame_count(animation_name) == frame_count,
			"%s has its manifest frame count" % animation_name,
		)
		_expect(frame_order.size() == frame_count, "%s has complete frame order" % animation_name)
		_expect(durations.size() == frame_count, "%s has complete timing" % animation_name)
		if crop.size() != 4 or frame_order.size() != frame_count:
			continue
		var timing_unit := _greatest_common_divisor(durations)
		_expect(
			is_equal_approx(
				sprite_frames.get_animation_speed(animation_name),
				1000.0 / float(timing_unit),
			),
			"%s uses its declared speed" % animation_name,
		)
		for frame_index in range(frame_count):
			var texture := sprite_frames.get_frame_texture(
				animation_name,
				frame_index,
			) as AtlasTexture
			_expect(
				texture != null,
				"%s frame %d uses AtlasTexture" % [animation_name, frame_index],
			)
			if texture == null:
				continue
			var source_index := int(frame_order[frame_index])
			var frame_width := int(crop[2])
			var frame_height := int(crop[3])
			var expected_region := Rect2(
				(source_index % columns) * frame_width,
				(source_index / columns) * frame_height,
				frame_width,
				frame_height,
			)
			var expected_margin := Rect2(
				int(crop[0]),
				int(crop[1]),
				int(animation_canvas[0]) - frame_width,
				int(animation_canvas[1]) - frame_height,
			)
			_expect(texture.region == expected_region, "%s frame region matches" % animation_name)
			_expect(texture.margin == expected_margin, "%s frame margin matches" % animation_name)
			_expect(texture.filter_clip, "%s clips neighboring atlas cells" % animation_name)
			_expect(
				texture.get_size() == Vector2(animation_canvas[0], animation_canvas[1]),
				"%s restores its source canvas" % animation_name,
			)
			_expect(
				is_equal_approx(
					sprite_frames.get_frame_duration(animation_name, frame_index),
					float(durations[frame_index]) / float(timing_unit),
				),
				"%s frame duration matches" % animation_name,
			)
			if texture.atlas != null:
				_expect(
					texture.atlas.resource_path == expected_atlas_path,
					"%s references its own optimized sheet" % animation_name,
				)
				texture_paths[texture.atlas.resource_path] = true
		total_frames += frame_count

	_expect(total_frames == (48 if is_test_package else 256), "resource has its full frame set")
	_expect(texture_paths.size() == animation_count, "resource keeps separate directional textures")
	_expect(
		sprite_frames.get_animation_names().size() == expected_names.size(),
		"resource contains no undeclared animations",
	)
	for texture_path in texture_paths:
		var source_texture := load(str(texture_path)) as Texture2D
		var image := source_texture.get_image() if source_texture != null else null
		_expect(image != null, "%s loads as an image" % texture_path)
		_expect(image != null and not image.has_mipmaps(), "%s has no mipmaps" % texture_path)


func _test_test_pose_layout(manifest: Dictionary, sprite_frames: SpriteFrames) -> void:
	var reference := manifest.get("reference_pose", {}) as Dictionary
	var animation := StringName(str(reference.get("animation", "stand_S")))
	var frame := int(reference.get("frame", 0))
	var texture := sprite_frames.get_frame_texture(animation, frame) as AtlasTexture
	_expect(texture != null, "test reference has an atlas texture")
	if texture == null:
		return
	var cell := texture.atlas.get_image().get_region(Rect2i(texture.region))
	var used := cell.get_used_rect()
	used.position += Vector2i(texture.margin.position)
	var bounds := reference.get("alpha_bounds", []) as Array
	var expected := Rect2i(int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3]))
	_expect(
		used == expected,
		"test reference alpha bounds: observed %s, expected %s" % [used, expected],
	)
	var layouts := sprite_frames.get_meta(&"animation_layouts", {}) as Dictionary
	var layout := layouts.get(animation, {}) as Dictionary
	_expect(not layout.is_empty(), "test reference has calibrated layout metadata")
	if layout.is_empty():
		return
	var scale := layout["scale"] as Vector2
	_expect(
		is_equal_approx(float(used.size.y) * scale.y, float(reference["world_height"])),
		"test reference body has its intended world height without transparent margins",
	)
	var anchor := reference["foot_anchor"] as Array
	var foot := Vector2(float(anchor[0]), float(anchor[1]))
	var offset := layout["offset"] as Vector2
	_expect(
		(foot - texture.get_size() / 2.0 + offset).is_zero_approx(),
		"test reference foot stays on the ground anchor",
	)


func _test_still_source(manifest: Dictionary, animation: Dictionary) -> void:
	var sources := animation.get("source", {}) as Dictionary
	if not sources.has("reference_image"):
		return
	var root := str(manifest["resource_root"])
	var reference_record := sources["reference_image"] as Array
	var reference := Image.load_from_file(
		ProjectSettings.globalize_path("%s/%s" % [root, reference_record[0]]),
	)
	var sheet := Image.load_from_file(
		ProjectSettings.globalize_path("%s/%s" % [root, animation["runtime_file"]]),
	)
	var crop := animation["crop_rect"] as Array
	var crop_rect := Rect2i(int(crop[0]), int(crop[1]), int(crop[2]), int(crop[3]))
	var name := str(animation["name"])
	_expect(reference.get_used_rect() == crop_rect, "%s has its source alpha bounds" % name)
	var expected_pixels := reference.get_region(crop_rect).get_data()
	for frame in range(16):
		var origin := Vector2i(frame % 4, frame / 4) * crop_rect.size
		var cell := sheet.get_region(Rect2i(origin, crop_rect.size))
		_expect(
			cell.get_data() == expected_pixels,
			"%s frame %d matches the supplied still image" % [name, frame],
		)


func _test_runtime_animation(tree: SceneTree) -> void:
	_release_actions()
	var packed_scene := load(HERO_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "HeroCharacter scene loads with Green Hero")
	if packed_scene == null:
		return
	var hero: HERO_SCRIPT = packed_scene.instantiate() as HERO_SCRIPT
	_expect(hero != null, "HeroCharacter instantiates with animation controller")
	if hero == null:
		return
	tree.root.add_child(hero)
	await tree.physics_frame
	var sprite := hero.get_node_or_null(
		"Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	var controller := hero.get_node_or_null("AnimationController")
	_expect(sprite != null, "runtime HeroSprite is AnimatedSprite2D")
	_expect(controller != null, "runtime animation controller exists")
	if sprite == null or controller == null:
		hero.queue_free()
		await tree.process_frame
		return

	_expect(sprite.animation == &"stand_S", "hero starts in stand_S")
	_expect(sprite.is_playing(), "initial stand animation loops")
	_expect(hero.get_animation_direction_name() == &"S", "initial direction is south")

	for direction_case in DIRECTION_CASES:
		_release_actions()
		var actions := direction_case["actions"] as Array
		for action in actions:
			Input.action_press(action as StringName)
		await tree.physics_frame
		var suffix := str(direction_case["suffix"])
		_expect(
			hero.get_animation_direction_name() == StringName(suffix),
			"movement resolves direction %s" % suffix,
		)
		_expect(sprite.animation == StringName("walk_%s" % suffix), "walk_%s plays" % suffix)
		_expect_sprite_layout(sprite, 1205.0, Vector2(627, 1224), "walk_%s" % suffix)
		_expect(hero.is_ground_motion_active(), "walk_%s follows real movement" % suffix)
		for action in actions:
			Input.action_release(action as StringName)
		await tree.physics_frame
		_expect(sprite.animation == StringName("stand_%s" % suffix), "stand_%s follows" % suffix)
		_expect_sprite_layout(sprite, 1205.0, Vector2(627, 1224), "stand_%s" % suffix)
		_expect(
			hero.get_animation_direction_name() == StringName(suffix),
			"stand_%s retains its direction" % suffix,
		)

	var blocker := StaticBody2D.new()
	var blocker_collision := CollisionShape2D.new()
	var blocker_shape := RectangleShape2D.new()
	blocker_shape.size = Vector2(20.0, 100.0)
	blocker_collision.shape = blocker_shape
	blocker.add_child(blocker_collision)
	blocker.global_position = hero.global_position + Vector2(40.0, 0.0)
	tree.root.add_child(blocker)
	await tree.physics_frame
	Input.action_press(&"gameplay_move_right")
	for _frame in range(20):
		await tree.physics_frame
	var position_at_wall := hero.position
	await tree.physics_frame
	await tree.physics_frame
	_expect(hero.position == position_at_wall, "wall blocks grounded movement")
	_expect(not hero.is_ground_motion_active(), "blocked movement is not reported as walking")
	_expect(sprite.animation == &"stand_O", "blocked movement shows directional stand")
	Input.action_release(&"gameplay_move_right")
	blocker.queue_free()
	await tree.physics_frame

	Input.action_press(&"gameplay_move_down")
	await tree.physics_frame
	sprite.set_frame_and_progress(5, 0.4)
	var position_before_visual_turn := hero.position
	hero.animation_direction = HERO_SCRIPT.AnimationDirection.EAST
	controller.call(&"_physics_process", 0.0)
	_expect(sprite.animation == &"walk_O", "walking direction changes without action reset")
	_expect(sprite.frame == 5, "walking direction keeps its frame phase")
	_expect(is_equal_approx(sprite.frame_progress, 0.4), "walking direction keeps progress")
	_expect(
		hero.position == position_before_visual_turn,
		"visual direction change never moves hero",
	)
	Input.action_release(&"gameplay_move_down")
	await tree.physics_frame

	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	var position_before_lock := hero.position
	hero.set_movement_enabled(false)
	await tree.physics_frame
	_expect(sprite.animation == &"stand_O", "movement lock switches to directional stand")
	_expect(sprite.is_playing(), "movement lock leaves no walk animation running")
	_expect(hero.position == position_before_lock, "movement lock keeps world position")
	Input.action_release(&"gameplay_move_right")
	hero.set_movement_enabled(true)
	await tree.physics_frame

	hero._input(_key_event(KEY_SPACE, true))
	await tree.physics_frame
	_expect(hero.is_jumping(), "existing jump remains active")
	_expect(sprite.animation == &"stand_O", "jump uses its directional stand frame")
	_expect(sprite.frame == 0 and not sprite.is_playing(), "jump freezes the first stand frame")
	for _frame in range(60):
		if not hero.is_jumping():
			break
		await tree.physics_frame
	_expect(not hero.is_jumping(), "existing jump still lands")
	_expect(
		sprite.animation == &"stand_O" and sprite.is_playing(),
		"stand loop resumes after landing",
	)

	hero.queue_free()
	await tree.process_frame


func _expect_sprite_layout(
	sprite: AnimatedSprite2D,
	height_pixels: float,
	foot_anchor: Vector2,
	description: String,
) -> void:
	var texture_scale := sprite.get_parent() as Node2D
	var texture := sprite.sprite_frames.get_frame_texture(sprite.animation, 0)
	_expect(
		is_equal_approx(height_pixels * texture_scale.scale.y, 80.0),
		"%s keeps an 80-world-pixel reference height" % description,
	)
	var foot_position := sprite.offset - texture.get_size() / 2.0 + foot_anchor
	_expect(
		foot_position.is_zero_approx(),
		"%s keeps its visual foot at the sprite origin" % description,
	)


func _greatest_common_divisor(values: Array) -> int:
	var result := 0
	for value in values:
		result = _integer_gcd(result, int(value))
	return result


func _integer_gcd(left: int, right: int) -> int:
	left = absi(left)
	right = absi(right)
	while right != 0:
		var remainder := left % right
		left = right
		right = remainder
	return left


func _key_event(key: Key, pressed: bool) -> InputEventKey:
	var event := InputEventKey.new()
	event.device = InputEvent.DEVICE_ID_KEYBOARD
	event.keycode = key
	event.pressed = pressed
	return event


func _release_actions() -> void:
	for action in MOVEMENT_ACTIONS:
		Input.action_release(action)
	for action in [
		&"gameplay_jump",
		&"gameplay_sneak",
		&"gameplay_sprint",
	]:
		Input.action_release(action)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("GreenHeroAnimation: %s" % description)
