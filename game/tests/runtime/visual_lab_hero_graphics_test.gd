extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://scenes/dev/visual_lab.tscn"
const ULTRA_FRAMES_PATH := (
	"res://tests/assets/characters/heroes/green_hero/ultra/"
	+ "green_hero_stand_walk_ultra.tres"
)
const PIXEL_ART_FRAMES_PATH := (
	"res://tests/assets/characters/heroes/green_hero/pixel_art/"
	+ "green_hero_stand_walk_pixel_art.tres"
)
const HD_FRAMES_PATH := (
	"res://tests/assets/characters/heroes/green_hero/hd/green_hero_stand_walk_hd.tres"
)
const TEST_FRAMES_PATH := (
	"res://tests/assets/characters/heroes/green_hero/test/green_hero_stand_walk_test.tres"
)
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_TEST_PATH := "user://visual_lab_hero_graphics_test.cfg"
const HERO_GRAPHICS_SETTING := &"hero_graphics"
const EXPECTED_ANIMATIONS: Array[StringName] = [
	&"stand_N",
	&"stand_NO",
	&"stand_O",
	&"stand_SO",
	&"stand_S",
	&"stand_SW",
	&"stand_W",
	&"stand_NW",
	&"walk_N",
	&"walk_NO",
	&"walk_O",
	&"walk_SO",
	&"walk_S",
	&"walk_SW",
	&"walk_W",
	&"walk_NW",
]
const DIRECTION_SUFFIXES: Array[String] = [
	"N",
	"NO",
	"O",
	"SO",
	"S",
	"SW",
	"W",
	"NW",
]
const ULTRA_TEXTURE_SCALE := Vector2(80.0 / 1205.0, 80.0 / 1205.0)
const PIXEL_ART_TEXTURE_SCALE := Vector2(80.0 / 245.0, 80.0 / 245.0)

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null


func run(tree: SceneTree) -> PackedStringArray:
	_remember_and_set_test_path()
	_remove_test_settings()
	var pixel_art_frames := load(PIXEL_ART_FRAMES_PATH) as SpriteFrames
	_expect_pixel_art_resource(pixel_art_frames)

	var packed_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "VisualLab scene loads")
	if packed_scene == null:
		_cleanup()
		return failures

	var visual_lab := await _open_visual_lab(tree, packed_scene)
	if visual_lab != null:
		await _expect_graphics_switch(tree, visual_lab, pixel_art_frames)
		await _expect_additional_variants(tree, visual_lab)
		await _close_visual_lab(tree, visual_lab)

	var reopened := await _open_visual_lab(tree, packed_scene)
	if reopened != null:
		_expect_active_variant(
			reopened,
			PIXEL_ART_FRAMES_PATH,
			PIXEL_ART_TEXTURE_SCALE,
			Vector2(0.0, -122.5),
			"Hero-Grafik: Pixel Art · 1 Standbild je Richtung · 265 × 265 px",
			"saved Pixelart variant reopens",
		)
		await _close_visual_lab(tree, reopened)

	for variant_id in ["hd", "test"]:
		var settings := ConfigFile.new()
		settings.set_value("meta", "version", 4)
		settings.set_value("visual_lab", "hero_graphics", variant_id)
		settings.save(SETTINGS_TEST_PATH)
		var restored := await _open_visual_lab(tree, packed_scene)
		if restored != null:
			var sprite := restored.get_node(
				"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
			) as AnimatedSprite2D
			var expected_path := HD_FRAMES_PATH if variant_id == "hd" else TEST_FRAMES_PATH
			_expect(sprite.sprite_frames.resource_path == expected_path, "%s reopens" % variant_id)
			_expect_saved_variant(variant_id)
			await _close_visual_lab(tree, restored)

	_write_version_three_settings()
	var migrated := await _open_visual_lab(tree, packed_scene)
	if migrated != null:
		_expect_active_variant(
			migrated,
			ULTRA_FRAMES_PATH,
			ULTRA_TEXTURE_SCALE,
			Vector2(0.0, -597.0),
			"Hero-Grafik: Ultra · 16 Frames je Richtung · 1254 × 1254 px Standreferenz",
			"schema 3 settings migrate to the safe Ultra default",
		)
		_expect_saved_variant("ultra")
		await _close_visual_lab(tree, migrated)

	_cleanup()
	return failures


