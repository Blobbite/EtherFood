extends RefCounted

const WORLD_STATE_SCENE_PATH := "res://scenes/dev/world_state_preview.tscn"
const VISUAL_LAB_SCENE_PATH := "res://scenes/dev/visual_lab.tscn"
const WORLD_STATE_PREVIEW_SCRIPT := preload("res://scenes/dev/world_state_preview.gd")
const HERO_SCRIPT := preload("res://scenes/gameplay/hero/hero_character.gd")
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_TEST_PATH := "user://visual_lab_atmosphere_test.cfg"
const CAMERA_ZOOMS: Array[float] = [0.75, 1.0, 1.5]
const ATMOSPHERE_SETTING_KEYS: Array[String] = [
	"damaged_fog",
	"damaged_light",
	"restored_fog",
	"restored_light",
]

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null


func run(tree: SceneTree) -> PackedStringArray:
	_remember_and_set_test_path()
	_remove_test_settings()
	_expect_removed_shortcuts()
	await _expect_preview_profiles(tree)
	await _expect_visual_lab_matrix(tree)
	_cleanup_test_path()
	return failures


func _expect_preview_profiles(tree: SceneTree) -> void:
	var packed_scene := load(WORLD_STATE_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "WorldStatePreview loads for atmosphere tests")
	if packed_scene == null:
		return
	var preview := packed_scene.instantiate() as WORLD_STATE_PREVIEW_SCRIPT
	_expect(preview != null, "WorldStatePreview instantiates for atmosphere tests")
	if preview == null:
		return
	tree.root.add_child(preview)
	await tree.process_frame

	_expect(
		preview.get_fog_variant_count(preview.WorldState.DAMAGED) == 3,
		"damaged state exposes three fog strengths",
	)
	_expect(
		preview.get_fog_variant_count(preview.WorldState.RESTORED) == 3,
		"restored state exposes three fog strengths",
	)
	_expect(
		preview.get_light_variant_count(preview.WorldState.DAMAGED) == 2,
		"damaged state exposes two light profiles",
	)
	_expect(
		preview.get_light_variant_count(preview.WorldState.RESTORED) == 2,
		"restored state exposes two light profiles",
	)

	_expect_state_profile_matrix(preview, preview.WorldState.DAMAGED)
	_expect_state_profile_matrix(preview, preview.WorldState.RESTORED)
	_expect_preferred_profile_difference(preview)
	_expect(
		preview.find_children("*", "CollisionObject2D", true, false).is_empty(),
		"atmosphere variants add no collision object",
	)
	preview.queue_free()
	await tree.process_frame


