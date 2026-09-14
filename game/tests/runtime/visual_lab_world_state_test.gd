extends RefCounted

const WORLD_STATE_SCENE_PATH := "res://scenes/dev/world_state_preview.tscn"
const VISUAL_LAB_SCENE_PATH := "res://scenes/dev/visual_lab.tscn"
const WORLD_STATE_PREVIEW_SCRIPT := preload("res://scenes/dev/world_state_preview.gd")
const HERO_SCRIPT := preload("res://scenes/gameplay/hero/hero_character.gd")
const TILE_GRID_PREVIEW_SCRIPT := preload("res://scenes/dev/tile_grid_preview.gd")
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_TEST_PATH := "user://visual_lab_settings_test.cfg"
const DAMAGED_STATUS := "Weltzustand: Beschädigt"
const RESTORED_STATUS := "Weltzustand: Wiederhergestellt"
const DAMAGED_CHILDREN: Array[String] = [
	"Ground",
	"GroundTexture",
	"Path",
	"BrokenBuilding",
	"RuinedSawmill",
	"DeadTree",
	"Forest",
	"DeadPlants",
	"Fog",
	"ColdLight",
]
const RESTORED_CHILDREN: Array[String] = [
	"Ground",
	"GroundTexture",
	"Path",
	"RepairedBuilding",
	"WorkingSawmill",
	"LivingTree",
	"Forest",
	"LivingPlants",
	"Fog",
	"ClearAir",
	"WarmLight",
]
const PLANT_NAMES: Array[String] = ["PlantLeft", "PlantMiddle", "PlantRight"]
const FOREST_TREE_NAMES: Array[String] = [
	"Tree01",
	"Tree02",
	"Tree03",
	"Tree04",
	"Tree05",
	"Tree06",
	"Tree07",
	"Tree08",
	"Tree09",
	"Tree10",
	"Tree11",
	"Tree12",
]

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null


func run(tree: SceneTree) -> PackedStringArray:
	_remember_and_set_test_path()
	_remove_test_settings()
	_expect_removed_shortcut()
	await _expect_preview_scene_contract(tree)
	await _expect_visual_lab_contract(tree)
	_cleanup_test_path()
	return failures


func _expect_preview_scene_contract(tree: SceneTree) -> void:
	var preview_scene := load(WORLD_STATE_SCENE_PATH) as PackedScene
	_expect(preview_scene != null, "WorldStatePreview scene loads")
	if preview_scene == null:
		return
	var preview_node := preview_scene.instantiate()
	_expect(
		preview_node is WORLD_STATE_PREVIEW_SCRIPT,
		"WorldStatePreview uses its production script",
	)
	if not preview_node is WORLD_STATE_PREVIEW_SCRIPT:
		if preview_node != null:
			preview_node.free()
		return
	var preview: WORLD_STATE_PREVIEW_SCRIPT = preview_node as WORLD_STATE_PREVIEW_SCRIPT
	tree.root.add_child(preview)
	await tree.process_frame

	var damaged_state := preview.get_node_or_null("DamagedState") as Node2D
	var restored_state := preview.get_node_or_null("RestoredState") as Node2D
	var title := preview.get_node_or_null("Title") as Label
	_expect(damaged_state != null, "WorldStatePreview has DamagedState")
	_expect(restored_state != null, "WorldStatePreview has RestoredState")
	_expect(title != null, "WorldStatePreview has a Title")
	if damaged_state != null:
		for child_name in DAMAGED_CHILDREN:
			_expect(
				damaged_state.get_node_or_null(child_name) is CanvasItem,
				"DamagedState has visible test element %s" % child_name,
			)
	if restored_state != null:
		for child_name in RESTORED_CHILDREN:
			_expect(
				restored_state.get_node_or_null(child_name) is CanvasItem,
				"RestoredState has visible test element %s" % child_name,
			)
	if title != null:
		_expect(
			title.text
			== "Weltzustand · Haus, Wald und Sägewerk · Beschädigt ↔ Wiederhergestellt",
			"WorldStatePreview title identifies both states and all test zones",
		)
	_expect(
		preview.get_preview_size() == Vector2(1440, 810),
		"WorldStatePreview exposes its enlarged 1440 by 810 test area",
	)
	if damaged_state != null and restored_state != null:
		_expect_top_down_layout(damaged_state, restored_state)
		_expect_state_specific_details(damaged_state, restored_state)

	var original_preview_transform := preview.transform
	_expect_preview_state(preview, false, "preview starts damaged")
	preview.set_world_state(preview.WorldState.RESTORED)
	_expect_preview_state(preview, true, "setting restored shows only RestoredState")
	preview.set_world_state(preview.WorldState.DAMAGED)
	_expect_preview_state(preview, false, "setting damaged shows only DamagedState")
	_expect(
		preview.transform == original_preview_transform,
		"world-state changes keep the top-down preview transform unchanged",
	)
	_expect(
		preview.find_children("*", "CollisionObject2D", true, false).is_empty(),
		"WorldStatePreview contains no collision bodies or areas",
	)
	_expect(
		preview.find_children("*", "CollisionShape2D", true, false).is_empty(),
		"WorldStatePreview contains no collision shapes",
	)
	_expect(
		preview.find_children("*", "CollisionPolygon2D", true, false).is_empty(),
		"WorldStatePreview contains no collision polygons",
	)

	var damaged_ground := preview.get_node_or_null("DamagedState/Ground") as Sprite2D
	var restored_ground := preview.get_node_or_null("RestoredState/Ground") as Sprite2D
	_expect(
		damaged_ground != null
		and restored_ground != null
		and damaged_ground.texture != restored_ground.texture,
		"damaged and restored ground use visibly distinct pixel textures",
	)
	_expect(
		damaged_ground != null
		and restored_ground != null
		and damaged_ground.texture.get_size() == preview.get_preview_size()
		and restored_ground.texture.get_size() == preview.get_preview_size(),
		"both ground states cover the complete enlarged test area",
	)

	preview.queue_free()
	await tree.process_frame


