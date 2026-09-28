extends MarginContainer

signal option_selected(setting_id: StringName, option_index: int)
signal numeric_value_changed(setting_id: StringName, value: float)
signal setting_focused(setting_id: StringName)
signal accept_requested
signal close_requested

const NumericSettingScript := preload(
	"res://test_scenes/visual_lab/visual_lab_numeric_setting.gd"
)
const PortalGraphics := preload("res://test_scenes/environment/portal_lab/portal_graphics.gd")
const HERO_FRAMES_BUTTON_PATH := (
	"Menu/Pages/RenderingPage/Content/HeroAnimationOptions/"
	+ "HeroFramesColumn/HeroFramesOptions/"
)
const HERO_FPS_BUTTON_PATH := (
	"Menu/Pages/RenderingPage/Content/HeroAnimationOptions/"
	+ "HeroFpsColumn/HeroFpsOptions/"
)

const SETTING_CAMERA_CONTEXT := &"camera_context"
const SETTING_CAMERA_ZOOM := &"camera_zoom"
const SETTING_HERO_SIZE := &"hero_size"
const SETTING_TILE_SIZE := &"tile_size"
const SETTING_HERO_GRAPHICS := &"hero_graphics"
const SETTING_TEMPLE_FLOOR := &"temple_floor"
const SETTING_HERO_FRAMES := &"hero_frames"
const SETTING_HERO_FPS := &"hero_fps"
const SETTING_PIXEL_SNAP := &"pixel_snap"
const SETTING_TEXTURE_FILTER := &"texture_filter"
const SETTING_WORLD_STATE := &"world_state"
const SETTING_FOG := &"fog"
const SETTING_LIGHT := &"light"
const SETTING_DIAGNOSTICS := &"diagnostics"
const SETTING_PERFORMANCE := &"performance"
const SETTING_COLLISION := &"collision"
const SETTING_SNEAK_SPEED := &"sneak_speed"
const SETTING_WALK_SPEED := &"walk_speed"
const SETTING_JOG_SPEED := &"jog_speed"
const SETTING_RUN_SPEED := &"run_speed"
const SETTING_SPRINT_SPEED := &"sprint_speed"
const SETTING_STANDING_JUMP_HEIGHT := &"standing_jump_height"
const SETTING_WALK_JUMP_HEIGHT := &"walk_jump_height"
const SETTING_WALK_JUMP_DISTANCE := &"walk_jump_distance"
const SETTING_JOG_JUMP_HEIGHT := &"jog_jump_height"
const SETTING_JOG_JUMP_DISTANCE := &"jog_jump_distance"
const SETTING_RUN_JUMP_HEIGHT := &"run_jump_height"
const SETTING_RUN_JUMP_DISTANCE := &"run_jump_distance"
const SETTING_SPRINT_JUMP_HEIGHT := &"sprint_jump_height"
const SETTING_SPRINT_JUMP_DISTANCE := &"sprint_jump_distance"
const GAMEPLAY_SETTING_IDS: Array[StringName] = [
	SETTING_SNEAK_SPEED,
	SETTING_WALK_SPEED,
	SETTING_JOG_SPEED,
	SETTING_RUN_SPEED,
	SETTING_SPRINT_SPEED,
	SETTING_STANDING_JUMP_HEIGHT,
	SETTING_WALK_JUMP_HEIGHT,
	SETTING_WALK_JUMP_DISTANCE,
	SETTING_JOG_JUMP_HEIGHT,
	SETTING_JOG_JUMP_DISTANCE,
	SETTING_RUN_JUMP_HEIGHT,
	SETTING_RUN_JUMP_DISTANCE,
	SETTING_SPRINT_JUMP_HEIGHT,
	SETTING_SPRINT_JUMP_DISTANCE,
]

const TAB_TITLES: Array[String] = [
	"Kamera",
	"Maßstab",
	"Darstellung",
	"Welt & Atmosphäre",
	"Diagnose & Hilfe",
	"Gameplay",
]
const TAB_PRIMARY_SETTINGS: Array[StringName] = [
	SETTING_CAMERA_ZOOM,
	SETTING_HERO_SIZE,
	SETTING_PIXEL_SNAP,
	SETTING_WORLD_STATE,
	SETTING_DIAGNOSTICS,
	SETTING_SNEAK_SPEED,
]

