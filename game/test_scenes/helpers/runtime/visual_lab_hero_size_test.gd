extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://test_scenes/visual_lab/visual_lab.tscn"
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const REFERENCE_HEIGHT := 80.0
const TEXTURE_REFERENCE_HEIGHT := 1205.0
const SMALL_HEIGHT := 64.0
const MEDIUM_HEIGHT := 80.0
const LARGE_HEIGHT := 96.0
const SMALL_STATUS := "Figur: Klein · 64 Weltpixel"
const MEDIUM_STATUS := "Figur: Mittel · 80 Weltpixel"
const LARGE_STATUS := "Figur: Groß · 96 Weltpixel"

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_expect_removed_shortcuts()
	var visual_lab_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(visual_lab_scene != null, "VisualLab scene loads")
	if visual_lab_scene == null:
		return failures

	var visual_lab_node := visual_lab_scene.instantiate()
	_expect(visual_lab_node is Control, "VisualLab instantiates as Control")
	if not visual_lab_node is Control:
		if visual_lab_node != null:
			visual_lab_node.free()
		return failures

	var visual_lab := visual_lab_node as Control
	tree.root.add_child(visual_lab)
	await tree.process_frame

	var hero: HERO_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as HERO_SCRIPT
	var visual := visual_lab.get_node_or_null("TestWorld/HeroCharacter/Visual") as Node2D
	var shadow := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/Shadow"
	) as Polygon2D
	var jump_visual := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual"
	) as Node2D
	var appearance := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance"
	) as Node2D
	var texture_scale := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale"
	) as Node2D
	var hero_sprite := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	var facing_marker := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/FacingMarker"
	) as Polygon2D
	var hero_collision := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/CollisionShape2D"
	) as CollisionShape2D
	var player_camera := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/PlayerCamera"
	) as Camera2D
	var size_status := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/ScalePage/Content/HeroSizeStatus"
	) as Label

	_expect(hero != null, "VisualLab has HeroCharacter")
	_expect(visual != null, "HeroCharacter has Visual")
	_expect(shadow != null, "HeroCharacter has Shadow")
	_expect(jump_visual != null, "HeroCharacter has JumpVisual")
	_expect(appearance != null, "HeroCharacter has Appearance")
	_expect(texture_scale != null, "Appearance has TextureScale")
	_expect(hero_sprite != null, "Appearance has HeroSprite")
	_expect(facing_marker != null, "HeroCharacter has FacingMarker")
	_expect(
		hero_collision != null and hero_collision.shape != null,
		"HeroCharacter has a collision shape",
	)
	_expect(player_camera != null, "HeroCharacter has PlayerCamera")
	_expect(size_status != null, "VisualLab has a hero-size Label")

	if (
		hero == null
		or visual == null
		or shadow == null
		or jump_visual == null
		or appearance == null
		or texture_scale == null
		or hero_sprite == null
		or facing_marker == null
		or hero_collision == null
		or hero_collision.shape == null
		or player_camera == null
		or size_status == null
	):
		visual_lab.queue_free()
		await tree.process_frame
		return failures

	_expect(jump_visual.get_parent() == visual, "JumpVisual is directly under Visual")
	_expect(appearance.get_parent() == jump_visual, "Appearance is under JumpVisual")
	_expect(texture_scale.get_parent() == appearance, "TextureScale is under Appearance")
	_expect(hero_sprite.get_parent() == texture_scale, "HeroSprite is under TextureScale")
	_expect(hero_sprite.sprite_frames != null, "HeroSprite animation resource is available")
	_expect(
		hero_sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
		"HeroSprite uses nearest-neighbor filtering",
	)
	_expect(shadow.get_parent() == visual, "Shadow stays outside Appearance")
	_expect(facing_marker.get_parent() == jump_visual, "FacingMarker follows JumpVisual")
	_expect(hero_collision.get_parent() == hero, "collision stays outside Appearance")
	_expect(player_camera.get_parent() == hero, "camera stays outside Appearance")

	var original_hero_position := hero.position
	var original_hero_scale := hero.scale
	var original_walk_speed := hero.movement_config.walk_speed
	var original_facing_direction := hero.facing_direction
	var original_collision_shape := hero_collision.shape
	var original_collision_transform := hero_collision.transform
	var original_shadow_transform := shadow.transform
	var original_facing_marker_transform := facing_marker.transform
	var original_camera_position := player_camera.position
	var original_camera_zoom := player_camera.zoom
	var original_foot_position := appearance.global_position

	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		MEDIUM_HEIGHT,
		MEDIUM_STATUS,
		"VisualLab starts at the medium hero-size default",
	)

	visual_lab._unhandled_input(_pressed_key(KEY_F, true))
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		MEDIUM_HEIGHT,
		MEDIUM_STATUS,
		"removed F shortcut leaves hero size unchanged",
	)

	visual_lab._change_hero_size(-1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		SMALL_HEIGHT,
		SMALL_STATUS,
		"size decrement changes medium hero to small",
	)
	visual_lab._change_hero_size(-1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		SMALL_HEIGHT,
		SMALL_STATUS,
		"size decrease stops at small",
	)

	visual_lab._change_hero_size(1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		MEDIUM_HEIGHT,
		MEDIUM_STATUS,
		"size increment changes small hero to medium",
	)
	visual_lab._change_hero_size(1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		LARGE_HEIGHT,
		LARGE_STATUS,
		"size increment changes medium hero to large",
	)
	visual_lab._change_hero_size(1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		LARGE_HEIGHT,
		LARGE_STATUS,
		"size increase stops at large",
	)

	visual_lab._change_hero_size(-1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		MEDIUM_HEIGHT,
		MEDIUM_STATUS,
		"size decrement changes large hero to medium",
	)
	visual_lab._change_hero_size(-1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		SMALL_HEIGHT,
		SMALL_STATUS,
		"size decrement changes medium hero to small again",
	)
	visual_lab._change_hero_size(1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		MEDIUM_HEIGHT,
		MEDIUM_STATUS,
		"size increment changes small hero to medium again",
	)
	visual_lab._change_hero_size(1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		LARGE_HEIGHT,
		LARGE_STATUS,
		"size increment changes medium hero to large again",
	)

	for _iteration in range(24):
		visual_lab._change_hero_size(-1)
		visual_lab._change_hero_size(1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		LARGE_HEIGHT,
		LARGE_STATUS,
		"repeated switching does not accumulate scale error",
	)

	visual_lab._change_hero_size(-1)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		MEDIUM_HEIGHT,
		MEDIUM_STATUS,
		"size decrement returns hero to medium",
	)
	_expect(
		player_camera.zoom.is_equal_approx(original_camera_zoom),
		"hero-size changes keep camera zoom unchanged",
	)

	visual_lab._change_camera_zoom(-1)
	_expect(player_camera.zoom == Vector2(0.75, 0.75), "zoom can change independently")
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		MEDIUM_HEIGHT,
		MEDIUM_STATUS,
		"zoom changes keep hero size unchanged",
	)
	visual_lab._change_hero_size(1)
	_expect(
		player_camera.zoom == Vector2(0.75, 0.75),
		"size can change without camera zoom",
	)
	_expect_size_state(
		appearance,
		hero_sprite,
		size_status,
		LARGE_HEIGHT,
		LARGE_STATUS,
		"hero size remains independent at medium zoom",
	)
	visual_lab._change_camera_zoom(1)
	_expect(
		player_camera.zoom.is_equal_approx(original_camera_zoom),
		"zoom returns independently to the standard profile",
	)
	visual_lab._change_hero_size(-1)

	_expect(hero.position == original_hero_position, "size keeps hero position unchanged")
	_expect(hero.scale == original_hero_scale, "size never scales HeroCharacter")
	_expect(
		hero.movement_config.walk_speed == original_walk_speed,
		"size keeps walk speed unchanged",
	)
	_expect(
		hero.facing_direction == original_facing_direction,
		"size keeps facing direction unchanged",
	)
	_expect(
		hero_collision.shape == original_collision_shape,
		"size keeps the collision shape unchanged",
	)
	_expect(
		hero_collision.transform == original_collision_transform,
		"size keeps the collision transform unchanged",
	)
	_expect(shadow.transform == original_shadow_transform, "size keeps shadow unchanged")
	_expect(
		facing_marker.transform == original_facing_marker_transform,
		"size keeps facing marker unchanged",
	)
	_expect(
		player_camera.position == original_camera_position,
		"size keeps camera position unchanged",
	)
	_expect(
		appearance.global_position.is_equal_approx(original_foot_position),
		"all size changes keep the foot position fixed",
	)

	visual_lab.queue_free()
	await tree.process_frame
	await _expect_reopened_medium_size(tree, visual_lab_scene)
	return failures


