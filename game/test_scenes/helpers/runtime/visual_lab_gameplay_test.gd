extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://test_scenes/visual_lab/visual_lab.tscn"
const HeroMovementConfigResource := preload(
	"res://shared/resources/hero_movement_config.gd"
)
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const MOVEMENT_PATH_PROJECT_KEY := (
	"etherfood/development/hero_movement_standard_path"
)
const SETTINGS_TEST_PATH := "user://visual_lab_gameplay_test.cfg"
const MOVEMENT_TEST_PATH := "user://visual_lab_gameplay_standard.tres"
const CONTROLS_ACTION := &"dev_controls_toggle"
const EXPECTED_NUMERIC_ROWS: Array[Dictionary] = [
	{"node": "SneakSpeed", "value": 60.0, "min": 40.0, "max": 500.0, "step": 5.0},
	{"node": "WalkSpeed", "value": 100.0, "min": 40.0, "max": 500.0, "step": 5.0},
	{"node": "JogSpeed", "value": 220.0, "min": 40.0, "max": 500.0, "step": 5.0},
	{"node": "RunSpeed", "value": 310.0, "min": 40.0, "max": 500.0, "step": 5.0},
	{"node": "SprintSpeed", "value": 400.0, "min": 40.0, "max": 500.0, "step": 5.0},
	{"node": "StandingJumpHeight", "value": 24.0, "min": 8.0, "max": 64.0, "step": 1.0},
	{"node": "WalkJumpHeight", "value": 20.0, "min": 8.0, "max": 64.0, "step": 1.0},
	{"node": "WalkJumpDistance", "value": 32.0, "min": 16.0, "max": 160.0, "step": 1.0},
	{"node": "JogJumpHeight", "value": 24.0, "min": 8.0, "max": 64.0, "step": 1.0},
	{"node": "JogJumpDistance", "value": 48.0, "min": 16.0, "max": 160.0, "step": 1.0},
	{"node": "RunJumpHeight", "value": 30.0, "min": 8.0, "max": 64.0, "step": 1.0},
	{"node": "RunJumpDistance", "value": 80.0, "min": 16.0, "max": 160.0, "step": 1.0},
	{"node": "SprintJumpHeight", "value": 36.0, "min": 8.0, "max": 64.0, "step": 1.0},
	{"node": "SprintJumpDistance", "value": 112.0, "min": 16.0, "max": 160.0, "step": 1.0},
]
const EXPECTED_PLACEHOLDERS: Array[String] = [
	"Stehsprungangriff",
	"Gehsprungangriff",
	"Laufsprungangriff",
	"Rennsprungangriff",
	"Sprintsprungangriff",
	"Ausweichen",
	"Schleichrolle",
	"Ausweich-Backflip",
]

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null
var _had_movement_path_override := false
var _original_movement_path: Variant = null


func run(tree: SceneTree) -> PackedStringArray:
	_remember_project_settings()
	_remove_test_files()
	if not _write_movement_fixture():
		_cleanup()
		return failures

	var packed_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "VisualLab scene loads")
	if packed_scene == null:
		_cleanup()
		return failures

	var visual_lab := await _open_visual_lab(tree, packed_scene)
	if visual_lab != null:
		_expect_initial_gameplay_menu(visual_lab)
		_expect_runtime_preview_isolation(visual_lab)
		_expect_safe_runtime_edits(visual_lab)
		await _close_visual_lab(tree, visual_lab)

	var reopened := await _open_visual_lab(tree, packed_scene)
	if reopened != null:
		_expect_persisted_preview(reopened)
		_expect_single_value_acceptance(reopened)
		await _close_visual_lab(tree, reopened)

	_cleanup()
	return failures


