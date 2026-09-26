extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://test_scenes/visual_lab/visual_lab.tscn"
const HERO_ROOM_SCENE_PATH := "res://test_scenes/environment/hero_room.tscn"
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const WORLD_STATE_PREVIEW_SCRIPT := preload("res://test_scenes/visual_lab/world_state_preview.gd")
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_TEST_PATH := "user://visual_lab_texture_filter_test.cfg"
const CONTROLS_ACTION := &"dev_controls_toggle"
const DIAGNOSTICS_ACTION := &"dev_diagnostics_toggle"
const MINIMUM_TEXTURE_TARGET_COUNT := 51

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null


func run(tree: SceneTree) -> PackedStringArray:
	_remember_and_set_test_path()
	_remove_test_settings()
	_expect_removed_shortcut()

	var visual_lab_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	var hero_room_scene := load(HERO_ROOM_SCENE_PATH) as PackedScene
	_expect(visual_lab_scene != null, "VisualLab scene loads")
	_expect(hero_room_scene != null, "HeroRoom scene loads for isolation")
	if visual_lab_scene == null or hero_room_scene == null:
		_cleanup_test_path()
		return failures

	var hero_room := hero_room_scene.instantiate()
	var hero_room_sprite := hero_room.get_node_or_null(
		"World/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	_expect(hero_room_sprite != null, "HeroRoom retains its own hero sprite")
	_expect(
		hero_room_sprite != null
		and hero_room_sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
		"HeroRoom starts with its explicit nearest filter",
	)
	if hero_room_sprite == null:
		hero_room.free()
		_cleanup_test_path()
		return failures

	var visual_lab := await _open_visual_lab(tree, visual_lab_scene)
	if visual_lab == null:
		hero_room.free()
		_cleanup_test_path()
		return failures
	var texture_sprites := _texture_sprites(visual_lab)
	var original_filters: Array[int] = []
	for sprite in texture_sprites:
		original_filters.append(sprite.texture_filter)
	await _expect_texture_filter_contract(
		tree,
		visual_lab,
		texture_sprites,
		hero_room_sprite,
	)

	tree.root.remove_child(visual_lab)
	await tree.process_frame
	for sprite_index in range(texture_sprites.size()):
		_expect(
			texture_sprites[sprite_index].texture_filter == original_filters[sprite_index],
			"leaving VisualLab restores texture filter %d" % sprite_index,
		)
	visual_lab.free()
	_expect(
		hero_room_sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
		"leaving VisualLab does not alter the HeroRoom filter",
	)

	var reopened_visual_lab := await _open_visual_lab(tree, visual_lab_scene)
	if reopened_visual_lab != null:
		_expect_texture_filter_state(
			reopened_visual_lab,
			CanvasItem.TEXTURE_FILTER_LINEAR,
			"Texturfilter: Weich",
			"reopened VisualLab restores the saved soft filter",
		)
		await _close_visual_lab(tree, reopened_visual_lab)

	_write_settings_fixture(null, false)
	var legacy_visual_lab := await _open_visual_lab(tree, visual_lab_scene)
	if legacy_visual_lab != null:
		_expect_texture_filter_state(
			legacy_visual_lab,
			CanvasItem.TEXTURE_FILTER_NEAREST,
			"Texturfilter: Nearest-Neighbor",
			"version 1 preset without texture filter uses nearest",
		)
		await _close_visual_lab(tree, legacy_visual_lab)

	_write_settings_fixture("invalid", true)
	var invalid_visual_lab := await _open_visual_lab(tree, visual_lab_scene)
	if invalid_visual_lab != null:
		_expect_texture_filter_state(
			invalid_visual_lab,
			CanvasItem.TEXTURE_FILTER_NEAREST,
			"Texturfilter: Nearest-Neighbor",
			"invalid texture-filter ID uses nearest",
		)
		await _close_visual_lab(tree, invalid_visual_lab)

	hero_room.free()
	_cleanup_test_path()
	return failures


func _expect_texture_filter_contract(
	tree: SceneTree,
	visual_lab: Control,
	texture_sprites: Array[CanvasItem],
	hero_room_sprite: AnimatedSprite2D,
) -> void:
	var hero: HERO_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as HERO_SCRIPT
	var camera := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/PlayerCamera"
	) as Camera2D
	var test_world := visual_lab.get_node_or_null("TestWorld") as Node2D
	var tile_grid := visual_lab.get_node_or_null(
		"TestWorld/TileComparison/TileGridPreview"
	) as Node2D
	var world_state: WORLD_STATE_PREVIEW_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/WorldStatePreview"
	) as WORLD_STATE_PREVIEW_SCRIPT
	var hero_collision := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/CollisionShape2D"
	) as CollisionShape2D
	var obstacle_collision := visual_lab.get_node_or_null(
		"TestWorld/TestObstacle/CollisionShape2D"
	) as CollisionShape2D
	var controls := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface"
	) as MarginContainer
	var button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/TextureFilterOptions/SoftButton"
	) as Button
	var nearest_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/"
		+ "TextureFilterOptions/NearestButton"
	) as Button
	var rendering_tab := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/ThemeTabs/RenderingTab"
	) as Button
	var diagnostics := visual_lab.get_node_or_null(
		"InterfaceLayer/DiagnosticsPanel/Values"
	) as Label

	_expect(hero != null, "VisualLab retains the moving hero")
	_expect(camera != null, "VisualLab retains the following camera")
	_expect(test_world != null, "VisualLab retains the test world")
	_expect(tile_grid != null, "VisualLab retains the tile grid")
	_expect(world_state != null, "VisualLab retains both world states")
	_expect(hero_collision != null, "VisualLab retains the hero collision")
	_expect(obstacle_collision != null, "VisualLab retains the obstacle collision")
	_expect(controls != null, "VisualLab retains the controls menu")
	_expect(button != null, "controls menu has a texture-filter button")
	_expect(button != null and button.toggle_mode, "filter button exposes two states")
	_expect(nearest_button != null, "controls menu has a nearest-filter button")
	_expect(rendering_tab != null, "controls menu has a rendering tab")
	_expect(diagnostics != null, "VisualLab retains diagnostics values")
	_expect(
		texture_sprites.size() >= MINIMUM_TEXTURE_TARGET_COUNT,
		"filter comparison includes the original references and active room textures",
	)
	if (
		hero == null
		or camera == null
		or test_world == null
		or tile_grid == null
		or world_state == null
		or hero_collision == null
		or obstacle_collision == null
		or controls == null
		or button == null
		or nearest_button == null
		or rendering_tab == null
		or diagnostics == null
	):
		return

	var original_walk_speed := hero.movement_config.walk_speed
	var original_world_transform := test_world.global_transform
	var original_tile_size: Variant = tile_grid.get("tile_size")
	var original_hero_shape := hero_collision.shape
	var original_obstacle_shape := obstacle_collision.shape
	var initial_pixel_snap := visual_lab.get_viewport().snap_2d_transforms_to_pixel

	_expect_named_texture_targets(visual_lab)
	_expect_texture_filter_state(
		visual_lab,
		CanvasItem.TEXTURE_FILTER_NEAREST,
		"Texturfilter: Nearest-Neighbor",
		"VisualLab starts with nearest-neighbor",
	)
	visual_lab._unhandled_input(_pressed_action(CONTROLS_ACTION))
	_expect(controls.visible, "F5 opens the menu containing the filter control")
	rendering_tab.pressed.emit()
	await tree.process_frame
	_expect(button.is_visible_in_tree(), "filter button is visible on its theme page")
	visual_lab._unhandled_input(_pressed_action(DIAGNOSTICS_ACTION))
	_expect(
		diagnostics.text.contains("Texturfilter: Nearest-Neighbor"),
		"diagnostics immediately show nearest-neighbor",
	)

	var zoom_before_toggle := camera.zoom
	visual_lab._unhandled_input(_pressed_key(KEY_N, true))
	_expect_texture_filter_state(
		visual_lab,
		CanvasItem.TEXTURE_FILTER_NEAREST,
		"Texturfilter: Nearest-Neighbor",
		"held N does not toggle repeatedly",
	)
	visual_lab._unhandled_input(_pressed_key(KEY_N))
	_expect_texture_filter_state(
		visual_lab,
		CanvasItem.TEXTURE_FILTER_NEAREST,
		"Texturfilter: Nearest-Neighbor",
		"removed N shortcut leaves filtering unchanged",
	)
	button.pressed.emit()
	_expect_texture_filter_state(
		visual_lab,
		CanvasItem.TEXTURE_FILTER_LINEAR,
		"Texturfilter: Weich",
		"menu enables soft filtering while running",
	)
	_expect(camera.zoom == zoom_before_toggle, "filter toggle does not change camera zoom")
	_expect(
		visual_lab.get_viewport().snap_2d_transforms_to_pixel == initial_pixel_snap,
		"filter toggle does not change pixel snap",
	)
	_expect(
		hero_room_sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
		"soft VisualLab filter does not leak into HeroRoom",
	)
	_expect(
		diagnostics.text.contains("Texturfilter: Weich"),
		"diagnostics immediately show soft filtering",
	)
	_expect_saved_texture_filter("soft")

	nearest_button.pressed.emit()
	_expect_texture_filter_state(
		visual_lab,
		CanvasItem.TEXTURE_FILTER_NEAREST,
		"Texturfilter: Nearest-Neighbor",
		"menu button selects nearest-neighbor",
	)
	_expect_saved_texture_filter("nearest")
	await _expect_motion_contract(
		tree,
		visual_lab,
		hero,
		camera,
		false,
		"nearest-neighbor",
	)

	button.pressed.emit()
	_expect_texture_filter_state(
		visual_lab,
		CanvasItem.TEXTURE_FILTER_LINEAR,
		"Texturfilter: Weich",
		"menu button selects soft filtering",
	)
	_expect_saved_texture_filter("soft")
	await _expect_motion_contract(
		tree,
		visual_lab,
		hero,
		camera,
		true,
		"soft filtering",
	)
	_expect_zoom_filter_matrix(visual_lab, camera)
	_expect_world_state_matrix(visual_lab, world_state)

	_expect(
		hero.movement_config.walk_speed == original_walk_speed,
		"filter keeps hero walk speed",
	)
	_expect(
		test_world.global_transform.is_equal_approx(original_world_transform),
		"filter keeps the world transform",
	)
	_expect(tile_grid.get("tile_size") == original_tile_size, "filter keeps tile size")
	_expect(hero_collision.shape == original_hero_shape, "filter keeps hero collision")
	_expect(
		obstacle_collision.shape == original_obstacle_shape,
		"filter keeps obstacle collision",
	)
	_expect(camera.limit_left == 0, "filter keeps left camera limit")
	_expect(camera.limit_top == 0, "filter keeps top camera limit")
	_expect(camera.limit_right == 3840, "filter keeps right camera limit")
	_expect(camera.limit_bottom == 2160, "filter keeps bottom camera limit")
	_expect_saved_texture_filter("soft")


