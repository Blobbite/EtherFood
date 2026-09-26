extends RefCounted

const HERO_SCENE_PATH := "res://test_scenes/characters/heroes/greenhero/hero_character.tscn"
const HERO_ROOM_SCENE_PATH := "res://test_scenes/environment/hero_room.tscn"
const MOVEMENT_CONFIG_PATH := "res://shared/resources/hero_movement_v0.tres"
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const MOVEMENT_CONFIG_SCRIPT := preload(
	"res://shared/resources/hero_movement_config.gd"
)
const CAMERA_CONTROLLER_SCRIPT := preload(
	"res://shared/camera/player_camera_controller.gd"
)
const JUMP_ACTION := &"gameplay_jump"
const SNEAK_ACTION := &"gameplay_sneak"
const SPRINT_ACTION := &"gameplay_sprint"
const WALK_TOGGLE_ACTION := &"gameplay_walk_toggle"
const ALL_TEST_ACTIONS: Array[StringName] = [
	&"gameplay_move_left",
	&"gameplay_move_right",
	&"gameplay_move_up",
	&"gameplay_move_down",
	JUMP_ACTION,
	SNEAK_ACTION,
	SPRINT_ACTION,
	WALK_TOGGLE_ACTION,
]
const DIRECTION_CASES: Array[Dictionary] = [
	{
		"action": &"gameplay_move_up",
		"letter": KEY_W,
		"arrow": KEY_UP,
	},
	{
		"action": &"gameplay_move_down",
		"letter": KEY_S,
		"arrow": KEY_DOWN,
	},
	{
		"action": &"gameplay_move_left",
		"letter": KEY_A,
		"arrow": KEY_LEFT,
	},
	{
		"action": &"gameplay_move_right",
		"letter": KEY_D,
		"arrow": KEY_RIGHT,
	},
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_release_all_actions()
	_expect_resource_contract()
	await _test_walk_and_jog_modes(tree)
	await _test_all_double_tap_bindings(tree)
	await _test_echo_window_and_direction_changes(tree)
	await _test_sprint_sneak_and_camera_priority(tree)
	await _test_jump_profiles(tree)
	await _test_room_collisions_and_interaction_lock(tree)
	_release_all_actions()
	return failures


func _expect_resource_contract() -> void:
	var config := load(MOVEMENT_CONFIG_PATH) as MOVEMENT_CONFIG_SCRIPT
	_expect(config != null, "movement V0 resource loads")
	if config == null:
		return
	_expect(is_equal_approx(config.sneak_speed, 60.0), "sneak speed is 60 px/s")
	_expect(is_equal_approx(config.walk_speed, 100.0), "walk speed is 100 px/s")
	_expect(is_equal_approx(config.jog_speed, 220.0), "jog speed is 220 px/s")
	_expect(is_equal_approx(config.run_speed, 310.0), "run speed is 310 px/s")
	_expect(is_equal_approx(config.sprint_speed, 400.0), "sprint speed is 400 px/s")
	_expect(is_equal_approx(config.double_tap_window, 0.30), "double-tap window is 0.30 s")
	_expect(
		is_equal_approx(config.direction_change_grace, 0.12),
		"direction-change grace is 0.12 s",
	)
	_expect_jump_profile(config, HERO_SCRIPT.JumpState.STAND, 0.32, 0.0, 24.0)
	_expect_jump_profile(config, HERO_SCRIPT.JumpState.WALK, 0.28, 32.0, 20.0)
	_expect_jump_profile(config, HERO_SCRIPT.JumpState.JOG, 0.32, 48.0, 24.0)
	_expect_jump_profile(config, HERO_SCRIPT.JumpState.RUN, 0.40, 80.0, 30.0)
	_expect_jump_profile(config, HERO_SCRIPT.JumpState.SPRINT, 0.48, 112.0, 36.0)


func _test_walk_and_jog_modes(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.JOG,
		"plain direction starts normal running",
	)
	_expect(
		is_equal_approx(hero.velocity.length(), hero.movement_config.jog_speed),
		"normal running uses the configured jog speed",
	)
	_toggle_walk_mode(hero)
	await tree.physics_frame
	_expect(hero.is_walk_mode_active(), "Caps Lock enables persistent walking")
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.WALK,
		"Caps Lock changes held movement to walking",
	)
	_expect(
		is_equal_approx(hero.velocity.length(), hero.movement_config.walk_speed),
		"walking uses the configured walk speed",
	)
	Input.action_press(WALK_TOGGLE_ACTION)
	hero._input(_key_event(KEY_CAPSLOCK, true, true, true))
	Input.action_release(WALK_TOGGLE_ACTION)
	await tree.physics_frame
	_expect(hero.is_walk_mode_active(), "Caps Lock echo does not toggle walking")
	_toggle_walk_mode(hero)
	await tree.physics_frame
	_expect(not hero.is_walk_mode_active(), "second Caps Lock press restores running")
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _free_hero(tree, hero)