func _expect_state_profile_matrix(
	preview: WORLD_STATE_PREVIEW_SCRIPT,
	world_state: int,
) -> void:
	preview.set_world_state(world_state)
	var state_node := preview.damaged_state
	var fog_sprite := preview.damaged_fog
	var light_overlay := preview.damaged_light
	if world_state == preview.WorldState.RESTORED:
		state_node = preview.restored_state
		fog_sprite = preview.restored_fog
		light_overlay = preview.restored_light
	var state_transform := state_node.transform
	var fog_transform := fog_sprite.transform
	var fog_texture := fog_sprite.texture
	var light_polygon := light_overlay.polygon
	var previous_strength := -1.0
	var default_light := preview.get_default_light_variant(world_state)

	for fog_variant in range(preview.get_fog_variant_count(world_state)):
		preview.set_atmosphere_variants(fog_variant, default_light)
		var strength := preview.get_active_fog_strength()
		_expect(
			strength > previous_strength,
			"fog strengths increase monotonically for state %d" % world_state,
		)
		_expect(
			is_equal_approx(fog_sprite.self_modulate.a, strength),
			"fog strength controls only sprite opacity for state %d" % world_state,
		)
		_expect(
			not preview.get_active_fog_name().is_empty(),
			"every fog strength has a diagnostic name for state %d" % world_state,
		)
		previous_strength = strength

	var first_state_modulate := Color()
	var first_light_color := Color()
	for light_variant in range(preview.get_light_variant_count(world_state)):
		preview.set_atmosphere_variants(0, light_variant)
		_expect(
			state_node.modulate.is_equal_approx(preview.get_active_state_modulate()),
			"light profile applies its state modulation for state %d" % world_state,
		)
		_expect(
			light_overlay.color.is_equal_approx(preview.get_active_light_color()),
			"light profile applies its overlay color for state %d" % world_state,
		)
		_expect(
			not preview.get_active_light_name().is_empty()
			and not preview.get_active_brightness_name().is_empty()
			and not preview.get_active_contrast_name().is_empty()
			and not preview.get_active_color_mood().is_empty(),
			"every light profile exposes complete diagnostics for state %d" % world_state,
		)
		if light_variant == 0:
			first_state_modulate = preview.get_active_state_modulate()
			first_light_color = preview.get_active_light_color()
		else:
			_expect(
				not first_state_modulate.is_equal_approx(
					preview.get_active_state_modulate()
				),
				"light profiles use distinct modulation for state %d" % world_state,
			)
			_expect(
				not first_light_color.is_equal_approx(preview.get_active_light_color()),
				"light profiles use distinct overlays for state %d" % world_state,
			)

	var alpha_range := _texture_alpha_range(fog_texture)
	_expect(
		alpha_range.x <= 0.001 and alpha_range.y > 0.0 and alpha_range.y < 1.0,
		"fog texture stays patterned and translucent for state %d" % world_state,
	)
	var alpha_profile := _texture_alpha_profile(fog_texture)
	_expect(
		fog_texture != null and fog_texture.get_size() == preview.get_preview_size(),
		"fog texture covers the enlarged preview for state %d" % world_state,
	)
	_expect(
		int(alpha_profile["levels"]) >= 8,
		"fog texture uses graduated cloud density for state %d" % world_state,
	)
	_expect(
		float(alpha_profile["clear_ratio"]) >= 0.10
		and float(alpha_profile["mist_ratio"]) >= 0.25,
		"fog texture mixes clear gaps and cloudy banks for state %d" % world_state,
	)
	_expect(state_node.transform == state_transform, "atmosphere keeps state transform")
	_expect(fog_sprite.transform == fog_transform, "atmosphere keeps fog transform")
	_expect(fog_sprite.texture == fog_texture, "atmosphere keeps the existing fog asset")
	_expect(light_overlay.polygon == light_polygon, "atmosphere keeps light geometry")
	_expect(
		fog_sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
		"fog variant introduces no texture smoothing",
	)
	preview.set_atmosphere_variants(
		preview.get_default_fog_variant(world_state),
		preview.get_default_light_variant(world_state),
	)


func _expect_preferred_profile_difference(preview: WORLD_STATE_PREVIEW_SCRIPT) -> void:
	preview.set_world_state(preview.WorldState.DAMAGED)
	preview.set_atmosphere_variants(
		preview.get_default_fog_variant(preview.WorldState.DAMAGED),
		preview.get_default_light_variant(preview.WorldState.DAMAGED),
	)
	var damaged_fog := preview.get_active_fog_strength()
	var damaged_brightness := _color_luminance(preview.get_active_state_modulate())
	_expect(preview.get_active_fog_name() == "Mittel", "damaged preferred fog is medium")
	_expect(
		preview.get_active_light_name() == "Kühl und dunkel",
		"damaged preferred light is cool and dark",
	)
	preview.set_world_state(preview.WorldState.RESTORED)
	preview.set_atmosphere_variants(
		preview.get_default_fog_variant(preview.WorldState.RESTORED),
		preview.get_default_light_variant(preview.WorldState.RESTORED),
	)
	var restored_fog := preview.get_active_fog_strength()
	var restored_brightness := _color_luminance(preview.get_active_state_modulate())
	_expect(preview.get_active_fog_name() == "Gering", "restored preferred fog is low")
	_expect(
		preview.get_active_light_name() == "Warm und klar",
		"restored preferred light is warm and clear",
	)
	_expect(damaged_fog > restored_fog, "damaged preferred state has denser fog")
	_expect(
		damaged_brightness < restored_brightness,
		"damaged preferred state has darker ambient modulation",
	)