@onready var camera_status: Label = $Menu/Pages/CameraPage/Content/CameraStatus
@onready var hero_size_status: Label = $Menu/Pages/ScalePage/Content/HeroSizeStatus
@onready var tile_size_status: Label = $Menu/Pages/ScalePage/Content/TileSizeStatus
@onready var hero_graphics_status: Label = (
	$Menu/Pages/RenderingPage/Content/HeroGraphicsStatus
)
@onready var portal_graphics_status: Label = (
	$Menu/Pages/RenderingPage/Content/PortalGraphicsStatus
)
@onready var temple_floor_option: OptionButton = (
	$Menu/Pages/RenderingPage/Content/TempleFloorOption
)
@onready var world_state_status: Label = (
	$Menu/Pages/WorldPage/Content/WorldStateStatus
)
@onready var fog_status: Label = $Menu/Pages/WorldPage/Content/FogStatus
@onready var light_status: Label = $Menu/Pages/WorldPage/Content/LightStatus
@onready var window_size_status: Label = (
	$Menu/Pages/DiagnosticsPage/Content/WindowSizeStatus
)

@onready var _tab_buttons: Array[Button] = [
	$Menu/ThemeTabs/CameraTab,
	$Menu/ThemeTabs/ScaleTab,
	$Menu/ThemeTabs/RenderingTab,
	$Menu/ThemeTabs/WorldTab,
	$Menu/ThemeTabs/DiagnosticsTab,
	$Menu/ThemeTabs/GameplayTab,
]
@onready var _pages: Array[ScrollContainer] = [
	$Menu/Pages/CameraPage,
	$Menu/Pages/ScalePage,
	$Menu/Pages/RenderingPage,
	$Menu/Pages/WorldPage,
	$Menu/Pages/DiagnosticsPage,
	$Menu/Pages/GameplayPage,
]
@onready var _camera_context_buttons: Array[Button] = [
	$Menu/Pages/CameraPage/Content/ContextOptions/WorldButton,
	$Menu/Pages/CameraPage/Content/ContextOptions/VillageButton,
	$Menu/Pages/CameraPage/Content/ContextOptions/DungeonButton,
	$Menu/Pages/CameraPage/Content/ContextOptions/InteriorButton,
]
@onready var _camera_zoom_buttons: Array[Button] = [
	$Menu/Pages/CameraPage/Content/ZoomOptions/WideButton,
	$Menu/Pages/CameraPage/Content/ZoomOptions/MediumButton,
	$Menu/Pages/CameraPage/Content/ZoomOptions/NearButton,
]
@onready var _hero_size_buttons: Array[Button] = [
	$Menu/Pages/ScalePage/Content/HeroOptions/SmallButton,
	$Menu/Pages/ScalePage/Content/HeroOptions/MediumButton,
	$Menu/Pages/ScalePage/Content/HeroOptions/LargeButton,
]
@onready var _tile_size_buttons: Array[Button] = [
	$Menu/Pages/ScalePage/Content/TileOptions/SmallButton,
	$Menu/Pages/ScalePage/Content/TileOptions/MediumButton,
	$Menu/Pages/ScalePage/Content/TileOptions/LargeButton,
]
@onready var _pixel_snap_buttons: Array[Button] = [
	$Menu/Pages/RenderingPage/Content/PixelSnapOptions/OffButton,
	$Menu/Pages/RenderingPage/Content/PixelSnapOptions/OnButton,
]
@onready var _hero_graphics_buttons: Array[Button] = [
	$Menu/Pages/RenderingPage/Content/HeroGraphicsOptions/ComicHighButton,
	$Menu/Pages/RenderingPage/Content/HeroGraphicsOptions/ComicMidButton,
	$Menu/Pages/RenderingPage/Content/HeroGraphicsOptions/ComicLowButton,
	$Menu/Pages/RenderingPage/Content/HeroGraphicsOptions/PixelHighButton,
	$Menu/Pages/RenderingPage/Content/HeroGraphicsOptions/PixelLowButton,
]
@onready var _hero_frames_buttons: Array[Button] = [
	get_node(HERO_FRAMES_BUTTON_PATH + "Frames8Button") as Button,
	get_node(HERO_FRAMES_BUTTON_PATH + "Frames10Button") as Button,
	get_node(HERO_FRAMES_BUTTON_PATH + "Frames12Button") as Button,
	get_node(HERO_FRAMES_BUTTON_PATH + "Frames14Button") as Button,
	get_node(HERO_FRAMES_BUTTON_PATH + "Frames16Button") as Button,
]
@onready var _hero_fps_buttons: Array[Button] = [
	get_node(HERO_FPS_BUTTON_PATH + "FpsNewButton") as Button,
	get_node(HERO_FPS_BUTTON_PATH + "Fps8Button") as Button,
	get_node(HERO_FPS_BUTTON_PATH + "Fps10Button") as Button,
	get_node(HERO_FPS_BUTTON_PATH + "Fps12Button") as Button,
	get_node(HERO_FPS_BUTTON_PATH + "Fps14Button") as Button,
	get_node(HERO_FPS_BUTTON_PATH + "Fps16Button") as Button,
]
@onready var _texture_filter_buttons: Array[Button] = [
	$Menu/Pages/RenderingPage/Content/TextureFilterOptions/NearestButton,
	$Menu/Pages/RenderingPage/Content/TextureFilterOptions/SoftButton,
]
@onready var _world_state_buttons: Array[Button] = [
	$Menu/Pages/WorldPage/Content/WorldStateOptions/DamagedButton,
	$Menu/Pages/WorldPage/Content/WorldStateOptions/RestoredButton,
]
@onready var _fog_buttons: Array[Button] = [
	$Menu/Pages/WorldPage/Content/FogOptions/LowButton,
	$Menu/Pages/WorldPage/Content/FogOptions/MediumButton,
	$Menu/Pages/WorldPage/Content/FogOptions/HighButton,
]
@onready var _light_buttons: Array[Button] = [
	$Menu/Pages/WorldPage/Content/LightOptions/FirstButton,
	$Menu/Pages/WorldPage/Content/LightOptions/SecondButton,
]
@onready var _diagnostics_buttons: Array[Button] = [
	$Menu/Pages/DiagnosticsPage/Content/DiagnosticsOptions/OffButton,
	$Menu/Pages/DiagnosticsPage/Content/DiagnosticsOptions/OnButton,
]
@onready var _collision_buttons: Array[Button] = [
	$Menu/Pages/DiagnosticsPage/Content/CollisionOptions/OffButton,
	$Menu/Pages/DiagnosticsPage/Content/CollisionOptions/OnButton,
]
@onready var _performance_buttons: Array[Button] = [
	$Menu/Pages/DiagnosticsPage/Content/PerformanceOptions/OffButton,
	$Menu/Pages/DiagnosticsPage/Content/PerformanceOptions/OnButton,
]
@onready var _numeric_settings: Array[NumericSettingScript] = [
	$Menu/Pages/GameplayPage/Content/SneakSpeed,
	$Menu/Pages/GameplayPage/Content/WalkSpeed,
	$Menu/Pages/GameplayPage/Content/JogSpeed,
	$Menu/Pages/GameplayPage/Content/RunSpeed,
	$Menu/Pages/GameplayPage/Content/SprintSpeed,
	$Menu/Pages/GameplayPage/Content/StandingJumpHeight,
	$Menu/Pages/GameplayPage/Content/WalkJumpHeight,
	$Menu/Pages/GameplayPage/Content/WalkJumpDistance,
	$Menu/Pages/GameplayPage/Content/JogJumpHeight,
	$Menu/Pages/GameplayPage/Content/JogJumpDistance,
	$Menu/Pages/GameplayPage/Content/RunJumpHeight,
	$Menu/Pages/GameplayPage/Content/RunJumpDistance,
	$Menu/Pages/GameplayPage/Content/SprintJumpHeight,
	$Menu/Pages/GameplayPage/Content/SprintJumpDistance,
]
@onready var _accept_button: Button = $Menu/Acceptance/AcceptButton
@onready var _focus_status: Label = $Menu/FocusStatus
@onready var _feedback_status: Label = $Menu/FeedbackStatus
@onready var _close_button: Button = $Menu/Header/CloseButton