func _test_all_double_tap_bindings(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	for direction_case in DIRECTION_CASES:
		var action := direction_case["action"] as StringName
		var letter := direction_case["letter"] as Key
		var arrow := direction_case["arrow"] as Key
		await _expect_double_tap_binding(tree, hero, action, letter, true)
		await _expect_double_tap_binding(tree, hero, action, arrow, false)
	_tap_direction(hero, &"gameplay_move_up", KEY_W, true)
	_press_direction(hero, &"gameplay_move_up", KEY_UP, false)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN,
		"W followed by Up shares the same action-level double-tap window",
	)
	_release_direction(hero, &"gameplay_move_up", KEY_UP, false)
	await _free_hero(tree, hero)


func _expect_double_tap_binding(
		tree: SceneTree,
		hero: HERO_SCRIPT,
		action: StringName,
		key: Key,
		physical: bool,
) -> void:
	_toggle_walk_mode(hero)
	_double_press_direction(hero, action, key, physical)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN,
		"double press overrides walking and activates running for %s" % key,
	)
	_expect(
		is_equal_approx(hero.velocity.length(), hero.movement_config.run_speed),
		"running uses configured speed for %s" % key,
	)
	_release_direction(hero, action, key, physical)
	hero.set_movement_enabled(false)
	hero.set_movement_enabled(true)
	_toggle_walk_mode(hero)
	await tree.physics_frame


func _test_echo_window_and_direction_changes(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	_press_direction(hero, &"gameplay_move_up", KEY_W, true)
	hero._input(_key_event(KEY_W, true, true, true))
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.JOG,
		"keyboard echo does not count as a second tap",
	)
	_release_direction(hero, &"gameplay_move_up", KEY_W, true)
	hero.set_movement_enabled(false)
	hero.set_movement_enabled(true)
	_tap_direction(hero, &"gameplay_move_up", KEY_W, true)
	hero._advance_timers(hero.movement_config.double_tap_window + 0.01)
	_press_direction(hero, &"gameplay_move_up", KEY_W, true)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.JOG,
		"second tap outside the window stays at normal running",
	)
	_release_direction(hero, &"gameplay_move_up", KEY_W, true)
	hero.set_movement_enabled(false)
	hero.set_movement_enabled(true)
	_double_press_direction(hero, &"gameplay_move_up", KEY_W, true)
	await tree.physics_frame
	_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN,
		"running stays active for a diagonal direction change",
	)
	_expect(
		is_equal_approx(hero.velocity.length(), hero.movement_config.run_speed),
		"diagonal running is not faster than straight running",
	)
	_release_direction(hero, &"gameplay_move_up", KEY_W, true)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN
		and hero.velocity.x > 0.0
		and is_zero_approx(hero.velocity.y),
		"running transfers from the original direction to the held direction",
	)
	_press_direction(hero, &"gameplay_move_down", KEY_S, true)
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN
		and hero.velocity.y > 0.0,
		"direct direction changes preserve running",
	)
	_release_direction(hero, &"gameplay_move_down", KEY_S, true)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN,
		"running survives the first empty frame inside direction grace",
	)
	await _wait_physics_seconds(
		tree,
		hero.movement_config.direction_change_grace + 0.05,
	)
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.JOG,
		"releasing every direction ends running after direction grace",
	)
	await _free_hero(tree, hero)