func _expect_additional_variants(tree: SceneTree, visual_lab: Control) -> void:
	var options := visual_lab.get_node(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/HeroGraphicsOptions"
	) as GridContainer
	_expect(options != null and options.columns == 2, "four variants fit into two columns")
	if options == null:
		return
	var hero := visual_lab.get_node("TestWorld/HeroCharacter") as CharacterBody2D
	var controller := hero.get_node("AnimationController")
	var texture_scale := hero.get_node("Visual/JumpVisual/Appearance/TextureScale") as Node2D
	var sprite := texture_scale.get_node("HeroSprite") as AnimatedSprite2D
	var position_before := hero.position
	var collision := hero.get_node("CollisionShape2D") as CollisionShape2D
	var shape_before := collision.shape
	controller.set_physics_process(false)
	var cases := [
		["HdButton", "hd", HD_FRAMES_PATH],
		["TestButton", "test", TEST_FRAMES_PATH],
	]
	for item in cases:
		var button := options.get_node_or_null(str(item[0])) as Button
		_expect(button != null, "%s button exists" % item[1])
		if button == null:
			continue
		button.pressed.emit()
		await tree.process_frame
		_expect(sprite.sprite_frames.resource_path == item[2], "%s selects its resource" % item[1])
		_expect_saved_variant(str(item[1]))
		_expect(button.text.contains("●"), "%s is marked as selected" % item[1])
		_expect(
			button.position.x + button.size.x <= options.size.x + 1.0,
			"%s button fits inside the menu" % item[1],
		)
		var layouts := sprite.sprite_frames.get_meta(&"animation_layouts", {}) as Dictionary
		for direction_index in range(DIRECTION_SUFFIXES.size()):
			hero.set("animation_direction", direction_index)
			for action in [&"stand", &"walk"]:
				controller.call(&"_apply_animation", action, false)
				var expected := StringName("%s_%s" % [action, DIRECTION_SUFFIXES[direction_index]])
				_expect(sprite.animation == expected, "%s supports %s" % [item[1], expected])
				_expect(
					sprite.is_playing() == (item[1] != "test"),
					"%s uses its pose playback for %s" % [item[1], expected],
				)
				var layout := layouts.get(expected, {}) as Dictionary
				_expect(not layout.is_empty(), "%s has layout data" % expected)
				if not layout.is_empty():
					_expect(texture_scale.scale == layout["scale"], "%s uses its scale" % expected)
					_expect(sprite.offset == layout["offset"], "%s uses its foot anchor" % expected)
		_expect(hero.position == position_before, "%s preserves hero position" % item[1])
		_expect(collision.shape == shape_before, "%s preserves collision geometry" % item[1])
		if item[1] == "test":
			var speed_before := sprite.sprite_frames.get_animation_speed(&"stand_S")
			sprite.sprite_frames.set_animation_speed(&"stand_S", 99.0)
			button.pressed.emit()
			_expect(
				is_equal_approx(sprite.sprite_frames.get_animation_speed(&"stand_S"), speed_before),
				"selecting Testversion again reloads its resource from disk",
			)
			hero.set("animation_direction", 1)
			controller.call(&"_apply_animation", &"jump", false)
			_expect(sprite.animation == &"jump_NO", "Testversion exposes its jump pose")
			(options.get_node("UltraButton") as Button).pressed.emit()
			_expect(
				sprite.animation == &"stand_NO",
				"switching away from a test-only pose preserves the facing direction",
			)
	var pixel_art_button := options.get_node("PixelArtButton") as Button
	pixel_art_button.pressed.emit()
	controller.set_physics_process(true)