func _expect_visual_lab_matrix(tree: SceneTree) -> void:
	var packed_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "VisualLab loads for atmosphere matrix")
	if packed_scene == null:
		return
	var visual_lab := await _open_visual_lab(tree, packed_scene)
	if visual_lab == null:
		return
	var preview: WORLD_STATE_PREVIEW_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/WorldStatePreview"
	) as WORLD_STATE_PREVIEW_SCRIPT
	var fog_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/WorldPage/Content/FogStatus"
	) as Label
	var light_button := visual_lab.get_node_or_null(
		"InterfaceLayer/Interface/Menu/Pages/WorldPage/Content/LightStatus"
	) as Label
	var diagnostics := visual_lab.get_node_or_null(
		"InterfaceLayer/DiagnosticsPanel/Values"
	) as Label
	var camera := visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter/PlayerCamera"
	) as Camera2D
	var hero: HERO_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as HERO_SCRIPT
	var obstacle := visual_lab.get_node_or_null("TestWorld/TestObstacle") as StaticBody2D
	var obstacle_collision := visual_lab.get_node_or_null(
		"TestWorld/TestObstacle/CollisionShape2D"
	) as CollisionShape2D
	var collision_overlay := visual_lab.get_node_or_null(
		"TestWorld/CollisionDebugOverlay"
	) as Node2D
	_expect(preview != null, "VisualLab keeps its world-state preview")
	_expect(fog_button != null, "VisualLab exposes a fog variant button")
	_expect(light_button != null, "VisualLab exposes a light variant button")
	_expect(diagnostics != null, "VisualLab keeps its diagnostics values")
	_expect(camera != null, "VisualLab keeps its player camera")
	_expect(hero != null, "VisualLab keeps its controllable hero")
	_expect(obstacle != null, "VisualLab keeps its test obstacle")
	_expect(obstacle_collision != null, "VisualLab keeps its obstacle collision")
	_expect(collision_overlay != null, "VisualLab keeps its collision overlay")
	if (
		preview == null
		or fog_button == null
		or light_button == null
		or diagnostics == null
		or camera == null
		or hero == null
		or obstacle == null
		or obstacle_collision == null
		or collision_overlay == null
	):
		await _close_visual_lab(tree, visual_lab)
		return

	visual_lab._toggle_diagnostics()
	_expect_atmosphere_state(
		preview,
		fog_button,
		light_button,
		diagnostics,
		false,
		"Mittel",
		"Kühl und dunkel",
		"preferred damaged start",
	)
	visual_lab._unhandled_input(_pressed_key(KEY_B, true))
	_expect(preview.get_active_fog_name() == "Mittel", "removed B leaves fog unchanged")
	visual_lab._cycle_fog_variant()
	visual_lab._cycle_light_variant()
	_expect_atmosphere_state(
		preview,
		fog_button,
		light_button,
		diagnostics,
		false,
		"Hoch",
		"Kühl und gedämpft",
		"damaged alternatives",
	)
	_expect_saved_atmosphere("high", "cool_muted", "low", "warm_clear")

	visual_lab._toggle_world_state()
	_expect_atmosphere_state(
		preview,
		fog_button,
		light_button,
		diagnostics,
		true,
		"Gering",
		"Warm und klar",
		"preferred restored start",
	)
	visual_lab._cycle_fog_variant()
	visual_lab._cycle_light_variant()
	_expect_atmosphere_state(
		preview,
		fog_button,
		light_button,
		diagnostics,
		true,
		"Mittel",
		"Neutral und klar",
		"restored alternatives",
	)
	visual_lab._toggle_world_state()
	_expect(
		preview.get_active_fog_name() == "Hoch"
		and preview.get_active_light_name() == "Kühl und gedämpft",
		"world toggle restores damaged atmosphere selections",
	)

	_expect_zoom_and_variant_matrix(visual_lab, preview, camera, obstacle_collision)
	await _expect_collision_contract(tree, visual_lab, preview, hero, obstacle)
	visual_lab._toggle_collision_debug()
	visual_lab._toggle_world_state()
	visual_lab._cycle_fog_variant()
	_expect(
		collision_overlay.visible and collision_overlay.z_index > 5,
		"collision boundaries remain visible above every atmosphere layer",
	)
	visual_lab._selected_fog_variants[preview.WorldState.DAMAGED] = 2
	visual_lab._selected_light_variants[preview.WorldState.DAMAGED] = 0
	visual_lab._selected_fog_variants[preview.WorldState.RESTORED] = 0
	visual_lab._selected_light_variants[preview.WorldState.RESTORED] = 0
	visual_lab._selected_world_state = preview.WorldState.RESTORED
	visual_lab._apply_world_state()
	visual_lab._save_settings()
	await _close_visual_lab(tree, visual_lab)

	var reopened := await _open_visual_lab(tree, packed_scene)
	if reopened != null:
		var reopened_preview: WORLD_STATE_PREVIEW_SCRIPT = reopened.get_node_or_null(
			"TestWorld/WorldStatePreview"
		) as WORLD_STATE_PREVIEW_SCRIPT
		_expect(reopened_preview != null, "reopened lab keeps atmosphere preview")
		if reopened_preview != null:
			_expect(
				reopened_preview.is_restored()
				and reopened_preview.get_active_fog_name() == "Aus"
				and reopened_preview.get_active_light_name() == "Neutral und klar",
				"reopened lab restores active restored atmosphere",
			)
			reopened._toggle_world_state()
			_expect(
				reopened_preview.get_active_fog_name() == "Hoch"
				and reopened_preview.get_active_light_name() == "Kühl und gedämpft",
				"reopened lab retains inactive damaged atmosphere",
			)
		await _close_visual_lab(tree, reopened)

	_write_invalid_atmosphere_settings()
	var fallback := await _open_visual_lab(tree, packed_scene)
	if fallback != null:
		var fallback_preview: WORLD_STATE_PREVIEW_SCRIPT = fallback.get_node_or_null(
			"TestWorld/WorldStatePreview"
		) as WORLD_STATE_PREVIEW_SCRIPT
		_expect(
			fallback_preview != null
			and fallback_preview.get_active_fog_name() == "Mittel"
			and fallback_preview.get_active_light_name() == "Kühl und dunkel",
			"invalid atmosphere IDs fall back to preferred damaged variants",
		)
		await _close_visual_lab(tree, fallback)