func _test_sprint_sneak_and_camera_priority(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	var camera: CAMERA_CONTROLLER_SCRIPT = hero.get_node_or_null(
		"PlayerCamera"
	) as CAMERA_CONTROLLER_SCRIPT
	_expect(camera != null, "shared player camera uses its controller")
	if camera == null:
		await _free_hero(tree, hero)
		return
	var sneak_events: Array[bool] = []
	hero.sneak_state_changed.connect(
		func(active: bool) -> void:
			sneak_events.append(active)
	)
	_press_sprint(hero)
	await tree.physics_frame
	_expect(not hero.is_jumping(), "Shift alone is not a jump input")
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.JOG,
		"Shift alone does not change movement state",
	)
	_double_press_direction(hero, &"gameplay_move_up", KEY_W, true)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.SPRINT,
		"held Shift turns active running into sprinting",
	)
	_expect(
		is_equal_approx(hero.velocity.length(), hero.movement_config.sprint_speed),
		"sprinting uses the configured speed",
	)
	_release_sprint(hero)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.RUN,
		"releasing Shift falls back to persistent running",
	)
	_press_sprint(hero)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.SPRINT,
		"pressing Shift again resumes sprinting without another double tap",
	)
	Input.action_press(SNEAK_ACTION)
	hero._input(_key_event(KEY_CTRL, true, false, true, KEY_LOCATION_LEFT))
	_expect(
		camera.zoom == Vector2.ONE * 1.5,
		"Ctrl press applies 1.50 camera zoom in the input event",
	)
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.SNEAK,
		"Ctrl overrides active sprinting with sneak",
	)
	_expect(
		is_equal_approx(hero.velocity.length(), hero.movement_config.sneak_speed),
		"sneak uses configured speed",
	)
	_expect(camera.is_sneak_zoom_active(), "camera reports the temporary sneak profile")
	Input.action_release(SNEAK_ACTION)
	hero._input(_key_event(KEY_CTRL, false, false, true, KEY_LOCATION_LEFT))
	await tree.physics_frame
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.SPRINT,
		"releasing Ctrl restores held sprinting",
	)
	_expect(not camera.is_sneak_zoom_active(), "releasing Ctrl restores scene camera")
	_expect(sneak_events == [true, false], "hero emits each sneak transition exactly once")
	_release_direction(hero, &"gameplay_move_up", KEY_W, true)
	_release_sprint(hero)
	await _wait_physics_seconds(
		tree,
		hero.movement_config.direction_change_grace + 0.05,
	)
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.JOG,
		"full stop ends running and sprinting",
	)
	await _free_hero(tree, hero)


func _test_jump_profiles(tree: SceneTree) -> void:
	await _expect_standing_jump(tree)
	await _expect_walk_jump(tree)
	await _expect_jog_jump(tree)
	await _expect_run_jump(tree)
	await _expect_sprint_jump(tree)
	await _expect_sneak_jump(tree)
	await _expect_air_control(tree)