var _buttons_by_setting: Dictionary = {}
var _numeric_by_setting: Dictionary = {}
var _labels_by_setting: Dictionary = {}
var _status_by_setting: Dictionary = {}
var _current_indices: Dictionary = {}
var _accepted_indices: Dictionary = {}
var _accepted_descriptions: Dictionary = {}
var _focused_setting_id: StringName = SETTING_CAMERA_ZOOM
var _active_tab := 0
var _normal_style: StyleBoxFlat
var _hover_style: StyleBoxFlat
var _pressed_style: StyleBoxFlat
var _standard_style: StyleBoxFlat
var _standard_hover_style: StyleBoxFlat
var _standard_pressed_style: StyleBoxFlat
var _focus_style: StyleBoxFlat


func _ready() -> void:
	_create_styles()
	_register_tabs()
	_register_settings()
	_register_numeric_settings()
	for label in PortalGraphics.FLOOR_NAMES:
		temple_floor_option.add_item(label)
	temple_floor_option.item_selected.connect(_on_temple_floor_selected)
	temple_floor_option.focus_entered.connect(_on_setting_focused.bind(SETTING_TEMPLE_FLOOR))
	_apply_base_button_theme(temple_floor_option)
	var floor_popup := temple_floor_option.get_popup()
	floor_popup.add_theme_stylebox_override("panel", _normal_style)
	floor_popup.add_theme_stylebox_override("hover", _hover_style)
	floor_popup.add_theme_color_override("font_color", Color(0.84, 0.87, 0.86, 1))
	floor_popup.add_theme_color_override("font_hover_color", Color(0.96, 0.98, 0.97, 1))
	floor_popup.add_theme_font_size_override("font_size", 17)
	_accept_button.pressed.connect(_on_accept_button_pressed)
	_close_button.pressed.connect(_on_close_button_pressed)
	_select_tab(0, false)
	show_feedback("Wähle einen Testwert zum Vergleichen.")