func _expect_zoom_and_variant_matrix(
	visual_lab: Control,
	preview: WORLD_STATE_PREVIEW_SCRIPT,
	camera: Camera2D,
	obstacle_collision: CollisionShape2D,
) -> void:
	var preview_transform := preview.transform
	var collision_shape := obstacle_collision.shape
	var collision_transform := obstacle_collision.transform
	for zoom_index in range(CAMERA_ZOOMS.size()):
		visual_lab._selected_camera_zoom = zoom_index
		visual_lab._apply_camera_zoom()
		_expect(
			camera.zoom == Vector2.ONE * CAMERA_ZOOMS[zoom_index],
			"atmosphere matrix keeps zoom %d exact" % zoom_index,
		)
		for world_state in range(2):
			visual_lab._selected_world_state = world_state
			visual_lab._apply_world_state()
			for fog_variant in range(preview.get_fog_variant_count(world_state)):
				for light_variant in range(
					preview.get_light_variant_count(world_state)
				):
					visual_lab._selected_fog_variants[world_state] = fog_variant
					visual_lab._selected_light_variants[world_state] = light_variant
					visual_lab._apply_atmosphere()
					_expect(
						preview.transform == preview_transform,
						"atmosphere matrix keeps preview transform",
					)
					_expect(
						obstacle_collision.shape == collision_shape
						and obstacle_collision.transform == collision_transform,
						"atmosphere matrix keeps collision geometry",
					)


