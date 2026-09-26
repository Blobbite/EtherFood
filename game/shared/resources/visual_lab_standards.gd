extends Resource
class_name VisualLabStandards

## References the versioned visual defaults promoted through the Visual Lab.

const CONTEXT_WORLD := &"world"
const CONTEXT_VILLAGE := &"village"
const CONTEXT_DUNGEON := &"dungeon"
const CONTEXT_SMALL_INTERIOR := &"small_interior"

@export_range(1, 100, 1) var schema_version: int = 1
@export var scale_profile: VisualScaleProfile
@export_range(8, 16, 2) var hero_frame_count: int = 8
@export_range(8, 16, 2) var hero_fps: int = 8
@export var world_camera_profile: CameraProfile
@export var village_camera_profile: CameraProfile
@export var village_inherits_world: bool = true
@export var dungeon_camera_profile: CameraProfile
@export var small_interior_camera_profile: CameraProfile
@export var damaged_fog_id: String = "medium"
@export var damaged_light_id: String = "cool_dark"
@export var restored_fog_id: String = "low"
@export var restored_light_id: String = "warm_clear"


## Returns the versioned base camera profile for one stable scene context.
func camera_profile_for(context_id: StringName) -> CameraProfile:
	match context_id:
		CONTEXT_WORLD:
			return world_camera_profile
		CONTEXT_VILLAGE:
			if village_inherits_world:
				return world_camera_profile
			return village_camera_profile
		CONTEXT_DUNGEON:
			return dungeon_camera_profile
		CONTEXT_SMALL_INTERIOR:
			return small_interior_camera_profile
	return null


## Returns the dedicated writable profile even when a context currently inherits.
func owned_camera_profile_for(context_id: StringName) -> CameraProfile:
	match context_id:
		CONTEXT_WORLD:
			return world_camera_profile
		CONTEXT_VILLAGE:
			return village_camera_profile
		CONTEXT_DUNGEON:
			return dungeon_camera_profile
		CONTEXT_SMALL_INTERIOR:
			return small_interior_camera_profile
	return null


## Reports whether the context currently follows another versioned profile.
func camera_context_is_inherited(context_id: StringName) -> bool:
	return context_id == CONTEXT_VILLAGE and village_inherits_world


## Returns the accepted fog ID for a stable world-state ID.
func fog_id_for(world_state_id: StringName) -> String:
	if world_state_id == &"restored":
		return restored_fog_id
	return damaged_fog_id


## Returns the accepted light ID for a stable world-state ID.
func light_id_for(world_state_id: StringName) -> String:
	if world_state_id == &"restored":
		return restored_light_id
	return damaged_light_id


## Replaces one accepted fog ID without changing the other world state.
func set_fog_id(world_state_id: StringName, fog_id: String) -> void:
	if world_state_id == &"restored":
		restored_fog_id = fog_id
		return
	damaged_fog_id = fog_id


## Replaces one accepted light ID without changing the other world state.
func set_light_id(world_state_id: StringName, light_id: String) -> void:
	if world_state_id == &"restored":
		restored_light_id = light_id
		return
	damaged_light_id = light_id
