extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://test_scenes/visual_lab/visual_lab.tscn"
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_TEST_PATH := "user://visual_lab_hero_graphics_test.cfg"
const VARIANTS: Array[String] = [
	"comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low",
]
const FRAME_VALUES: Array[int] = [8, 10, 12, 14, 16]
const FPS_VALUES: Array[int] = [8, 10, 12, 14, 16]
const ACTIONS: Array[String] = ["stand", "slowwalk", "walk", "sneak", "run", "sprint", "jump"]
const DIRECTIONS: Array[String] = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null


func run(tree: SceneTree) -> PackedStringArray:
	_remember_and_set_test_path()
	_remove_test_settings()
	var packed_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "VisualLab scene loads")
	if packed_scene == null:
		_cleanup()
		return failures

	var visual_lab := await _open_visual_lab(tree, packed_scene)
	if visual_lab != null:
		await _test_menu_and_animation_matrix(tree, visual_lab)
		await _close_visual_lab(tree, visual_lab)

	var reopened := await _open_visual_lab(tree, packed_scene)
	if reopened != null:
		var sprite := _hero_sprite(reopened)
		_expect(
			sprite.sprite_frames.get_meta(&"hero_variant", "") == "pixel_low",
			"saved graphics variant reopens",
		)
		_expect(
			sprite.sprite_frames.get_meta(&"hero_frames", 0) == 16,
			"saved animation frames reopens",
		)
		_expect(
			sprite.sprite_frames.get_meta(&"hero_fps", 0) == 16,
			"saved animation FPS reopens",
		)
		await _close_visual_lab(tree, reopened)

	_write_legacy_settings()
	var migrated := await _open_visual_lab(tree, packed_scene)
	if migrated != null:
		var migrated_sprite := _hero_sprite(migrated)
		_expect(
			migrated_sprite.sprite_frames.get_meta(&"hero_variant", "") == "comic_high",
			"legacy settings migrate to Comic High",
		)
		_expect(
			migrated_sprite.sprite_frames.get_meta(&"hero_fps", 0) == 8,
			"legacy settings migrate to 8 FPS",
		)
		await _close_visual_lab(tree, migrated)

	_cleanup()
	return failures


