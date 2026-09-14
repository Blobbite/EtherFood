extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://scenes/dev/visual_lab.tscn"
const CameraProfileResource := preload("res://shared/resources/camera_profile.gd")
const VisualScaleProfileResource := preload(
	"res://shared/resources/visual_scale_profile.gd"
)
const VisualLabStandardsResource := preload(
	"res://shared/resources/visual_lab_standards.gd"
)
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const STANDARDS_PATH_PROJECT_KEY := (
	"etherfood/development/visual_lab_standards_path"
)
const SETTINGS_TEST_PATH := "user://visual_lab_controls_test.cfg"
const STANDARDS_TEST_PATH := "user://visual_lab_controls_standards.tres"
const SCALE_TEST_PATH := "user://visual_lab_controls_scale.tres"
const WORLD_CAMERA_TEST_PATH := "user://visual_lab_controls_camera_world.tres"
const VILLAGE_CAMERA_TEST_PATH := "user://visual_lab_controls_camera_village.tres"
const DUNGEON_CAMERA_TEST_PATH := "user://visual_lab_controls_camera_dungeon.tres"
const INTERIOR_CAMERA_TEST_PATH := "user://visual_lab_controls_camera_interior.tres"
const CONTROLS_ACTION := &"dev_controls_toggle"
const DIAGNOSTICS_ACTION := &"dev_diagnostics_toggle"
const COLLISION_ACTION := &"dev_collision_debug_toggle"
const ACCEPT_ACTION := &"dev_accept_visual_standard"
const MOVE_RIGHT_ACTION := &"gameplay_move_right"
const EXPECTED_PANEL_SIZE := Vector2(620, 700)
const EXPECTED_MENU_SIZE := Vector2(600, 684)
const TEST_RESOURCE_PATHS: Array[String] = [
	STANDARDS_TEST_PATH,
	SCALE_TEST_PATH,
	WORLD_CAMERA_TEST_PATH,
	VILLAGE_CAMERA_TEST_PATH,
	DUNGEON_CAMERA_TEST_PATH,
	INTERIOR_CAMERA_TEST_PATH,
]

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null
var _had_standards_path_override := false
var _original_standards_path: Variant = null


func run(tree: SceneTree) -> PackedStringArray:
	_remember_project_settings()
	_remove_test_files()
	if not _write_standard_fixture():
		_cleanup()
		return failures

	var packed_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "VisualLab scene loads")
	if packed_scene == null:
		_cleanup()
		return failures
	var visual_lab := await _open_visual_lab(tree, packed_scene)
	if visual_lab != null:
		await _expect_menu_contract(tree, visual_lab)
		await _close_visual_lab(tree, visual_lab)
		_expect_saved_standard_files()

	var reopened := await _open_visual_lab(tree, packed_scene)
	if reopened != null:
		var panel := reopened.get_node_or_null("InterfaceLayer/HudPanel") as Panel
		var interface := reopened.get_node_or_null(
			"InterfaceLayer/Interface"
		) as MarginContainer
		_expect(panel != null and not panel.visible, "F5 panel reopens closed")
		_expect(interface != null and not interface.visible, "F5 menu reopens closed")
		await _close_visual_lab(tree, reopened)
	_cleanup()
	return failures