func _expect_top_down_layout(damaged_state: Node2D, restored_state: Node2D) -> void:
	_expect(
		damaged_state.transform == restored_state.transform,
		"both world states use the same preview perspective",
	)
	for sprite_path in [^"Ground", ^"GroundTexture", ^"Path"]:
		_expect_matching_sprite_canvas(
			damaged_state,
			restored_state,
			sprite_path,
			sprite_path,
			"paired layer %s" % sprite_path,
		)

	var broken_building := damaged_state.get_node_or_null("BrokenBuilding") as Node2D
	var repaired_building := restored_state.get_node_or_null("RepairedBuilding") as Node2D
	_expect_matching_position(
		broken_building,
		repaired_building,
		"building",
	)
	_expect_matching_sprite_canvas(
		broken_building,
		repaired_building,
		^"Sprite2D",
		^"Sprite2D",
		"building canvas and anchor",
	)

	var ruined_sawmill := damaged_state.get_node_or_null("RuinedSawmill") as Node2D
	var working_sawmill := restored_state.get_node_or_null("WorkingSawmill") as Node2D
	_expect_matching_position(ruined_sawmill, working_sawmill, "sawmill")
	_expect_matching_sprite_canvas(
		ruined_sawmill,
		working_sawmill,
		^"Sprite2D",
		^"Sprite2D",
		"sawmill canvas and anchor",
	)

	var dead_tree := damaged_state.get_node_or_null("DeadTree") as Node2D
	var living_tree := restored_state.get_node_or_null("LivingTree") as Node2D
	_expect_matching_position(dead_tree, living_tree, "tree")
	_expect_matching_sprite_canvas(
		dead_tree,
		living_tree,
		^"Sprite2D",
		^"Sprite2D",
		"tree canvas and anchor",
	)

	var damaged_forest := damaged_state.get_node_or_null("Forest") as Node2D
	var restored_forest := restored_state.get_node_or_null("Forest") as Node2D
	_expect(
		damaged_forest != null and restored_forest != null,
		"both states contain the enlarged forest section",
	)
	if damaged_forest != null and restored_forest != null:
		for tree_name in FOREST_TREE_NAMES:
			_expect_matching_sprite_canvas(
				damaged_forest,
				restored_forest,
				NodePath(tree_name),
				NodePath(tree_name),
				"forest tree %s" % tree_name,
			)

	var dead_plants := damaged_state.get_node_or_null("DeadPlants") as Node2D
	var living_plants := restored_state.get_node_or_null("LivingPlants") as Node2D
	_expect(
		dead_plants != null and living_plants != null,
		"both states contain their top-down plant groups",
	)
	if dead_plants != null and living_plants != null:
		for plant_name in PLANT_NAMES:
			var dead_plant := dead_plants.get_node_or_null(plant_name) as Node2D
			var living_plant := living_plants.get_node_or_null(plant_name) as Node2D
			_expect_matching_position(dead_plant, living_plant, "plant %s" % plant_name)
			_expect_matching_sprite_canvas(
				dead_plant,
				living_plant,
				^"Sprite2D",
				^"Sprite2D",
				"plant canvas and anchor %s" % plant_name,
			)

	_expect_matching_sprite_canvas(
		damaged_state,
		restored_state,
		^"Fog/Sprite2D",
		^"Fog/Sprite2D",
		"fog canvas and anchor",
	)


