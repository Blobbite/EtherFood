extends RefCounted

const TOUCH_ADAPTER_SCRIPT := preload("res://shared/input/touch_action_adapter.gd")

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	var adapter: TOUCH_ADAPTER_SCRIPT = TOUCH_ADAPTER_SCRIPT.new()
	tree.root.add_child(adapter)

	_expect(
		adapter.press_action(&"gameplay_move_left", 0.75) == OK,
		"touch adapter presses a configured semantic action",
	)
	_expect(
		Input.is_action_pressed(&"gameplay_move_left"),
		"synthetic movement action becomes pressed",
	)
	_expect(
		is_equal_approx(Input.get_action_strength(&"gameplay_move_left"), 0.75),
		"synthetic movement preserves normalized analog strength",
	)
	_expect(
		adapter.release_action(&"gameplay_move_left") == OK,
		"touch adapter releases a configured semantic action",
	)
	_expect(
		not Input.is_action_pressed(&"gameplay_move_left"),
		"released movement action is no longer pressed",
	)

	_expect(
		adapter.press_action(&"ui_accept", 2.0) == OK,
		"touch adapter accepts a button-style semantic action",
	)
	_expect(
		is_equal_approx(Input.get_action_strength(&"ui_accept"), 1.0),
		"touch strength is clamped to one",
	)
	_expect(
		adapter.press_action(&"ui_accept", 0.0) == OK,
		"zero strength releases an owned action",
	)
	_expect(not Input.is_action_pressed(&"ui_accept"), "zero strength clears input")

	_expect(
		adapter.press_action(&"") == ERR_INVALID_PARAMETER,
		"empty action names are rejected",
	)
	_expect(
		adapter.press_action(&"missing_touch_action") == ERR_DOES_NOT_EXIST,
		"unknown semantic actions are rejected",
	)

	_expect(adapter.press_action(&"ui_cancel") == OK, "first action can be owned")
	_expect(adapter.press_action(&"app_pause") == OK, "second action can be owned")
	adapter.set_input_enabled(false)
	_expect(not adapter.is_input_enabled(), "touch adapter can be disabled")
	_expect(not Input.is_action_pressed(&"ui_cancel"), "disable releases first action")
	_expect(not Input.is_action_pressed(&"app_pause"), "disable releases second action")
	_expect(
		adapter.press_action(&"ui_accept") == ERR_UNAVAILABLE,
		"disabled adapter rejects new presses",
	)

	adapter.set_input_enabled(true)
	_expect(adapter.is_input_enabled(), "touch adapter can be re-enabled")
	_expect(adapter.press_action(&"app_pause") == OK, "re-enabled adapter can press")
	adapter.queue_free()
	await tree.process_frame
	_expect(
		not Input.is_action_pressed(&"app_pause"),
		"tree exit releases the final owned action",
	)
	return failures


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("TouchActionAdapter: %s" % description)