func update_temple_floor(option_index: int) -> void:
	temple_floor_option.select(option_index)
	_current_indices[SETTING_TEMPLE_FLOOR] = option_index


## Updates labels for a setting whose option names depend on another selection.
func set_setting_labels(setting_id: StringName, labels: Array[String]) -> Error:
	var buttons := _setting_buttons(setting_id)
	if buttons.is_empty() or buttons.size() != labels.size():
		return ERR_INVALID_PARAMETER
	_labels_by_setting[setting_id] = labels.duplicate()
	_refresh_setting(setting_id)
	return OK


## Updates current and accepted options without emitting a user-selection signal.
func update_setting(
		setting_id: StringName,
		current_index: int,
		accepted_index: int = -1,
		accepted_description: String = "",
) -> Error:
	var buttons := _setting_buttons(setting_id)
	if buttons.is_empty() or current_index < -1 or current_index >= buttons.size():
		return ERR_INVALID_PARAMETER
	if accepted_index < -1 or accepted_index >= buttons.size():
		return ERR_INVALID_PARAMETER
	_current_indices[setting_id] = current_index
	_accepted_indices[setting_id] = accepted_index
	_accepted_descriptions[setting_id] = accepted_description
	_refresh_setting(setting_id)
	return OK


## Updates one numeric preview and its accepted value without emitting an edit.
func update_numeric_setting(
		setting_id: StringName,
		current_value: float,
		accepted_value: float,
) -> Error:
	var numeric_setting := _numeric_by_setting.get(setting_id) as NumericSettingScript
	if numeric_setting == null:
		return ERR_INVALID_PARAMETER
	numeric_setting.update_setting(current_value, accepted_value)
	return OK