func _expect_zoom_filter_matrix(
	visual_lab: Control,
	camera: Camera2D,
) -> void:
	visual_lab._change_camera_zoom(1)
	var expected_zooms: Array[float] = [1.5, 1.0, 0.75]
	for zoom_index in range(expected_zooms.size()):
		_expect(
			is_equal_approx(camera.zoom.x, expected_zooms[zoom_index]),
			"zoom level %d is active" % (zoom_index + 1),
		)
		_expect_all_texture_filters(
			visual_lab,
			CanvasItem.TEXTURE_FILTER_LINEAR,
			"soft filter at zoom level %d" % (zoom_index + 1),
		)
		visual_lab._toggle_texture_filter()
		_expect_all_texture_filters(
			visual_lab,
			CanvasItem.TEXTURE_FILTER_NEAREST,
			"nearest filter at zoom level %d" % (zoom_index + 1),
		)
		visual_lab._toggle_texture_filter()
		if zoom_index < expected_zooms.size() - 1:
			visual_lab._change_camera_zoom(-1)


func _expect_world_state_matrix(
	visual_lab: Control,
	world_state: WORLD_STATE_PREVIEW_SCRIPT,
) -> void:
	var damaged_state := world_state.get_node_or_null("DamagedState") as Node2D
	var restored_state := world_state.get_node_or_null("RestoredState") as Node2D
	_expect(damaged_state != null and damaged_state.visible, "damaged state is testable")
	_expect(
		restored_state != null and not restored_state.visible,
		"restored state starts hidden",
	)
	if damaged_state != null:
		_expect_subtree_filter(
			damaged_state,
			CanvasItem.TEXTURE_FILTER_LINEAR,
			"damaged world",
		)
	visual_lab._toggle_world_state()
	_expect(world_state.is_restored(), "restored state can be selected with soft filter")
	_expect(damaged_state != null and not damaged_state.visible, "damaged state becomes hidden")
	_expect(restored_state != null and restored_state.visible, "restored state becomes visible")
	if restored_state != null:
		_expect_subtree_filter(
			restored_state,
			CanvasItem.TEXTURE_FILTER_LINEAR,
			"restored world",
		)


