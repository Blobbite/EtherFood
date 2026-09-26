extends Node

signal room_changed(room_id: StringName, room: TestRoom)

const TestRoom := preload("res://test_scenes/environment/portal_lab/test_room.gd")
const RoomCatalog := preload("res://test_scenes/environment/portal_lab/test_room_catalog.gd")
const PortalDoor := preload("res://test_scenes/environment/portal_lab/portal_door.gd")
const HeroScript := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const HUB_SCENE := preload("res://test_scenes/environment/portal_lab/rooms/portal_tower.tscn")
const DEFAULT_CATALOG := preload("res://test_scenes/environment/portal_lab/rooms.tres")

@export var catalog: RoomCatalog = DEFAULT_CATALOG

var current_room: TestRoom
var current_room_id: StringName = &""
var _hero: HeroScript
var _host: Node2D
var _room_states: Dictionary = {}
var _transition_pending := false
var _arrival_lock := true
var _rearm_delay := 0.0


func initialize(world: Node2D, hero: HeroScript) -> Error:
	if catalog == null or not catalog.validation_errors().is_empty():
		push_error("Test lab room catalog is invalid.")
		return ERR_INVALID_DATA
	_host = world.get_node("RoomHost") as Node2D
	_hero = hero
	_hero.add_to_group(PortalDoor.HERO_GROUP)
	return enter_room(&"hub")


func _process(delta: float) -> void:
	if not _arrival_lock or current_room == null or _transition_pending:
		return
	_rearm_delay = maxf(0.0, _rearm_delay - delta)
	if _rearm_delay > 0.0:
		return
	for action in HeroScript.MOVEMENT_ACTIONS:
		if Input.is_action_pressed(action):
			return
	for door in current_room.portals.get_children():
		if (door as PortalDoor).has_hero_inside():
			return
	for door in current_room.portals.get_children():
		(door as PortalDoor).armed = true
	_arrival_lock = false


func enter_room(room_id: StringName, return_id: StringName = &"") -> Error:
	if _hero == null or _host == null:
		return ERR_UNCONFIGURED
	var scene := HUB_SCENE
	var title := "PORTALTURM"
	var description := "Mitte · %d Testräume · Eine Tür betreten" % catalog.rooms.size()
	if room_id != &"hub":
		var definition := catalog.find_room(room_id)
		if definition == null:
			return ERR_DOES_NOT_EXIST
		scene = definition.scene
		title = definition.title
		description = definition.description
	if scene == null or not scene.can_instantiate():
		return ERR_CANT_CREATE
	var candidate := scene.instantiate()
	if not candidate is TestRoom:
		candidate.free()
		return ERR_INVALID_DATA
	var next_room := candidate as TestRoom
	if current_room != null:
		_room_states[current_room_id] = current_room.get_local_state()
		_host.remove_child(current_room)
		current_room.queue_free()
	_hero.set_movement_enabled(false)
	current_room = next_room
	current_room_id = room_id
	_host.add_child(current_room)
	if room_id == &"hub":
		_build_hub_portals()
	else:
		current_room.add_portal(
			&"hub", room_id, "← Zum Portalturm",
			current_room.return_portal_position, current_room.return_arrival_offset,
		)
	current_room.set_heading(title, description)
	current_room.restore_local_state(_room_states.get(room_id, {}) as Dictionary)
	for door in current_room.portals.get_children():
		(door as PortalDoor).passage_requested.connect(_on_passage_requested)
	var arrival := current_room.world_size / 2.0
	if room_id != &"hub":
		arrival = (current_room.portals.get_child(0) as PortalDoor).get_arrival_position()
	elif return_id != &"":
		var door := find_portal(return_id)
		if door != null:
			arrival = door.get_arrival_position()
	_hero.position = arrival
	_hero.velocity = Vector2.ZERO
	_hero.set_movement_enabled(true)
	_arrival_lock = true
	_rearm_delay = 0.25
	_transition_pending = false
	room_changed.emit(room_id, current_room)
	return OK


func find_portal(return_id: StringName) -> PortalDoor:
	if current_room == null:
		return null
	for child in current_room.portals.get_children():
		var door := child as PortalDoor
		if door.return_id == return_id:
			return door
	return null


func _build_hub_portals() -> void:
	var portal_radius := maxf(760.0, float(catalog.rooms.size()) * 400.0 / TAU)
	var floor_radius := portal_radius + 240.0
	current_room.world_size = Vector2(
		maxf(3840, floor_radius * 2.0 + 160.0),
		maxf(2160, floor_radius * 2.0 + 160.0),
	)
	current_room.floor_grid.world_size = current_room.world_size
	current_room.floor_grid.radius = floor_radius
	var center := current_room.world_size / 2.0
	if current_room.soul != null:
		current_room.soul.position = center + current_room.soul.HUB_OFFSET
	for index in range(catalog.rooms.size()):
		var definition := catalog.rooms[index]
		var angle := -PI / 2.0 + TAU * float(index) / float(catalog.rooms.size())
		var direction := Vector2.from_angle(angle)
		var point := center + direction * portal_radius
		current_room.add_portal(
			definition.room_id, definition.room_id, "%02d · %s" % [index + 1, definition.title],
			point, -direction * 180.0,
		)
		current_room.floor_grid.portal_positions.append(point)
	current_room.floor_grid.queue_redraw()
	current_room.build_tower_boundary(floor_radius)


func _on_passage_requested(room_id: StringName, return_id: StringName) -> void:
	if _transition_pending or _arrival_lock:
		return
	_transition_pending = true
	call_deferred("_complete_passage", room_id, return_id)


func _complete_passage(room_id: StringName, return_id: StringName) -> void:
	var result := enter_room(room_id, return_id)
	if result != OK:
		_transition_pending = false
		_arrival_lock = true
		push_error("Test lab could not enter room %s: %s" % [room_id, error_string(result)])