func _expect_pixel_art_resource(sprite_frames: SpriteFrames) -> void:
	_expect(sprite_frames != null, "Pixelart SpriteFrames resource loads")
	if sprite_frames == null:
		return
	var actual_names := sprite_frames.get_animation_names()
	_expect(actual_names.size() == 16, "Pixelart resource has exactly 16 animations")
	for animation_name in EXPECTED_ANIMATIONS:
		_expect(
			actual_names.has(animation_name),
			"Pixelart resource contains %s" % animation_name,
		)
		_expect(
			sprite_frames.get_frame_count(animation_name) == 1,
			"%s contains one still frame" % animation_name,
		)
		_expect(
			sprite_frames.get_animation_loop(animation_name),
			"%s loops" % animation_name,
		)
		var texture := sprite_frames.get_frame_texture(animation_name, 0)
		_expect(texture != null, "%s has a texture" % animation_name)
		if texture != null:
			_expect(
				texture.get_size() == Vector2(265.0, 265.0),
				"%s keeps the 265 x 265 canvas" % animation_name,
			)


func _expect_graphics_switch(
	tree: SceneTree,
	visual_lab: Control,
	pixel_art_frames: SpriteFrames,
) -> void:
	var interface := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface"
	) as MarginContainer
	var rendering_tab := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/ThemeTabs/RenderingTab"
	) as Button
	var ultra_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/"
		+ "HeroGraphicsOptions/UltraButton"
	) as Button
	var pixel_art_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/"
		+ "HeroGraphicsOptions/PixelArtButton"
	) as Button
	var accept_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Acceptance/AcceptButton"
	) as Button
	var hero := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as CharacterBody2D
	var controller := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/AnimationController"
	)

	_expect(interface != null, "graphics comparison has the F5 interface")
	_expect(rendering_tab != null, "graphics comparison is in Darstellung")
	_expect(ultra_button != null, "graphics comparison exposes Ultra")
	_expect(pixel_art_button != null, "graphics comparison exposes Pixelart")
	_expect(accept_button != null, "graphics comparison keeps the acceptance control")
	_expect(hero != null, "graphics comparison has a controllable hero")
	_expect(controller != null, "graphics comparison keeps the animation controller")
	if (
		interface == null
		or rendering_tab == null
		or ultra_button == null
		or pixel_art_button == null
		or accept_button == null
		or hero == null
		or controller == null
	):
		return

	_expect_active_variant(
		visual_lab,
		ULTRA_FRAMES_PATH,
		ULTRA_TEXTURE_SCALE,
		Vector2(0.0, -597.0),
		"Hero-Grafik: Ultra · 16 Frames je Richtung · 1254 × 1254 px Standreferenz",
		"VisualLab starts with Ultra",
	)
	visual_lab._set_controls_visible(true)
	rendering_tab.pressed.emit()
	pixel_art_button.pressed.emit()
	await tree.process_frame
	_expect_active_variant(
		visual_lab,
		PIXEL_ART_FRAMES_PATH,
		PIXEL_ART_TEXTURE_SCALE,
		Vector2(0.0, -122.5),
		"Hero-Grafik: Pixel Art · 1 Standbild je Richtung · 265 × 265 px",
		"Pixelart button switches immediately",
	)
	_expect(
		pixel_art_button.text.contains("●") and not pixel_art_button.text.contains("★"),
		"Pixelart is marked only as the current test value",
	)
	pixel_art_button.grab_focus()
	await tree.process_frame
	_expect(accept_button.disabled, "Pixelart cannot be accepted as a game standard")
	_expect(
		interface.get_current_index(HERO_GRAPHICS_SETTING) == 1,
		"menu reports Pixelart as selected",
	)
	_expect_saved_variant("pixel_art")
	_expect_directional_stills(hero, controller, pixel_art_frames)

	ultra_button.pressed.emit()
	await tree.process_frame
	_expect_active_variant(
		visual_lab,
		ULTRA_FRAMES_PATH,
		ULTRA_TEXTURE_SCALE,
		Vector2(0.0, -597.0),
		"Hero-Grafik: Ultra · 16 Frames je Richtung · 1254 × 1254 px Standreferenz",
		"Ultra button restores the test pose resource",
	)
	pixel_art_button.pressed.emit()
	await tree.process_frame
	_expect_saved_variant("pixel_art")

	controller.set_physics_process(false)
	controller.call(&"_apply_animation", &"walk", false)
	var position_before_switch := hero.position
	ultra_button.pressed.emit()
	_expect_active_variant(
		visual_lab,
		ULTRA_FRAMES_PATH,
		ULTRA_TEXTURE_SCALE,
		Vector2(0.0, -597.0),
		"Hero-Grafik: Ultra · 16 Frames je Richtung · 1254 × 1254 px Standreferenz",
		"switching graphics during walking uses the shared Ultra pose scale",
	)
	pixel_art_button.pressed.emit()
	_expect_active_variant(
		visual_lab,
		PIXEL_ART_FRAMES_PATH,
		PIXEL_ART_TEXTURE_SCALE,
		Vector2(0.0, -122.5),
		"Hero-Grafik: Pixel Art · 1 Standbild je Richtung · 265 × 265 px",
		"switching back during walking restores the Pixelart scale",
	)
	_expect(hero.position == position_before_switch, "graphics switches preserve hero position")
	controller.set_physics_process(true)