func _expect_collision_contract(
	tree: SceneTree,
	visual_lab: Control,
	preview: WORLD_STATE_PREVIEW_SCRIPT,
	hero: HERO_SCRIPT,
	obstacle: StaticBody2D,
) -> void:
	visual_lab.get_node("LabNavigation").call(&"enter_room", &"objects")
	visual_lab._selected_camera_zoom = 1
	visual_lab._apply_camera_zoom()
	for world_state in range(2):
		visual_lab._selected_world_state = world_state
		visual_lab._selected_fog_variants[world_state] = (
			preview.get_default_fog_variant(world_state)
		)
		visual_lab._selected_light_variants[world_state] = (
			preview.get_default_light_variant(world_state)
		)
		visual_lab._apply_world_state()
		var start_x := obstacle.global_position.x - 160.0
		hero.global_position = Vector2(start_x, obstacle.global_position.y)
		Input.action_press(&"gameplay_move_right")
		for _frame in range(30):
			await tree.physics_frame
		Input.action_release(&"gameplay_move_right")
		_expect(
			hero.global_position.x > start_x
			and hero.global_position.x <= obstacle.global_position.x - 88.5,
			"test obstacle blocks movement in atmosphere state %d" % world_state,
		)


func _expect_atmosphere_state(
	preview: WORLD_STATE_PREVIEW_SCRIPT,
	fog_button: Label,
	light_button: Label,
	diagnostics: Label,
	expected_restored: bool,
	expected_fog: String,
	expected_light: String,
	description: String,
) -> void:
	_expect(preview.is_restored() == expected_restored, "%s: world state" % description)
	_expect(preview.get_active_fog_name() == expected_fog, "%s: fog" % description)
	_expect(preview.get_active_light_name() == expected_light, "%s: light" % description)
	_expect(fog_button.text == "Nebel: %s" % expected_fog, "%s: fog status" % description)
	_expect(
		light_button.text == "Licht: %s" % expected_light,
		"%s: light status" % description,
	)
	_expect(
		diagnostics.text.contains("Nebel: %s" % expected_fog),
		"%s: fog diagnostic" % description,
	)
	_expect(
		diagnostics.text.contains("Lichtprofil: %s" % expected_light),
		"%s: light diagnostic" % description,
	)


func _texture_alpha_range(texture: Texture2D) -> Vector2:
	if texture == null:
		return Vector2(1.0, 1.0)
	var image := texture.get_image()
	if image == null or image.is_empty():
		return Vector2(1.0, 1.0)
	var minimum_alpha := 1.0
	var maximum_alpha := 0.0
	for y in range(0, image.get_height(), 4):
		for x in range(0, image.get_width(), 4):
			var alpha := image.get_pixel(x, y).a
			minimum_alpha = minf(minimum_alpha, alpha)
			maximum_alpha = maxf(maximum_alpha, alpha)
	return Vector2(minimum_alpha, maximum_alpha)