func _expect_reopened_medium_size(tree: SceneTree, visual_lab_scene: PackedScene) -> void:
	var reopened_node := visual_lab_scene.instantiate()
	_expect(reopened_node is Control, "VisualLab can be reopened")
	if not reopened_node is Control:
		if reopened_node != null:
			reopened_node.free()
		return
	var reopened_visual_lab := reopened_node as Control
	tree.root.add_child(reopened_visual_lab)
	await tree.process_frame
	var reopened_appearance := reopened_visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance"
	) as Node2D
	var reopened_sprite := reopened_visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	var reopened_status := reopened_visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/ScalePage/Content/HeroSizeStatus"
	) as Label
	_expect(reopened_appearance != null, "reopened VisualLab has Appearance")
	_expect(reopened_sprite != null, "reopened VisualLab has HeroSprite")
	_expect(reopened_status != null, "reopened VisualLab has hero-size status")
	if (
		reopened_appearance != null
		and reopened_sprite != null
		and reopened_status != null
	):
		_expect_size_state(
			reopened_appearance,
			reopened_sprite,
			reopened_status,
			MEDIUM_HEIGHT,
			MEDIUM_STATUS,
			"reopened VisualLab loads the saved medium hero size",
		)
	reopened_visual_lab.queue_free()
	await tree.process_frame


