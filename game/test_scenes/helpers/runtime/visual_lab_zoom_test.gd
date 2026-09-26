extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://test_scenes/visual_lab/visual_lab.tscn"
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const WIDE_ZOOM := Vector2(0.75, 0.75)
const MEDIUM_ZOOM := Vector2.ONE
const NEAR_ZOOM := Vector2(1.5, 1.5)
const WIDE_STATUS := "Kamera: Außenwelt · Weit · 0,75×"
const MEDIUM_STATUS := "Kamera: Außenwelt · Mittel · 1,00×"
const NEAR_STATUS := "Kamera: Außenwelt · Nah · 1,50×"
const LIMITED_WIDE_STATUS := (
	"Kamera: Außenwelt · Weit · 1,25× · durch Weltgröße begrenzt"
)
const LIMITED_MEDIUM_STATUS := (
	"Kamera: Außenwelt · Mittel · 1,25× · durch Weltgröße begrenzt"
)
const WORLD_SIZE := Vector2(3840, 2160)

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

	var player_camera := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/PlayerCamera"
	) as Camera2D
	var camera_status := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/CameraStatus"
	) as Label
	var hero: HERO_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as HERO_SCRIPT
	var hero_collision := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/CollisionShape2D"
	) as CollisionShape2D

	_expect(player_camera != null, "VisualLab has PlayerCamera")
	_expect(camera_status != null, "VisualLab has a camera-status Label")
	_expect(hero != null, "VisualLab has HeroCharacter")
	_expect(
		hero_collision != null and hero_collision.shape != null,
		"VisualLab HeroCharacter has a collision shape",
	)

	var original_walk_speed := (
		hero.movement_config.walk_speed if hero != null else 0.0
	)
	var original_hero_scale := hero.scale if hero != null else Vector2.ZERO
	var original_collision_shape := hero_collision.shape if hero_collision != null else null
	var status_screen_position := (
		camera_status.get_screen_transform().origin if camera_status != null else Vector2.ZERO
	)
	if player_camera != null and camera_status != null:
		_expect_zoom_state(
			player_camera,
			camera_status,
			MEDIUM_ZOOM,
			MEDIUM_STATUS,
			"VisualLab starts at the Maßstab V0 zoom",
		)

		visual_lab._unhandled_input(_pressed_key(KEY_PLUS, true))
		_expect_zoom_state(
			player_camera,
			camera_status,
			MEDIUM_ZOOM,
			MEDIUM_STATUS,
			"removed plus shortcut leaves zoom unchanged",
		)

		visual_lab._change_camera_zoom(-1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			WIDE_ZOOM,
			WIDE_STATUS,
			"zoom decrement changes medium to wide",
		)
		if hero != null:
			await _expect_camera_limits(
				tree,
				hero,
				player_camera,
				visual_lab.size,
				"wide zoom",
			)
		visual_lab._change_camera_zoom(-1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			WIDE_ZOOM,
			WIDE_STATUS,
			"zoom-out stops at wide",
		)

		visual_lab._change_camera_zoom(1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			MEDIUM_ZOOM,
			MEDIUM_STATUS,
			"zoom increment changes wide to medium",
		)
		if hero != null:
			await _expect_camera_limits(
				tree,
				hero,
				player_camera,
				visual_lab.size,
				"medium zoom",
			)
		visual_lab._change_camera_zoom(1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			NEAR_ZOOM,
			NEAR_STATUS,
			"zoom increment changes medium to near",
		)
		if hero != null:
			await _expect_camera_limits(
				tree,
				hero,
				player_camera,
				visual_lab.size,
				"near zoom",
			)
		visual_lab._change_camera_zoom(1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			NEAR_ZOOM,
			NEAR_STATUS,
			"zoom-in stops at near",
		)

		visual_lab._change_camera_zoom(-1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			MEDIUM_ZOOM,
			MEDIUM_STATUS,
			"zoom decrement changes near to medium",
		)
		visual_lab._change_camera_zoom(-1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			WIDE_ZOOM,
			WIDE_STATUS,
			"zoom decrement changes medium to wide again",
		)
		visual_lab._change_camera_zoom(1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			MEDIUM_ZOOM,
			MEDIUM_STATUS,
			"zoom increment changes wide to medium again",
		)
		visual_lab._change_camera_zoom(1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			NEAR_ZOOM,
			NEAR_STATUS,
			"zoom increment changes medium to near again",
		)

		visual_lab._change_camera_zoom(-1)
		visual_lab._change_camera_zoom(-1)
		visual_lab.size = Vector2(4800, 2700)
		_expect_zoom_state(
			player_camera,
			camera_status,
			Vector2(1.25, 1.25),
			LIMITED_WIDE_STATUS,
			"world size limits wide zoom after viewport resize",
		)
		visual_lab._change_camera_zoom(1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			Vector2(1.25, 1.25),
			LIMITED_MEDIUM_STATUS,
			"limited zoom still displays the selected medium preset",
		)
		visual_lab._change_camera_zoom(1)
		_expect_zoom_state(
			player_camera,
			camera_status,
			NEAR_ZOOM,
			NEAR_STATUS,
			"near zoom exceeds the resized viewport minimum",
		)

		_expect(player_camera.limit_left == 0, "zoom keeps the left camera limit")
		_expect(player_camera.limit_top == 0, "zoom keeps the top camera limit")
		_expect(player_camera.limit_right == 3840, "zoom keeps the right camera limit")
		_expect(player_camera.limit_bottom == 2160, "zoom keeps the bottom camera limit")
		_expect(
			camera_status.get_screen_transform().origin.is_equal_approx(
				status_screen_position,
			),
			"camera status stays fixed while zoom and world position change",
		)

	if hero != null:
		_expect(
			hero.movement_config.walk_speed == original_walk_speed,
			"zoom does not change hero walk speed",
		)
		_expect(hero.scale == original_hero_scale, "zoom does not change hero scale")
	if hero_collision != null:
		_expect(
			hero_collision.shape == original_collision_shape,
			"zoom does not change the hero collision shape",
		)

	visual_lab.queue_free()
	await tree.process_frame

	var reopened_node := visual_lab_scene.instantiate()
	_expect(reopened_node is Control, "VisualLab can be reopened")
	if reopened_node is Control:
		var reopened_visual_lab := reopened_node as Control
		tree.root.add_child(reopened_visual_lab)
		await tree.process_frame
		var reopened_camera := reopened_visual_lab.get_node_or_null(
			"TestWorld/HeroCharacter/PlayerCamera"
		) as Camera2D
		var reopened_status := reopened_visual_lab.get_node_or_null(
			"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/CameraStatus"
		) as Label
		_expect(reopened_camera != null, "reopened VisualLab has PlayerCamera")
		_expect(reopened_status != null, "reopened VisualLab has camera status")
		if reopened_camera != null and reopened_status != null:
			_expect_zoom_state(
				reopened_camera,
				reopened_status,
				NEAR_ZOOM,
				NEAR_STATUS,
				"reopened VisualLab loads the saved near zoom",
			)
		reopened_visual_lab.queue_free()
		await tree.process_frame
	elif reopened_node != null:
		reopened_node.free()
	return failures


