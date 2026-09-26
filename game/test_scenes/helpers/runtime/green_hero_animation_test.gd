extends RefCounted

const HERO_SCENE_PATH := "res://test_scenes/characters/heroes/greenhero/hero_character.tscn"
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const VARIANTS: Array[String] = [
	"comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low",
]
const FPS_VALUES: Array[int] = [8, 10, 12, 14, 16]
const ACTIONS: Array[String] = ["stand", "slowwalk", "walk", "sneak", "run", "sprint", "jump"]
const DIRECTIONS: Array[String] = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
const MOVEMENT_ACTIONS: Array[StringName] = [
	&"gameplay_move_left", &"gameplay_move_right", &"gameplay_move_up", &"gameplay_move_down",
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_test_runtime_animation_library()
	await _test_runtime_movement(tree)
	_release_actions()
	return failures


func _test_runtime_animation_library() -> void:
	var library := preload(
		"res://test_scenes/characters/heroes/greenhero/green_hero_animation_library.gd"
	)
	for variant in VARIANTS:
		for fps in FPS_VALUES:
			var frames := library.build(variant, fps)
			_expect(
				frames.get_animation_names().size() == ACTIONS.size() * DIRECTIONS.size(),
				"full matrix %s/%d" % [variant, fps],
			)
			for action in ACTIONS:
				for direction in DIRECTIONS:
					var name := StringName("%s_%s" % [action, direction])
					_expect(frames.has_animation(name), "%s/%s exists" % [variant, name])
					if not frames.has_animation(name):
						continue
					var frame_count := (
						1 if action == "jump" else (12 if action == "sprint" else fps)
					)
					_expect(frames.get_frame_count(name) == frame_count, "%s frame count" % name)
					_expect(
						frames.get_animation_loop(name) == (action != "jump"),
						"%s loop" % name,
					)
					var speed := 12.0 if action == "sprint" else float(fps)
					_expect(
						is_equal_approx(frames.get_animation_speed(name), speed),
						"%s FPS" % name,
					)
	var sixteen_frames := library.build("comic_high", 16, 16)
	var walk_sw_frame := sixteen_frames.get_frame_texture(&"walk_SW", 0) as AtlasTexture
	_expect(walk_sw_frame != null, "Walk SW 4x4 has an atlas frame")
	if walk_sw_frame != null:
		_expect(
			walk_sw_frame.atlas.resource_path.ends_with(
				"/walk/comic_high/spritesheet-fram16/greenhero_hd_walk_spritesheet_SW_4x4_o.png"
			),
			"Walk SW 4x4 loads the SW sheet instead of SO",
		)


func _test_runtime_movement(tree: SceneTree) -> void:
	_release_actions()
	var packed_scene := load(HERO_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "HeroCharacter scene loads")
	if packed_scene == null:
		return
	var hero: HERO_SCRIPT = packed_scene.instantiate() as HERO_SCRIPT
	_expect(hero != null, "HeroCharacter instantiates")
	if hero == null:
		return
	tree.root.add_child(hero)
	await tree.physics_frame
	var sprite := hero.get_node_or_null(
		"Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	var controller := hero.get_node_or_null("AnimationController")
	_expect(sprite != null and controller != null, "HeroSprite and controller exist")
	if sprite == null or controller == null:
		hero.queue_free()
		await tree.process_frame
		return

	_expect(sprite.animation == &"stand_S", "hero starts in stand_S")
	_expect(
		sprite.sprite_frames.get_meta(&"hero_variant", "") == "comic_high",
		"default variant is Comic High",
	)
	_expect(sprite.sprite_frames.get_meta(&"hero_frames", 0) == 8, "default animation frames are 8")
	_expect(sprite.sprite_frames.get_meta(&"hero_fps", 0) == 8, "default FPS is 8")

	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	_expect(sprite.animation == &"walk_O", "normal movement uses Walk")
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame

	Input.action_press(&"gameplay_sprint")
	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	_expect(sprite.animation == &"slowwalk_O", "Shift movement uses Slow Walk")
	Input.action_release(&"gameplay_sprint")
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame

	hero.set("_walk_mode_active", true)
	Input.action_press(&"gameplay_move_left")
	Input.action_press(&"gameplay_move_down")
	await tree.physics_frame
	_expect(sprite.animation == &"walk_SW", "Walk movement to southwest uses Walk SW")
	Input.action_release(&"gameplay_move_left")
	Input.action_release(&"gameplay_move_down")
	hero.set("_walk_mode_active", false)
	await tree.physics_frame

	Input.action_press(&"gameplay_sneak")
	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	_expect(sprite.animation == &"sneak_O", "Sneak movement uses Sneak")
	Input.action_release(&"gameplay_sneak")
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame

	Input.action_press(&"gameplay_sprint")
	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	_expect(sprite.animation == &"sprint_O", "Sprint movement uses Sprint")
	_expect(
		is_equal_approx(sprite.sprite_frames.get_animation_speed(&"sprint_O"), 12.0),
		"Sprint runs at 12 FPS",
	)
	Input.action_release(&"gameplay_sprint")
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame

	hero.animation_direction = HERO_SCRIPT.AnimationDirection.EAST
	hero._input(_key_event(KEY_SPACE, true))
	await tree.physics_frame
	_expect(sprite.animation == &"jump_O", "Jump uses its directional pose")
	_expect(sprite.frame == 0 and not sprite.is_playing(), "Jump freezes its single frame")
	for _frame in range(60):
		if not hero.is_jumping():
			break
		await tree.physics_frame
	_expect(not hero.is_jumping(), "Jump lands")

	hero.queue_free()
	await tree.process_frame


func _key_event(key: Key, pressed: bool) -> InputEventKey:
	var event := InputEventKey.new()
	event.device = InputEvent.DEVICE_ID_KEYBOARD
	event.keycode = key
	event.pressed = pressed
	return event


func _release_actions() -> void:
	for action in MOVEMENT_ACTIONS:
		Input.action_release(action)
	for action in [&"gameplay_jump", &"gameplay_sneak", &"gameplay_sprint"]:
		Input.action_release(action)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("GreenHeroAnimation: %s" % description)