func _expect_state_specific_details(damaged_state: Node2D, restored_state: Node2D) -> void:
	_expect(
		_expect_distinct_sprite_textures(damaged_state, restored_state, ^"GroundTexture"),
		"damaged cracks and restored grass use distinct pixel textures",
	)
	_expect(
		damaged_state.get_node_or_null("BrokenBuilding/DamageDetails") is Node2D,
		"damaged building identifies its missing roof and blocked entrance details",
	)
	_expect(
		restored_state.get_node_or_null("RepairedBuilding/RepairedDetails") is Node2D,
		"restored building identifies its continuous roof and clean entrance details",
	)
	_expect(
		damaged_state.get_node_or_null("RuinedSawmill/DamageDetails") is Node2D,
		"damaged state identifies the ruined sawmill details",
	)
	_expect(
		restored_state.get_node_or_null("WorkingSawmill/RepairedDetails") is Node2D,
		"restored state identifies the working sawmill details",
	)
	_expect(
		_expect_distinct_sprite_textures(
			damaged_state,
			restored_state,
			^"BrokenBuilding/Sprite2D",
			^"RepairedBuilding/Sprite2D",
		),
		"building damage and repair are baked into distinct original textures",
	)
	_expect(
		_expect_distinct_sprite_textures(
			damaged_state,
			restored_state,
			^"RuinedSawmill/Sprite2D",
			^"WorkingSawmill/Sprite2D",
		),
		"sawmill damage and repair use paired state textures",
	)
	_expect(
		_expect_distinct_sprite_textures(
			damaged_state,
			restored_state,
			^"DeadTree/Sprite2D",
			^"LivingTree/Sprite2D",
		),
		"dead branches and living canopy use distinct top-down textures",
	)
	_expect(
		_expect_distinct_sprite_textures(
			damaged_state,
			restored_state,
			^"DeadPlants/PlantLeft/Sprite2D",
			^"LivingPlants/PlantLeft/Sprite2D",
		),
		"dead and living plants use distinct top-down textures",
	)
	_expect(
		_expect_distinct_sprite_textures(
			damaged_state,
			restored_state,
			^"Fog/Sprite2D",
			^"Fog/Sprite2D",
		),
		"restored state uses a less opaque fog texture on the same canvas",
	)
	_expect_all_preview_sprites_are_pixel_safe(damaged_state)
	_expect_all_preview_sprites_are_pixel_safe(restored_state)


func _expect_matching_position(
	damaged_node: Node2D,
	restored_node: Node2D,
	description: String,
) -> void:
	_expect(
		damaged_node != null
		and restored_node != null
		and damaged_node.position == restored_node.position,
		"both states keep the same %s position" % description,
	)


func _expect_matching_sprite_canvas(
	damaged_parent: Node,
	restored_parent: Node,
	damaged_path: NodePath,
	restored_path: NodePath,
	description: String,
) -> void:
	if damaged_parent == null or restored_parent == null:
		_expect(false, "both states contain the %s nodes" % description)
		return
	var damaged_sprite := damaged_parent.get_node_or_null(damaged_path) as Sprite2D
	var restored_sprite := restored_parent.get_node_or_null(restored_path) as Sprite2D
	_expect(
		damaged_sprite != null
		and restored_sprite != null
		and damaged_sprite.position == restored_sprite.position
		and damaged_sprite.centered == restored_sprite.centered
		and damaged_sprite.texture != null
		and restored_sprite.texture != null
		and damaged_sprite.texture.get_size() == restored_sprite.texture.get_size(),
		"both states keep the same %s" % description,
	)