func _expect_motion_contract(
	tree: SceneTree,
	visual_lab: Control,
	hero: HERO_SCRIPT,
	camera: Camera2D,
	expected_soft: bool,
	description: String,
) -> void:
	hero.position = Vector2(1800.25, 1000.5)
	await tree.physics_frame
	visual_lab._update_pixel_snap_render_alignment()
	camera.force_update_scroll()
	var hero_start := hero.global_position
	var camera_start := camera.global_position

	var movement_per_frame := hero.get_current_speed() / Engine.physics_ticks_per_second
	var movement_frame_count := maxi(
		4,
		ceili(visual_lab._pixel_snap_world_grid_step().x / movement_per_frame) + 2,
	)
	await _hold_action_for_physics_frames(
		tree,
		&"gameplay_move_right",
		movement_frame_count,
	)
	await tree.process_frame
	visual_lab._update_pixel_snap_render_alignment()
	camera.force_update_scroll()
	var hero_movement := hero.global_position - hero_start
	var camera_movement := camera.global_position - camera_start
	var grid_step: Vector2 = visual_lab._pixel_snap_world_grid_step()
	_expect(hero_movement.x > 0.0, "%s: hero movement works" % description)
	_expect(
		camera_movement.x > 0.0,
		"%s: aligned camera follows the hero" % description,
	)
	_expect(
		absf(camera.global_position.x - hero.global_position.x)
		<= grid_step.x / 2.0 + 0.01,
		"%s: aligned camera stays within half an output-pixel grid step" % description,
	)
	_expect(camera.enabled and camera.is_current(), "%s: camera remains active" % description)
	var expected_filter := CanvasItem.TEXTURE_FILTER_LINEAR
	if not expected_soft:
		expected_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_expect_all_texture_filters(hero.get_parent().get_parent(), expected_filter, description)

	hero.position = Vector2(2268.25, 1080.5)
	await _hold_action_for_physics_frames(tree, &"gameplay_move_right", 4)
	_expect(hero.position.x <= 2271.5, "%s: obstacle collision works" % description)