func _expect_menu_contract(tree: SceneTree, visual_lab: Control) -> void:
	var panel := visual_lab.get_node_or_null("InterfaceLayer/HudPanel") as Panel
	var interface := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface"
	) as MarginContainer
	var prompt := visual_lab.get_node_or_null(
		"InterfaceLayer/ControlsPrompt"
	) as Label
	var hero := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as CharacterBody2D
	var title := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Header/Title"
	) as Label
	var tabs := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/ThemeTabs"
	) as GridContainer
	var medium_zoom := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/"
		+ "ZoomOptions/MediumButton"
	) as Button
	var near_zoom := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/"
		+ "ZoomOptions/NearButton"
	) as Button
	var world_context := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/"
		+ "ContextOptions/WorldButton"
	) as Button
	var village_context := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/"
		+ "ContextOptions/VillageButton"
	) as Button
	var dungeon_context := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/"
		+ "ContextOptions/DungeonButton"
	) as Button
	var interior_context := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/"
		+ "ContextOptions/InteriorButton"
	) as Button
	var wide_zoom := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/CameraPage/Content/"
		+ "ZoomOptions/WideButton"
	) as Button
	var accept_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Acceptance/AcceptButton"
	) as Button
	var scale_tab := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/ThemeTabs/ScaleTab"
	) as Button
	var removed_profile_options := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/ScalePage/Content/ProfileOptions"
	)
	var medium_hero := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/ScalePage/Content/"
		+ "HeroOptions/MediumButton"
	) as Button
	var world_tab := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/ThemeTabs/WorldTab"
	) as Button
	var high_fog := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/WorldPage/Content/"
		+ "FogOptions/HighButton"
	) as Button
	var first_light := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/WorldPage/Content/"
		+ "LightOptions/FirstButton"
	) as Button
	var gameplay_tab := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/ThemeTabs/GameplayTab"
	) as Button
	var gameplay_page := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage"
	) as ScrollContainer
	var sneak_speed := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage/Content/SneakSpeed"
	) as VBoxContainer
	var standing_jump_attack := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage/Content/"
		+ "FutureOptions/StandingJumpAttack"
	) as Button
	var diagnostics_panel := visual_lab.get_node_or_null(
		"InterfaceLayer/DiagnosticsPanel"
	) as Control
	var collision_overlay := visual_lab.get_node_or_null(
		"TestWorld/CollisionDebugOverlay"
	) as Node2D

	_expect(panel != null, "VisualLab has a compact menu background")
	_expect(interface != null, "VisualLab has the themed F5 menu")
	_expect(prompt != null and prompt.text == "F5 · Steuerung", "closed menu shows F5")
	_expect(hero != null, "VisualLab retains its controllable hero")
	_expect(title != null and title.text == "VISUELLES TESTLABOR", "menu has a title")
	_expect(
		tabs != null
		and _button_texts(tabs)
		== [
			"Kamera",
			"Maßstab",
			"Darstellung",
			"Welt & Atmosphäre",
			"Diagnose & Hilfe",
			"Gameplay",
		],
		"menu has the six ordered theme tabs",
	)
	_expect(medium_zoom != null and near_zoom != null, "camera has three zoom options")
	_expect(
		world_context != null
		and village_context != null
		and dungeon_context != null
		and interior_context != null,
		"camera has all four target contexts",
	)
	_expect(wide_zoom != null, "camera exposes the wide zoom")
	_expect(accept_button != null, "menu has a visible acceptance button")
	_expect(
		scale_tab != null and removed_profile_options == null and medium_hero != null,
		"scale menu exposes only individual values",
	)
	_expect(
		world_tab != null and high_fog != null and first_light != null,
		"menu has world-state atmosphere values",
	)
	_expect(
		gameplay_tab != null
		and gameplay_page != null
		and sneak_speed != null
		and standing_jump_attack != null
		and standing_jump_attack.disabled,
		"scrollable Gameplay tab exposes sliders and disabled future mechanics",
	)
	_expect(diagnostics_panel != null, "F11 diagnostics remain available")
	_expect(collision_overlay != null, "F4 collision overlay remains available")
	if (
		panel == null
		or interface == null
		or prompt == null
		or hero == null
		or medium_zoom == null
		or near_zoom == null
		or world_context == null
		or village_context == null
		or dungeon_context == null
		or interior_context == null
		or wide_zoom == null
		or accept_button == null
		or scale_tab == null
		or medium_hero == null
		or world_tab == null
		or high_fog == null
		or first_light == null
		or gameplay_tab == null
		or gameplay_page == null
		or sneak_speed == null
		or standing_jump_attack == null
		or diagnostics_panel == null
		or collision_overlay == null
	):
		return

	_expect(not panel.visible and not interface.visible, "F5 menu starts closed")
	_expect(hero.call(&"is_movement_enabled"), "closed menu leaves movement enabled")
	_expect(panel.size == EXPECTED_PANEL_SIZE, "F5 background stays narrow and compact")
	_expect(interface.size == EXPECTED_MENU_SIZE, "F5 menu occupies only a small area")
	_expect(medium_zoom.text.contains("★"), "world standard starts gold and starred")
	_expect(medium_zoom.text.contains("●"), "matching test value is also marked current")
	interior_context.pressed.emit()
	_expect(
		near_zoom.text.contains("★") and near_zoom.text.contains("●"),
		"small-interior context starts at its independent 1.50 standard",
	)
	dungeon_context.pressed.emit()
	_expect(
		medium_zoom.text.contains("★") and medium_zoom.text.contains("●"),
		"dungeon context starts at its independent 1.00 standard",
	)
	world_context.pressed.emit()
	_expect(
		interface.get_combined_minimum_size().x <= interface.size.x
		and interface.get_combined_minimum_size().y <= interface.size.y,
		"compact menu remains operable without covering the viewport",
	)

	visual_lab._unhandled_input(_pressed_action(CONTROLS_ACTION))
	_expect(panel.visible and interface.visible, "F5 opens the complete menu")
	_expect(not prompt.visible, "open menu replaces the compact prompt")
	_expect(hero.call(&"is_movement_enabled"), "open menu leaves hero movement enabled")
	_expect(medium_zoom.has_focus(), "F5 focuses the current camera zoom")
	var position_before_open_menu_movement := hero.global_position
	Input.action_press(MOVE_RIGHT_ACTION)
	await tree.physics_frame
	await tree.physics_frame
	Input.action_release(MOVE_RIGHT_ACTION)
	await tree.physics_frame
	_expect(
		hero.global_position.x > position_before_open_menu_movement.x,
		"hero can move while the F5 menu is open",
	)
	visual_lab._unhandled_input(_pressed_key(KEY_F5, true))
	_expect(interface.visible, "held F5 does not close the menu")

	near_zoom.pressed.emit()
	_expect(near_zoom.button_pressed, "menu selects a new current zoom")
	_expect(near_zoom.text.contains("●"), "current test value has a non-gold marker")
	_expect(not near_zoom.text.contains("★"), "untaken test value is not starred")
	_expect(medium_zoom.text.contains("★"), "gold marker stays on the game standard")
	_expect(
		is_equal_approx(visual_lab._standards.world_camera_profile.base_zoom, 1.0),
		"testing a zoom does not change the game standard",
	)

	visual_lab._unhandled_input(_pressed_action(CONTROLS_ACTION))
	visual_lab._unhandled_input(_pressed_action(ACCEPT_ACTION))
	_expect(
		is_equal_approx(visual_lab._standards.world_camera_profile.base_zoom, 1.0),
		"accept shortcut is inert while F5 is closed",
	)
	visual_lab._unhandled_input(_pressed_action(CONTROLS_ACTION))
	near_zoom.grab_focus()
	visual_lab._unhandled_input(_pressed_action(ACCEPT_ACTION))
	_expect(
		is_equal_approx(visual_lab._standards.world_camera_profile.base_zoom, 1.5),
		"Ctrl Alt E accepts only the focused open-menu setting",
	)
	_expect(near_zoom.text.contains("★"), "gold marker moves after a successful write")
	_expect(not medium_zoom.text.contains("★"), "previous standard loses its gold marker")

	medium_zoom.pressed.emit()
	accept_button.pressed.emit()
	_expect(
		is_equal_approx(visual_lab._standards.world_camera_profile.base_zoom, 1.0),
		"visible button performs the same single-value acceptance",
	)

	village_context.pressed.emit()
	wide_zoom.pressed.emit()
	wide_zoom.grab_focus()
	accept_button.pressed.emit()
	_expect(
		not visual_lab._standards.village_inherits_world,
		"accepting a village zoom ends initial world inheritance",
	)
	_expect(
		is_equal_approx(visual_lab._standards.village_camera_profile.base_zoom, 0.75),
		"village receives its own accepted zoom",
	)
	_expect(
		is_equal_approx(visual_lab._standards.world_camera_profile.base_zoom, 1.0),
		"village acceptance leaves world zoom unchanged",
	)

	world_context.pressed.emit()
	world_context.grab_focus()
	_expect(accept_button.disabled, "non-standard context row cannot be accepted")
	visual_lab._unhandled_input(_pressed_action(ACCEPT_ACTION))
	_expect(
		is_equal_approx(visual_lab._standards.world_camera_profile.base_zoom, 1.0),
		"ineligible focused row cannot change a standard",
	)

	scale_tab.pressed.emit()
	medium_hero.pressed.emit()
	medium_hero.grab_focus()
	accept_button.pressed.emit()
	_expect(
		is_equal_approx(visual_lab._standards.scale_profile.hero_height, 80.0)
		and visual_lab._standards.scale_profile.tile_size == 32
		and is_equal_approx(
			visual_lab._standards.world_camera_profile.base_zoom,
			1.0,
		),
		"single-value scale acceptance leaves all other values unchanged",
	)

	world_tab.pressed.emit()
	high_fog.pressed.emit()
	high_fog.grab_focus()
	accept_button.pressed.emit()
	first_light.pressed.emit()
	first_light.grab_focus()
	accept_button.pressed.emit()
	_expect(
		visual_lab._standards.damaged_fog_id == "high"
		and visual_lab._standards.damaged_light_id == "cool_muted",
		"fog and light standards are accepted per visible world state",
	)

	visual_lab._unhandled_input(_pressed_action(DIAGNOSTICS_ACTION))
	visual_lab._unhandled_input(_pressed_action(COLLISION_ACTION))
	_expect(diagnostics_panel.visible, "F11 still toggles diagnostics directly")
	_expect(collision_overlay.visible, "F4 still toggles collisions directly")
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_TEST_PATH) == OK, "local preview settings load")
	_expect(
		not settings.has_section_key("visual_lab", "diagnostics")
		and not settings.has_section_key("visual_lab", "collision"),
		"diagnostic tools are never persisted as test or game values",
	)

	visual_lab._unhandled_input(_pressed_action(CONTROLS_ACTION))
	_expect(not interface.visible and prompt.visible, "F5 closes the menu")
	_expect(hero.call(&"is_movement_enabled"), "closing F5 leaves movement enabled")