func _expect_distinct_sprite_textures(
	damaged_parent: Node,
	restored_parent: Node,
	damaged_path: NodePath,
	restored_path: NodePath = NodePath(),
) -> bool:
	var effective_restored_path := restored_path
	if effective_restored_path.is_empty():
		effective_restored_path = damaged_path
	var damaged_sprite := damaged_parent.get_node_or_null(damaged_path) as Sprite2D
	var restored_sprite := restored_parent.get_node_or_null(
		effective_restored_path
	) as Sprite2D
	return (
		damaged_sprite != null
		and restored_sprite != null
		and damaged_sprite.texture != null
		and restored_sprite.texture != null
		and damaged_sprite.texture != restored_sprite.texture
	)


func _expect_all_preview_sprites_are_pixel_safe(state: Node2D) -> void:
	for node in state.find_children("*", "Sprite2D", true, false):
		var sprite := node as Sprite2D
		_expect(sprite.texture != null, "%s has a visible pixel texture" % sprite.name)
		_expect(
			sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
			"%s uses nearest-neighbor filtering" % sprite.name,
		)
		_expect(sprite.scale == Vector2.ONE, "%s uses uniform source scale" % sprite.name)
		_expect(sprite.rotation == 0.0, "%s is not rotated" % sprite.name)
		if sprite.texture != null:
			var image := sprite.texture.get_image()
			_expect(
				image != null and not image.has_mipmaps(),
				"%s texture has no mipmaps" % sprite.name,
			)