func _expect_texture_filter_state(
	visual_lab: Control,
	expected_filter: CanvasItem.TextureFilter,
	_expected_text: String,
	description: String,
) -> void:
	var soft_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/"
		+ "TextureFilterOptions/SoftButton"
	) as Button
	var nearest_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/"
		+ "TextureFilterOptions/NearestButton"
	) as Button
	var expected_soft := expected_filter == CanvasItem.TEXTURE_FILTER_LINEAR
	_expect(
		soft_button != null and nearest_button != null,
		"%s: filter buttons exist" % description,
	)
	_expect(
		soft_button != null and soft_button.button_pressed == expected_soft,
		"%s: soft-option state" % description,
	)
	_expect(
		nearest_button != null and nearest_button.button_pressed != expected_soft,
		"%s: nearest-option state" % description,
	)
	_expect_all_texture_filters(visual_lab, expected_filter, description)


func _expect_all_texture_filters(
	visual_lab: Node,
	expected_filter: CanvasItem.TextureFilter,
	description: String,
) -> void:
	var sprites := _texture_sprites(visual_lab)
	_expect(not sprites.is_empty(), "%s: textured sprites exist" % description)
	for sprite in sprites:
		_expect(
			sprite.texture_filter == expected_filter,
			"%s: %s uses expected filter" % [description, sprite.name],
		)


func _expect_subtree_filter(
	root: Node,
	expected_filter: CanvasItem.TextureFilter,
	description: String,
) -> void:
	var sprites := _texture_sprites(root)
	_expect(not sprites.is_empty(), "%s has textured sprites" % description)
	for sprite in sprites:
		_expect(
			sprite.texture_filter == expected_filter,
			"%s sprite %s uses expected filter" % [description, sprite.name],
		)


func _expect_named_texture_targets(visual_lab: Control) -> void:
	var target_paths: Array[String] = [
		(
			"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/"
			+ "TextureScale/HeroSprite"
		),
		"TestWorld/ScaleComparison/GroundStrip",
		"TestWorld/ScaleComparison/SmallEnemyReference/Sprite2D",
		"TestWorld/ScaleComparison/DoorReference/Sprite2D",
		"TestWorld/ScaleComparison/HouseWallReference/Sprite2D",
		"TestWorld/ScaleComparison/LargeEnemyReference/Sprite2D",
		"TestWorld/ScaleComparison/TreeReference/Sprite2D",
		"TestWorld/WorldStatePreview/DamagedState/Ground",
		"TestWorld/WorldStatePreview/RestoredState/Ground",
		"TestWorld/WorldStatePreview/DamagedState/RuinedSawmill/Sprite2D",
		"TestWorld/WorldStatePreview/RestoredState/WorkingSawmill/Sprite2D",
		"TestWorld/WorldStatePreview/DamagedState/Forest/Tree01",
		"TestWorld/WorldStatePreview/RestoredState/Forest/Tree01",
	]
	for target_path in target_paths:
		var target := visual_lab.get_node_or_null(target_path) as CanvasItem
		_expect(
			target != null and _canvas_item_has_texture(target),
			"filter matrix includes %s" % target_path,
		)


