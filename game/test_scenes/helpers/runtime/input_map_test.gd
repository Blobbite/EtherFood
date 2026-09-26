extends RefCounted

const REQUIRED_ACTIONS: Dictionary[StringName, float] = {
	&"ui_up": 0.5,
	&"ui_down": 0.5,
	&"ui_left": 0.5,
	&"ui_right": 0.5,
	&"ui_accept": 0.5,
	&"ui_cancel": 0.5,
	&"gameplay_move_up": 0.2,
	&"gameplay_move_down": 0.2,
	&"gameplay_move_left": 0.2,
	&"gameplay_move_right": 0.2,
	&"gameplay_interact": 0.5,
	&"gameplay_jump": 0.5,
	&"gameplay_sneak": 0.5,
	&"gameplay_sprint": 0.5,
	&"gameplay_walk_toggle": 0.5,
	&"app_pause": 0.5,
	&"dev_diagnostics_toggle": 0.5,
	&"dev_performance_toggle": 0.5,
	&"dev_collision_debug_toggle": 0.5,
	&"dev_controls_toggle": 0.5,
	&"dev_accept_visual_standard": 0.5,
}
const REMOVED_VISUAL_LAB_ACTIONS: Array[StringName] = [
	&"dev_camera_zoom_out",
	&"dev_camera_zoom_in",
	&"dev_hero_size_decrease",
	&"dev_hero_size_increase",
	&"dev_tile_size_decrease",
	&"dev_tile_size_increase",
	&"dev_world_state_toggle",
	&"dev_fog_variant_cycle",
	&"dev_light_variant_cycle",
	&"dev_pixel_snap_toggle",
	&"dev_texture_filter_toggle",
]
const DIRECTION_ACTIONS: Array[StringName] = [
	&"ui_up",
	&"ui_down",
	&"ui_left",
	&"ui_right",
	&"gameplay_move_up",
	&"gameplay_move_down",
	&"gameplay_move_left",
	&"gameplay_move_right",
]
const BUTTON_ACTIONS: Array[StringName] = [
	&"ui_accept",
	&"ui_cancel",
	&"gameplay_interact",
	&"app_pause",
	&"dev_diagnostics_toggle",
]

var failures: PackedStringArray = []


func run(_tree: SceneTree) -> PackedStringArray:
	for action in REQUIRED_ACTIONS:
		_expect(InputMap.has_action(action), "InputMap defines '%s'" % action)
		if not InputMap.has_action(action):
			continue
		_expect(
			is_equal_approx(InputMap.action_get_deadzone(action), REQUIRED_ACTIONS[action]),
			"InputMap configures the reviewed deadzone for '%s'" % action,
		)
		_expect(
			not InputMap.action_get_events(action).is_empty(),
			"InputMap configures device events for '%s'" % action,
		)

	for action in DIRECTION_ACTIONS:
		_expect(_has_keyboard_event(action), "'%s' has a keyboard mapping" % action)
		_expect(_has_button_event(action), "'%s' has a D-pad mapping" % action)
		_expect(_has_axis_event(action), "'%s' has an analog-axis mapping" % action)
	for action in BUTTON_ACTIONS:
		_expect(_has_keyboard_event(action), "'%s' has a keyboard mapping" % action)
		_expect(_has_button_event(action), "'%s' has a controller mapping" % action)
	_expect(
		_has_key_mapping(&"gameplay_jump", KEY_SPACE, KEY_LOCATION_UNSPECIFIED),
		"gameplay_jump uses Space",
	)
	_expect_modifier_pair(&"gameplay_sneak", KEY_CTRL, "gameplay_sneak uses both Ctrl keys")
	_expect_modifier_pair(&"gameplay_sprint", KEY_SHIFT, "gameplay_sprint uses both Shift keys")
	_expect(
		_has_key_mapping(
			&"gameplay_walk_toggle",
			KEY_CAPSLOCK,
			KEY_LOCATION_UNSPECIFIED,
		),
		"gameplay_walk_toggle uses Caps Lock",
	)
	_expect(
		_has_accept_standard_mapping(),
		"dev_accept_visual_standard uses Ctrl + Alt + physical E",
	)
	_expect(
		_has_key_mapping(&"dev_diagnostics_toggle", KEY_F11, KEY_LOCATION_UNSPECIFIED),
		"game diagnostics use F11",
	)
	_expect(
		_has_key_mapping(&"dev_performance_toggle", KEY_F12, KEY_LOCATION_UNSPECIFIED),
		"performance diagnostics use F12",
	)
	_expect(
		not _has_key_mapping(&"dev_diagnostics_toggle", KEY_F3, KEY_LOCATION_UNSPECIFIED),
		"F3 no longer toggles diagnostics",
	)
	for action in REMOVED_VISUAL_LAB_ACTIONS:
		_expect(
			not InputMap.has_action(action),
			"obsolete direct Visual Lab action '%s' is absent" % action,
		)
	for action in [
		&"gameplay_jump",
		&"gameplay_sneak",
		&"gameplay_sprint",
		&"gameplay_walk_toggle",
	]:
		_expect(
			not _has_button_event(action) and not _has_axis_event(action),
			"'%s' remains keyboard-only in movement V0" % action,
		)
	return failures


func _has_accept_standard_mapping() -> bool:
	for input_event in InputMap.action_get_events(&"dev_accept_visual_standard"):
		var key_event := input_event as InputEventKey
		if key_event == null:
			continue
		if (
			key_event.physical_keycode == KEY_E
			and key_event.ctrl_pressed
			and key_event.alt_pressed
			and not key_event.shift_pressed
		):
			return true
	return false


func _has_keyboard_event(action: StringName) -> bool:
	for event in InputMap.action_get_events(action):
		if event is InputEventKey:
			return true
	return false


func _has_button_event(action: StringName) -> bool:
	for event in InputMap.action_get_events(action):
		if event is InputEventJoypadButton:
			return true
	return false


func _has_axis_event(action: StringName) -> bool:
	for event in InputMap.action_get_events(action):
		if event is InputEventJoypadMotion:
			return true
	return false


func _has_key_mapping(
		action: StringName,
		expected_key: Key,
		expected_location: KeyLocation,
) -> bool:
	for input_event in InputMap.action_get_events(action):
		var key_event := input_event as InputEventKey
		if key_event == null:
			continue
		if (
			(key_event.keycode == expected_key or key_event.physical_keycode == expected_key)
			and key_event.location == expected_location
		):
			return true
	return false


func _expect_modifier_pair(action: StringName, key: Key, description: String) -> void:
	_expect(
		_has_key_mapping(action, key, KEY_LOCATION_LEFT)
		and _has_key_mapping(action, key, KEY_LOCATION_RIGHT)
		and _modifier_event_matches(action, key, KEY_LOCATION_LEFT)
		and _modifier_event_matches(action, key, KEY_LOCATION_RIGHT),
		description,
	)


func _modifier_event_matches(
		action: StringName,
		key: Key,
		location: KeyLocation,
) -> bool:
	var event := InputEventKey.new()
	event.device = InputEvent.DEVICE_ID_KEYBOARD
	event.physical_keycode = key
	event.location = location
	event.pressed = true
	return InputMap.event_is_action(event, action, true)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("InputMap: %s" % description)