func _expect_visual_lab_contract(tree: SceneTree) -> void:
	var visual_lab_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(visual_lab_scene != null, "VisualLab scene loads")
	if visual_lab_scene == null:
		return
	var visual_lab := await _open_visual_lab(tree, visual_lab_scene)
	if visual_lab == null:
		return

	var preview: WORLD_STATE_PREVIEW_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/WorldStatePreview"
	) as WORLD_STATE_PREVIEW_SCRIPT
	var status := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/WorldPage/Content/WorldStateStatus"
	) as Label
	var player_camera := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/PlayerCamera"
	) as Camera2D
	var hero: HERO_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as HERO_SCRIPT
	var tile_grid_preview: TILE_GRID_PREVIEW_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/TileComparison/TileGridPreview"
	) as TILE_GRID_PREVIEW_SCRIPT
	var hero_collision := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/CollisionShape2D"
	) as CollisionShape2D

	_expect(preview != null, "VisualLab contains WorldStatePreview")
	_expect(status != null, "VisualLab has a world-state status Label")
	_expect(player_camera != null, "VisualLab retains PlayerCamera")
	_expect(hero != null, "VisualLab retains HeroCharacter")
	_expect(tile_grid_preview != null, "VisualLab retains TileGridPreview")
	_expect(
		hero_collision != null and hero_collision.shape != null,
		"VisualLab retains the hero collision shape",
	)
	if (
		preview == null
		or status == null
		or player_camera == null
		or hero == null
		or tile_grid_preview == null
		or hero_collision == null
		or hero_collision.shape == null
	):
		await _close_visual_lab(tree, visual_lab)
		return

	_expect(
		preview.position == Vector2(1200, 480),
		"WorldStatePreview occupies the dedicated world-state room",
	)
	var preview_bounds := Rect2(preview.position, preview.get_preview_size())
	_expect(
		Rect2(0, 0, 3840, 2160).encloses(preview_bounds),
		"WorldStatePreview stays inside the enlarged TestWorld",
	)
	_expect(
		not visual_lab.get_node("TestWorld/TileComparison").is_visible_in_tree(),
		"world-state and tile comparisons occupy separate rooms",
	)
	_expect(
		not preview_bounds.has_point(hero.position),
		"WorldStatePreview does not cover the hero start",
	)
	_expect(
		preview.get_parent() == hero.get_parent(),
		"WorldStatePreview and the controllable hero share the same TestWorld",
	)
	var building_side := preview.position + Vector2(390, 270)
	_expect(
		preview_bounds.has_point(building_side)
		and Rect2(0, 0, 3840, 2160).has_point(building_side)
		and hero.position.distance_to(building_side) < 1500.0,
		"the controllable hero can walk directly beside the preview building",
	)

	var original_camera_zoom := player_camera.zoom
	var original_hero_height := hero.get_appearance_height()
	var original_hero_position := hero.position
	var original_walk_speed := hero.movement_config.walk_speed
	var original_tile_size := tile_grid_preview.tile_size
	var original_collision_shape := hero_collision.shape
	var original_collision_transform := hero_collision.transform

	_expect_preview_state(preview, false, "VisualLab starts with damaged world state")
	_expect(status.text == DAMAGED_STATUS, "damaged start state has matching HUD text")
	visual_lab._unhandled_input(_pressed_key(KEY_V, true))
	_expect_preview_state(preview, false, "removed V shortcut leaves state unchanged")

	visual_lab._toggle_world_state()
	_expect_preview_state(preview, true, "state helper changes damaged to restored")
	_expect(status.text == RESTORED_STATUS, "restored state has matching HUD text")
	_expect_saved_world_state("restored")
	visual_lab._toggle_world_state()
	_expect_preview_state(preview, false, "second state change restores damaged state")
	_expect(status.text == DAMAGED_STATUS, "second state change updates the HUD")
	_expect_saved_world_state("damaged")
	visual_lab._toggle_world_state()
	_expect_preview_state(preview, true, "state helper restores the restored preview")
	_expect(status.text == RESTORED_STATUS, "state helper updates the HUD")
	_expect_saved_world_state("restored")

	_expect(
		player_camera.zoom.is_equal_approx(original_camera_zoom),
		"world-state changes keep camera zoom unchanged",
	)
	_expect(
		is_equal_approx(hero.get_appearance_height(), original_hero_height),
		"world-state changes keep hero size unchanged",
	)
	_expect(hero.position == original_hero_position, "world-state changes keep hero position")
	_expect(
		hero.movement_config.walk_speed == original_walk_speed,
		"world-state changes keep walk speed",
	)
	_expect(
		tile_grid_preview.tile_size == original_tile_size,
		"world-state changes keep tile size unchanged",
	)
	_expect(
		hero_collision.shape == original_collision_shape,
		"world-state changes keep the collision shape",
	)
	_expect(
		hero_collision.transform == original_collision_transform,
		"world-state changes keep the collision transform",
	)
	_expect(
		preview.find_children("*", "CollisionObject2D", true, false).is_empty(),
		"preview remains visual-only without a building entrance trigger",
	)

	await _close_visual_lab(tree, visual_lab)
	var reopened_visual_lab := await _open_visual_lab(tree, visual_lab_scene)
	if reopened_visual_lab != null:
		var reopened_preview: WORLD_STATE_PREVIEW_SCRIPT = (
			reopened_visual_lab.get_node_or_null("TestWorld/WorldStatePreview")
			as WORLD_STATE_PREVIEW_SCRIPT
		)
		var reopened_status := reopened_visual_lab.get_node_or_null(
			"InterfaceLayer/Interface/Menu/Pages/WorldPage/Content/WorldStateStatus"
		) as Label
		_expect(reopened_preview != null, "reopened VisualLab has WorldStatePreview")
		_expect(reopened_status != null, "reopened VisualLab has world-state status")
		if reopened_preview != null and reopened_status != null:
			_expect_preview_state(reopened_preview, true, "reopened VisualLab loads restored")
			_expect(
				reopened_status.text == RESTORED_STATUS,
				"reopened VisualLab displays restored status",
			)
		await _close_visual_lab(tree, reopened_visual_lab)

	_write_legacy_or_invalid_settings(null)
	await _expect_file_world_fallback(
		tree,
		visual_lab_scene,
		"missing world_state remains backward compatible",
	)
	_write_legacy_or_invalid_settings("unknown-world")
	await _expect_file_world_fallback(
		tree,
		visual_lab_scene,
		"unknown world_state falls back to damaged",
	)