func _write_standard_fixture() -> bool:
	var scale_profile := VisualScaleProfileResource.new()
	scale_profile.profile_id = "visual_lab_controls"
	scale_profile.profile_name = "Teststandard"
	scale_profile.hero_height = 80.0
	scale_profile.tile_size = 32
	scale_profile.camera_zoom = 1.0
	scale_profile.reference_resolution = Vector2i(1920, 1080)
	scale_profile.aspect_ratio = "16:9"
	scale_profile.pixel_snap_enabled = true
	scale_profile.texture_filter_id = "nearest"
	if ResourceSaver.save(scale_profile, SCALE_TEST_PATH) != OK:
		_expect(false, "isolated scale standard can be written")
		return false

	var world_camera := _camera_profile(1.0, "World")
	var village_camera := _camera_profile(1.0, "Village")
	var dungeon_camera := _camera_profile(1.0, "Dungeon")
	var interior_camera := _camera_profile(1.5, "Small interior")
	var camera_profiles: Array[CameraProfileResource] = [
		world_camera,
		village_camera,
		dungeon_camera,
		interior_camera,
	]
	var camera_paths: Array[String] = [
		WORLD_CAMERA_TEST_PATH,
		VILLAGE_CAMERA_TEST_PATH,
		DUNGEON_CAMERA_TEST_PATH,
		INTERIOR_CAMERA_TEST_PATH,
	]
	for profile_index in range(camera_profiles.size()):
		if ResourceSaver.save(camera_profiles[profile_index], camera_paths[profile_index]) != OK:
			_expect(false, "isolated camera standard %d can be written" % profile_index)
			return false
	scale_profile = load(SCALE_TEST_PATH) as VisualScaleProfileResource
	world_camera = load(WORLD_CAMERA_TEST_PATH) as CameraProfileResource
	village_camera = load(VILLAGE_CAMERA_TEST_PATH) as CameraProfileResource
	dungeon_camera = load(DUNGEON_CAMERA_TEST_PATH) as CameraProfileResource
	interior_camera = load(INTERIOR_CAMERA_TEST_PATH) as CameraProfileResource

	var standards := VisualLabStandardsResource.new()
	standards.scale_profile = scale_profile
	standards.world_camera_profile = world_camera
	standards.village_camera_profile = village_camera
	standards.village_inherits_world = true
	standards.dungeon_camera_profile = dungeon_camera
	standards.small_interior_camera_profile = interior_camera
	standards.damaged_fog_id = "medium"
	standards.damaged_light_id = "cool_dark"
	standards.restored_fog_id = "low"
	standards.restored_light_id = "warm_clear"
	var save_error := ResourceSaver.save(standards, STANDARDS_TEST_PATH)
	_expect(save_error == OK, "isolated standard registry can be written")
	return save_error == OK