func _expect_removed_shortcuts() -> void:
	_expect(
		not InputMap.has_action(&"dev_hero_size_decrease"),
		"hero-size decrease action is absent",
	)
	_expect(
		not InputMap.has_action(&"dev_hero_size_increase"),
		"hero-size increase action is absent",
	)


func _pressed_key(keycode: Key, echo: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.physical_keycode = keycode
	event.pressed = true
	event.echo = echo
	return event


func _expect_size_state(
	appearance: Node2D,
	sprite: AnimatedSprite2D,
	status: Label,
	expected_height: float,
	expected_status: String,
	description: String,
) -> void:
	var expected_scale := Vector2.ONE * (expected_height / REFERENCE_HEIGHT)
	_expect(
		appearance.scale.is_equal_approx(expected_scale),
		"%s: uniform Appearance scale" % description,
	)
	_expect(
		is_equal_approx(_measure_height(sprite), expected_height),
		"%s: measured sprite-to-foot height" % description,
	)
	_expect(
		is_equal_approx(_measure_bottom(sprite), appearance.global_position.y),
		"%s: visible foot stays at the scale origin" % description,
	)
	_expect(status.text == expected_status, "%s: status text" % description)


func _measure_height(sprite: AnimatedSprite2D) -> float:
	var texture_scale := sprite.get_parent() as Node2D
	if texture_scale == null:
		return 0.0
	return TEXTURE_REFERENCE_HEIGHT * absf(texture_scale.global_scale.y)


func _measure_bottom(sprite: AnimatedSprite2D) -> float:
	return sprite.global_position.y


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLabHeroSize: %s" % description)