func _expect_standing_jump(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	var jump_visual := hero.get_node_or_null("Visual/JumpVisual") as Node2D
	var shadow := hero.get_node_or_null("Visual/Shadow") as Polygon2D
	var collision := hero.get_node_or_null("CollisionShape2D") as CollisionShape2D
	var shadow_position := shadow.position if shadow != null else Vector2.ZERO
	var collision_position := collision.position if collision != null else Vector2.ZERO
	var start_position := hero.global_position
	hero._input(_key_event(KEY_SPACE, true, false, false))
	_expect(
		hero.get_jump_state() == HERO_SCRIPT.JumpState.STAND,
		"Space from standstill starts a standing jump",
	)
	var result := await _complete_jump(tree, hero, true)
	_expect_jump_result(
		result,
		hero.global_position.distance_to(start_position),
		0.0,
		hero.movement_config.standing_jump_height,
		"standing jump",
	)
	_expect(shadow != null and shadow.position == shadow_position, "jump keeps shadow grounded")
	_expect(
		collision != null and collision.position == collision_position,
		"jump keeps the collision at its ground anchor",
	)
	_expect(
		jump_visual != null and jump_visual.position.is_zero_approx(),
		"standing jump returns its visual to the ground anchor",
	)
	hero._input(_key_event(KEY_SPACE, true, true, false))
	_expect(not hero.is_jumping(), "Space echo does not start another jump")
	await _free_hero(tree, hero)


func _expect_walk_jump(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	_toggle_walk_mode(hero)
	_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _expect_active_jump(
		tree,
		hero,
		HERO_SCRIPT.JumpState.WALK,
		hero.movement_config.walk_jump_distance,
		hero.movement_config.walk_jump_height,
		"walking jump",
	)
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _free_hero(tree, hero)


func _expect_jog_jump(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _expect_active_jump(
		tree,
		hero,
		HERO_SCRIPT.JumpState.JOG,
		hero.movement_config.jog_jump_distance,
		hero.movement_config.jog_jump_height,
		"normal running jump",
	)
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _free_hero(tree, hero)


func _expect_run_jump(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	_double_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _expect_active_jump(
		tree,
		hero,
		HERO_SCRIPT.JumpState.RUN,
		hero.movement_config.run_jump_distance,
		hero.movement_config.run_jump_height,
		"running jump",
	)
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _free_hero(tree, hero)


func _expect_sprint_jump(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	_press_sprint(hero)
	_double_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _expect_active_jump(
		tree,
		hero,
		HERO_SCRIPT.JumpState.SPRINT,
		hero.movement_config.sprint_jump_distance,
		hero.movement_config.sprint_jump_height,
		"sprint jump",
	)
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	_release_sprint(hero)
	await _free_hero(tree, hero)


func _expect_active_jump(
		tree: SceneTree,
		hero: HERO_SCRIPT,
		expected_state: int,
		expected_distance: float,
		expected_height: float,
		description: String,
) -> void:
	await tree.physics_frame
	var start_position := hero.global_position
	hero._input(_key_event(KEY_SPACE, true, false, false))
	_expect(hero.get_jump_state() == expected_state, "%s selects its profile" % description)
	var result := await _complete_jump(tree, hero, false)
	_expect_jump_result(
		result,
		hero.global_position.distance_to(start_position),
		expected_distance,
		expected_height,
		description,
	)


func _expect_sneak_jump(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	var camera: CAMERA_CONTROLLER_SCRIPT = hero.get_node("PlayerCamera")
	_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	Input.action_press(SNEAK_ACTION)
	hero._input(_key_event(KEY_CTRL, true, false, true, KEY_LOCATION_LEFT))
	await tree.physics_frame
	var start_position := hero.global_position
	hero._input(_key_event(KEY_SPACE, true, false, false))
	_expect(
		hero.get_jump_state() == HERO_SCRIPT.JumpState.STAND,
		"jumping while sneaking selects the standing jump",
	)
	_expect(not camera.is_sneak_zoom_active(), "sneak ends immediately at takeoff")
	var result := await _complete_jump(tree, hero, false)
	_expect_jump_result(
		result,
		hero.global_position.distance_to(start_position),
		0.0,
		hero.movement_config.standing_jump_height,
		"sneak standing jump",
	)
	_expect(
		hero.get_movement_state() == HERO_SCRIPT.MovementState.SNEAK,
		"held Ctrl restores sneak after landing",
	)
	_expect(camera.is_sneak_zoom_active(), "held Ctrl restores sneak camera after landing")
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	Input.action_release(SNEAK_ACTION)
	hero._input(_key_event(KEY_CTRL, false, false, true, KEY_LOCATION_LEFT))
	await _free_hero(tree, hero)


func _expect_air_control(tree: SceneTree) -> void:
	var hero := await _spawn_hero(tree)
	if hero == null:
		return
	_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await tree.physics_frame
	var start_position := hero.global_position
	hero._input(_key_event(KEY_SPACE, true, false, false))
	Input.action_press(&"gameplay_move_up")
	await _complete_jump(tree, hero, false)
	Input.action_release(&"gameplay_move_up")
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	var movement := hero.global_position - start_position
	_expect(movement.x > 0.0, "air control preserves the takeoff direction as primary")
	_expect(movement.y < 0.0, "air control permits a directional adjustment")
	_expect(absf(movement.x) > absf(movement.y), "air control remains a light adjustment")
	await _free_hero(tree, hero)


func _complete_jump(
		tree: SceneTree,
		hero: HERO_SCRIPT,
		test_second_press: bool,
) -> Dictionary:
	var jump_visual := hero.get_node_or_null("Visual/JumpVisual") as Node2D
	var peak_height := 0.0
	var frame_count := 0
	var maximum_frames := ceili(1.0 * Engine.physics_ticks_per_second)
	while hero.is_jumping() and frame_count < maximum_frames:
		await tree.physics_frame
		frame_count += 1
		if jump_visual != null:
			peak_height = maxf(peak_height, -jump_visual.position.y)
		if test_second_press and frame_count == 3:
			var elapsed_before_second_press: float = hero._jump_elapsed
			hero._input(_key_event(KEY_SPACE, true, false, false))
			_expect(
				is_equal_approx(hero._jump_elapsed, elapsed_before_second_press),
				"Space during a jump does not restart its elapsed time",
			)
	_expect(not hero.is_jumping(), "jump lands within one second")
	return {
		"frames": frame_count,
		"peak_height": peak_height,
	}


func _expect_jump_result(
		result: Dictionary,
		actual_distance: float,
		expected_distance: float,
		expected_height: float,
		description: String,
) -> void:
	_expect(
		absf(actual_distance - expected_distance) <= 2.0,
		"%s reaches its configured distance" % description,
	)
	_expect(
		absf(float(result["peak_height"]) - expected_height) <= 1.0,
		"%s reaches its configured visible height" % description,
	)
	_expect(
		int(result["frames"]) < Engine.physics_ticks_per_second,
		"%s does not restart" % description,
	)


func _test_room_collisions_and_interaction_lock(tree: SceneTree) -> void:
	var packed_scene := load(HERO_ROOM_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "hero room loads for movement collision regression")
	if packed_scene == null:
		return
	var room := packed_scene.instantiate() as Control
	_expect(room != null, "hero room instantiates for movement collision regression")
	if room == null:
		return
	tree.root.add_child(room)
	await tree.process_frame
	await tree.physics_frame
	var hero: HERO_SCRIPT = room.get_node_or_null("World/HeroCharacter") as HERO_SCRIPT
	_expect(hero != null, "hero room retains shared movement hero")
	if hero == null:
		room.queue_free()
		await tree.process_frame
		return
	var camera: CAMERA_CONTROLLER_SCRIPT = room.get_node_or_null(
		"World/HeroCharacter/PlayerCamera"
	) as CAMERA_CONTROLLER_SCRIPT
	_expect(camera != null, "hero room retains the shared camera controller")
	if camera != null:
		Input.action_press(SNEAK_ACTION)
		await tree.physics_frame
		_expect(
			camera.zoom == Vector2.ONE * 1.5,
			"small-interior zoom stays at 1.50 while sneaking",
		)
		Input.action_release(SNEAK_ACTION)
		await tree.physics_frame
		_expect(
			camera.zoom == Vector2.ONE * 1.5,
			"small-interior profile returns to 1.50 after sneaking",
		)
	hero.global_position = Vector2(31.0, 720.0)
	Input.action_press(SNEAK_ACTION)
	Input.action_press(&"gameplay_move_left")
	await _wait_physics_frames(tree, 4)
	_expect(hero.global_position.x >= 29.5, "left wall blocks sneak speed")
	Input.action_release(&"gameplay_move_left")
	Input.action_release(SNEAK_ACTION)
	hero.set_movement_enabled(false)
	hero.set_movement_enabled(true)
	hero.global_position = Vector2(2529.0, 720.0)
	_double_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _wait_physics_frames(tree, 4)
	_expect(hero.global_position.x <= 2530.5, "right wall blocks running speed")
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	hero.set_movement_enabled(false)
	hero.set_movement_enabled(true)
	hero.global_position = Vector2(2529.0, 720.0)
	_press_sprint(hero)
	_double_press_direction(hero, &"gameplay_move_right", KEY_D, true)
	await _wait_physics_frames(tree, 4)
	_expect(hero.global_position.x <= 2530.5, "right wall blocks sprint speed")
	_release_direction(hero, &"gameplay_move_right", KEY_D, true)
	_release_sprint(hero)
	hero.set_movement_enabled(false)
	hero.set_movement_enabled(true)
	hero.global_position = Vector2(2529.0, 720.0)
	hero._input(_key_event(KEY_SPACE, true, false, false))
	await _complete_jump(tree, hero, false)
	_expect(hero.global_position.x <= 2530.5, "massive wall remains stable during standing jump")
	hero.global_position = Vector2(1344.0, 720.0)
	await _wait_physics_frames(tree, 2)
	hero._input(_key_event(KEY_SPACE, true, false, false))
	_expect(not hero.try_interact(), "interaction is blocked while jumping")
	_expect(not room.is_guide_message_open(), "jump cannot open the guide message")
	await _complete_jump(tree, hero, false)
	_expect(hero.try_interact(), "guide interaction still works after landing")
	_expect(room.is_guide_message_open(), "guide message still opens after landing")
	var blocked_position := hero.global_position
	Input.action_press(&"gameplay_move_right")
	Input.action_press(SPRINT_ACTION)
	hero._input(_key_event(KEY_SPACE, true, false, false))
	await _wait_physics_frames(tree, 3)
	_expect(
		hero.global_position.is_equal_approx(blocked_position)
		and hero.velocity.is_zero_approx()
		and not hero.is_jumping(),
		"dialog movement lock overrides every held movement modifier",
	)
	Input.action_release(&"gameplay_move_right")
	Input.action_release(SPRINT_ACTION)
	room.queue_free()
	await tree.process_frame


func _spawn_hero(tree: SceneTree) -> HERO_SCRIPT:
	var packed_scene := load(HERO_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "shared hero scene loads")
	if packed_scene == null:
		return null
	var hero := packed_scene.instantiate() as HERO_SCRIPT
	_expect(hero != null, "shared hero scene instantiates")
	if hero == null:
		return null
	tree.root.add_child(hero)
	await tree.process_frame
	await tree.physics_frame
	return hero


func _free_hero(tree: SceneTree, hero: HERO_SCRIPT) -> void:
	_release_all_actions()
	hero.queue_free()
	await tree.process_frame


func _toggle_walk_mode(hero: HERO_SCRIPT) -> void:
	Input.action_press(WALK_TOGGLE_ACTION)
	hero._input(_key_event(KEY_CAPSLOCK, true, false, true))
	Input.action_release(WALK_TOGGLE_ACTION)
	hero._input(_key_event(KEY_CAPSLOCK, false, false, true))


func _press_sprint(hero: HERO_SCRIPT) -> void:
	Input.action_press(SPRINT_ACTION)
	hero._input(_key_event(KEY_SHIFT, true, false, true, KEY_LOCATION_LEFT))


func _release_sprint(hero: HERO_SCRIPT) -> void:
	Input.action_release(SPRINT_ACTION)
	hero._input(_key_event(KEY_SHIFT, false, false, true, KEY_LOCATION_LEFT))


func _double_press_direction(
		hero: HERO_SCRIPT,
		action: StringName,
		key: Key,
		physical: bool,
) -> void:
	_tap_direction(hero, action, key, physical)
	_press_direction(hero, action, key, physical)


func _tap_direction(
		hero: HERO_SCRIPT,
		action: StringName,
		key: Key,
		physical: bool,
) -> void:
	_press_direction(hero, action, key, physical)
	_release_direction(hero, action, key, physical)


func _press_direction(
		hero: HERO_SCRIPT,
		action: StringName,
		key: Key,
		physical: bool,
) -> void:
	Input.action_press(action)
	hero._input(_key_event(key, true, false, physical))


func _release_direction(
		hero: HERO_SCRIPT,
		action: StringName,
		key: Key,
		physical: bool,
) -> void:
	Input.action_release(action)
	hero._input(_key_event(key, false, false, physical))


func _key_event(
		key: Key,
		pressed: bool,
		echo: bool,
		physical: bool,
		location: KeyLocation = KEY_LOCATION_UNSPECIFIED,
) -> InputEventKey:
	var event := InputEventKey.new()
	event.device = InputEvent.DEVICE_ID_KEYBOARD
	event.pressed = pressed
	event.echo = echo
	event.location = location
	if physical:
		event.physical_keycode = key
	else:
		event.keycode = key
	return event


func _wait_physics_seconds(tree: SceneTree, duration: float) -> void:
	var frame_count := ceili(duration * Engine.physics_ticks_per_second) + 1
	await _wait_physics_frames(tree, frame_count)


func _wait_physics_frames(tree: SceneTree, frame_count: int) -> void:
	for _frame in range(frame_count):
		await tree.physics_frame


func _release_all_actions() -> void:
	for action in ALL_TEST_ACTIONS:
		Input.action_release(action)


func _expect_jump_profile(
		config: MOVEMENT_CONFIG_SCRIPT,
		jump_state: int,
		expected_duration: float,
		expected_distance: float,
		expected_height: float,
) -> void:
	var duration := config.standing_jump_duration
	var distance := 0.0
	var height := config.standing_jump_height
	match jump_state:
		HERO_SCRIPT.JumpState.WALK:
			duration = config.walk_jump_duration
			distance = config.walk_jump_distance
			height = config.walk_jump_height
		HERO_SCRIPT.JumpState.JOG:
			duration = config.jog_jump_duration
			distance = config.jog_jump_distance
			height = config.jog_jump_height
		HERO_SCRIPT.JumpState.RUN:
			duration = config.run_jump_duration
			distance = config.run_jump_distance
			height = config.run_jump_height
		HERO_SCRIPT.JumpState.SPRINT:
			duration = config.sprint_jump_duration
			distance = config.sprint_jump_distance
			height = config.sprint_jump_height
	_expect(is_equal_approx(duration, expected_duration), "jump duration matches V0")
	_expect(is_equal_approx(distance, expected_distance), "jump distance matches V0")
	_expect(is_equal_approx(height, expected_height), "jump height matches V0")


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("HeroMovementV0: %s" % description)