func _camera_profile(zoom: float, profile_name: String) -> CameraProfileResource:
	var profile := CameraProfileResource.new()
	profile.base_zoom = zoom
	profile.profile_name = profile_name
	return profile


func _button_texts(container: Container) -> Array[String]:
	var result: Array[String] = []
	for child in container.get_children():
		var button := child as Button
		if button != null:
			result.append(button.text)
	return result


func _expect_saved_standard_files() -> void:
	var registry_text := FileAccess.get_file_as_string(STANDARDS_TEST_PATH)
	var scale_profile := ResourceLoader.load(
		SCALE_TEST_PATH,
		"",
		ResourceLoader.CACHE_MODE_IGNORE,
	) as VisualScaleProfileResource
	var world_camera := ResourceLoader.load(
		WORLD_CAMERA_TEST_PATH,
		"",
		ResourceLoader.CACHE_MODE_IGNORE,
	) as CameraProfileResource
	var village_camera := ResourceLoader.load(
		VILLAGE_CAMERA_TEST_PATH,
		"",
		ResourceLoader.CACHE_MODE_IGNORE,
	) as CameraProfileResource
	_expect(
		registry_text.contains("village_inherits_world = false")
		and registry_text.contains("damaged_fog_id = \"high\"")
		and registry_text.contains("damaged_light_id = \"cool_muted\""),
		"accepted registry values are written to the isolated resource",
	)
	_expect(
		scale_profile != null
		and is_equal_approx(scale_profile.hero_height, 80.0)
		and scale_profile.tile_size == 32
		and is_equal_approx(scale_profile.camera_zoom, 1.0),
		"accepted scale values are written to the isolated resource",
	)
	_expect(
		world_camera != null
		and village_camera != null
		and is_equal_approx(world_camera.base_zoom, 1.0)
		and is_equal_approx(village_camera.base_zoom, 0.75),
		"accepted contextual camera values are written to isolated resources",
	)


