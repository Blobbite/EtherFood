extends VBoxContainer

signal value_changed(setting_id: StringName, value: float)
signal focused(setting_id: StringName)

@export var setting_id: StringName
@export var display_name := "Testwert"
@export var unit := "px"
@export var minimum_value := 0.0
@export var maximum_value := 100.0
@export var step := 1.0
@export var initial_value := 0.0

@onready var name_label: Label = $Header/Name
@onready var value_label: Label = $Header/Value
@onready var slider: HSlider = $Slider
@onready var standard_status: Label = $StandardStatus

var _accepted_value := 0.0


func _ready() -> void:
	name_label.text = display_name
	slider.min_value = minimum_value
	slider.max_value = maximum_value
	slider.step = step
	slider.set_value_no_signal(clampf(initial_value, minimum_value, maximum_value))
	_accepted_value = slider.value
	slider.value_changed.connect(_on_value_changed)
	slider.focus_entered.connect(_on_focus_entered)
	_refresh_labels()


## Updates preview and accepted values without emitting a user edit.
func update_setting(current_value: float, accepted_value: float) -> void:
	_accepted_value = clampf(accepted_value, minimum_value, maximum_value)
	slider.set_value_no_signal(clampf(current_value, minimum_value, maximum_value))
	_refresh_labels()


## Gives keyboard focus to the bounded slider.
func grab_slider_focus() -> void:
	slider.grab_focus()


## Returns the clamped value currently visible in the row.
func get_current_value() -> float:
	return slider.value


func _on_value_changed(new_value: float) -> void:
	_refresh_labels()
	value_changed.emit(setting_id, new_value)


func _on_focus_entered() -> void:
	focused.emit(setting_id)


func _refresh_labels() -> void:
	value_label.text = "%d %s" % [roundi(slider.value), unit]
	if is_equal_approx(slider.value, _accepted_value):
		standard_status.text = "Entspricht dem Spielstandard · ★ %d %s" % [
			roundi(_accepted_value),
			unit,
		]
		standard_status.add_theme_color_override(
			"font_color",
			Color(0.9, 0.73, 0.33, 1),
		)
		return
	standard_status.text = "Testwert · ★ Spielstandard: %d %s" % [
		roundi(_accepted_value),
		unit,
	]
	standard_status.add_theme_color_override(
		"font_color",
		Color(0.7, 0.79, 0.82, 1),
	)