## Describes whether the focused setting can replace a versioned game default.
func update_acceptance(
		can_accept: bool,
		matches_standard: bool,
		subject: String,
) -> void:
	_accept_button.disabled = not can_accept or matches_standard
	if not can_accept:
		_accept_button.text = "Keine Spielstandard-Einstellung fokussiert"
	elif matches_standard:
		_accept_button.text = "%s ist bereits Spielstandard" % subject
	else:
		_accept_button.text = "%s als Spielstandard übernehmen" % subject


## Shows a non-persistent result for the last menu action.
func show_feedback(message: String, is_error: bool = false) -> void:
	_feedback_status.text = message
	_feedback_status.add_theme_color_override(
		"font_color",
		Color(0.96, 0.52, 0.46, 1) if is_error else Color(0.7, 0.79, 0.82, 1),
	)


## Gives focus to the primary camera setting whenever the menu opens.
func focus_primary_setting() -> void:
	_select_tab(0, false)
	_focus_setting(SETTING_CAMERA_ZOOM)


## Releases retained UI focus when the menu closes.
func release_menu_focus() -> void:
	for control in find_children("*", "Control", true, false):
		var focus_control := control as Control
		if focus_control != null and focus_control.has_focus():
			focus_control.release_focus()


## Returns the setting row most recently focused in the open menu.
func get_focused_setting_id() -> StringName:
	return _focused_setting_id


## Returns the selected option index for deterministic menu tests.
func get_current_index(setting_id: StringName) -> int:
	return int(_current_indices.get(setting_id, -1))


## Returns the visible value for deterministic numeric-setting tests.
func get_numeric_value(setting_id: StringName) -> float:
	var numeric_setting := _numeric_by_setting.get(setting_id) as NumericSettingScript
	if numeric_setting == null:
		return NAN
	return numeric_setting.get_current_value()


func _register_tabs() -> void:
	var tab_group := ButtonGroup.new()
	tab_group.allow_unpress = false
	for tab_index in range(_tab_buttons.size()):
		var button := _tab_buttons[tab_index]
		button.text = TAB_TITLES[tab_index]
		button.toggle_mode = true
		button.button_group = tab_group
		button.pressed.connect(_on_tab_pressed.bind(tab_index))
		_apply_base_button_theme(button)


func _register_settings() -> void:
	_register_setting(
		SETTING_CAMERA_CONTEXT,
		_camera_context_buttons,
		["Außenwelt", "Dorf", "Dungeon", "Kleiner Innenraum"],
	)
	_register_setting(
		SETTING_CAMERA_ZOOM,
		_camera_zoom_buttons,
		["0,75×", "1,00×", "1,50×"],
		$Menu/Pages/CameraPage/Content/ZoomStandardStatus,
	)
	_register_setting(
		SETTING_HERO_SIZE,
		_hero_size_buttons,
		["64 px", "80 px", "96 px"],
		$Menu/Pages/ScalePage/Content/HeroStandardStatus,
	)
	_register_setting(
		SETTING_TILE_SIZE,
		_tile_size_buttons,
		["32 × 32 px", "48 × 48 px", "64 × 64 px"],
		$Menu/Pages/ScalePage/Content/TileStandardStatus,
	)
	_register_setting(
		SETTING_HERO_GRAPHICS,
		_hero_graphics_buttons,
		["Comic High", "Comic Mittel", "Comic Low", "Pixel Art High", "Pixel Art Low"],
	)
	_register_setting(
		SETTING_HERO_FRAMES,
		_hero_frames_buttons,
		["8 Frames", "10 Frames", "12 Frames", "14 Frames", "16 Frames"],
	)
	_register_setting(
		SETTING_HERO_FPS,
		_hero_fps_buttons,
		[
			"Neu",
			"8 FPS",
			"10 FPS",
			"12 FPS",
			"14 FPS",
			"16 FPS",
		],
	)
	_register_setting(
		SETTING_PIXEL_SNAP,
		_pixel_snap_buttons,
		["AUS", "AN"],
		$Menu/Pages/RenderingPage/Content/PixelSnapStandardStatus,
	)
	_register_setting(
		SETTING_TEXTURE_FILTER,
		_texture_filter_buttons,
		["Nearest-Neighbor", "Weich"],
		$Menu/Pages/RenderingPage/Content/TextureFilterStandardStatus,
	)
	_register_setting(
		SETTING_WORLD_STATE,
		_world_state_buttons,
		["Beschädigt", "Wiederhergestellt"],
	)
	_register_setting(
		SETTING_FOG,
		_fog_buttons,
		["Gering", "Mittel", "Hoch"],
		$Menu/Pages/WorldPage/Content/FogStandardStatus,
	)
	_register_setting(
		SETTING_LIGHT,
		_light_buttons,
		["Profil 1", "Profil 2"],
		$Menu/Pages/WorldPage/Content/LightStandardStatus,
	)
	_register_setting(
		SETTING_DIAGNOSTICS,
		_diagnostics_buttons,
		["AUS", "AN"],
	)
	_register_setting(
		SETTING_PERFORMANCE,
		_performance_buttons,
		["AUS", "AN"],
	)
	_register_setting(
		SETTING_COLLISION,
		_collision_buttons,
		["AUS", "AN"],
	)