func _remember_project_settings() -> void:
	_had_settings_path_override = ProjectSettings.has_setting(
		SETTINGS_PATH_PROJECT_KEY
	)
	if _had_settings_path_override:
		_original_settings_path = ProjectSettings.get_setting(
			SETTINGS_PATH_PROJECT_KEY
		)
	_had_standards_path_override = ProjectSettings.has_setting(
		STANDARDS_PATH_PROJECT_KEY
	)
	if _had_standards_path_override:
		_original_standards_path = ProjectSettings.get_setting(
			STANDARDS_PATH_PROJECT_KEY
		)
	ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, SETTINGS_TEST_PATH)
	ProjectSettings.set_setting(STANDARDS_PATH_PROJECT_KEY, STANDARDS_TEST_PATH)


func _open_visual_lab(tree: SceneTree, packed_scene: PackedScene) -> Control:
	var node := packed_scene.instantiate()
	_expect(node is Control, "VisualLab instantiates")
	if not node is Control:
		if node != null:
			node.free()
		return null
	var visual_lab := node as Control
	tree.root.add_child(visual_lab)
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
	event.pressed = true
	event.echo = echo
	return event


func _cleanup() -> void:
	_remove_test_files()
	if _had_settings_path_override:
		ProjectSettings.set_setting(
			SETTINGS_PATH_PROJECT_KEY,
			_original_settings_path,
		)
	else:
		ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, null)
	if _had_standards_path_override:
		ProjectSettings.set_setting(
			STANDARDS_PATH_PROJECT_KEY,
			_original_standards_path,
		)
	else:
		ProjectSettings.set_setting(STANDARDS_PATH_PROJECT_KEY, null)


func _remove_test_files() -> void:
	var paths := TEST_RESOURCE_PATHS.duplicate()
	paths.append(SETTINGS_TEST_PATH)
	for resource_path in paths:
		if FileAccess.file_exists(resource_path):
			var remove_error := DirAccess.remove_absolute(
				ProjectSettings.globalize_path(resource_path)
			)
			_expect(remove_error == OK, "isolated test file can be removed")


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLab controls: %s" % description)