func _expect_initial_gameplay_menu(visual_lab: Control) -> void:
	var gameplay_page := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage"
	) as ScrollContainer
	var content := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage/Content"
	) as VBoxContainer
	var standing_distance := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage/Content/"
		+ "StandingJumpDistance"
	) as Label
	var future_options := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage/Content/FutureOptions"
	) as GridContainer
	_expect(gameplay_page != null, "Gameplay page is scrollable")
	_expect(content != null, "Gameplay page has content")
	_expect(
		standing_distance != null
		and standing_distance.text == "Stehsprung · Weite: 0 px · fest senkrecht",
		"standing jump keeps a fixed zero distance",
	)
	for expected in EXPECTED_NUMERIC_ROWS:
		var row := content.get_node_or_null(str(expected["node"])) if content != null else null
		var slider := row.get_node_or_null("Slider") as HSlider if row != null else null
		_expect(slider != null, "%s slider exists" % expected["node"])
		if slider == null:
			continue
		_expect(
			is_equal_approx(slider.value, float(expected["value"])),
			"%s starts at the staged value" % expected["node"],
		)
		_expect(
			is_equal_approx(slider.min_value, float(expected["min"]))
			and is_equal_approx(slider.max_value, float(expected["max"]))
			and is_equal_approx(slider.step, float(expected["step"])),
			"%s has safe numeric limits" % expected["node"],
		)
	_expect(future_options != null, "future-mechanics placeholder grid exists")
	if future_options != null:
		var placeholder_names: Array[String] = []
		for child in future_options.get_children():
			var button := child as Button
			if button == null:
				continue
			placeholder_names.append(button.text)
			_expect(button.disabled, "%s is visibly unavailable" % button.text)
			_expect(
				button.focus_mode == Control.FOCUS_NONE,
				"%s cannot receive focus" % button.text,
			)
		_expect(
			placeholder_names == EXPECTED_PLACEHOLDERS,
			"all eight future mechanics are listed in order",
		)


func _expect_runtime_preview_isolation(visual_lab: Control) -> void:
	var hero := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as CharacterBody2D
	_expect(hero != null, "Gameplay lab retains the playable hero")
	if hero == null:
		return
	var hero_config := hero.get("movement_config") as Resource
	_expect(hero_config != null, "hero receives a movement preview")
	_expect(
		hero_config == visual_lab._movement_preview
		and hero_config != visual_lab._movement_standard,
		"laboratory movement is a deep runtime copy",
	)


func _expect_safe_runtime_edits(visual_lab: Control) -> void:
	_expect(
		visual_lab._set_gameplay_value(&"walk_speed", NAN) == ERR_INVALID_PARAMETER
		and is_equal_approx(visual_lab._movement_preview.walk_speed, 100.0),
		"non-finite edits are rejected without changing the preview",
	)
	_expect(
		visual_lab._set_gameplay_value(&"walk_speed", 137.0) == OK
		and is_equal_approx(visual_lab._movement_preview.walk_speed, 135.0),
		"speed edits snap to increments of five",
	)
	_expect(
		visual_lab._set_gameplay_value(&"sprint_speed", 100000.0) == OK
		and is_equal_approx(visual_lab._movement_preview.sprint_speed, 500.0),
		"speed edits cannot exceed 500 px/s",
	)
	_expect(
		visual_lab._set_gameplay_value(&"standing_jump_height", -1000.0) == OK
		and is_equal_approx(visual_lab._movement_preview.standing_jump_height, 8.0),
		"jump heights cannot fall below 8 px",
	)
	_expect(
		visual_lab._set_gameplay_value(&"run_jump_distance", 100000.0) == OK
		and is_equal_approx(visual_lab._movement_preview.run_jump_distance, 160.0),
		"moving jump distances cannot exceed 160 px",
	)
	_expect(
		is_equal_approx(visual_lab._movement_standard.walk_speed, 100.0)
		and is_equal_approx(visual_lab._movement_standard.sprint_speed, 400.0)
		and is_equal_approx(visual_lab._movement_standard.standing_jump_height, 24.0)
		and is_equal_approx(visual_lab._movement_standard.run_jump_distance, 80.0),
		"preview edits leave every game-standard value unchanged",
	)
	var standard_text := FileAccess.get_file_as_string(MOVEMENT_TEST_PATH)
	_expect(
		not standard_text.contains("walk_speed = 135.0")
		and not standard_text.contains("sprint_speed = 500.0")
		and not standard_text.contains("standing_jump_height = 8.0")
		and not standard_text.contains("run_jump_distance = 160.0"),
		"preview edits do not write the versioned movement resource",
	)