func _expect_directional_stills(
	hero: CharacterBody2D,
	controller: Node,
	pixel_art_frames: SpriteFrames,
) -> void:
	var sprite := hero.get_node_or_null(
		"Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	_expect(sprite != null, "direction test has the hero sprite")
	if sprite == null:
		return
	for direction_index in range(DIRECTION_SUFFIXES.size()):
		hero.set("animation_direction", direction_index)
		var suffix := DIRECTION_SUFFIXES[direction_index]
		for action in ["stand", "walk"]:
			controller.call(&"_apply_animation", StringName(action), false)
			var expected_name := StringName("%s_%s" % [action, suffix])
			_expect(sprite.animation == expected_name, "%s can be selected" % expected_name)
			_expect(
				sprite.sprite_frames == pixel_art_frames,
				"%s stays on the Pixelart resource" % expected_name,
			)
			_expect(sprite.frame == 0, "%s displays its still frame" % expected_name)


func _expect_active_variant(
	visual_lab: Control,
	expected_resource_path: String,
	expected_scale: Vector2,
	expected_offset: Vector2,
	expected_status: String,
	description: String,
) -> void:
	var texture_scale := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale"
	) as Node2D
	var sprite := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
	) as AnimatedSprite2D
	var status := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/RenderingPage/Content/HeroGraphicsStatus"
	) as Label
	_expect(texture_scale != null, "%s: texture scale exists" % description)
	_expect(sprite != null, "%s: hero sprite exists" % description)
	_expect(status != null, "%s: status exists" % description)
	if texture_scale == null or sprite == null or status == null:
		return
	_expect(
		texture_scale.scale.is_equal_approx(expected_scale),
		"%s: visible height normalization" % description,
	)
	_expect(sprite.offset.is_equal_approx(expected_offset), "%s: foot anchor" % description)
	_expect(
		sprite.sprite_frames.resource_path == expected_resource_path,
		"%s: selected SpriteFrames" % description,
	)
	_expect(status.text == expected_status, "%s: status text" % description)


func _expect_saved_variant(expected_id: String) -> void:
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_TEST_PATH) == OK, "graphics settings file loads")
	_expect(settings.get_value("meta", "version", 0) == 4, "settings use schema 4")
	_expect(
		settings.get_value("visual_lab", "hero_graphics", "") == expected_id,
		"selected graphics ID is saved locally",
	)


func _write_version_three_settings() -> void:
	var settings := ConfigFile.new()
	settings.set_value("meta", "version", 3)
	settings.set_value("visual_lab", "camera_context", "world")
	_expect(
		settings.save(SETTINGS_TEST_PATH) == OK,
		"schema 3 migration fixture can be written",
	)


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