func _register_numeric_settings() -> void:
	for numeric_setting in _numeric_settings:
		_numeric_by_setting[numeric_setting.setting_id] = numeric_setting
		numeric_setting.value_changed.connect(_on_numeric_value_changed)
		numeric_setting.focused.connect(_on_setting_focused)


func _register_setting(
		setting_id: StringName,
		buttons: Array[Button],
		labels: Array[String],
		status_label: Label = null,
) -> void:
	_buttons_by_setting[setting_id] = buttons
	_labels_by_setting[setting_id] = labels
	_current_indices[setting_id] = 0
	_accepted_indices[setting_id] = -1
	_accepted_descriptions[setting_id] = ""
	if status_label != null:
		_status_by_setting[setting_id] = status_label
	var button_group := ButtonGroup.new()
	button_group.allow_unpress = false
	for option_index in range(buttons.size()):
		var button := buttons[option_index]
		button.toggle_mode = true
		button.button_group = button_group
		button.custom_minimum_size = Vector2(142.0, 42.0)
		button.pressed.connect(
			_on_option_button_pressed.bind(setting_id, option_index)
		)
		button.focus_entered.connect(_on_setting_focused.bind(setting_id))
		_apply_base_button_theme(button)
	_refresh_setting(setting_id)


func _refresh_setting(setting_id: StringName) -> void:
	var buttons := _setting_buttons(setting_id)
	if buttons.is_empty():
		return
	var labels: Array = _labels_by_setting.get(setting_id, [])
	var current_index := int(_current_indices.get(setting_id, 0))
	var accepted_index := int(_accepted_indices.get(setting_id, -1))
	for option_index in range(buttons.size()):
		var button := buttons[option_index]
		var is_standard := option_index == accepted_index
		var is_current := option_index == current_index
		button.set_pressed_no_signal(is_current)
		button.text = (
			("● " if is_current else "")
			+ ("★ " if is_standard else "")
			+ str(labels[option_index])
		)
		button.tooltip_text = (
			_setting_tooltip(str(labels[option_index]), is_current, is_standard)
		)
		_apply_option_style(button, is_standard)
	_refresh_setting_status(setting_id)


func _refresh_setting_status(setting_id: StringName) -> void:
	var status := _status_by_setting.get(setting_id) as Label
	if status == null:
		return
	var labels: Array = _labels_by_setting.get(setting_id, [])
	var current_index := int(_current_indices.get(setting_id, 0))
	var accepted_index := int(_accepted_indices.get(setting_id, -1))
	var accepted_name := str(_accepted_descriptions.get(setting_id, ""))
	if accepted_name.is_empty() and accepted_index >= 0:
		accepted_name = str(labels[accepted_index])
	if current_index == accepted_index and accepted_index >= 0:
		status.text = "Entspricht dem Spielstandard · ★ %s" % accepted_name
		return
	status.text = (
		"Nicht übernommener Testwert · ★ Spielstandard: %s" % accepted_name
	)


