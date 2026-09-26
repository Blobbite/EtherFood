extends Control

const TITLE_ROUTE := &"title"
const HERO_ROOM_ROUTE := &"hero_room"
const VISUAL_LAB_ROUTE := &"visual_lab"

@onready var new_game_button: Button = $Content/Text/Buttons/NewGameButton
@onready var visual_lab_button: Button = $Content/Text/Buttons/VisualLabButton

var _navigation_requested := false


func _ready() -> void:
	var has_hero_room := SceneRouter.has_route(HERO_ROOM_ROUTE)
	new_game_button.disabled = not has_hero_room
	new_game_button.focus_mode = Control.FOCUS_ALL if has_hero_room else Control.FOCUS_NONE
	var has_visual_lab := SceneRouter.has_route(VISUAL_LAB_ROUTE)
	visual_lab_button.visible = has_visual_lab
	visual_lab_button.disabled = not has_visual_lab
	visual_lab_button.focus_mode = (
		Control.FOCUS_ALL if has_visual_lab else Control.FOCUS_NONE
	)
	if has_hero_room:
		new_game_button.grab_focus()


func _unhandled_input(event: InputEvent) -> void:
	if _navigation_requested or not event.is_action_pressed(&"ui_cancel"):
		return

	get_viewport().set_input_as_handled()
	_navigate(TITLE_ROUTE)


func _on_new_game_button_pressed() -> void:
	_navigate(HERO_ROOM_ROUTE)


func _on_visual_lab_button_pressed() -> void:
	_navigate(VISUAL_LAB_ROUTE)


func _navigate(route_id: StringName) -> void:
	if _navigation_requested:
		return

	_navigation_requested = true
	var navigation_error := SceneRouter.navigate(route_id)
	if navigation_error == OK:
		return

	_navigation_requested = false
	push_error(
		"MainMenu failed to navigate to route '%s' with error %d."
		% [route_id, navigation_error],
	)
