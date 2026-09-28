extends RefCounted

const LAB_SCENE := preload("res://test_scenes/visual_lab/visual_lab.tscn")
const LabScript := preload("res://test_scenes/visual_lab/visual_lab.gd")
const HeroScript := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const PortalGraphics := preload("res://test_scenes/environment/portal_lab/portal_graphics.gd")
const TestRoom := preload("res://test_scenes/environment/portal_lab/test_room.gd")
const SETTINGS_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_PATH := "user://portal_lab_graphics_test.cfg"
const CONTENT_PATH := "Menu/Pages/RenderingPage/Content/"
const ROOM_IDS: Array[StringName] = [
	&"lamps", &"monsters", &"shaders", &"objects", &"particles",
	&"fog", &"day_night", &"world_state", &"sprites",
]
const GRAPHICS_OPTIONS := [
	["ComicHighButton", &"comic_high", "Comic High"],
	["ComicMidButton", &"comic_mid", "Comic Mittel"],
	["ComicLowButton", &"comic_low", "Comic Low"],
	["PixelHighButton", &"pixel_high", "Pixel Art High"],
	["PixelLowButton", &"pixel_low", "Pixel Art Low"],
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	var had_override := ProjectSettings.has_setting(SETTINGS_KEY)
	var previous: Variant = ProjectSettings.get_setting(SETTINGS_KEY, null)
	ProjectSettings.set_setting(SETTINGS_KEY, SETTINGS_PATH)
	_remove_settings()
	for action in HeroScript.MOVEMENT_ACTIONS:
		Input.action_release(action)
	var lab := LAB_SCENE.instantiate() as LabScript
	tree.root.add_child(lab)
	await tree.process_frame
	_test_f5_switch(lab)
	_test_floor_motifs(lab)
	_test_room_variants(lab)
	_select_graphics(lab, "PixelHighButton")
	lab.queue_free()
	await tree.process_frame
	lab = LAB_SCENE.instantiate() as LabScript
	tree.root.add_child(lab)
	await tree.process_frame
	_expect(lab._selected_hero_graphics == lab.HeroGraphicsPreset.PIXEL_HIGH,
		"restart restores the common graphics choice")
	_expect_room_textures(lab.lab_navigation.current_room, &"pixel_high", "stone_grid")
	_expect(lab.controls_interface.temple_floor_option.selected == 8,
		"restart restores the selected floor in the F5 menu")
	lab.lab_navigation.enter_room(&"particles")
	_expect_room_textures(lab.lab_navigation.current_room, &"pixel_high", "stone_grid")
	_select_graphics(lab, "ComicLowButton")
	lab.queue_free()
	await tree.process_frame
	lab = LAB_SCENE.instantiate() as LabScript
	tree.root.add_child(lab)
	await tree.process_frame
	_expect(lab._selected_hero_graphics == lab.HeroGraphicsPreset.COMIC_LOW,
		"restart also restores the comic variant")
	_expect_room_textures(lab.lab_navigation.current_room, &"comic_low", "stone_grid")
	lab.queue_free()
	await tree.process_frame
	for invalid_motif: Variant in ["unknown_motif", 42]:
		var settings := ConfigFile.new()
		settings.set_value("meta", "version", LabScript.SETTINGS_VERSION)
		settings.set_value(LabScript.SETTINGS_SECTION, "temple_floor", invalid_motif)
		_expect(settings.save(SETTINGS_PATH) == OK, "invalid-motif fixture is saved")
		lab = LAB_SCENE.instantiate() as LabScript
		tree.root.add_child(lab)
		await tree.process_frame
		_expect(lab.lab_navigation.current_room.floor_grid.floor_id == "ornate",
			"unknown or wrongly typed saved motifs use the default")
		_expect(lab.controls_interface.temple_floor_option.selected == 0,
			"invalid saved motifs show the default in F5")
		lab.queue_free()
		await tree.process_frame
	_remove_settings()
	ProjectSettings.set_setting(SETTINGS_KEY, previous if had_override else null)
	return failures


func _test_f5_switch(lab: LabScript) -> void:
	lab._set_controls_visible(true)
	(lab.controls_interface.get_node("Menu/ThemeTabs/RenderingTab") as Button).pressed.emit()
	_expect(lab.controls_interface.portal_graphics_status.is_visible_in_tree(),
		"F5 rendering page shows the portal graphics status")
	lab._set_tile_size(lab.TileSizePreset.LARGE)
	lab._set_texture_filter(lab.TextureFilterPreset.SOFT)
	var room := lab.lab_navigation.current_room
	var hero_position := lab.hero_character.position
	var camera_zoom := lab.player_camera.zoom
	var movement := lab.hero_character.movement_config
	var pixel_snap := lab._pixel_snap_enabled
	var floor_size := room.floor_grid.world_size
	var floor_radius := room.floor_grid.radius
	var boundary := room.get_node("TowerBoundary")
	for option in GRAPHICS_OPTIONS:
		_select_graphics(lab, option[0] as String)
		_expect(lab.HERO_GRAPHICS_IDS[lab._selected_hero_graphics] == option[1],
			"F5 also switches the hero")
		_expect_room_textures(room, option[1] as StringName)
		_expect(lab.controls_interface.portal_graphics_status.text.contains(option[2]),
			"F5 identifies the actual temple resolution")
		_expect(room.floor_grid.world_size == floor_size and room.floor_grid.radius == floor_radius,
			"different native resolutions occupy the same floor area")
		_expect(room.get_node("TowerBoundary") == boundary, "temple switch preserves collisions")
		_expect(lab.lab_navigation.current_room == room, "graphics switch keeps the active room")
		_expect(lab.hero_character.position == hero_position, "graphics switch never teleports")
		_expect(lab.hero_character.movement_config == movement, "movement settings are preserved")
		_expect(lab.player_camera.zoom == camera_zoom, "camera zoom is preserved")
		_expect(lab._pixel_snap_enabled == pixel_snap, "pixel snap is independent of graphics")
		_expect(room.floor_grid.tile_size == 64, "chosen floor grid is preserved")
		_expect(room.floor_grid.texture_filter == CanvasItem.TEXTURE_FILTER_LINEAR,
			"independent soft filter remains active on the blueprint floor")
		for portal in room.portals.get_children():
			var sprite := portal.get_node("Door") as Sprite2D
			_expect(sprite.texture_filter == CanvasItem.TEXTURE_FILTER_LINEAR,
				"independent soft filter remains active on the doors")
			var shape := portal.get_node("Threshold").shape as RectangleShape2D
			_expect(shape.size == Vector2(96, 52), "texture changes never resize portal thresholds")
	lab._set_controls_visible(false)


func _test_floor_motifs(lab: LabScript) -> void:
	lab._set_controls_visible(true)
	(lab.controls_interface.get_node("Menu/ThemeTabs/RenderingTab") as Button).pressed.emit()
	var selector := lab.controls_interface.temple_floor_option
	_expect(selector.is_visible_in_tree(), "F5 offers the temple floor selector")
	_expect(selector.item_count == 9, "all nine supplied floor motifs are selectable")
	var room := lab.lab_navigation.current_room
	var hero_position := lab.hero_character.position
	for motif in [
		"ornate", "plain", "cyan_ornate", "cyan_panels", "framed_stone",
		"octagonal_stone", "riveted_metal", "staggered_stone", "stone_grid",
	]:
		var index := PortalGraphics.FLOOR_IDS.find(motif)
		selector.select(index)
		selector.item_selected.emit(index)
		for option in GRAPHICS_OPTIONS:
			_select_graphics(lab, option[0] as String)
			_expect_room_textures(room, option[1] as StringName, motif)
			_expect(room.floor_grid.texture_filter == CanvasItem.TEXTURE_FILTER_LINEAR,
				"motif and resolution switches preserve the independent filter")
		_expect(lab.lab_navigation.current_room == room, "floor motif keeps the room instance")
		_expect(lab.hero_character.position == hero_position, "floor motif keeps the hero position")
		var settings := ConfigFile.new()
		_expect(settings.load(SETTINGS_PATH) == OK, "F5 saves the floor choice")
		_expect(settings.get_value(LabScript.SETTINGS_SECTION, "temple_floor") == motif,
			"floor settings store the stable motif ID")
	_expect(not lab._setting_is_acceptable(&"temple_floor"),
		"comparing a temple motif does not approve a game standard")
	lab._set_controls_visible(false)


func _test_room_variants(lab: LabScript) -> void:
	_select_graphics(lab, "PixelHighButton")
	for room_id in ROOM_IDS:
		lab.lab_navigation.enter_room(room_id)
		var room := lab.lab_navigation.current_room
		_expect_room_textures(room, &"pixel_high", "stone_grid")
		if room_id == &"lamps":
			room.activate_control(&"lamps")
		elif room_id == &"particles":
			room.activate_control(&"particles")
		elif room_id == &"day_night":
			room.activate_control(&"night")
		var local_state := room.get_local_state()
		var gallery_frames: Array[SpriteFrames] = []
		for node in room.contents.get_children():
			if node is AnimatedSprite2D:
				gallery_frames.append(node.sprite_frames)
		for option in GRAPHICS_OPTIONS:
			_select_graphics(lab, option[0] as String)
			_expect_room_textures(room, option[1] as StringName, "stone_grid")
			_expect(room.get_local_state() == local_state,
				"graphics switch preserves room controls")
		if room_id == &"sprites":
			_expect(gallery_frames.size() == 5, "sprite gallery retains all five comparison sets")
			for node in room.contents.get_children():
				if node is AnimatedSprite2D:
					_expect(node.sprite_frames in gallery_frames,
						"gallery references remain unchanged")
		_select_graphics(lab, "PixelHighButton")
		_expect_room_textures(room, &"pixel_high", "stone_grid")
		lab.lab_navigation.enter_room(&"hub", room_id)
		_expect_room_textures(lab.lab_navigation.current_room, &"pixel_high", "stone_grid")
	_expect(PortalGraphics.get_texture(&"door", &"future_variant").resource_path.ends_with(
		"/test/door.svg"), "unavailable variants use the shipped test fallback")
	_expect(PortalGraphics.get_temple_texture(&"floors", &"future_variant", "missing")
		.resource_path.ends_with("/comic_high/blueprinttempel_floor_blueprint_ornate.png"),
		"unknown temple variants and motifs use the supplied default")
	_expect(PortalGraphics.get_temple_texture(&"missing", &"comic_high") == null,
		"unknown temple surfaces return no texture")


func _expect_room_textures(room: TestRoom, variant: StringName, motif: String = "ornate") -> void:
	_expect(room.graphics_variant == variant, "room records the selected blueprint variant")
	_expect(room.floor_grid.floor_id == motif, "room retains the selected floor motif")
	_expect_temple_texture(room.floor_grid.floor_texture, variant,
		"floors", "blueprinttempel_floor_blueprint_%s.png" % motif)
	_expect_temple_texture(room.floor_grid.wall_texture, variant,
		"walls", "blueprinttempel_wall_blueprint_cyan_blocks.png")
	_expect_temple_texture(room.floor_grid.roof_texture, variant,
		"roofs", "blueprinttempel_roof_texture_stone_shingles.png")
	var props := &"pixelart" if String(variant).begins_with("pixel_") else &"test"
	for portal in room.portals.get_children():
		var sprite := portal.get_node("Door") as Sprite2D
		_expect_texture(sprite.texture, props, &"door")
		_expect_sprite_size(sprite, Vector2(112, 128))
	for binding in room._sample_bindings:
		var sprite := binding["sprite"] as Sprite2D
		var key := binding["asset_key"] as StringName
		_expect_texture(sprite.texture, props, key)
		var size := PortalGraphics.WORLD_SIZES[key] as Vector2
		_expect_sprite_size(sprite, size * float(binding["size_factor"]))
	for emitter in room._particles:
		_expect_texture(emitter.texture, props, &"particle")
		_expect(is_equal_approx(emitter.texture.get_width() * emitter.scale_amount_max, 12.0),
			"particle size is independent of its image resolution")


func _expect_temple_texture(
		texture: Texture2D, variant: StringName, surface: String, file: String,
) -> void:
	_expect(texture != null, "%s has a temple texture" % surface)
	if texture != null:
		var expected := "res://test_assets/environment/tilesets/temple/%s/blueprint/%s/%s"
		_expect(texture.resource_path == expected % [surface, variant, file],
			"%s uses its %s temple source: %s" % [surface, variant, file])


func _expect_texture(texture: Texture2D, variant: StringName, key: StringName) -> void:
	_expect(texture != null, "%s has a texture" % key)
	if texture != null:
		_expect(texture.resource_path.contains("/%s/%s." % [variant, key]),
			"%s uses its %s source" % [key, variant])


func _expect_sprite_size(sprite: Sprite2D, expected: Vector2) -> void:
	_expect((sprite.texture.get_size() * sprite.scale).is_equal_approx(expected),
		"object world size is independent of image resolution")
	_expect(is_zero_approx(sprite.get_rect().end.y), "object stays anchored at its feet")
	_expect(is_zero_approx(sprite.offset.x), "object stays horizontally centered")


func _select_graphics(lab: LabScript, button_name: String) -> void:
	var button := lab.controls_interface.get_node(
		CONTENT_PATH + "HeroGraphicsOptions/" + button_name
	) as Button
	button.pressed.emit()


func _remove_settings() -> void:
	if FileAccess.file_exists(SETTINGS_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_PATH))


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("PortalLabGraphics: %s" % description)