func _setting_tooltip(
		label: String,
		is_current: bool,
		is_standard: bool,
) -> String:
	var states: Array[String] = []
	if is_current:
		states.append("aktueller Testwert")
	if is_standard:
		states.append("Spielstandard")
	if states.is_empty():
		return label
	return "%s · %s" % [label, " und ".join(states)]


func _setting_buttons(setting_id: StringName) -> Array[Button]:
	var result: Array[Button] = []
	var stored: Variant = _buttons_by_setting.get(setting_id)
	if not stored is Array:
		return result
	for value in stored:
		var button := value as Button
		if button != null:
			result.append(button)
	return result


func _select_tab(tab_index: int, focus_page: bool = true) -> void:
	_active_tab = clampi(tab_index, 0, _pages.size() - 1)
	for page_index in range(_pages.size()):
		_pages[page_index].visible = page_index == _active_tab
		_tab_buttons[page_index].set_pressed_no_signal(page_index == _active_tab)
	if focus_page:
		_focus_setting(TAB_PRIMARY_SETTINGS[_active_tab])


func _focus_setting(setting_id: StringName) -> void:
	if setting_id == SETTING_TEMPLE_FLOOR:
		temple_floor_option.grab_focus()
		return
	var numeric_setting := _numeric_by_setting.get(setting_id) as NumericSettingScript
	if numeric_setting != null:
		numeric_setting.grab_slider_focus()
		return
	var buttons := _setting_buttons(setting_id)
	if buttons.is_empty():
		return
	var current_index := clampi(
		int(_current_indices.get(setting_id, 0)),
		0,
		buttons.size() - 1,
	)
	buttons[current_index].grab_focus()


func _apply_base_button_theme(button: Button) -> void:
	button.add_theme_font_size_override("font_size", 17)
	button.add_theme_color_override("font_color", Color(0.84, 0.87, 0.86, 1))
	button.add_theme_color_override("font_hover_color", Color(0.96, 0.98, 0.97, 1))
	button.add_theme_color_override("font_pressed_color", Color(1, 1, 1, 1))
	button.add_theme_stylebox_override("normal", _normal_style)
	button.add_theme_stylebox_override("hover", _hover_style)
	button.add_theme_stylebox_override("pressed", _pressed_style)
	button.add_theme_stylebox_override("focus", _focus_style)


func _apply_option_style(button: Button, is_standard: bool) -> void:
	button.add_theme_stylebox_override(
		"normal",
		_standard_style if is_standard else _normal_style,
	)
	button.add_theme_stylebox_override(
		"hover",
		_standard_hover_style if is_standard else _hover_style,
	)
	button.add_theme_stylebox_override(
		"pressed",
		_standard_pressed_style if is_standard else _pressed_style,
	)


func _create_styles() -> void:
	_normal_style = _create_style(
		Color(0.075, 0.098, 0.11, 1),
		Color(0.34, 0.42, 0.45, 1),
		2,
	)
	_hover_style = _create_style(
		Color(0.11, 0.14, 0.16, 1),
		Color(0.54, 0.68, 0.72, 1),
		2,
	)
	_pressed_style = _create_style(
		Color(0.12, 0.22, 0.27, 1),
		Color(0.45, 0.82, 0.9, 1),
		2,
	)
	_standard_style = _create_style(
		Color(0.12, 0.105, 0.065, 1),
		Color(0.86, 0.66, 0.22, 1),
		3,
	)
	_standard_hover_style = _create_style(
		Color(0.17, 0.14, 0.075, 1),
		Color(1.0, 0.82, 0.36, 1),
		3,
	)
	_standard_pressed_style = _create_style(
		Color(0.24, 0.19, 0.08, 1),
		Color(1.0, 0.86, 0.42, 1),
		3,
	)
	_focus_style = _create_style(
		Color(0, 0, 0, 0),
		Color(0.58, 0.9, 1.0, 1),
		2,
	)


func _create_style(
		background_color: Color,
		border_color: Color,
		border_width: int,
) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = background_color
	style.border_color = border_color
	style.border_width_left = border_width
	style.border_width_top = border_width
	style.border_width_right = border_width
	style.border_width_bottom = border_width
	style.corner_radius_top_left = 5
	style.corner_radius_top_right = 5
	style.corner_radius_bottom_left = 5
	style.corner_radius_bottom_right = 5
	style.content_margin_left = 10.0
	style.content_margin_top = 6.0
	style.content_margin_right = 10.0
	style.content_margin_bottom = 6.0
	return style


