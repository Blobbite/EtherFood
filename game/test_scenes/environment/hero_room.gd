extends Control

const MAIN_MENU_ROUTE := &"main_menu"
const ROOM_LEFT := 0
const ROOM_TOP := 0
const ROOM_RIGHT := 2560
const ROOM_BOTTOM := 1440
const INTERACT_ACTION := &"gameplay_interact"
const VisualLabStandardsResource := preload(
	"res://shared/resources/visual_lab_standards.gd"
)
const VISUAL_STANDARDS_V0 := preload(
	"res://shared/resources/visual_lab_standards_v0.tres"
)

const HeroCharacterScript := preload(
	"res://test_scenes/characters/heroes/greenhero/hero_character.gd"
)
const GuideCompanionScript := preload(
	"res://test_scenes/characters/npc/guide/guide_companion.gd"
)
const PlayerCameraControllerScript := preload(
	"res://shared/camera/player_camera_controller.gd"
)

@onready var hero_character: HeroCharacterScript = $World/HeroCharacter
@onready var hero_spawn: Marker2D = $World/HeroSpawn
@onready var player_camera: PlayerCameraControllerScript = (
	$World/HeroCharacter/PlayerCamera
)
@onready var guide_companion: GuideCompanionScript = $World/GuideCompanion
@onready var development_hint: Label = $InterfaceLayer/DevelopmentHint
@onready var interaction_prompt: Label = $InterfaceLayer/InteractionPrompt
@onready var dialogue_panel: Panel = $InterfaceLayer/DialoguePanel

var _navigation_requested := false
var _guide_message_open := false


func _ready() -> void:
	hero_character.global_position = hero_spawn.global_position
	hero_character.set_appearance_height(
		VISUAL_STANDARDS_V0.scale_profile.hero_height
	)

	player_camera.limit_left = ROOM_LEFT
	player_camera.limit_top = ROOM_TOP
	player_camera.limit_right = ROOM_RIGHT
	player_camera.limit_bottom = ROOM_BOTTOM
	var camera_profile := VISUAL_STANDARDS_V0.camera_profile_for(
		VisualLabStandardsResource.CONTEXT_SMALL_INTERIOR
	)
	var profile_error := player_camera.set_profile(camera_profile)
	if profile_error != OK:
		push_error("HeroRoom could not apply its camera profile.")
	player_camera.position_smoothing_enabled = false
	player_camera.enabled = true
	player_camera.make_current()

	development_hint.visible = OS.is_debug_build()
	interaction_prompt.visible = false
	dialogue_panel.visible = false
	hero_character.interaction_target_changed.connect(
		_on_interaction_target_changed
	)
	guide_companion.interaction_requested.connect(
		_on_guide_interaction_requested
	)


## Returns the versioned world grid used by this production scene.
func get_visual_tile_size() -> Vector2i:
	return Vector2i.ONE * VISUAL_STANDARDS_V0.scale_profile.tile_size


func _unhandled_input(event: InputEvent) -> void:
	if _navigation_requested:
		return
	if _guide_message_open:
		if (
			event.is_action_pressed(INTERACT_ACTION)
			or event.is_action_pressed(&"ui_cancel")
		):
			get_viewport().set_input_as_handled()
			_close_guide_message()
		return
	if event.is_action_pressed(INTERACT_ACTION):
		get_viewport().set_input_as_handled()
		hero_character.try_interact()
		return
	if not event.is_action_pressed(&"ui_cancel"):
		return

	get_viewport().set_input_as_handled()
	_navigation_requested = true
	var navigation_error := SceneRouter.navigate(MAIN_MENU_ROUTE)
	if navigation_error == OK:
		return

	_navigation_requested = false
	push_error(
		"HeroRoom failed to navigate to route '%s' with error %d."
		% [MAIN_MENU_ROUTE, navigation_error],
	)


func is_guide_message_open() -> bool:
	return _guide_message_open


func _on_interaction_target_changed(target: Area2D) -> void:
	_update_interaction_prompt(target)


func _on_guide_interaction_requested(interactor: Node) -> void:
	if interactor != hero_character or _guide_message_open:
		return
	_guide_message_open = true
	dialogue_panel.visible = true
	interaction_prompt.visible = false
	hero_character.set_movement_enabled(false)


func _close_guide_message() -> void:
	_guide_message_open = false
	dialogue_panel.visible = false
	hero_character.set_movement_enabled(true)
	_update_interaction_prompt(hero_character.get_nearest_interactable())


func _update_interaction_prompt(target: Area2D) -> void:
	if _guide_message_open or target == null:
		interaction_prompt.visible = false
		return
	var prompt := str(target.call(&"get_interaction_prompt"))
	interaction_prompt.text = prompt
	interaction_prompt.visible = not prompt.is_empty()