func _expect_file_world_fallback(
	tree: SceneTree,
	visual_lab_scene: PackedScene,
	description: String,
) -> void:
	var visual_lab := await _open_visual_lab(tree, visual_lab_scene)
	if visual_lab == null:
		return
	var preview: WORLD_STATE_PREVIEW_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/WorldStatePreview"
	) as WORLD_STATE_PREVIEW_SCRIPT
	var status := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/WorldPage/Content/WorldStateStatus"
	) as Label
	var camera := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/PlayerCamera"
	) as Camera2D
	var hero: HERO_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as HERO_SCRIPT
	var tile_grid_preview: TILE_GRID_PREVIEW_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/TileComparison/TileGridPreview"
	) as TILE_GRID_PREVIEW_SCRIPT
	_expect(preview != null, "%s: WorldStatePreview exists" % description)
	_expect(status != null, "%s: world-state status exists" % description)
	if preview != null:
		_expect_preview_state(preview, false, description)
	if status != null:
		_expect(status.text == DAMAGED_STATUS, "%s: damaged HUD text" % description)
	_expect(
		camera != null and camera.zoom == Vector2(0.75, 0.75),
		"%s: existing camera setting still loads" % description,
	)
	_expect(
		hero != null and is_equal_approx(hero.get_appearance_height(), 96.0),
		"%s: existing hero-size setting still loads" % description,
	)
	_expect(
		tile_grid_preview != null and tile_grid_preview.tile_size == 64,
		"%s: existing tile-size setting still loads" % description,
	)
	await _close_visual_lab(tree, visual_lab)


func _expect_preview_state(
	preview: WORLD_STATE_PREVIEW_SCRIPT,
	expected_restored: bool,
	description: String,
) -> void:
	var damaged_state := preview.get_node_or_null("DamagedState") as Node2D
	var restored_state := preview.get_node_or_null("RestoredState") as Node2D
	_expect(damaged_state != null, "%s: DamagedState exists" % description)
	_expect(restored_state != null, "%s: RestoredState exists" % description)
	if damaged_state == null or restored_state == null:
		return
	_expect(preview.is_restored() == expected_restored, "%s: current state" % description)
	_expect(
		damaged_state.visible == not expected_restored,
		"%s: DamagedState visibility" % description,
	)
	_expect(
		restored_state.visible == expected_restored,
		"%s: RestoredState visibility" % description,
	)
	_expect(
		damaged_state.visible != restored_state.visible,
		"%s: exactly one state is visible" % description,
	)


func _expect_removed_shortcut() -> void:
	_expect(
		not InputMap.has_action(&"dev_world_state_toggle"),
		"world-state direct action is absent",
	)


func _expect_saved_world_state(expected_id: String) -> void:
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_TEST_PATH) == OK, "saved settings file loads")
	_expect(
		settings.get_value("visual_lab", "world_state", "") == expected_id,
		"saved settings contain world_state=%s" % expected_id,
	)


func _write_legacy_or_invalid_settings(world_state: Variant) -> void:
	var settings := ConfigFile.new()
	settings.set_value("meta", "version", 1)
	settings.set_value("visual_lab", "camera_zoom", "wide")
	settings.set_value("visual_lab", "hero_size", "large")
	settings.set_value("visual_lab", "tile_size", "large")
	if world_state != null:
		settings.set_value("visual_lab", "world_state", world_state)
	_expect(settings.save(SETTINGS_TEST_PATH) == OK, "world-state fixture can be saved")


func _open_visual_lab(tree: SceneTree, visual_lab_scene: PackedScene) -> Control:
	var visual_lab_node := visual_lab_scene.instantiate()
	_expect(visual_lab_node is Control, "VisualLab instantiates as Control")
	if not visual_lab_node is Control:
		if visual_lab_node != null:
			visual_lab_node.free()
		return null
	var visual_lab := visual_lab_node as Control
	tree.root.add_child(visual_lab)
	visual_lab.get_node("LabNavigation").call(&"enter_room", &"world_state")
	await tree.process_frame
	return visual_lab


func _close_visual_lab(tree: SceneTree, visual_lab: Control) -> void:
	visual_lab.queue_free()
	await tree.process_frame


func _pressed_key(keycode: Key, echo: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.physical_keycode = keycode
	event.pressed = true
	event.echo = echo
	return event


func _remember_and_set_test_path() -> void:
	_had_settings_path_override = ProjectSettings.has_setting(SETTINGS_PATH_PROJECT_KEY)
	if _had_settings_path_override:
		_original_settings_path = ProjectSettings.get_setting(SETTINGS_PATH_PROJECT_KEY)
	ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, SETTINGS_TEST_PATH)
	_expect(
		ProjectSettings.get_setting(SETTINGS_PATH_PROJECT_KEY) == SETTINGS_TEST_PATH,
		"world-state tests use only the isolated settings path",
	)


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
	_expect(remove_error == OK, "isolated world-state test settings can be removed")


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLabWorldState: %s" % description)