func _texture_alpha_profile(texture: Texture2D) -> Dictionary:
	if texture == null:
		return {"levels": 0, "clear_ratio": 0.0, "mist_ratio": 0.0}
	var image := texture.get_image()
	if image == null or image.is_empty():
		return {"levels": 0, "clear_ratio": 0.0, "mist_ratio": 0.0}
	var sampled_levels: Dictionary = {}
	var clear_samples := 0
	var mist_samples := 0
	var sample_count := 0
	for y in range(0, image.get_height(), 8):
		for x in range(0, image.get_width(), 8):
			var alpha := image.get_pixel(x, y).a
			sampled_levels[roundi(alpha * 255.0)] = true
			if alpha <= 0.02:
				clear_samples += 1
			if alpha >= 0.08:
				mist_samples += 1
			sample_count += 1
	return {
		"levels": sampled_levels.size(),
		"clear_ratio": float(clear_samples) / float(sample_count),
		"mist_ratio": float(mist_samples) / float(sample_count),
	}


func _color_luminance(color: Color) -> float:
	return color.r * 0.2126 + color.g * 0.7152 + color.b * 0.0722


func _expect_removed_shortcuts() -> void:
	_expect(
		not InputMap.has_action(&"dev_fog_variant_cycle"),
		"fog direct action is absent",
	)
	_expect(
		not InputMap.has_action(&"dev_light_variant_cycle"),
		"light direct action is absent",
	)


func _expect_saved_atmosphere(
	damaged_fog: String,
	damaged_light: String,
	restored_fog: String,
	restored_light: String,
) -> void:
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_TEST_PATH) == OK, "atmosphere preset loads")
	var expected_values: Array[String] = [
		damaged_fog,
		damaged_light,
		restored_fog,
		restored_light,
	]
	for setting_index in range(ATMOSPHERE_SETTING_KEYS.size()):
		_expect(
			settings.get_value(
				"visual_lab",
				ATMOSPHERE_SETTING_KEYS[setting_index],
				"",
			) == expected_values[setting_index],
			"preset stores %s" % ATMOSPHERE_SETTING_KEYS[setting_index],
		)


func _write_invalid_atmosphere_settings() -> void:
	var settings := ConfigFile.new()
	settings.set_value("meta", "version", 1)
	settings.set_value("visual_lab", "world_state", "damaged")
	for setting_key in ATMOSPHERE_SETTING_KEYS:
		settings.set_value("visual_lab", setting_key, "unknown")
	_expect(settings.save(SETTINGS_TEST_PATH) == OK, "invalid atmosphere fixture saves")


func _pressed_key(keycode: Key, echo: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.device = InputEvent.DEVICE_ID_KEYBOARD
	event.physical_keycode = keycode
	event.pressed = true
	event.echo = echo
	return event


func _open_visual_lab(tree: SceneTree, packed_scene: PackedScene) -> Control:
	var node := packed_scene.instantiate()
	_expect(node is Control, "VisualLab instantiates for atmosphere matrix")
	if not node is Control:
		if node != null:
			node.free()
		return null
	var visual_lab := node as Control
	tree.root.add_child(visual_lab)
	visual_lab.get_node("LabNavigation").call(&"enter_room", &"fog")
	await tree.process_frame
	await tree.physics_frame
	return visual_lab


func _close_visual_lab(tree: SceneTree, visual_lab: Control) -> void:
	Input.action_release(&"gameplay_move_right")
	visual_lab.queue_free()
	await tree.process_frame


func _remember_and_set_test_path() -> void:
	_had_settings_path_override = ProjectSettings.has_setting(SETTINGS_PATH_PROJECT_KEY)
	if _had_settings_path_override:
		_original_settings_path = ProjectSettings.get_setting(SETTINGS_PATH_PROJECT_KEY)
	ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, SETTINGS_TEST_PATH)


func _cleanup_test_path() -> void:
	_remove_test_settings()
	if _had_settings_path_override:
		ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, _original_settings_path)
	else:
		ProjectSettings.set_setting(SETTINGS_PATH_PROJECT_KEY, null)


func _remove_test_settings() -> void:
	if FileAccess.file_exists(SETTINGS_TEST_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_TEST_PATH))


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLab atmosphere: %s" % description)