func _texture_sprites(root: Node) -> Array[CanvasItem]:
	var sprites: Array[CanvasItem] = []
	for descendant in root.find_children("*", "Sprite2D", true, false):
		var sprite := descendant as Sprite2D
		if sprite != null and sprite.texture != null:
			sprites.append(sprite)
	for descendant in root.find_children("*", "AnimatedSprite2D", true, false):
		var sprite := descendant as AnimatedSprite2D
		if sprite != null and sprite.sprite_frames != null:
			sprites.append(sprite)
	return sprites


func _canvas_item_has_texture(target: CanvasItem) -> bool:
	var sprite := target as Sprite2D
	if sprite != null:
		return sprite.texture != null
	var animated_sprite := target as AnimatedSprite2D
	return animated_sprite != null and animated_sprite.sprite_frames != null


func _expect_saved_texture_filter(expected_id: String) -> void:
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_TEST_PATH) == OK, "texture-filter preset loads")
	_expect(
		settings.get_value("visual_lab", "texture_filter", "") == expected_id,
		"texture-filter preset stores '%s'" % expected_id,
	)


func _expect_removed_shortcut() -> void:
	_expect(
		not InputMap.has_action(&"dev_texture_filter_toggle"),
		"texture-filter direct action is absent",
	)


func _hold_action_for_physics_frames(
	tree: SceneTree,
	action: StringName,
	frame_count: int,
) -> void:
	Input.action_press(action)
	for _frame in range(frame_count):
		await tree.physics_frame
	Input.action_release(action)


func _open_visual_lab(tree: SceneTree, packed_scene: PackedScene) -> Control:
	var node := packed_scene.instantiate()
	_expect(node is Control, "VisualLab instantiates as Control")
	if not node is Control:
		if node != null:
			node.free()
		return null
	var visual_lab := node as Control
	tree.root.add_child(visual_lab)
	visual_lab.get_node("LabNavigation").call(&"enter_room", &"objects")
	await tree.process_frame
	return visual_lab


func _close_visual_lab(tree: SceneTree, visual_lab: Control) -> void:
	visual_lab.queue_free()
	await tree.process_frame


func _pressed_action(action: StringName) -> InputEventAction:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = true
	return event


func _pressed_key(keycode: Key, echo: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.keycode = keycode
	event.physical_keycode = keycode
	event.pressed = true
	event.echo = echo
	return event


func _remember_and_set_test_path() -> void:
	_had_settings_path_override = ProjectSettings.has_setting(SETTINGS_PATH_PROJECT_KEY)
	if _had_settings_path_override:
		_original_settings_path = ProjectSettings.get_setting(SETTINGS_PATH_PROJECT_KEY)
	ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, SETTINGS_TEST_PATH)


func _write_settings_fixture(texture_filter_value: Variant, include_filter: bool) -> void:
	var settings := ConfigFile.new()
	settings.set_value("meta", "version", 1)
	settings.set_value("visual_lab", "camera_zoom", "near")
	settings.set_value("visual_lab", "hero_size", "medium")
	settings.set_value("visual_lab", "tile_size", "small")
	settings.set_value("visual_lab", "world_state", "damaged")
	settings.set_value("visual_lab", "pixel_snap", false)
	if include_filter:
		settings.set_value("visual_lab", "texture_filter", texture_filter_value)
	_expect(settings.save(SETTINGS_TEST_PATH) == OK, "filter fixture can be written")


func _cleanup_test_path() -> void:
	_remove_test_settings()
	if _had_settings_path_override:
		ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, _original_settings_path)
		return
	ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, null)


func _remove_test_settings() -> void:
	if not FileAccess.file_exists(SETTINGS_TEST_PATH):
		return
	var remove_error := DirAccess.remove_absolute(
		ProjectSettings.globalize_path(SETTINGS_TEST_PATH)
	)
	_expect(remove_error == OK, "isolated texture-filter settings can be removed")


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLabTextureFilter: %s" % description)
