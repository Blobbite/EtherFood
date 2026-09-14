extends RefCounted

const HERO_SCENE_PATH := "res://scenes/gameplay/hero/hero_character.tscn"
const HERO_SCRIPT := preload("res://scenes/gameplay/hero/hero_character.gd")
const EXPECTED_APPEARANCE_REFERENCE_HEIGHT := 80.0
const EXPECTED_TEXTURE_REFERENCE_HEIGHT := 1205.0
const EXPECTED_TEXTURE_SCALE := 80.0 / EXPECTED_TEXTURE_REFERENCE_HEIGHT
const MOVEMENT_ACTIONS: Array[StringName] = [
	&"gameplay_move_left",
	&"gameplay_move_right",
	&"gameplay_move_up",
	&"gameplay_move_down",
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_release_movement_actions()
	var hero_scene := load(HERO_SCENE_PATH) as PackedScene
	_expect(hero_scene != null, "HeroCharacter scene loads")
	if hero_scene == null:
		return failures

	var hero_node := hero_scene.instantiate()
	_expect(hero_node is CharacterBody2D, "HeroCharacter instantiates as CharacterBody2D")
	if not hero_node is CharacterBody2D:
		if hero_node != null:
			hero_node.free()
		return failures

	var hero: HERO_SCRIPT = hero_node as HERO_SCRIPT
	tree.root.add_child(hero)
	await tree.physics_frame

	_expect(
		hero.motion_mode == CharacterBody2D.MOTION_MODE_FLOATING,
		"HeroCharacter uses floating motion mode",
	)
	var collision_shape := hero.get_node_or_null("CollisionShape2D") as CollisionShape2D
	_expect(collision_shape != null, "HeroCharacter has a CollisionShape2D")
	if collision_shape != null:
		_expect(collision_shape.shape != null, "HeroCharacter collision has a shape")
	var interaction_detector := hero.get_node_or_null("InteractionDetector") as Area2D
	var interaction_shape := hero.get_node_or_null(
		"InteractionDetector/CollisionShape2D"
	) as CollisionShape2D
	_expect(interaction_detector != null, "HeroCharacter has an InteractionDetector")
	_expect(
		interaction_shape != null and interaction_shape.shape != null,
		"InteractionDetector has a detection shape",
	)
	if interaction_detector != null:
		_expect(
			interaction_detector.collision_layer == 0,
			"InteractionDetector adds no physical collision layer",
		)
		_expect(
			interaction_detector.collision_mask == 2,
			"InteractionDetector scans only interactable areas",
		)
	if interaction_shape != null:
		var interaction_circle := interaction_shape.shape as CircleShape2D
		_expect(
			interaction_circle != null
			and is_equal_approx(interaction_circle.radius, 96.0),
			"InteractionDetector reaches 96 world pixels",
		)
	var player_camera := hero.get_node_or_null("PlayerCamera") as Camera2D
	_expect(player_camera != null, "HeroCharacter has a PlayerCamera")
	if player_camera != null:
		_expect(player_camera.get_parent() == hero, "PlayerCamera is a direct child")
		_expect(not player_camera.enabled, "PlayerCamera is disabled by default")
		_expect(player_camera.zoom == Vector2.ONE, "PlayerCamera uses neutral zoom")
		_expect(
			player_camera.has_method(&"get_base_zoom")
			and is_equal_approx(float(player_camera.call(&"get_base_zoom")), 1.0),
			"PlayerCamera starts with the world profile",
		)
		_expect(
			not player_camera.position_smoothing_enabled,
			"PlayerCamera has position smoothing disabled",
		)
		_expect(
			player_camera.process_callback == Camera2D.CAMERA2D_PROCESS_PHYSICS,
			"PlayerCamera updates during physics frames",
		)
	var visual := hero.get_node_or_null("Visual") as Node2D
	var shadow := hero.get_node_or_null("Visual/Shadow") as Polygon2D
	var jump_visual := hero.get_node_or_null("Visual/JumpVisual") as Node2D
	var appearance := hero.get_node_or_null("Visual/JumpVisual/Appearance") as Node2D
	var texture_scale := hero.get_node_or_null(
		"Visual/JumpVisual/Appearance/TextureScale"
	) as Node2D
	var hero_sprite := hero.get_node_or_null(
		"Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	_expect(visual != null, "HeroCharacter has a Visual group")
	_expect(shadow != null, "HeroCharacter has a shadow")
	_expect(jump_visual != null, "HeroCharacter has a separate jump visual")
	_expect(appearance != null, "HeroCharacter has an Appearance group")
	_expect(texture_scale != null, "Appearance has a texture-normalization group")
	_expect(hero_sprite != null, "HeroCharacter has an animated HeroSprite")
	if visual != null and jump_visual != null and appearance != null:
		_expect(jump_visual.get_parent() == visual, "JumpVisual is directly under Visual")
		_expect(appearance.get_parent() == jump_visual, "Appearance belongs to JumpVisual")
		_expect(appearance.position == Vector2(0, 10), "Appearance origin is at the feet")
		_expect(appearance.scale == Vector2.ONE, "Appearance uses its reference scale")
	if appearance != null and texture_scale != null and hero_sprite != null:
		_expect(texture_scale.get_parent() == appearance, "TextureScale belongs to Appearance")
		_expect(hero_sprite.get_parent() == texture_scale, "HeroSprite belongs to TextureScale")
		_expect(appearance.get_child_count() == 1, "Appearance contains only TextureScale")
		_expect(texture_scale.get_child_count() == 1, "TextureScale contains only HeroSprite")
		_expect(hero_sprite.sprite_frames != null, "HeroSprite has SpriteFrames")
		_expect(hero_sprite.visible, "HeroSprite is visible")
		_expect(
			hero_sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
			"HeroSprite uses nearest-neighbor filtering",
		)
		_expect(hero_sprite.rotation == 0.0, "HeroSprite is not rotated")
		_expect(
			texture_scale.scale.is_equal_approx(Vector2.ONE * EXPECTED_TEXTURE_SCALE),
			"TextureScale normalizes the audited 1205-pixel reference pose",
		)
		_expect(hero_sprite.offset == Vector2(0, -597), "HeroSprite uses the audited foot anchor")
		_expect(
			is_equal_approx(
				EXPECTED_TEXTURE_REFERENCE_HEIGHT * texture_scale.global_scale.y,
				EXPECTED_APPEARANCE_REFERENCE_HEIGHT,
			),
			"unscaled reference pose is 80 world pixels high",
		)
		_expect(
			hero_sprite.global_position.is_equal_approx(appearance.global_position),
			"Appearance origin matches the visible foot position",
		)
		var reference_foot_position := appearance.global_position
		hero.set_appearance_height(80.0)
		_expect(
			appearance.scale.is_equal_approx(Vector2.ONE),
			"HeroCharacter applies a uniform appearance scale from the reference height",
		)
		_expect(
			is_equal_approx(hero.get_appearance_height(), 80.0),
			"HeroCharacter reports its scaled appearance height",
		)
		_expect(
			appearance.global_position.is_equal_approx(reference_foot_position),
			"scaling Appearance keeps its foot origin fixed",
		)
		hero.set_appearance_height(EXPECTED_APPEARANCE_REFERENCE_HEIGHT)
	var facing_marker := hero.get_node_or_null(
		"Visual/JumpVisual/FacingMarker"
	) as Polygon2D
	_expect(facing_marker != null, "HeroCharacter has a facing marker")
	if visual != null:
		_expect(shadow == null or shadow.get_parent() == visual, "Shadow stays grounded")
	if jump_visual != null:
		_expect(
			facing_marker == null or facing_marker.get_parent() == jump_visual,
			"Facing marker belongs to JumpVisual",
		)
	_expect(hero.movement_config != null, "HeroCharacter has a movement configuration")
	_expect(hero.get_current_speed() > 0.0, "HeroCharacter running speed is positive")
	_expect(hero.is_movement_enabled(), "HeroCharacter movement starts enabled")
	_expect(
		hero.get_nearest_interactable() == null,
		"HeroCharacter starts without a nearby interaction target",
	)
	_expect(hero.facing_direction == Vector2.DOWN, "HeroCharacter initially faces down")
	_expect(
		hero.get_animation_direction_name() == &"S",
		"HeroCharacter initially exposes the south animation direction",
	)
	_expect(hero.velocity.is_zero_approx(), "HeroCharacter remains still without input")

	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	_expect(hero.velocity.x > 0.0, "right input produces positive X velocity")
	_expect(is_zero_approx(hero.velocity.y), "right input has no vertical velocity")
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame
	_expect(hero.velocity.is_zero_approx(), "releasing right input stops movement")
	_expect(
		hero.facing_direction == Vector2.RIGHT,
		"facing direction remains right after releasing input",
	)
	if facing_marker != null:
		_expect(
			is_equal_approx(facing_marker.rotation, -PI / 2.0),
			"facing marker visibly remains pointed right",
		)

	Input.action_press(&"gameplay_move_left")
	await tree.physics_frame
	_expect(hero.velocity.x < 0.0, "left input produces negative X velocity")
	Input.action_release(&"gameplay_move_left")
	await tree.physics_frame

	Input.action_press(&"gameplay_move_up")
	await tree.physics_frame
	_expect(hero.velocity.y < 0.0, "up input produces negative Y velocity")
	Input.action_release(&"gameplay_move_up")
	await tree.physics_frame

	Input.action_press(&"gameplay_move_down")
	await tree.physics_frame
	_expect(hero.velocity.y > 0.0, "down input produces positive Y velocity")
	Input.action_release(&"gameplay_move_down")
	await tree.physics_frame

	Input.action_press(&"gameplay_move_right", 0.5)
	await tree.physics_frame
	_expect(hero.velocity.x > 0.0, "analog-strength input produces movement")
	_expect(
		hero.velocity.length() < hero.movement_config.jog_speed,
		"analog-strength input preserves partial movement speed",
	)
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame

	Input.action_press(&"gameplay_move_right")
	Input.action_press(&"gameplay_move_down")
	await tree.physics_frame
	_expect(
		hero.velocity.x > 0.0 and hero.velocity.y > 0.0,
		"diagonal input produces diagonal velocity",
	)
	_expect(
		hero.velocity.length() <= hero.movement_config.jog_speed + 0.001,
		"diagonal velocity does not exceed move speed",
	)
	Input.action_release(&"gameplay_move_right")
	Input.action_release(&"gameplay_move_down")
	await tree.physics_frame
	_expect(hero.velocity.is_zero_approx(), "releasing all actions clears velocity")
	_expect(
		hero.facing_direction == Vector2.DOWN,
		"four-direction facing remains after diagonal input is released",
	)
	if facing_marker != null:
		_expect(
			is_zero_approx(facing_marker.rotation),
			"facing marker visibly remains pointed down",
		)

	var position_before_disabled_input := hero.position
	hero.set_movement_enabled(false)
	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	_expect(hero.velocity.is_zero_approx(), "disabled movement clears hero velocity")
	_expect(
		hero.position.is_equal_approx(position_before_disabled_input),
		"disabled movement ignores held movement input",
	)
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame
	hero.set_movement_enabled(true)
	_expect(hero.is_movement_enabled(), "HeroCharacter movement can be re-enabled")
	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	_expect(
		hero.position.x > position_before_disabled_input.x,
		"re-enabled movement accepts input again",
	)
	Input.action_release(&"gameplay_move_right")
	await tree.physics_frame

	_release_movement_actions()
	hero.queue_free()
	await tree.process_frame
	return failures


func _release_movement_actions() -> void:
	for action in MOVEMENT_ACTIONS:
		Input.action_release(action)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("HeroCharacter: %s" % description)
