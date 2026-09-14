extends RefCounted

const HERO_SCRIPT := preload("res://scenes/gameplay/hero/hero_character.gd")
const HERO_SCENE := preload("res://scenes/gameplay/hero/hero_character.tscn")
const ANIMATION_TEST := preload("res://tests/runtime/green_hero_animation_test.gd")
const PACKAGE_ROOT := "res://tests/assets/characters/heroes/green_hero/"
const TEST_FRAMES_PATH := PACKAGE_ROOT + "test/green_hero_stand_walk_test.tres"
const SPRITE_PATH := "Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
const ARROW_KEYS := {
	&"gameplay_move_up": KEY_UP,
	&"gameplay_move_right": KEY_RIGHT,
	&"gameplay_move_down": KEY_DOWN,
	&"gameplay_move_left": KEY_LEFT,
}

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_release_actions()
	await _test_movement_poses(tree)
	await _test_legacy_fallback(tree)
	_release_actions()
	return failures


func _test_movement_poses(tree: SceneTree) -> void:
	var hero := HERO_SCENE.instantiate() as HERO_SCRIPT
	tree.root.add_child(hero)
	var sprite := hero.get_node(SPRITE_PATH) as AnimatedSprite2D
	sprite.sprite_frames = load(TEST_FRAMES_PATH) as SpriteFrames
	await tree.physics_frame
	await tree.physics_frame
	_expect_pose(sprite, &"stand_S")
	var shape := (hero.get_node("CollisionShape2D") as CollisionShape2D).shape

	for direction_case in ANIMATION_TEST.DIRECTION_CASES:
		var actions := direction_case["actions"] as Array
		var suffix := str(direction_case["suffix"])
		hero.set_movement_enabled(false)
		hero.set_movement_enabled(true)
		for action in actions:
			Input.action_press(action as StringName)
		await tree.physics_frame
		await tree.physics_frame
		_expect(hero.get_movement_state() == HERO_SCRIPT.MovementState.JOG, "normal motion jogs")
		_expect_pose(sprite, StringName("run_%s" % suffix))

		hero._input(_key_event(KEY_CAPSLOCK, true, true))
		await tree.physics_frame
		_expect(hero.get_movement_state() == HERO_SCRIPT.MovementState.WALK, "Caps Lock walks")
		_expect_pose(sprite, StringName("walk_%s" % suffix))
		hero._input(_key_event(KEY_CAPSLOCK, true, true))

		var key := ARROW_KEYS[actions[0]] as Key
		hero._input(_key_event(key, true))
		hero._input(_key_event(key, false))
		hero._input(_key_event(key, true))
		await tree.physics_frame
		_expect(hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN, "double tap runs")
		_expect_pose(sprite, StringName("run_%s" % suffix))

		Input.action_press(&"gameplay_sprint")
		await tree.physics_frame
		_expect(hero.get_movement_state() == HERO_SCRIPT.MovementState.SPRINT, "held Shift sprints")
		_expect_pose(sprite, StringName("sprint_%s" % suffix))
		Input.action_release(&"gameplay_sprint")
		Input.action_press(&"gameplay_sneak")
		await tree.physics_frame
		_expect(hero.get_movement_state() == HERO_SCRIPT.MovementState.SNEAK, "held Ctrl sneaks")
		_expect_pose(sprite, StringName("sneak_%s" % suffix))
		Input.action_release(&"gameplay_sneak")
		await tree.physics_frame

		hero._input(_key_event(KEY_SPACE, true))
		await tree.physics_frame
		_expect(hero.is_jumping(), "Space starts the existing jump")
		_expect_pose(sprite, StringName("jump_%s" % suffix))
		_expect(hero.jump_visual.position.y < 0.0, "jump pose follows the existing visual arc")
		for _frame in range(90):
			if not hero.is_jumping():
				break
			await tree.physics_frame
		_expect(not hero.is_jumping(), "jump lands normally")
		await tree.physics_frame
		_expect_pose(sprite, StringName("run_%s" % suffix))
		_release_actions()
		await tree.physics_frame
		_expect_pose(sprite, StringName("stand_%s" % suffix))
		_expect(
			(hero.get_node("CollisionShape2D") as CollisionShape2D).shape == shape,
			"pose changes preserve collision geometry",
		)

	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	var position_before := hero.position
	hero.set_movement_enabled(false)
	await tree.physics_frame
	_expect_pose(sprite, &"stand_O")
	_expect(hero.position == position_before, "movement lock holds the test pose in place")
	hero.queue_free()
	_release_actions()
	await tree.process_frame


func _test_legacy_fallback(tree: SceneTree) -> void:
	var hero := HERO_SCENE.instantiate() as HERO_SCRIPT
	tree.root.add_child(hero)
	var sprite := hero.get_node(SPRITE_PATH) as AnimatedSprite2D
	var controller := hero.get_node("AnimationController")
	hero.set_physics_process(false)
	controller.set_physics_process(false)
	hero.animation_direction = HERO_SCRIPT.AnimationDirection.NORTH_EAST
	hero.set("_ground_motion_active", true)
	for variant in ["hd", "pixel_art", "ultra"]:
		sprite.sprite_frames = load(
			PACKAGE_ROOT + "%s/green_hero_stand_walk_%s.tres" % [variant, variant]
		) as SpriteFrames
		for state in HERO_SCRIPT.MovementState.values():
			hero.set("_movement_state", state)
			controller.call(&"_physics_process", 0.0)
			_expect(
				sprite.animation == &"walk_NO", "%s keeps ground fallback %s" % [variant, state],
			)
			_expect(sprite.is_playing(), "%s keeps its ground playback" % variant)
		hero.set("_jump_state", HERO_SCRIPT.JumpState.STAND)
		controller.call(&"_physics_process", 0.0)
		_expect(sprite.animation == &"stand_NO", "%s keeps the jump fallback direction" % variant)
		_expect(not sprite.is_playing() and sprite.frame == 0, "%s freezes its jump" % variant)
		hero.set("_jump_state", HERO_SCRIPT.JumpState.GROUND)
	hero.queue_free()
	await tree.process_frame


func _expect_pose(sprite: AnimatedSprite2D, name: StringName) -> void:
	_expect(sprite.animation == name, "%s selected, observed %s" % [name, sprite.animation])
	_expect(sprite.frame == 0 and not sprite.is_playing(), "%s is a stationary pose" % name)
	var texture_scale := sprite.get_parent() as Node2D
	_expect(
		texture_scale.scale.is_equal_approx(Vector2.ONE * (80.0 / 1205.0)),
		"%s retains standing scale, including crouched and airborne poses" % name,
	)
	_expect(sprite.offset == Vector2(0.0, -597.0), "%s retains the shared ground anchor" % name)
	var texture := sprite.sprite_frames.get_frame_texture(name, 0) as AtlasTexture
	_expect(texture != null, "%s has its individual texture" % name)
	if texture != null:
		_expect(texture.get_size() == Vector2(1436, 1254), "%s preserves its full canvas" % name)


func _key_event(key: Key, pressed: bool, physical: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.device = InputEvent.DEVICE_ID_KEYBOARD
	event.pressed = pressed
	if physical:
		event.physical_keycode = key
	else:
		event.keycode = key
	return event


func _release_actions() -> void:
	for action in ARROW_KEYS:
		Input.action_release(action)
	for action in [&"gameplay_jump", &"gameplay_sprint", &"gameplay_sneak"]:
		Input.action_release(action)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("GreenHeroTestPoses: %s" % description)