func _expect_persisted_preview(visual_lab: Control) -> void:
	_expect(
		is_equal_approx(visual_lab._movement_preview.walk_speed, 135.0)
		and is_equal_approx(visual_lab._movement_preview.sprint_speed, 500.0)
		and is_equal_approx(visual_lab._movement_preview.standing_jump_height, 8.0)
		and is_equal_approx(visual_lab._movement_preview.run_jump_distance, 160.0),
		"a reopened laboratory restores all local Gameplay test values",
	)
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_TEST_PATH) == OK, "Gameplay settings file loads")
	_expect(
		settings.get_value("meta", "version", 0) == 4
		and is_equal_approx(settings.get_value("visual_lab", "walk_speed", 0.0), 135.0)
		and is_equal_approx(settings.get_value("visual_lab", "sprint_speed", 0.0), 500.0),
		"Gameplay previews use the current local settings format",
	)


func _expect_single_value_acceptance(visual_lab: Control) -> void:
	var walk_row := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/GameplayPage/Content/WalkSpeed"
	)
	var accept_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Acceptance/AcceptButton"
	) as Button
	_expect(walk_row != null and accept_button != null, "Gameplay acceptance controls exist")
	if walk_row == null or accept_button == null:
		return
	visual_lab._unhandled_input(_pressed_action(CONTROLS_ACTION))
	walk_row.call(&"grab_slider_focus")
	accept_button.pressed.emit()
	_expect(
		is_equal_approx(visual_lab._movement_standard.walk_speed, 135.0),
		"explicit acceptance writes the focused movement value",
	)
	_expect(
		is_equal_approx(visual_lab._movement_standard.sprint_speed, 400.0)
		and is_equal_approx(visual_lab._movement_standard.standing_jump_height, 24.0)
		and is_equal_approx(visual_lab._movement_standard.run_jump_distance, 80.0),
		"focused acceptance leaves other preview values out of the standard",
	)
	var standard_text := FileAccess.get_file_as_string(MOVEMENT_TEST_PATH)
	_expect(
		standard_text.contains("walk_speed = 135.0")
		and not standard_text.contains("sprint_speed = 500.0")
		and not standard_text.contains("standing_jump_height = 8.0")
		and not standard_text.contains("run_jump_distance = 160.0"),
		"only the focused property is persisted to the movement resource",
	)


func _write_movement_fixture() -> bool:
	var movement := HeroMovementConfigResource.new()
	var save_error := ResourceSaver.save(movement, MOVEMENT_TEST_PATH)
	_expect(save_error == OK, "isolated movement standard can be written")
	return save_error == OK


func _remember_project_settings() -> void:
	_had_settings_path_override = ProjectSettings.has_setting(
		SETTINGS_PATH_PROJECT_KEY
	)
	if _had_settings_path_override:
		_original_settings_path = ProjectSettings.get_setting(
			SETTINGS_PATH_PROJECT_KEY
		)
	_had_movement_path_override = ProjectSettings.has_setting(
		MOVEMENT_PATH_PROJECT_KEY
	)
	if _had_movement_path_override:
		_original_movement_path = ProjectSettings.get_setting(
			MOVEMENT_PATH_PROJECT_KEY
		)
	ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, SETTINGS_TEST_PATH)
	ProjectSettings.set_setting(MOVEMENT_PATH_PROJECT_KEY, MOVEMENT_TEST_PATH)


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


func _cleanup() -> void:
	_remove_test_files()
	if _had_settings_path_override:
		ProjectSettings.set_setting(
			SETTINGS_PATH_PROJECT_KEY,
			_original_settings_path,
		)
	else:
		ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, null)
	if _had_movement_path_override:
		ProjectSettings.set_setting(
			MOVEMENT_PATH_PROJECT_KEY,
			_original_movement_path,
		)
	else:
		ProjectSettings.set_setting(MOVEMENT_PATH_PROJECT_KEY, null)


func _remove_test_files() -> void:
	for resource_path in [SETTINGS_TEST_PATH, MOVEMENT_TEST_PATH]:
		if not FileAccess.file_exists(resource_path):
			continue
		var remove_error := DirAccess.remove_absolute(
			ProjectSettings.globalize_path(resource_path)
		)
		_expect(remove_error == OK, "isolated Gameplay test file can be removed")


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLab Gameplay: %s" % description)
