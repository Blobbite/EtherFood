extends RefCounted

const LAB_SCENE := preload("res://test_scenes/visual_lab/visual_lab.tscn")
const LabScript := preload("res://test_scenes/visual_lab/visual_lab.gd")
const HeroScript := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const PortalDoor := preload("res://test_scenes/environment/portal_lab/portal_door.gd")
const RoomDefinition := preload("res://test_scenes/environment/portal_lab/test_room_definition.gd")
const Palette := preload("res://test_scenes/environment/portal_lab/blueprint_palette.gd")
const SETTINGS_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_PATH := "user://portal_lab_test.cfg"
const EXPECTED_ROOMS: Array[StringName] = [
	&"lamps", &"sprites", &"monsters", &"shaders", &"objects", &"particles",
	&"fog", &"day_night", &"world_state",
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	var had_override := ProjectSettings.has_setting(SETTINGS_KEY)
	var previous: Variant = ProjectSettings.get_setting(SETTINGS_KEY, null)
	ProjectSettings.set_setting(SETTINGS_KEY, SETTINGS_PATH)
	_remove_settings()
	_release_input()
	var lab := LAB_SCENE.instantiate() as LabScript
	tree.root.add_child(lab)
	await tree.physics_frame
	await tree.physics_frame
	_expect_hub(lab)
	await _test_portal_round_trips(tree, lab)
	await _test_room_isolation(tree, lab)
	_test_catalog_expansion(lab)
	_release_input()
	lab.queue_free()
	await tree.process_frame
	_remove_settings()
	ProjectSettings.set_setting(SETTINGS_KEY, previous if had_override else null)
	return failures


func _expect_hub(lab: LabScript) -> void:
	var navigation := lab.lab_navigation
	_expect(navigation.current_room_id == &"hub", "route opens the portal tower")
	_expect(lab.hero_character.position == Vector2(1920, 1080), "hero starts in the center")
	_expect(navigation.catalog.validation_errors().is_empty(), "room catalog is valid")
	_expect(Palette.COLORS.size() == 8, "blueprint environment defines exactly eight colors")
	_expect(navigation.current_room.floor_grid.circular, "tower floor is circular")
	_expect(navigation.current_room.floor_grid.floor_texture.get_width() >= 1024,
		"blueprint floor uses an HD texture")
	_expect(navigation.current_room.portals.get_child_count() == 9, "all nine rooms have portals")
	_expect(not lab.world_state_preview.is_visible_in_tree(), "tower contains no world preview")
	_expect(not lab.get_node("TestWorld/ScaleComparison").is_visible_in_tree(),
		"old mixed comparison area is absent from the tower")
	_expect((lab.get_node("TestWorld/TestObstacle/CollisionShape2D") as CollisionShape2D).disabled,
		"old test obstacle does not obstruct the tower")
	for room_id in EXPECTED_ROOMS:
		var door := navigation.find_portal(room_id)
		_expect(door != null and door.target_room == room_id,
			"%s has its own destination" % room_id)
		if door == null:
			continue
		_expect(is_equal_approx(door.position.distance_to(Vector2(1920, 1080)), 760.0),
			"%s door belongs to the circular portal ring" % room_id)
		var sprite := door.get_node("Door") as Sprite2D
		_expect(sprite.texture.get_height() >= 1024, "door uses an HD texture")
		_expect(sprite.texture.get_height() * sprite.scale.y == 128.0,
			"HD texture preserves the portal's world size")
		_expect(door.find_children("*", "AnimationPlayer", true, false).is_empty(),
			"door has no animation")
		_expect(door.find_children("*", "GPUParticles2D", true, false).is_empty(),
			"door has no particles")
		for node in door.find_children("*", "CanvasItem", true, false):
			_expect((node as CanvasItem).material == null, "door has no shader material")


func _test_portal_round_trips(tree: SceneTree, lab: LabScript) -> void:
	var navigation := lab.lab_navigation
	var hero := lab.hero_character
	lab._set_hero_graphics(lab.HeroGraphicsPreset.PIXEL_HIGH)
	lab._set_tile_size(lab.TileSizePreset.LARGE)
	var movement_config := hero.movement_config
	for room_id in EXPECTED_ROOMS:
		await _wait_for_portals(tree, lab)
		var entry := navigation.find_portal(room_id)
		var expected_return := entry.get_arrival_position()
		await _walk_through(tree, lab, entry, room_id)
		if navigation.current_room_id != room_id:
			return
		var room := navigation.current_room
		_expect(room.portals.get_child_count() == 1, "%s has a return portal" % room_id)
		var return_door := room.portals.get_child(0) as PortalDoor
		_expect(return_door.target_room == &"hub", "%s leads back to the tower" % room_id)
		_expect(return_door.return_id == room_id, "%s keeps its entry association" % room_id)
		_expect(hero.movement_config == movement_config, "portal preserves movement preview")
		_expect(room.floor_grid.tile_size == 64, "portal preserves the selected floor grid")
		_expect(lab._selected_hero_graphics == lab.HeroGraphicsPreset.PIXEL_HIGH,
			"portal preserves the selected hero graphics")
		_expect(not hero.is_jumping(), "arrival clears any old jump")
		var arrived_at := hero.position
		_expect(arrived_at.distance_to(return_door.position) >= 160.0,
			"arrival is outside the opposite threshold")

		Input.action_press(&"gameplay_move_up")
		hero.position = return_door.position
		await tree.physics_frame
		await tree.physics_frame
		_expect(navigation.current_room_id == room_id, "held input cannot cause a return loop")
		hero.position = return_door.get_arrival_position()
		_release_input()
		await _wait_for_portals(tree, lab)
		var intruder := CharacterBody2D.new()
		room.add_child(intruder)
		return_door._on_body_entered(intruder)
		await tree.process_frame
		_expect(navigation.current_room_id == room_id, "only the lab hero uses a portal")
		intruder.queue_free()
		await _walk_through(tree, lab, return_door, &"hub")
		_expect(hero.position.distance_to(expected_return) < 12.0,
			"%s returns to the correct tower entrance" % room_id)
		_expect(navigation.current_room.ambient.color == Color.WHITE,
			"room lighting never leaks into the tower")


func _walk_through(
		tree: SceneTree, lab: LabScript, door: PortalDoor, destination: StringName,
) -> void:
	lab.hero_character.position = door.global_position + Vector2(0, 96)
	await tree.physics_frame
	Input.action_press(&"gameplay_move_up")
	for _frame in range(90):
		await tree.physics_frame
		if lab.lab_navigation.current_room_id == destination:
			break
	_release_input()
	_expect(lab.lab_navigation.current_room_id == destination,
		"walking across the threshold reaches %s" % destination)


func _wait_for_portals(tree: SceneTree, lab: LabScript) -> void:
	for _frame in range(90):
		if not lab.lab_navigation._arrival_lock:
			return
		await tree.physics_frame
	_expect(false, "portals rearm after arrival and released movement")


func _test_room_isolation(tree: SceneTree, lab: LabScript) -> void:
	var navigation := lab.lab_navigation
	navigation.enter_room(&"fog")
	await tree.process_frame
	var preview := lab.world_state_preview
	_expect(preview.is_visible_in_tree() and preview.preview_mode == &"fog",
		"fog has its own visible preview")
	_expect(preview.damaged_fog.visible and not preview.damaged_light.visible,
		"fog room enables fog without the former lighting overlay")
	_expect(preview.damaged_state.modulate == Color.WHITE, "fog backdrop has neutral lighting")
	lab._set_fog_variant(2)
	_expect(is_equal_approx(preview.get_active_fog_strength(), 1.0), "F5 controls the fog sample")
	navigation.enter_room(&"world_state")
	_expect(not preview.damaged_fog.visible and not preview.restored_fog.visible,
		"world-state room has no fog")
	lab._set_world_state(lab.WorldStatePreset.RESTORED)
	_expect(preview.restored_state.visible and not preview.damaged_state.visible,
		"world-state room shows reconstruction")
	lab._set_world_state(lab.WorldStatePreset.DAMAGED)
	_expect(preview.damaged_state.visible and not preview.restored_state.visible,
		"world-state room shows destruction")
	navigation.enter_room(&"day_night")
	_expect(not preview.damaged_fog.visible, "day-night room has no fog")
	var room := navigation.current_room
	room.activate_control(&"night")
	_expect(room.ambient.color.r < 0.2, "night darkens the room")
	room.activate_control(&"day")
	_expect(room.ambient.color == Color.WHITE, "day restores full brightness")
	room.activate_control(&"cycle")
	room._process(7.5)
	_expect(is_equal_approx(room.cycle_phase, 0.25), "day-night cycle advances at its own rate")
	room.activate_control(&"cycle")
	navigation.enter_room(&"lamps")
	_expect(navigation.current_room._lamps.size() == 3, "lamp room has three light strengths")
	navigation.current_room.activate_control(&"lamps")
	for light in navigation.current_room._lamps:
		_expect(not light.enabled, "lamp switch affects the room lights")
	navigation.enter_room(&"particles")
	room = navigation.current_room
	_expect(room._particles.size() == 3, "particle room has three emission samples")
	room.activate_control(&"particles")
	for emitter in room._particles:
		_expect(emitter.emitting, "particle switch starts only the room emitters")
		_expect(is_equal_approx(emitter.texture.get_width() * emitter.scale_amount_max, 12.0),
			"HD particle texture keeps a small world footprint")
	navigation.enter_room(&"hub")
	_expect(navigation.current_room.find_children("*", "CPUParticles2D", true, false).is_empty(),
		"tower remains free of particles")
	navigation.enter_room(&"day_night")
	_expect(is_equal_approx(navigation.current_room.cycle_phase, 0.25),
		"revisiting a room preserves its local preview state")
	navigation.enter_room(&"objects")
	_expect(lab.get_node("TestWorld/ScaleComparison").is_visible_in_tree(),
		"object room owns the scale comparisons")
	_expect(lab.get_node("TestWorld/TileComparison").is_visible_in_tree(),
		"object room owns the tile sample")
	var obstacle := lab.get_node("TestWorld/TestObstacle/CollisionShape2D") as CollisionShape2D
	_expect(not obstacle.disabled,
		"object room enables its collision sample")
	navigation.enter_room(&"hub")
	var original := navigation.current_room
	_expect(navigation.enter_room(&"missing_room") == ERR_DOES_NOT_EXIST,
		"unavailable rooms are rejected")
	_expect(navigation.current_room == original, "invalid destination keeps the current room")


func _test_catalog_expansion(lab: LabScript) -> void:
	var navigation := lab.lab_navigation
	var original := navigation.catalog
	var expanded := original.duplicate(true)
	for index in range(24):
		var definition := RoomDefinition.new()
		definition.room_id = StringName("future_%d" % index)
		definition.title = "Zukünftiger Raum %d" % index
		definition.scene = original.rooms[0].scene
		expanded.rooms.append(definition)
	_expect(expanded.validation_errors().is_empty(), "catalog accepts additional test scenes")
	navigation.catalog = expanded
	navigation.enter_room(&"hub")
	_expect(navigation.current_room.portals.get_child_count() == 33,
		"additional catalog entries create additional portals")
	_expect(navigation.current_room.world_size.y > 2160.0,
		"tower and camera space grow with the portal ring")
	_expect(lab.player_camera.limit_bottom == int(navigation.current_room.world_size.y),
		"camera follows the expanded world bounds")
	expanded.rooms.append(expanded.rooms[0])
	_expect(not expanded.validation_errors().is_empty(), "duplicate room IDs are rejected")
	navigation.catalog = original
	navigation.enter_room(&"hub")


func _release_input() -> void:
	for action in HeroScript.MOVEMENT_ACTIONS:
		Input.action_release(action)
	for action in [&"gameplay_jump", &"gameplay_sneak", &"gameplay_sprint"]:
		Input.action_release(action)


func _remove_settings() -> void:
	if FileAccess.file_exists(SETTINGS_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_PATH))


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("PortalLab: %s" % description)