func _test_menu_and_animation_matrix(tree: SceneTree, visual_lab: Control) -> void:
	var options := visual_lab.get_node(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/HeroGraphicsOptions"
	) as GridContainer
	var fps_options := visual_lab.get_node(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/HeroAnimationOptions/"
		+ "HeroFpsColumn/HeroFpsOptions"
	) as VBoxContainer
	var frame_options := visual_lab.get_node(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/HeroAnimationOptions/"
		+ "HeroFramesColumn/HeroFramesOptions"
	) as VBoxContainer
	_expect(
		options != null and options.get_child_count() == 5,
		"five graphics options exist",
	)
	_expect(
		fps_options != null and fps_options.get_child_count() == 6,
		"FPS column with New option exists",
	)
	_expect(
		frame_options != null and frame_options.get_child_count() == 5,
		"five frame options exist",
	)
	if options == null or frame_options == null or fps_options == null:
		return

	var hero := visual_lab.get_node("TestWorld/HeroCharacter") as CharacterBody2D
	var sprite := _hero_sprite(visual_lab)
	var controller := hero.get_node("AnimationController")
	controller.set_physics_process(false)
	for variant_index in range(VARIANTS.size()):
		(visual_lab as Object).call("_set_hero_graphics", variant_index)
		for frame_index in range(FRAME_VALUES.size()):
			(visual_lab as Object).call("_set_hero_frames", frame_index)
			await tree.process_frame
			_expect(
				sprite.sprite_frames.get_meta(&"hero_frames", 0) == FRAME_VALUES[frame_index],
				"frame metadata is current",
			)
			_expect(
				sprite.sprite_frames.get_meta(&"hero_fps", 0) == FRAME_VALUES[frame_index],
				"New uses frame count as temporary FPS",
			)
			for fps_index in range(FPS_VALUES.size()):
				(visual_lab as Object).call("_set_hero_fps", fps_index + 1)
				await tree.process_frame
				var frames := sprite.sprite_frames
				_expect(
					frames.get_meta(&"hero_variant", "") == VARIANTS[variant_index],
					"variant metadata is current",
				)
				_expect(
					frames.get_meta(&"hero_frames", 0) == FRAME_VALUES[frame_index],
					"frame metadata is current",
				)
				_expect(
					frames.get_meta(&"hero_fps", 0) == FPS_VALUES[fps_index],
					"FPS metadata is current",
				)
				_expect(
					frames.get_animation_names().size() == ACTIONS.size() * DIRECTIONS.size(),
					"full animation matrix exists",
				)
				for action in ACTIONS:
					for direction in DIRECTIONS:
						var name := StringName("%s_%s" % [action, direction])
						_expect(frames.has_animation(name), "%s exists" % name)
						if not frames.has_animation(name):
							continue
						var expected_count := (
							1 if action == "jump"
							else (12 if action == "sprint" else FRAME_VALUES[frame_index])
						)
						_expect(
							frames.get_frame_count(name) == expected_count,
							"%s uses its source frame count" % name,
						)
						_expect(
							frames.get_animation_loop(name) == (action != "jump"),
							"%s loop contract" % name,
						)
						var expected_speed := (
							12.0 if action == "sprint" else float(FPS_VALUES[fps_index])
						)
						_expect(
							is_equal_approx(frames.get_animation_speed(name), expected_speed),
							"%s playback FPS" % name,
						)
						_expect(
							(frames.get_meta(&"animation_layouts", {}) as Dictionary).has(name),
							"%s has layout" % name,
						)
	_expect_saved_settings("pixel_low", 16, 16)
	controller.set_physics_process(true)


func _hero_sprite(visual_lab: Control) -> AnimatedSprite2D:
	return visual_lab.get_node(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D


func _expect_saved_settings(variant: String, frames: int, fps: int) -> void:
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_TEST_PATH) == OK, "visual lab settings load")
	_expect(settings.get_value("meta", "version", 0) == 5, "settings use schema 5")
	_expect(
		settings.get_value("visual_lab", "hero_graphics", "") == variant,
		"graphics variant is saved",
	)
	_expect(
		settings.get_value("visual_lab", "hero_frames", "") == str(frames),
		"animation frames are saved",
	)
	_expect(
		settings.get_value("visual_lab", "hero_fps", "") == str(fps),
		"animation FPS is saved",
	)


func _write_legacy_settings() -> void:
	var settings := ConfigFile.new()
	settings.set_value("meta", "version", 4)
	settings.set_value("visual_lab", "camera_context", "world")
	_expect(settings.save(SETTINGS_TEST_PATH) == OK, "legacy settings fixture can be written")


func _open_visual_lab(tree: SceneTree, packed_scene: PackedScene) -> Control:
	var node := packed_scene.instantiate()
	_expect(node is Control, "VisualLab instantiates as Control")
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


func _remember_and_set_test_path() -> void:
	_had_settings_path_override = ProjectSettings.has_setting(SETTINGS_PATH_PROJECT_KEY)
	if _had_settings_path_override:
		_original_settings_path = ProjectSettings.get_setting(SETTINGS_PATH_PROJECT_KEY)
	ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, SETTINGS_TEST_PATH)


func _cleanup() -> void:
	_remove_test_settings()
	if _had_settings_path_override:
		ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, _original_settings_path)
	else:
		ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, null)


func _remove_test_settings() -> void:
	if FileAccess.file_exists(SETTINGS_TEST_PATH):
		DirAccess.remove_absolute(SETTINGS_TEST_PATH)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLabHeroGraphics: %s" % description)