func _expect_removed_shortcuts() -> void:
	_expect(
		not InputMap.has_action(&"dev_camera_zoom_out"),
		"zoom-out direct action is absent",
	)
	_expect(
		not InputMap.has_action(&"dev_camera_zoom_in"),
		"zoom-in direct action is absent",
	)


func _pressed_key(keycode: Key, echo: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.keycode = keycode
	event.pressed = true
	event.echo = echo
	return event


func _expect_zoom_state(
		camera: Camera2D,
		status: Label,
		expected_zoom: Vector2,
		expected_status: String,
		description: String,
) -> void:
	_expect(camera.zoom.is_equal_approx(expected_zoom), "%s: camera zoom" % description)
	_expect(status.text == expected_status, "%s: status text" % description)


func _expect_camera_limits(
		tree: SceneTree,
		hero: HERO_SCRIPT,
		camera: Camera2D,
		viewport_size: Vector2,
		description: String,
) -> void:
	var visible_half_size := viewport_size / camera.zoom / 2.0
	hero.position = Vector2(30, 21)
	await tree.physics_frame
	camera.force_update_scroll()
	_expect(
		camera.get_screen_center_position().is_equal_approx(visible_half_size),
		"%s stops at top-left world limits" % description,
	)
	hero.position = Vector2(3810, 2133)
	await tree.physics_frame
	camera.force_update_scroll()
	_expect(
		camera.get_screen_center_position().is_equal_approx(WORLD_SIZE - visible_half_size),
		"%s stops at bottom-right world limits" % description,
	)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLabZoom: %s" % description)