func _on_tab_pressed(tab_index: int) -> void:
	_select_tab(tab_index)


func _on_option_button_pressed(setting_id: StringName, option_index: int) -> void:
	_focused_setting_id = setting_id
	_focus_status.text = "Fokus: %s" % _setting_display_name(setting_id)
	setting_focused.emit(setting_id)
	option_selected.emit(setting_id, option_index)


func _on_numeric_value_changed(setting_id: StringName, value: float) -> void:
	_focused_setting_id = setting_id
	_focus_status.text = "Fokus: %s" % _setting_display_name(setting_id)
	setting_focused.emit(setting_id)
	numeric_value_changed.emit(setting_id, value)


func _on_setting_focused(setting_id: StringName) -> void:
	_focused_setting_id = setting_id
	_focus_status.text = "Fokus: %s" % _setting_display_name(setting_id)
	setting_focused.emit(setting_id)


func _on_accept_button_pressed() -> void:
	accept_requested.emit()


func _on_close_button_pressed() -> void:
	close_requested.emit()


func _on_temple_floor_selected(option_index: int) -> void:
	_on_setting_focused(SETTING_TEMPLE_FLOOR)
	option_selected.emit(SETTING_TEMPLE_FLOOR, option_index)


func _setting_display_name(setting_id: StringName) -> String:
	match setting_id:
		SETTING_CAMERA_CONTEXT:
			return "Kamera-Zielbereich"
		SETTING_CAMERA_ZOOM:
			return "Kamera-Zoom"
		SETTING_HERO_SIZE:
			return "Heldenhöhe"
		SETTING_TILE_SIZE:
			return "Tilegröße"
		SETTING_HERO_GRAPHICS:
			return "Grafik: Figur und Portal-Labor"
		SETTING_TEMPLE_FLOOR:
			return "Tempelboden"
		SETTING_HERO_FRAMES:
			return "Heldenanimation · Frames"
		SETTING_HERO_FPS:
			return "Heldenanimation · FPS"
		SETTING_PIXEL_SNAP:
			return "Pixel-Snap"
		SETTING_TEXTURE_FILTER:
			return "Texturfilter"
		SETTING_WORLD_STATE:
			return "Weltzustandsvorschau"
		SETTING_FOG:
			return "Nebel"
		SETTING_LIGHT:
			return "Licht"
		SETTING_DIAGNOSTICS:
			return "Spieldiagnose"
		SETTING_PERFORMANCE:
			return "Leistung und Technik"
		SETTING_COLLISION:
			return "Kollisionsflächen"
		SETTING_SNEAK_SPEED:
			return "Schleichgeschwindigkeit"
		SETTING_WALK_SPEED:
			return "Gehgeschwindigkeit"
		SETTING_JOG_SPEED:
			return "Laufgeschwindigkeit"
		SETTING_RUN_SPEED:
			return "Renngeschwindigkeit"
		SETTING_SPRINT_SPEED:
			return "Sprintgeschwindigkeit"
		SETTING_STANDING_JUMP_HEIGHT:
			return "Stehsprunghöhe"
		SETTING_WALK_JUMP_HEIGHT:
			return "Gehsprunghöhe"
		SETTING_WALK_JUMP_DISTANCE:
			return "Gehsprungweite"
		SETTING_JOG_JUMP_HEIGHT:
			return "Laufsprunghöhe"
		SETTING_JOG_JUMP_DISTANCE:
			return "Laufsprungweite"
		SETTING_RUN_JUMP_HEIGHT:
			return "Rennsprunghöhe"
		SETTING_RUN_JUMP_DISTANCE:
			return "Rennsprungweite"
		SETTING_SPRINT_JUMP_HEIGHT:
			return "Sprintsprunghöhe"
		SETTING_SPRINT_JUMP_DISTANCE:
			return "Sprintsprungweite"
	return "Testlabor"
