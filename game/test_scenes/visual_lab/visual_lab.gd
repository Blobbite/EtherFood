extends Control

enum CameraZoomPreset {
	WIDE,
	MEDIUM,
	NEAR,
}

enum HeroSizePreset {
	SMALL,
	MEDIUM,
	LARGE,
}

enum TileSizePreset {
	SMALL,
	MEDIUM,
	LARGE,
}

enum WorldStatePreset {
	DAMAGED,
	RESTORED,
}

enum TextureFilterPreset {
	NEAREST,
	SOFT,
}

enum HeroGraphicsPreset {
	COMIC_HIGH,
	COMIC_MID,
	COMIC_LOW,
	PIXEL_HIGH,
	PIXEL_LOW,
}

enum HeroFpsPreset {
	NEW = -1,
	FPS_8,
	FPS_10,
	FPS_12,
	FPS_14,
	FPS_16,
}

const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const TILE_GRID_PREVIEW_SCRIPT := preload("res://test_scenes/visual_lab/tile_grid_preview.gd")
const WORLD_STATE_PREVIEW_SCRIPT := preload("res://test_scenes/visual_lab/world_state_preview.gd")
const COLLISION_DEBUG_OVERLAY_SCRIPT := preload(
	"res://test_scenes/visual_lab/collision_debug_overlay.gd"
)
const CameraProfileResource := preload("res://shared/resources/camera_profile.gd")
const HeroMovementConfigResource := preload(
	"res://shared/resources/hero_movement_config.gd"
)
const VisualLabMenuScript := preload("res://test_scenes/visual_lab/visual_lab_menu.gd")
const VisualLabStandardsResource := preload(
	"res://shared/resources/visual_lab_standards.gd"
)
const PlayerCameraControllerScript := preload(
	"res://shared/camera/player_camera_controller.gd"
)
const DEFAULT_STANDARDS: VisualLabStandardsResource = preload(
	"res://shared/resources/visual_lab_standards_v0.tres"
)
const DEFAULT_MOVEMENT_STANDARD: HeroMovementConfigResource = preload(
	"res://shared/resources/hero_movement_v0.tres"
)
const HERO_ANIMATION_LIBRARY := preload(
	"res://test_scenes/characters/heroes/greenhero/green_hero_animation_library.gd"
)
const MAIN_MENU_ROUTE := &"main_menu"
const SETTINGS_VERSION := 5
const DEFAULT_SETTINGS_PATH := "user://visual_lab_settings.cfg"
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const DEFAULT_STANDARDS_PATH := (
	"res://shared/resources/visual_lab_standards_v0.tres"
)
const STANDARDS_PATH_PROJECT_KEY := (
	"etherfood/development/visual_lab_standards_path"
)
const DEFAULT_MOVEMENT_STANDARD_PATH := (
	"res://shared/resources/hero_movement_v0.tres"
)
const MOVEMENT_STANDARD_PATH_PROJECT_KEY := (
	"etherfood/development/hero_movement_standard_path"
)
const SETTINGS_META_SECTION := "meta"
const SETTINGS_SECTION := "visual_lab"
const DIAGNOSTICS_TOGGLE_ACTION := &"dev_diagnostics_toggle"
const PERFORMANCE_TOGGLE_ACTION := &"dev_performance_toggle"
const PerformanceDiagnosticsScript := preload(
	"res://test_scenes/visual_lab/performance_diagnostics.gd"
)
const LabNavigationScript := preload("res://test_scenes/environment/portal_lab/lab_navigation.gd")
const TestRoomScript := preload("res://test_scenes/environment/portal_lab/test_room.gd")
const BlueprintPalette := preload("res://test_scenes/environment/portal_lab/blueprint_palette.gd")
const PortalGraphics := preload("res://test_scenes/environment/portal_lab/portal_graphics.gd")
const COLLISION_DEBUG_TOGGLE_ACTION := &"dev_collision_debug_toggle"
const CONTROLS_TOGGLE_ACTION := &"dev_controls_toggle"
const ACCEPT_STANDARD_ACTION := &"dev_accept_visual_standard"
const DIAGNOSTICS_UPDATE_INTERVAL := 0.2
const PERFORMANCE_UPDATE_INTERVAL := 0.5
const OUTPUT_PIXEL_PHASE_BIAS := 0.25
const WORLD_LEFT := 0
const WORLD_TOP := 0
const WORLD_RIGHT := 3840
const WORLD_BOTTOM := 2160
const CAMERA_ZOOM_NAMES: Array[String] = ["Weit", "Mittel", "Nah"]
const CAMERA_ZOOM_VALUES: Array[float] = [0.75, 1.0, 1.5]
const CAMERA_ZOOM_IDS: Array[String] = ["wide", "medium", "near"]
const CAMERA_CONTEXT_IDS: Array[StringName] = [
	&"world",
	&"village",
	&"dungeon",
	&"small_interior",
]
const CAMERA_CONTEXT_NAMES: Array[String] = [
	"Außenwelt",
	"Dorf",
	"Dungeon",
	"Kleiner Innenraum",
]
const CAMERA_SETTING_KEYS: Array[String] = [
	"camera_zoom_world",
	"camera_zoom_village",
	"camera_zoom_dungeon",
	"camera_zoom_small_interior",
]
const HERO_SIZE_NAMES: Array[String] = ["Klein", "Mittel", "Groß"]
const HERO_SIZE_VALUES: Array[float] = [64.0, 80.0, 96.0]
const HERO_SIZE_IDS: Array[String] = ["small", "medium", "large"]
const HERO_FRAME_IDS: Array[String] = ["8", "10", "12", "14", "16"]
const HERO_GRAPHICS_NAMES: Array[String] = [
	"Comic High", "Comic Mittel", "Comic Low", "Pixel Art High", "Pixel Art Low",
]
const HERO_GRAPHICS_IDS: Array[String] = [
	"comic_high", "comic_mid", "comic_low", "pixel_high", "pixel_low",
]
const HERO_FPS_VALUES: Array[int] = [8, 10, 12, 14, 16]
const HERO_FPS_IDS: Array[String] = ["new", "8", "10", "12", "14", "16"]
const TILE_SIZE_NAMES: Array[String] = ["Klein", "Mittel", "Groß"]
const TILE_SIZE_VALUES: Array[int] = [32, 48, 64]
const TILE_SIZE_IDS: Array[String] = ["small", "medium", "large"]
const WORLD_STATE_NAMES: Array[String] = ["Beschädigt", "Wiederhergestellt"]
const WORLD_STATE_IDS: Array[String] = ["damaged", "restored"]
const FOG_SETTING_KEYS: Array[String] = ["damaged_fog", "restored_fog"]
const LIGHT_SETTING_KEYS: Array[String] = ["damaged_light", "restored_light"]
const TEXTURE_FILTER_NAMES: Array[String] = ["Nearest-Neighbor", "Weich"]
const TEXTURE_FILTER_IDS: Array[String] = ["nearest", "soft"]
const TEXTURE_FILTER_VALUES: Array[int] = [
	CanvasItem.TEXTURE_FILTER_NEAREST,
	CanvasItem.TEXTURE_FILTER_LINEAR,
]
const REFERENCE_ASPECT_RATIO := "16:9"
const SPEED_SETTING_IDS: Array[StringName] = [
	VisualLabMenuScript.SETTING_SNEAK_SPEED,
	VisualLabMenuScript.SETTING_WALK_SPEED,
	VisualLabMenuScript.SETTING_JOG_SPEED,
	VisualLabMenuScript.SETTING_RUN_SPEED,
	VisualLabMenuScript.SETTING_SPRINT_SPEED,
]
const JUMP_HEIGHT_SETTING_IDS: Array[StringName] = [
	VisualLabMenuScript.SETTING_STANDING_JUMP_HEIGHT,
	VisualLabMenuScript.SETTING_WALK_JUMP_HEIGHT,
	VisualLabMenuScript.SETTING_JOG_JUMP_HEIGHT,
	VisualLabMenuScript.SETTING_RUN_JUMP_HEIGHT,
	VisualLabMenuScript.SETTING_SPRINT_JUMP_HEIGHT,
]
const JUMP_DISTANCE_SETTING_IDS: Array[StringName] = [
	VisualLabMenuScript.SETTING_WALK_JUMP_DISTANCE,
	VisualLabMenuScript.SETTING_JOG_JUMP_DISTANCE,
	VisualLabMenuScript.SETTING_RUN_JUMP_DISTANCE,
	VisualLabMenuScript.SETTING_SPRINT_JUMP_DISTANCE,
]
const GAMEPLAY_SETTING_SUBJECTS: Dictionary = {
	VisualLabMenuScript.SETTING_SNEAK_SPEED: "Schleichgeschwindigkeit",
	VisualLabMenuScript.SETTING_WALK_SPEED: "Gehgeschwindigkeit",
	VisualLabMenuScript.SETTING_JOG_SPEED: "Laufgeschwindigkeit",
	VisualLabMenuScript.SETTING_RUN_SPEED: "Renngeschwindigkeit",
	VisualLabMenuScript.SETTING_SPRINT_SPEED: "Sprintgeschwindigkeit",
	VisualLabMenuScript.SETTING_STANDING_JUMP_HEIGHT: "Stehsprunghöhe",
	VisualLabMenuScript.SETTING_WALK_JUMP_HEIGHT: "Gehsprunghöhe",
	VisualLabMenuScript.SETTING_WALK_JUMP_DISTANCE: "Gehsprungweite",
	VisualLabMenuScript.SETTING_JOG_JUMP_HEIGHT: "Laufsprunghöhe",
	VisualLabMenuScript.SETTING_JOG_JUMP_DISTANCE: "Laufsprungweite",
	VisualLabMenuScript.SETTING_RUN_JUMP_HEIGHT: "Rennsprunghöhe",
	VisualLabMenuScript.SETTING_RUN_JUMP_DISTANCE: "Rennsprungweite",
	VisualLabMenuScript.SETTING_SPRINT_JUMP_HEIGHT: "Sprintsprunghöhe",
	VisualLabMenuScript.SETTING_SPRINT_JUMP_DISTANCE: "Sprintsprungweite",
}

@onready var player_camera: PlayerCameraControllerScript = (
	$TestWorld/HeroCharacter/PlayerCamera
)
@onready var hero_visual: Node2D = $TestWorld/HeroCharacter/Visual
@onready var hero_character: HERO_SCRIPT = $TestWorld/HeroCharacter
@onready var hero_texture_scale: Node2D = (
	$TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale
)
@onready var hero_sprite: AnimatedSprite2D = (
	$TestWorld/HeroCharacter/Visual/JumpVisual/Appearance/TextureScale/HeroSprite
)
@onready var tile_grid_preview: TILE_GRID_PREVIEW_SCRIPT = (
	$TestWorld/TileComparison/TileGridPreview
)
@onready var world_state_preview: WORLD_STATE_PREVIEW_SCRIPT = $TestWorld/WorldStatePreview
@onready var diagnostics_panel: Control = $InterfaceLayer/DiagnosticsPanel
@onready var diagnostics_values: Label = $InterfaceLayer/DiagnosticsPanel/Values
@onready var performance_panel: Control = $InterfaceLayer/PerformancePanel
@onready var performance_values: Label = $InterfaceLayer/PerformancePanel/Values
@onready var collision_debug_overlay: COLLISION_DEBUG_OVERLAY_SCRIPT = (
	$TestWorld/CollisionDebugOverlay
)
@onready var controls_panel: Panel = $InterfaceLayer/HudPanel
@onready var controls_interface: VisualLabMenuScript = $InterfaceLayer/Interface
@onready var controls_prompt: Label = $InterfaceLayer/ControlsPrompt
@onready var test_world: Node2D = $TestWorld
@onready var lab_navigation: LabNavigationScript = $LabNavigation
@onready var room_status: Label = $InterfaceLayer/RoomStatus
@onready var room_actions: HBoxContainer = $InterfaceLayer/RoomActions
@onready var camera_status: Label = controls_interface.camera_status
@onready var hero_size_status: Label = controls_interface.hero_size_status
@onready var hero_graphics_status: Label = controls_interface.hero_graphics_status
@onready var tile_size_status: Label = controls_interface.tile_size_status
@onready var world_state_status: Label = controls_interface.world_state_status
@onready var window_size_status: Label = controls_interface.window_size_status

var _navigation_requested := false
var _diagnostics_elapsed := 0.0
var _performance_elapsed := 0.0
var _performance_diagnostics := PerformanceDiagnosticsScript.new()
var _selected_camera_context := 0
var _selected_camera_zoom: int = CameraZoomPreset.MEDIUM
var _selected_camera_zooms: Array[int] = [
	CameraZoomPreset.MEDIUM,
	CameraZoomPreset.MEDIUM,
	CameraZoomPreset.MEDIUM,
	CameraZoomPreset.NEAR,
]
var _selected_hero_size: int = HeroSizePreset.MEDIUM
var _selected_hero_graphics: int = HeroGraphicsPreset.COMIC_HIGH
var _selected_temple_floor := 0
var _selected_hero_frames: int = HeroFpsPreset.FPS_8
var _selected_hero_fps: int = HeroFpsPreset.FPS_8
var _selected_tile_size: int = TileSizePreset.SMALL
var _selected_world_state: int = WorldStatePreset.DAMAGED
var _selected_fog_variants: Array[int] = [
	WORLD_STATE_PREVIEW_SCRIPT.DAMAGED_DEFAULT_FOG_VARIANT,
	WORLD_STATE_PREVIEW_SCRIPT.RESTORED_DEFAULT_FOG_VARIANT,
]
var _selected_light_variants: Array[int] = [
	WORLD_STATE_PREVIEW_SCRIPT.DAMAGED_DEFAULT_LIGHT_VARIANT,
	WORLD_STATE_PREVIEW_SCRIPT.RESTORED_DEFAULT_LIGHT_VARIANT,
]
var _pixel_snap_enabled := true
var _selected_texture_filter: int = TextureFilterPreset.NEAREST
var _standards: VisualLabStandardsResource = DEFAULT_STANDARDS
var _movement_standard: HeroMovementConfigResource = DEFAULT_MOVEMENT_STANDARD
var _movement_preview: HeroMovementConfigResource
var _active_camera_profile: CameraProfileResource = CameraProfileResource.new()
var _pixel_snap_viewport: Viewport
var _initial_viewport_pixel_snap := false
var _initial_viewport_vertex_snap := false
var _initial_camera_position := Vector2.ZERO
var _initial_hero_visual_position := Vector2.ZERO
var _initial_camera_top_level := false
var _initial_hero_visual_top_level := false
var _texture_filter_targets: Array[CanvasItem] = []
var _initial_texture_filters: Array[int] = []
var _lab_world_bounds := Rect2(WORLD_LEFT, WORLD_TOP, WORLD_RIGHT, WORLD_BOTTOM)


func _ready() -> void:
	_pixel_snap_viewport = get_viewport()
	_initial_viewport_pixel_snap = _pixel_snap_viewport.snap_2d_transforms_to_pixel
	_initial_viewport_vertex_snap = _pixel_snap_viewport.snap_2d_vertices_to_pixel
	_initial_camera_position = player_camera.position
	_initial_hero_visual_position = hero_visual.position
	_initial_camera_top_level = player_camera.top_level
	_initial_hero_visual_top_level = hero_visual.top_level
	_collect_texture_filter_targets(test_world)
	controls_interface.option_selected.connect(_on_menu_option_selected)
	controls_interface.numeric_value_changed.connect(_on_menu_numeric_value_changed)
	controls_interface.setting_focused.connect(_on_menu_setting_focused)
	controls_interface.accept_requested.connect(_on_accept_requested)
	controls_interface.close_requested.connect(_on_menu_close_requested)
	player_camera.limit_left = WORLD_LEFT
	player_camera.limit_top = WORLD_TOP
	player_camera.limit_right = WORLD_RIGHT
	player_camera.limit_bottom = WORLD_BOTTOM
	player_camera.position_smoothing_enabled = false
	player_camera.enabled = true
	player_camera.make_current()
	diagnostics_panel.visible = false
	performance_panel.visible = false
	collision_debug_overlay.set_debug_visible(false)
	resized.connect(_on_visual_lab_resized)
	get_window().size_changed.connect(_on_main_window_size_changed)
	_load_standards()
	_load_movement_standard()
	_load_settings()
	_apply_camera_zoom()
	_apply_hero_graphics()
	_apply_hero_size()
	_apply_tile_size()
	_apply_world_state()
	_apply_pixel_snap()
	_apply_texture_filter()
	_update_window_size_status()
	_refresh_menu()
	_set_controls_visible(false)
	lab_navigation.room_changed.connect(_on_lab_room_changed)
	if lab_navigation.initialize(test_world, hero_character) != OK:
		push_error("VisualLab could not open its portal tower.")


func _exit_tree() -> void:
	if _pixel_snap_viewport != null and is_instance_valid(_pixel_snap_viewport):
		_pixel_snap_viewport.snap_2d_transforms_to_pixel = _initial_viewport_pixel_snap
		_pixel_snap_viewport.snap_2d_vertices_to_pixel = _initial_viewport_vertex_snap
	_restore_texture_filters()


func _process(delta: float) -> void:
	_update_pixel_snap_render_alignment()
	_update_soul_prompt()
	if diagnostics_panel.visible:
		_diagnostics_elapsed += delta
		if _diagnostics_elapsed >= DIAGNOSTICS_UPDATE_INTERVAL:
			_diagnostics_elapsed = 0.0
			_update_diagnostics_values()
	if performance_panel.visible:
		_performance_elapsed += delta
		if _performance_elapsed >= PERFORMANCE_UPDATE_INTERVAL:
			_performance_elapsed = 0.0
			_update_performance_values()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(PERFORMANCE_TOGGLE_ACTION):
		get_viewport().set_input_as_handled()
		if not _is_repeated_key_event(event):
			_toggle_performance()
		return
	if event.is_action_pressed(DIAGNOSTICS_TOGGLE_ACTION):
		get_viewport().set_input_as_handled()
		if not _is_repeated_key_event(event):
			_toggle_diagnostics()
		return
	if event.is_action_pressed(COLLISION_DEBUG_TOGGLE_ACTION):
		get_viewport().set_input_as_handled()
		if not _is_repeated_key_event(event):
			_toggle_collision_debug()
		return
	if event.is_action_pressed(CONTROLS_TOGGLE_ACTION):
		get_viewport().set_input_as_handled()
		if not _is_repeated_key_event(event):
			_set_controls_visible(not controls_panel.visible)
		return
	if event.is_action_pressed(ACCEPT_STANDARD_ACTION):
		get_viewport().set_input_as_handled()
		if controls_panel.visible and not _is_repeated_key_event(event):
			_on_accept_requested()
		return
	if event.is_action_pressed(&"gameplay_interact"):
		get_viewport().set_input_as_handled()
		if not controls_panel.visible and not _is_repeated_key_event(event):
			hero_character.try_interact()
		return
	var room := lab_navigation.current_room
	if (
		room != null and room.soul != null and room.soul.is_conversation_active()
		and event.is_action_pressed(&"ui_cancel")
	):
		get_viewport().set_input_as_handled()
		room.soul.dismiss_dialogue()
		return
	if _navigation_requested or not event.is_action_pressed(&"ui_cancel"):
		return

	get_viewport().set_input_as_handled()
	_navigation_requested = true
	_save_settings()
	var navigation_error := SceneRouter.navigate(MAIN_MENU_ROUTE)
	if navigation_error == OK:
		return

	_navigation_requested = false
	push_error(
		"VisualLab failed to navigate to route '%s' with error %d."
		% [MAIN_MENU_ROUTE, navigation_error],
	)


func _change_camera_zoom(direction: int) -> void:
	var next_zoom := clampi(
		_selected_camera_zoom + direction,
		CameraZoomPreset.WIDE,
		CameraZoomPreset.NEAR,
	)
	if next_zoom == _selected_camera_zoom:
		return
	_set_camera_zoom(next_zoom)


func _set_camera_context(context_index: int) -> void:
	_selected_camera_context = clampi(
		context_index,
		0,
		CAMERA_CONTEXT_IDS.size() - 1,
	)
	_selected_camera_zoom = _selected_camera_zooms[_selected_camera_context]
	_apply_camera_zoom()
	_save_settings()
	_refresh_menu()


func _set_camera_zoom(zoom_index: int) -> void:
	_selected_camera_zoom = clampi(
		zoom_index,
		CameraZoomPreset.WIDE,
		CameraZoomPreset.NEAR,
	)
	_selected_camera_zooms[_selected_camera_context] = _selected_camera_zoom
	_apply_camera_zoom()
	_save_settings()
	_refresh_menu()


func _apply_camera_zoom() -> void:
	var selected_zoom := CAMERA_ZOOM_VALUES[_selected_camera_zoom]
	var effective_zoom := maxf(selected_zoom, _minimum_camera_zoom())
	_active_camera_profile.base_zoom = effective_zoom
	_active_camera_profile.profile_name = (
		"Testlabor · %s" % CAMERA_CONTEXT_NAMES[_selected_camera_context]
	)
	var profile_error := player_camera.set_profile(_active_camera_profile)
	if profile_error != OK:
		push_error("VisualLab could not apply its camera profile.")
	_update_pixel_snap_render_alignment()
	var limited_suffix := ""
	if effective_zoom > selected_zoom:
		limited_suffix = " · durch Weltgröße begrenzt"
	var inheritance_suffix := ""
	if (
		CAMERA_CONTEXT_IDS[_selected_camera_context] == &"village"
		and _standards.village_inherits_world
	):
		inheritance_suffix = " · Spielstandard erbt Außenwelt"
	camera_status.text = "Kamera: %s · %s · %s×%s%s" % [
		CAMERA_CONTEXT_NAMES[_selected_camera_context],
		CAMERA_ZOOM_NAMES[_selected_camera_zoom],
		_format_camera_zoom(effective_zoom),
		limited_suffix,
		inheritance_suffix,
	]
	_refresh_diagnostics_if_visible()


func _change_hero_size(direction: int) -> void:
	var next_size := clampi(
		_selected_hero_size + direction,
		HeroSizePreset.SMALL,
		HeroSizePreset.LARGE,
	)
	if next_size == _selected_hero_size:
		return
	_set_hero_size(next_size)


func _set_hero_size(size_index: int) -> void:
	_selected_hero_size = clampi(
		size_index,
		HeroSizePreset.SMALL,
		HeroSizePreset.LARGE,
	)
	_apply_hero_size()
	_save_settings()
	_refresh_menu()


func _apply_hero_size() -> void:
	var selected_height := HERO_SIZE_VALUES[_selected_hero_size]
	hero_character.set_appearance_height(selected_height)
	hero_size_status.text = "Figur: %s · %d Weltpixel" % [
		HERO_SIZE_NAMES[_selected_hero_size],
		roundi(hero_character.get_appearance_height()),
	]
	_refresh_diagnostics_if_visible()


func _set_hero_graphics(graphics_index: int) -> void:
	_selected_hero_graphics = clampi(
		graphics_index,
		HeroGraphicsPreset.COMIC_HIGH,
		HeroGraphicsPreset.PIXEL_LOW,
	)
	_apply_hero_graphics()
	_save_settings()
	_refresh_menu()


func _set_hero_frames(frame_index: int) -> void:
	_selected_hero_frames = clampi(
		frame_index,
		HeroFpsPreset.FPS_8,
		HeroFpsPreset.FPS_16,
	)
	_selected_hero_fps = HeroFpsPreset.NEW
	_apply_hero_graphics()
	_save_settings()
	_refresh_menu()


func _set_hero_fps(fps_index: int) -> void:
	_selected_hero_fps = clampi(
		fps_index - 1,
		HeroFpsPreset.NEW,
		HeroFpsPreset.FPS_16,
	)
	_apply_hero_graphics()
	_save_settings()
	_refresh_menu()


func _apply_hero_graphics() -> void:
	var previous_animation := hero_sprite.animation
	var was_playing := hero_sprite.is_playing()
	hero_sprite.sprite_frames = HERO_ANIMATION_LIBRARY.build(
		HERO_GRAPHICS_IDS[_selected_hero_graphics],
		HERO_FPS_VALUES[_selected_hero_frames],
		_selected_hero_playback_fps(),
	)
	if not hero_sprite.sprite_frames.has_animation(previous_animation):
		previous_animation = StringName("stand_%s" % hero_character.get_animation_direction_name())
		hero_sprite.animation = previous_animation
	hero_sprite.set_frame_and_progress(0, 0.0)
	if was_playing:
		hero_sprite.play(previous_animation)
	else:
		hero_sprite.pause()
	var animation_controller := hero_character.get_node("AnimationController")
	animation_controller.call(&"refresh_animation")
	animation_controller.call(&"apply_sprite_layout")
	var fps_label := "Neu"
	if _selected_hero_fps != HeroFpsPreset.NEW:
		fps_label = "%d FPS" % _selected_hero_playback_fps()
	hero_graphics_status.text = "Hero-Grafik: %s · %d Frames · %s" % [
		HERO_GRAPHICS_NAMES[_selected_hero_graphics],
		HERO_FPS_VALUES[_selected_hero_frames],
		fps_label,
	]
	_apply_portal_graphics()
	_refresh_diagnostics_if_visible()


func _selected_hero_playback_fps() -> int:
	if _selected_hero_fps == HeroFpsPreset.NEW:
		return HERO_FPS_VALUES[_selected_hero_frames]
	return HERO_FPS_VALUES[_selected_hero_fps]


func _apply_portal_graphics() -> void:
	var graphics_id := StringName(HERO_GRAPHICS_IDS[_selected_hero_graphics])
	if lab_navigation.current_room != null:
		lab_navigation.current_room.set_graphics_variant(graphics_id)
		lab_navigation.current_room.floor_grid.set_floor_motif(
			PortalGraphics.FLOOR_IDS[_selected_temple_floor],
		)
	controls_interface.portal_graphics_status.text = PortalGraphics.status_text(graphics_id)


func _set_temple_floor(option_index: int) -> void:
	_selected_temple_floor = clampi(option_index, 0, PortalGraphics.FLOOR_IDS.size() - 1)
	if lab_navigation.current_room != null:
		lab_navigation.current_room.floor_grid.set_floor_motif(
			PortalGraphics.FLOOR_IDS[_selected_temple_floor],
		)
	_save_settings()
	_refresh_menu()
	_refresh_diagnostics_if_visible()


func _change_tile_size(direction: int) -> void:
	var next_size := clampi(
		_selected_tile_size + direction,
		TileSizePreset.SMALL,
		TileSizePreset.LARGE,
	)
	if next_size == _selected_tile_size:
		return
	_set_tile_size(next_size)


func _set_tile_size(size_index: int) -> void:
	_selected_tile_size = clampi(
		size_index,
		TileSizePreset.SMALL,
		TileSizePreset.LARGE,
	)
	_apply_tile_size()
	_save_settings()
	_refresh_menu()


func _apply_tile_size() -> void:
	var selected_size := TILE_SIZE_VALUES[_selected_tile_size]
	tile_grid_preview.set_tile_size(selected_size)
	if lab_navigation.current_room != null:
		lab_navigation.current_room.floor_grid.tile_size = selected_size
	tile_size_status.text = "Tiles: %s · %d × %d Weltpixel" % [
		TILE_SIZE_NAMES[_selected_tile_size],
		selected_size,
		selected_size,
	]
	_refresh_diagnostics_if_visible()


func _toggle_world_state() -> void:
	if _selected_world_state == WorldStatePreset.DAMAGED:
		_selected_world_state = WorldStatePreset.RESTORED
	else:
		_selected_world_state = WorldStatePreset.DAMAGED
	_set_world_state(_selected_world_state)


func _set_world_state(world_state: int) -> void:
	_selected_world_state = clampi(
		world_state,
		WorldStatePreset.DAMAGED,
		WorldStatePreset.RESTORED,
	)
	_apply_world_state()
	_save_settings()
	_refresh_menu()


func _apply_world_state() -> void:
	world_state_preview.set_world_state(_selected_world_state)
	world_state_status.text = "Weltzustand: %s" % WORLD_STATE_NAMES[_selected_world_state]
	_apply_atmosphere()


func _cycle_fog_variant() -> void:
	var variant_count := world_state_preview.get_fog_variant_count(
		_selected_world_state
	)
	_set_fog_variant(wrapi(
		_selected_fog_variants[_selected_world_state] + 1,
		0,
		variant_count,
	))


func _set_fog_variant(variant_index: int) -> void:
	_selected_fog_variants[_selected_world_state] = clampi(
		variant_index,
		0,
		world_state_preview.get_fog_variant_count(_selected_world_state) - 1,
	)
	_apply_atmosphere()
	_save_settings()
	_refresh_menu()


func _cycle_light_variant() -> void:
	var variant_count := world_state_preview.get_light_variant_count(
		_selected_world_state
	)
	_set_light_variant(wrapi(
		_selected_light_variants[_selected_world_state] + 1,
		0,
		variant_count,
	))


func _set_light_variant(variant_index: int) -> void:
	_selected_light_variants[_selected_world_state] = clampi(
		variant_index,
		0,
		world_state_preview.get_light_variant_count(_selected_world_state) - 1,
	)
	_apply_atmosphere()
	if lab_navigation.current_room_id == &"day_night":
		var phases: Array[float] = (
			[0.3, 0.5] if _selected_world_state == WorldStatePreset.DAMAGED else [0.1, 0.0]
		)
		lab_navigation.current_room.cycle_enabled = false
		lab_navigation.current_room.cycle_phase = phases[
			_selected_light_variants[_selected_world_state]
		]
		_refresh_room_actions()
	_save_settings()
	_refresh_menu()


func _apply_atmosphere() -> void:
	world_state_preview.set_atmosphere_variants(
		_selected_fog_variants[_selected_world_state],
		_selected_light_variants[_selected_world_state],
	)
	controls_interface.fog_status.text = (
		"Nebel: %s" % world_state_preview.get_active_fog_name()
	)
	controls_interface.light_status.text = (
		"Licht: %s" % world_state_preview.get_active_light_name()
	)
	_refresh_diagnostics_if_visible()


func _toggle_pixel_snap() -> void:
	_set_pixel_snap_enabled(not _pixel_snap_enabled, true)


func _set_pixel_snap_enabled(
		pixel_snap_enabled: bool,
		persist_and_refresh: bool = false,
) -> void:
	_pixel_snap_enabled = pixel_snap_enabled
	_apply_pixel_snap()
	if persist_and_refresh:
		_save_settings()
		_refresh_menu()


func _apply_pixel_snap() -> void:
	_pixel_snap_viewport.snap_2d_transforms_to_pixel = false
	_pixel_snap_viewport.snap_2d_vertices_to_pixel = false
	_update_pixel_snap_render_alignment()
	_refresh_diagnostics_if_visible()


func _toggle_texture_filter() -> void:
	var next_filter := TextureFilterPreset.SOFT
	if _selected_texture_filter == TextureFilterPreset.SOFT:
		next_filter = TextureFilterPreset.NEAREST
	_set_texture_filter(next_filter, true)


func _set_texture_filter(
		texture_filter: int,
		persist_and_refresh: bool = false,
) -> void:
	_selected_texture_filter = clampi(
		texture_filter,
		TextureFilterPreset.NEAREST,
		TextureFilterPreset.SOFT,
	)
	_apply_texture_filter()
	if persist_and_refresh:
		_save_settings()
		_refresh_menu()


func _set_gameplay_value(setting_id: StringName, value: float) -> Error:
	if (
		_movement_preview == null
		or setting_id not in VisualLabMenuScript.GAMEPLAY_SETTING_IDS
		or not is_finite(value)
	):
		return ERR_INVALID_PARAMETER
	var bounds := _gameplay_setting_bounds(setting_id)
	var setting_step := 5.0 if setting_id in SPEED_SETTING_IDS else 1.0
	var clamped_value := clampf(
		roundf(value / setting_step) * setting_step,
		bounds.x,
		bounds.y,
	)
	_movement_preview.set(setting_id, clamped_value)
	_save_settings()
	_refresh_menu()
	_refresh_diagnostics_if_visible()
	return OK


func _gameplay_setting_bounds(setting_id: StringName) -> Vector2:
	if setting_id in SPEED_SETTING_IDS:
		return Vector2(40.0, 500.0)
	if setting_id in JUMP_HEIGHT_SETTING_IDS:
		return Vector2(8.0, 64.0)
	if setting_id in JUMP_DISTANCE_SETTING_IDS:
		return Vector2(16.0, 160.0)
	return Vector2.ZERO


func _apply_texture_filter() -> void:
	var selected_filter := TEXTURE_FILTER_VALUES[_selected_texture_filter]
	for target in _texture_filter_targets:
		if is_instance_valid(target):
			target.texture_filter = selected_filter as CanvasItem.TextureFilter
	_refresh_diagnostics_if_visible()


func _collect_texture_filter_targets(node: Node) -> void:
	var target := node as CanvasItem
	if target != null and _canvas_item_has_texture(target):
		_texture_filter_targets.append(target)
		_initial_texture_filters.append(target.texture_filter)
	for child in node.get_children():
		_collect_texture_filter_targets(child)


func _canvas_item_has_texture(target: CanvasItem) -> bool:
	if target is TestRoomScript.BlueprintFloor:
		return true
	var particles := target as CPUParticles2D
	if particles != null:
		return particles.texture != null
	var sprite := target as Sprite2D
	if sprite != null:
		return sprite.texture != null
	var animated_sprite := target as AnimatedSprite2D
	return animated_sprite != null and animated_sprite.sprite_frames != null


func _restore_texture_filters() -> void:
	for target_index in range(_texture_filter_targets.size()):
		var target := _texture_filter_targets[target_index]
		if is_instance_valid(target):
			target.texture_filter = (
				_initial_texture_filters[target_index] as CanvasItem.TextureFilter
			)


func _toggle_diagnostics() -> void:
	diagnostics_panel.visible = not diagnostics_panel.visible
	_diagnostics_elapsed = 0.0
	if diagnostics_panel.visible:
		_update_diagnostics_values()
	_refresh_menu()


func _toggle_performance() -> void:
	performance_panel.visible = not performance_panel.visible
	_performance_elapsed = 0.0
	_performance_diagnostics.reset()
	if performance_panel.visible:
		_update_performance_values()
	_refresh_menu()


func _update_performance_values() -> void:
	performance_values.text = _performance_diagnostics.sample()


func _toggle_collision_debug() -> void:
	collision_debug_overlay.set_debug_visible(not collision_debug_overlay.visible)
	_refresh_menu()


func _set_controls_visible(controls_visible: bool) -> void:
	controls_panel.visible = controls_visible
	controls_interface.visible = controls_visible
	controls_prompt.visible = not controls_visible
	var room := lab_navigation.current_room
	if room != null and room.soul != null:
		room.soul.set_interface_visible(not controls_visible)
	if controls_visible:
		_refresh_menu()
		controls_interface.focus_primary_setting()
	else:
		controls_interface.release_menu_focus()


func _update_diagnostics_values() -> void:
	var player_position := hero_character.global_position
	var rendered_player_position := hero_visual.global_position
	var raw_camera_position := hero_character.to_global(_initial_camera_position)
	var rendered_camera_position := player_camera.global_position
	var camera_position := player_camera.get_screen_center_position()
	var world_position := test_world.global_position
	var tile_size := tile_grid_preview.tile_size
	var window_size := get_window().size
	var stretch_scale := _pixel_snap_viewport.get_stretch_transform().get_scale()
	diagnostics_values.text = "\n".join(
		[
			"Testraum: %s" % _current_room_title(),
			"Spielerposition roh: %s" % _format_diagnostic_position(player_position),
			"Spieleranzeige gerastert: %s"
			% _format_diagnostic_position(rendered_player_position),
			"Kameraposition roh: %s"
			% _format_diagnostic_position(raw_camera_position),
			"Kameraposition gerastert: %s"
			% _format_diagnostic_position(rendered_camera_position),
			"Kamerazentrum: %s" % _format_diagnostic_position(camera_position),
			"Weltanker: %s" % _format_diagnostic_position(world_position),
			"Maßstab: manuelle Einzelwerte",
			"Referenzauflösung: %d × %d"
			% [_reference_resolution().x, _reference_resolution().y],
			"Seitenverhältnis: %s" % REFERENCE_ASPECT_RATIO,
			"Kamerabereich: %s" % CAMERA_CONTEXT_NAMES[_selected_camera_context],
			"Kamera-Basis: %s×"
			% _format_camera_zoom(player_camera.get_base_zoom()),
			"Kamera-Aktiv: %s×"
			% _format_camera_zoom(player_camera.get_active_zoom()),
			"Bewegung: %s" % hero_character.get_movement_diagnostic(),
			"Geschwindigkeit: %d px/s" % roundi(hero_character.get_current_speed()),
			"Feststelltasten-Gehen: %s"
			% ("AN" if hero_character.is_walk_mode_active() else "AUS"),
			"Sprung: %s" % hero_character.get_jump_diagnostic(),
			"Hero-Animation: %s" % hero_sprite.animation,
			"Hero-Quelle: %s" % _hero_animation_source_path(),
			"Hero-Grafik: %s" % _hero_graphics_name(),
			PortalGraphics.status_text(StringName(HERO_GRAPHICS_IDS[_selected_hero_graphics])),
			"Tempelboden: %s" % PortalGraphics.FLOOR_NAMES[_selected_temple_floor],
			"Figur: %d px" % roundi(hero_character.get_appearance_height()),
			"Tiles: %d × %d px" % [tile_size, tile_size],
			"Weltzustand: %s" % WORLD_STATE_NAMES[_selected_world_state],
			"Nebel: %s" % world_state_preview.get_active_fog_name(),
			"Lichtprofil: %s" % world_state_preview.get_active_light_name(),
			"Pixel-Snap: %s" % _pixel_snap_name(),
			"Viewport-Transform-Snap: %s"
			% (
				"AN"
				if _pixel_snap_viewport.snap_2d_transforms_to_pixel
				else "AUS"
			),
			"Vertex-Snap: %s"
			% ("AN" if _pixel_snap_viewport.snap_2d_vertices_to_pixel else "AUS"),
			"Darstellungsraster: %s" % _pixel_snap_grid_name(),
			"Rasterphase: %s" % _pixel_snap_phase_name(),
			"Texturfilter: %s" % _texture_filter_name(),
			"Fenster: %d × %d" % [window_size.x, window_size.y],
			"Fensterskalierung: %s" % _format_stretch_scale(stretch_scale),
		]
	)


func _hero_animation_source_path() -> String:
	if hero_sprite.sprite_frames == null:
		return "nicht geladen"
	var sources := hero_sprite.sprite_frames.get_meta(&"animation_sources", {}) as Dictionary
	var source_path := str(sources.get(hero_sprite.animation, "nicht registriert"))
	var path_parts := source_path.trim_prefix("res://").split("/")
	if path_parts.size() <= 4:
		return "/".join(path_parts)
	return "/".join(path_parts.slice(-4))


func _on_lab_room_changed(room_id: StringName, room: TestRoomScript) -> void:
	if room.soul != null:
		room.soul.conversation_changed.connect(_on_soul_conversation_changed)
		room.soul.set_interface_visible(not controls_panel.visible)
	_lab_world_bounds = Rect2(Vector2.ZERO, room.world_size)
	_update_room_bounds(room.world_size)
	var objects_visible := room_id == &"objects"
	$TestWorld/ScaleComparison.visible = objects_visible
	$TestWorld/TileComparison.visible = objects_visible
	$TestWorld/TestObstacle.visible = objects_visible
	$TestWorld/TestObstacle/CollisionShape2D.disabled = not objects_visible
	world_state_preview.visible = room_id in [&"fog", &"day_night", &"world_state"]
	world_state_preview.position = Vector2(1200, 480)
	world_state_preview.set_preview_mode(room_id)
	collision_debug_overlay.extra_collision_root = room
	_apply_portal_graphics()
	_restore_texture_filters()
	_texture_filter_targets.clear()
	_initial_texture_filters.clear()
	_collect_texture_filter_targets(test_world)
	_apply_texture_filter()
	_apply_tile_size()
	_apply_camera_zoom()
	_update_pixel_snap_render_alignment()
	player_camera.reset_smoothing()
	player_camera.force_update_scroll()
	room_status.text = "%s · Tür betreten: %s · F5: Testwerte" % [
		_current_room_title(), "Testraum öffnen" if room_id == &"hub" else "zurück zum Portalturm",
	]
	room_status.add_theme_color_override("font_color", BlueprintPalette.BRIGHT)
	_refresh_room_actions()
	_refresh_diagnostics_if_visible()


func _on_soul_conversation_changed(active: bool) -> void:
	hero_character.set_movement_enabled(not active)
	_update_soul_prompt()


func _update_soul_prompt() -> void:
	var room := lab_navigation.current_room
	if room != null and room.soul != null:
		var target: Area2D = null
		if hero_character.is_movement_enabled() and not hero_character.is_jumping():
			target = hero_character.get_nearest_interactable()
		room.soul.update_prompt(target)


func _current_room_title() -> String:
	if lab_navigation.current_room_id == &"hub" or lab_navigation.current_room_id == &"":
		return "Portalturm"
	var definition := lab_navigation.catalog.find_room(lab_navigation.current_room_id)
	return definition.title if definition != null else "Testraum"


func _update_room_bounds(world_size: Vector2) -> void:
	player_camera.limit_left = 0
	player_camera.limit_top = 0
	player_camera.limit_right = int(world_size.x)
	player_camera.limit_bottom = int(world_size.y)
	$TestWorld/Floor.polygon = PackedVector2Array([
		Vector2.ZERO, Vector2(world_size.x, 0), world_size, Vector2(0, world_size.y),
	])
	var walls := {
		"LeftWall": [Vector2(0, world_size.y / 2.0), Vector2(32, world_size.y)],
		"RightWall": [Vector2(world_size.x, world_size.y / 2.0), Vector2(32, world_size.y)],
		"TopWall": [Vector2(world_size.x / 2.0, 0), Vector2(world_size.x, 32)],
		"BottomWall": [Vector2(world_size.x / 2.0, world_size.y), Vector2(world_size.x, 32)],
	}
	for wall_name in walls:
		var wall := $TestWorld/ArenaBounds.get_node(NodePath(wall_name)) as StaticBody2D
		wall.position = walls[wall_name][0]
		var shape := RectangleShape2D.new()
		shape.size = walls[wall_name][1]
		(wall.get_node("CollisionShape2D") as CollisionShape2D).shape = shape


func _refresh_room_actions() -> void:
	for child in room_actions.get_children():
		room_actions.remove_child(child)
		child.queue_free()
	if lab_navigation.current_room == null:
		return
	for item in lab_navigation.current_room.get_controls():
		var button := Button.new()
		button.text = item["text"]
		button.custom_minimum_size = Vector2(120, 38)
		button.focus_mode = Control.FOCUS_NONE
		button.pressed.connect(_on_room_control_pressed.bind(item["id"]))
		room_actions.add_child(button)


func _on_room_control_pressed(control_id: StringName) -> void:
	if lab_navigation.current_room != null:
		lab_navigation.current_room.activate_control(control_id)
		_refresh_room_actions()


func _refresh_diagnostics_if_visible() -> void:
	if diagnostics_panel != null and diagnostics_panel.visible:
		_update_diagnostics_values()


func _is_repeated_key_event(event: InputEvent) -> bool:
	var echo_value: Variant = event.get("echo")
	return echo_value is bool and echo_value


func _load_standards() -> void:
	var loaded := load(_standards_path()) as VisualLabStandardsResource
	if not _standards_are_valid(loaded):
		push_error("VisualLab could not load valid visual standards.")
		_standards = DEFAULT_STANDARDS
		return
	_standards = loaded


func _load_movement_standard() -> void:
	var loaded := load(_movement_standard_path()) as HeroMovementConfigResource
	if not _movement_standard_is_valid(loaded):
		push_error("VisualLab could not load a valid movement standard.")
		_movement_standard = DEFAULT_MOVEMENT_STANDARD
		return
	_movement_standard = loaded


func _standards_are_valid(standards: VisualLabStandardsResource) -> bool:
	return (
		standards != null
		and standards.schema_version == 1
		and standards.hero_frame_count in HERO_FPS_VALUES
		and standards.hero_fps in HERO_FPS_VALUES
		and standards.scale_profile != null
		and standards.world_camera_profile != null
		and standards.village_camera_profile != null
		and standards.dungeon_camera_profile != null
		and standards.small_interior_camera_profile != null
	)


func _movement_standard_is_valid(config: HeroMovementConfigResource) -> bool:
	if config == null:
		return false
	for setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS:
		var bounds := _gameplay_setting_bounds(setting_id)
		var value := float(config.get(setting_id))
		if not is_finite(value) or value < bounds.x or value > bounds.y:
			return false
	return (
		config.standing_jump_duration > 0.0
		and config.walk_jump_duration > 0.0
		and config.jog_jump_duration > 0.0
		and config.run_jump_duration > 0.0
		and config.sprint_jump_duration > 0.0
	)


func _load_settings() -> void:
	_reset_preview_to_standards()
	var settings := ConfigFile.new()
	var load_error := settings.load(_settings_path())
	if load_error == ERR_FILE_NOT_FOUND:
		return
	if load_error != OK:
		push_warning("VisualLab could not load its settings (error %d)." % load_error)
		return
	var stored_version: Variant = settings.get_value(SETTINGS_META_SECTION, "version", 0)
	if not stored_version is int:
		return
	if stored_version == 1:
		_load_legacy_settings(settings)
		_save_settings()
		return
	if stored_version == 2 or stored_version == 3 or stored_version == 4:
		_load_current_settings(settings)
		if stored_version == 3:
			_load_gameplay_settings(settings)
		if stored_version == 4:
			_load_gameplay_settings(settings)
		_save_settings()
		return
	if stored_version != SETTINGS_VERSION:
		return
	_load_current_settings(settings)
	_load_gameplay_settings(settings)


func _reset_preview_to_standards() -> void:
	for context_index in range(CAMERA_CONTEXT_IDS.size()):
		_selected_camera_zooms[context_index] = _accepted_camera_zoom_index(
			context_index
		)
	_selected_camera_context = 0
	_selected_camera_zoom = _selected_camera_zooms[_selected_camera_context]
	var scale_profile := _standards.scale_profile
	_selected_hero_size = _preset_index_for_float(
		HERO_SIZE_VALUES,
		scale_profile.hero_height,
		HeroSizePreset.MEDIUM,
	)
	_selected_hero_graphics = HeroGraphicsPreset.COMIC_HIGH
	_selected_hero_frames = _accepted_hero_frame_index()
	_selected_hero_fps = _accepted_hero_fps_index()
	_selected_tile_size = _preset_index_for_int(
		TILE_SIZE_VALUES,
		scale_profile.tile_size,
		TileSizePreset.SMALL,
	)
	_selected_world_state = WorldStatePreset.DAMAGED
	for world_state in range(WORLD_STATE_IDS.size()):
		_selected_fog_variants[world_state] = _accepted_fog_index(world_state)
		_selected_light_variants[world_state] = _accepted_light_index(world_state)
	_pixel_snap_enabled = scale_profile.pixel_snap_enabled
	_selected_texture_filter = _preset_index_for_string(
		TEXTURE_FILTER_IDS,
		scale_profile.texture_filter_id,
		TextureFilterPreset.NEAREST,
	)
	_movement_preview = _movement_standard.duplicate(true) as HeroMovementConfigResource
	if _movement_preview == null:
		_movement_preview = DEFAULT_MOVEMENT_STANDARD.duplicate(
			true
		) as HeroMovementConfigResource
	hero_character.movement_config = _movement_preview


func _load_legacy_settings(settings: ConfigFile) -> void:
	_selected_camera_zooms[0] = _read_preset_index(
		settings,
		"camera_zoom",
		CAMERA_ZOOM_IDS,
		_selected_camera_zooms[0],
	)
	_load_shared_settings(settings)
	_selected_camera_zoom = _selected_camera_zooms[_selected_camera_context]


func _load_current_settings(settings: ConfigFile) -> void:
	_selected_camera_context = _read_preset_index(
		settings,
		"camera_context",
		_camera_context_string_ids(),
		0,
	)
	for context_index in range(CAMERA_CONTEXT_IDS.size()):
		_selected_camera_zooms[context_index] = _read_preset_index(
			settings,
			CAMERA_SETTING_KEYS[context_index],
			CAMERA_ZOOM_IDS,
			_selected_camera_zooms[context_index],
		)
	_load_shared_settings(settings)
	_selected_camera_zoom = _selected_camera_zooms[_selected_camera_context]


func _load_shared_settings(settings: ConfigFile) -> void:
	_selected_temple_floor = _read_preset_index(
		settings, "temple_floor", PortalGraphics.FLOOR_IDS, 0,
	)
	_selected_hero_size = _read_preset_index(
		settings,
		"hero_size",
		HERO_SIZE_IDS,
		_selected_hero_size,
	)
	_selected_hero_graphics = _read_preset_index(
		settings,
		"hero_graphics",
		HERO_GRAPHICS_IDS,
		_selected_hero_graphics,
	)
	var stored_frames: Variant = settings.get_value(
		SETTINGS_SECTION,
		"hero_frames",
		"",
	)
	var has_stored_frames := stored_frames is String and str(stored_frames) in HERO_FRAME_IDS
	_selected_hero_frames = _read_preset_index(
		settings,
		"hero_frames",
		HERO_FRAME_IDS,
		_selected_hero_frames,
	)
	_selected_hero_fps = _read_preset_index(
		settings,
		"hero_fps",
		HERO_FPS_IDS,
		_selected_hero_fps + 1,
	) - 1
	if not has_stored_frames and _selected_hero_fps != HeroFpsPreset.NEW:
		_selected_hero_frames = _selected_hero_fps
	_selected_tile_size = _read_preset_index(
		settings,
		"tile_size",
		TILE_SIZE_IDS,
		_selected_tile_size,
	)
	_selected_world_state = _read_preset_index(
		settings,
		"world_state",
		WORLD_STATE_IDS,
		WorldStatePreset.DAMAGED,
	)
	for world_state in range(WORLD_STATE_IDS.size()):
		var stored_fog: Variant = settings.get_value(
			SETTINGS_SECTION,
			FOG_SETTING_KEYS[world_state],
			_standards.fog_id_for(StringName(WORLD_STATE_IDS[world_state])),
		)
		_selected_fog_variants[world_state] = world_state_preview.find_fog_variant(
			world_state,
			str(stored_fog),
			_selected_fog_variants[world_state],
		)
		var stored_light: Variant = settings.get_value(
			SETTINGS_SECTION,
			LIGHT_SETTING_KEYS[world_state],
			_standards.light_id_for(StringName(WORLD_STATE_IDS[world_state])),
		)
		_selected_light_variants[world_state] = (
			world_state_preview.find_light_variant(
				world_state,
				str(stored_light),
				_selected_light_variants[world_state],
			)
		)
	_pixel_snap_enabled = _read_bool_setting(
		settings,
		"pixel_snap",
		_pixel_snap_enabled,
	)
	_selected_texture_filter = _read_preset_index(
		settings,
		"texture_filter",
		TEXTURE_FILTER_IDS,
		_selected_texture_filter,
	)


func _load_gameplay_settings(settings: ConfigFile) -> void:
	for setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS:
		var default_value := float(_movement_standard.get(setting_id))
		var bounds := _gameplay_setting_bounds(setting_id)
		var stored_value := _read_float_setting(
			settings,
			str(setting_id),
			default_value,
		)
		_movement_preview.set(
			setting_id,
			clampf(stored_value, bounds.x, bounds.y),
		)


func _save_settings() -> void:
	var settings := ConfigFile.new()
	settings.set_value(SETTINGS_META_SECTION, "version", SETTINGS_VERSION)
	settings.set_value(
		SETTINGS_SECTION,
		"camera_context",
		str(CAMERA_CONTEXT_IDS[_selected_camera_context]),
	)
	for context_index in range(CAMERA_CONTEXT_IDS.size()):
		settings.set_value(
			SETTINGS_SECTION,
			CAMERA_SETTING_KEYS[context_index],
			CAMERA_ZOOM_IDS[_selected_camera_zooms[context_index]],
		)
	settings.set_value(
		SETTINGS_SECTION,
		"hero_size",
		HERO_SIZE_IDS[_selected_hero_size],
	)
	settings.set_value(
		SETTINGS_SECTION,
		"hero_graphics",
		HERO_GRAPHICS_IDS[_selected_hero_graphics],
	)
	settings.set_value(
		SETTINGS_SECTION, "temple_floor", PortalGraphics.FLOOR_IDS[_selected_temple_floor],
	)
	settings.set_value(
		SETTINGS_SECTION,
		"hero_frames",
		HERO_FRAME_IDS[_selected_hero_frames],
	)
	settings.set_value(
		SETTINGS_SECTION,
		"hero_fps",
		HERO_FPS_IDS[_selected_hero_fps + 1],
	)
	settings.set_value(
		SETTINGS_SECTION,
		"tile_size",
		TILE_SIZE_IDS[_selected_tile_size],
	)
	settings.set_value(
		SETTINGS_SECTION,
		"world_state",
		WORLD_STATE_IDS[_selected_world_state],
	)
	for world_state in range(WORLD_STATE_IDS.size()):
		settings.set_value(
			SETTINGS_SECTION,
			FOG_SETTING_KEYS[world_state],
			world_state_preview.get_fog_variant_id(
				world_state,
				_selected_fog_variants[world_state],
			),
		)
		settings.set_value(
			SETTINGS_SECTION,
			LIGHT_SETTING_KEYS[world_state],
			world_state_preview.get_light_variant_id(
				world_state,
				_selected_light_variants[world_state],
			),
		)
	settings.set_value(SETTINGS_SECTION, "pixel_snap", _pixel_snap_enabled)
	settings.set_value(
		SETTINGS_SECTION,
		"texture_filter",
		TEXTURE_FILTER_IDS[_selected_texture_filter],
	)
	if _movement_preview != null:
		for setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS:
			settings.set_value(
				SETTINGS_SECTION,
				str(setting_id),
				float(_movement_preview.get(setting_id)),
			)
	var save_error := settings.save(_settings_path())
	if save_error != OK:
		push_warning("VisualLab could not save its settings (error %d)." % save_error)


func _read_preset_index(
	settings: ConfigFile,
	setting_key: String,
	preset_ids: Array[String],
	default_index: int,
) -> int:
	var stored_id: Variant = settings.get_value(SETTINGS_SECTION, setting_key, "")
	if not stored_id is String:
		return default_index
	var preset_index := preset_ids.find(str(stored_id))
	return preset_index if preset_index >= 0 else default_index


func _read_bool_setting(
	settings: ConfigFile,
	setting_key: String,
	default_value: bool,
) -> bool:
	var stored_value: Variant = settings.get_value(
		SETTINGS_SECTION,
		setting_key,
		default_value,
	)
	if not stored_value is bool:
		return default_value
	return bool(stored_value)


func _read_float_setting(
		settings: ConfigFile,
		setting_key: String,
		default_value: float,
) -> float:
	var stored_value: Variant = settings.get_value(
		SETTINGS_SECTION,
		setting_key,
		default_value,
	)
	if stored_value is float or stored_value is int:
		var numeric_value := float(stored_value)
		return numeric_value if is_finite(numeric_value) else default_value
	return default_value


func _settings_path() -> String:
	return str(
		ProjectSettings.get_setting(
			SETTINGS_PATH_PROJECT_KEY,
			DEFAULT_SETTINGS_PATH,
		)
	)


func _standards_path() -> String:
	return str(
		ProjectSettings.get_setting(
			STANDARDS_PATH_PROJECT_KEY,
			DEFAULT_STANDARDS_PATH,
		)
	)


func _movement_standard_path() -> String:
	return str(
		ProjectSettings.get_setting(
			MOVEMENT_STANDARD_PATH_PROJECT_KEY,
			DEFAULT_MOVEMENT_STANDARD_PATH,
		)
	)


func _camera_context_string_ids() -> Array[String]:
	var result: Array[String] = []
	for context_id in CAMERA_CONTEXT_IDS:
		result.append(str(context_id))
	return result


func _preset_index_for_float(
		values: Array[float],
		selected_value: float,
		fallback: int,
) -> int:
	for value_index in range(values.size()):
		if is_equal_approx(values[value_index], selected_value):
			return value_index
	return fallback


func _preset_index_for_int(
		values: Array[int],
		selected_value: int,
		fallback: int,
) -> int:
	var value_index := values.find(selected_value)
	return value_index if value_index >= 0 else fallback


func _preset_index_for_string(
		values: Array[String],
		selected_value: String,
		fallback: int,
) -> int:
	var value_index := values.find(selected_value)
	return value_index if value_index >= 0 else fallback


func _minimum_camera_zoom() -> float:
	var viewport_size := size
	if viewport_size.x <= 0.0 or viewport_size.y <= 0.0:
		viewport_size = Vector2(
			float(ProjectSettings.get_setting("display/window/size/viewport_width", 0)),
			float(ProjectSettings.get_setting("display/window/size/viewport_height", 0)),
		)
	var world_width := _lab_world_bounds.size.x
	var world_height := _lab_world_bounds.size.y
	return maxf(viewport_size.x / world_width, viewport_size.y / world_height)


func _format_camera_zoom(zoom_value: float) -> String:
	return ("%.2f" % zoom_value).replace(".", ",")


func _format_diagnostic_position(position: Vector2) -> String:
	return "x=%s · y=%s" % [
		_format_position_component(position.x),
		_format_position_component(position.y),
	]


func _format_position_component(value: float) -> String:
	return ("%.3f" % value).replace(".", ",")


func _pixel_snap_name() -> String:
	return "AN" if _pixel_snap_enabled else "AUS"


func _texture_filter_name() -> String:
	return TEXTURE_FILTER_NAMES[_selected_texture_filter]


func _hero_graphics_name() -> String:
	return HERO_GRAPHICS_NAMES[_selected_hero_graphics]


func _refresh_menu() -> void:
	if controls_interface == null or not is_instance_valid(controls_interface):
		return
	controls_interface.set_setting_labels(
		VisualLabMenuScript.SETTING_FOG,
		_fog_variant_names(_selected_world_state),
	)
	controls_interface.set_setting_labels(
		VisualLabMenuScript.SETTING_LIGHT,
		_light_variant_names(_selected_world_state),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_CAMERA_CONTEXT,
		_selected_camera_context,
	)
	var accepted_zoom := _accepted_camera_zoom_index(_selected_camera_context)
	var accepted_zoom_description := "%s×" % _format_camera_zoom(
		CAMERA_ZOOM_VALUES[accepted_zoom]
	)
	if (
		CAMERA_CONTEXT_IDS[_selected_camera_context] == &"village"
		and _standards.village_inherits_world
	):
		accepted_zoom_description += " · geerbt von Außenwelt"
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_CAMERA_ZOOM,
		_selected_camera_zoom,
		accepted_zoom,
		accepted_zoom_description,
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_HERO_SIZE,
		_selected_hero_size,
		_accepted_hero_size_index(),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_HERO_GRAPHICS,
		_selected_hero_graphics,
	)
	controls_interface.update_temple_floor(_selected_temple_floor)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_HERO_FRAMES,
		_selected_hero_frames,
		_accepted_hero_frame_index(),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_HERO_FPS,
		_selected_hero_fps + 1,
		_accepted_hero_fps_index() + 1,
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_TILE_SIZE,
		_selected_tile_size,
		_accepted_tile_size_index(),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_PIXEL_SNAP,
		int(_pixel_snap_enabled),
		int(_standards.scale_profile.pixel_snap_enabled),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_TEXTURE_FILTER,
		_selected_texture_filter,
		_accepted_texture_filter_index(),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_WORLD_STATE,
		_selected_world_state,
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_FOG,
		_selected_fog_variants[_selected_world_state],
		_accepted_fog_index(_selected_world_state),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_LIGHT,
		_selected_light_variants[_selected_world_state],
		_accepted_light_index(_selected_world_state),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_DIAGNOSTICS,
		int(diagnostics_panel.visible),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_PERFORMANCE,
		int(performance_panel.visible),
	)
	controls_interface.update_setting(
		VisualLabMenuScript.SETTING_COLLISION,
		int(collision_debug_overlay.visible),
	)
	if _movement_preview != null and _movement_standard != null:
		for setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS:
			controls_interface.update_numeric_setting(
				setting_id,
				float(_movement_preview.get(setting_id)),
				float(_movement_standard.get(setting_id)),
			)
	_on_menu_setting_focused(controls_interface.get_focused_setting_id())


func _fog_variant_names(world_state: int) -> Array[String]:
	var names: Array[String] = []
	for variant_index in range(
		world_state_preview.get_fog_variant_count(world_state)
	):
		names.append(
			world_state_preview.get_fog_variant_name(world_state, variant_index)
		)
	return names


func _light_variant_names(world_state: int) -> Array[String]:
	var names: Array[String] = []
	for variant_index in range(
		world_state_preview.get_light_variant_count(world_state)
	):
		names.append(
			world_state_preview.get_light_variant_name(world_state, variant_index)
		)
	return names


func _accepted_camera_zoom_index(context_index: int) -> int:
	var context_id := CAMERA_CONTEXT_IDS[clampi(
		context_index,
		0,
		CAMERA_CONTEXT_IDS.size() - 1,
	)]
	var profile := _standards.camera_profile_for(context_id)
	if profile == null:
		return CameraZoomPreset.MEDIUM
	return _preset_index_for_float(
		CAMERA_ZOOM_VALUES,
		profile.base_zoom,
		CameraZoomPreset.MEDIUM,
	)


func _accepted_hero_size_index() -> int:
	return _preset_index_for_float(
		HERO_SIZE_VALUES,
		_standards.scale_profile.hero_height,
		HeroSizePreset.MEDIUM,
	)


func _accepted_hero_frame_index() -> int:
	return _preset_index_for_int(
		HERO_FPS_VALUES,
		_standards.hero_frame_count,
		HeroFpsPreset.FPS_8,
	)


func _accepted_hero_fps_index() -> int:
	return _preset_index_for_int(
		HERO_FPS_VALUES,
		_standards.hero_fps,
		HeroFpsPreset.FPS_8,
	)


func _accepted_tile_size_index() -> int:
	return _preset_index_for_int(
		TILE_SIZE_VALUES,
		_standards.scale_profile.tile_size,
		TileSizePreset.SMALL,
	)


func _accepted_texture_filter_index() -> int:
	return _preset_index_for_string(
		TEXTURE_FILTER_IDS,
		_standards.scale_profile.texture_filter_id,
		TextureFilterPreset.NEAREST,
	)


func _accepted_fog_index(world_state: int) -> int:
	var default_index := world_state_preview.get_default_fog_variant(world_state)
	return world_state_preview.find_fog_variant(
		world_state,
		_standards.fog_id_for(StringName(WORLD_STATE_IDS[world_state])),
		default_index,
	)


func _accepted_light_index(world_state: int) -> int:
	var default_index := world_state_preview.get_default_light_variant(world_state)
	return world_state_preview.find_light_variant(
		world_state,
		_standards.light_id_for(StringName(WORLD_STATE_IDS[world_state])),
		default_index,
	)


func _on_menu_option_selected(setting_id: StringName, option_index: int) -> void:
	match setting_id:
		VisualLabMenuScript.SETTING_CAMERA_CONTEXT:
			_set_camera_context(option_index)
		VisualLabMenuScript.SETTING_CAMERA_ZOOM:
			_set_camera_zoom(option_index)
		VisualLabMenuScript.SETTING_HERO_SIZE:
			_set_hero_size(option_index)
		VisualLabMenuScript.SETTING_HERO_GRAPHICS:
			_set_hero_graphics(option_index)
		VisualLabMenuScript.SETTING_TEMPLE_FLOOR:
			_set_temple_floor(option_index)
		VisualLabMenuScript.SETTING_HERO_FRAMES:
			_set_hero_frames(option_index)
		VisualLabMenuScript.SETTING_HERO_FPS:
			_set_hero_fps(option_index)
		VisualLabMenuScript.SETTING_TILE_SIZE:
			_set_tile_size(option_index)
		VisualLabMenuScript.SETTING_PIXEL_SNAP:
			_set_pixel_snap_enabled(option_index == 1, true)
		VisualLabMenuScript.SETTING_TEXTURE_FILTER:
			_set_texture_filter(option_index, true)
		VisualLabMenuScript.SETTING_WORLD_STATE:
			_set_world_state(option_index)
		VisualLabMenuScript.SETTING_FOG:
			_set_fog_variant(option_index)
		VisualLabMenuScript.SETTING_LIGHT:
			_set_light_variant(option_index)
		VisualLabMenuScript.SETTING_DIAGNOSTICS:
			_set_diagnostics_visible(option_index == 1)
		VisualLabMenuScript.SETTING_PERFORMANCE:
			_set_performance_visible(option_index == 1)
		VisualLabMenuScript.SETTING_COLLISION:
			_set_collision_debug_visible(option_index == 1)


func _on_menu_numeric_value_changed(
		setting_id: StringName,
		value: float,
) -> void:
	var setting_error := _set_gameplay_value(setting_id, value)
	if setting_error != OK:
		controls_interface.show_feedback(
			"Gameplay-Testwert konnte nicht angewendet werden.",
			true,
		)


func _set_diagnostics_visible(visible: bool) -> void:
	if diagnostics_panel.visible == visible:
		return
	_toggle_diagnostics()


func _set_performance_visible(visible: bool) -> void:
	if performance_panel.visible == visible:
		return
	_toggle_performance()


func _set_collision_debug_visible(visible: bool) -> void:
	if collision_debug_overlay.visible == visible:
		return
	_toggle_collision_debug()


func _on_menu_setting_focused(setting_id: StringName) -> void:
	var can_accept := _focused_setting_can_be_accepted(setting_id)
	controls_interface.update_acceptance(
		can_accept,
		can_accept and _setting_matches_standard(setting_id),
		_setting_subject(setting_id),
	)


func _setting_is_acceptable(setting_id: StringName) -> bool:
	return setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS or setting_id in [
		VisualLabMenuScript.SETTING_CAMERA_ZOOM,
		VisualLabMenuScript.SETTING_HERO_SIZE,
		VisualLabMenuScript.SETTING_HERO_FRAMES,
		VisualLabMenuScript.SETTING_HERO_FPS,
		VisualLabMenuScript.SETTING_TILE_SIZE,
		VisualLabMenuScript.SETTING_PIXEL_SNAP,
		VisualLabMenuScript.SETTING_TEXTURE_FILTER,
		VisualLabMenuScript.SETTING_FOG,
		VisualLabMenuScript.SETTING_LIGHT,
	]


func _focused_setting_can_be_accepted(setting_id: StringName) -> bool:
	if setting_id in [
		VisualLabMenuScript.SETTING_HERO_FRAMES,
		VisualLabMenuScript.SETTING_HERO_FPS,
	]:
		return _selected_hero_fps != HeroFpsPreset.NEW
	return _setting_is_acceptable(setting_id)


func _setting_matches_standard(setting_id: StringName) -> bool:
	if setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS:
		return (
			_movement_preview != null
			and _movement_standard != null
			and is_equal_approx(
				float(_movement_preview.get(setting_id)),
				float(_movement_standard.get(setting_id)),
			)
		)
	match setting_id:
		VisualLabMenuScript.SETTING_CAMERA_ZOOM:
			return (
				_selected_camera_zoom
				== _accepted_camera_zoom_index(_selected_camera_context)
			)
		VisualLabMenuScript.SETTING_HERO_SIZE:
			return _selected_hero_size == _accepted_hero_size_index()
		VisualLabMenuScript.SETTING_HERO_FRAMES, VisualLabMenuScript.SETTING_HERO_FPS:
			return (
				_selected_hero_fps != HeroFpsPreset.NEW
				and _selected_hero_frames == _accepted_hero_frame_index()
				and _selected_hero_fps == _accepted_hero_fps_index()
			)
		VisualLabMenuScript.SETTING_TILE_SIZE:
			return _selected_tile_size == _accepted_tile_size_index()
		VisualLabMenuScript.SETTING_PIXEL_SNAP:
			return (
				_pixel_snap_enabled
				== _standards.scale_profile.pixel_snap_enabled
			)
		VisualLabMenuScript.SETTING_TEXTURE_FILTER:
			return (
				_selected_texture_filter == _accepted_texture_filter_index()
			)
		VisualLabMenuScript.SETTING_FOG:
			return (
				_selected_fog_variants[_selected_world_state]
				== _accepted_fog_index(_selected_world_state)
			)
		VisualLabMenuScript.SETTING_LIGHT:
			return (
				_selected_light_variants[_selected_world_state]
				== _accepted_light_index(_selected_world_state)
			)
	return false


func _setting_subject(setting_id: StringName) -> String:
	if setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS:
		return str(GAMEPLAY_SETTING_SUBJECTS.get(setting_id, "Gameplay-Testwert"))
	match setting_id:
		VisualLabMenuScript.SETTING_CAMERA_ZOOM:
			return "Zoom · %s" % CAMERA_CONTEXT_NAMES[_selected_camera_context]
		VisualLabMenuScript.SETTING_HERO_SIZE:
			return "Heldenhöhe"
		VisualLabMenuScript.SETTING_HERO_FRAMES:
			return "Heldenanimation · %d Frames" % HERO_FPS_VALUES[_selected_hero_frames]
		VisualLabMenuScript.SETTING_HERO_FPS:
			return "Heldenanimation · %d FPS" % _selected_hero_playback_fps()
		VisualLabMenuScript.SETTING_TILE_SIZE:
			return "Tilegröße"
		VisualLabMenuScript.SETTING_PIXEL_SNAP:
			return "Pixel-Snap"
		VisualLabMenuScript.SETTING_TEXTURE_FILTER:
			return "Texturfilter"
		VisualLabMenuScript.SETTING_FOG:
			return "Nebel · %s" % WORLD_STATE_NAMES[_selected_world_state]
		VisualLabMenuScript.SETTING_LIGHT:
			return "Licht · %s" % WORLD_STATE_NAMES[_selected_world_state]
	return "Testlaborwert"


func _on_accept_requested() -> void:
	if not controls_panel.visible:
		return
	var setting_id := controls_interface.get_focused_setting_id()
	if not _focused_setting_can_be_accepted(setting_id):
		controls_interface.show_feedback(
			"Dieser fokussierte Testwert kann nicht übernommen werden.",
			true,
		)
		return
	if _setting_matches_standard(setting_id):
		controls_interface.show_feedback("Der Wert ist bereits Spielstandard.")
		return
	_accept_single_setting(setting_id)


func _accept_single_setting(setting_id: StringName) -> void:
	var save_error := ERR_INVALID_PARAMETER
	if setting_id in VisualLabMenuScript.GAMEPLAY_SETTING_IDS:
		save_error = _accept_movement_property(setting_id)
	else:
		match setting_id:
			VisualLabMenuScript.SETTING_CAMERA_ZOOM:
				save_error = _accept_camera_zoom()
			VisualLabMenuScript.SETTING_HERO_SIZE:
				save_error = _accept_scale_property(
					&"hero_height",
					HERO_SIZE_VALUES[_selected_hero_size],
				)
			VisualLabMenuScript.SETTING_TILE_SIZE:
				save_error = _accept_scale_property(
					&"tile_size",
					TILE_SIZE_VALUES[_selected_tile_size],
				)
			VisualLabMenuScript.SETTING_HERO_FRAMES, VisualLabMenuScript.SETTING_HERO_FPS:
				save_error = _accept_hero_animation_standard()
			VisualLabMenuScript.SETTING_PIXEL_SNAP:
				save_error = _accept_scale_property(
					&"pixel_snap_enabled",
					_pixel_snap_enabled,
				)
			VisualLabMenuScript.SETTING_TEXTURE_FILTER:
				save_error = _accept_scale_property(
					&"texture_filter_id",
					TEXTURE_FILTER_IDS[_selected_texture_filter],
				)
			VisualLabMenuScript.SETTING_FOG:
				save_error = _accept_atmosphere(true)
			VisualLabMenuScript.SETTING_LIGHT:
				save_error = _accept_atmosphere(false)
	_finish_acceptance(_setting_subject(setting_id), save_error)


func _accept_camera_zoom() -> Error:
	if _selected_camera_context == 0:
		return _accept_world_camera_zoom()
	var context_id := CAMERA_CONTEXT_IDS[_selected_camera_context]
	var profile := _standards.owned_camera_profile_for(context_id)
	var old_zoom := profile.base_zoom
	var old_inheritance := _standards.village_inherits_world
	profile.base_zoom = CAMERA_ZOOM_VALUES[_selected_camera_zoom]
	if context_id == &"village":
		_standards.village_inherits_world = false
	var save_error := _save_standard_resource(profile)
	if save_error == OK and context_id == &"village":
		save_error = _save_standard_resource(_standards)
	if save_error == OK:
		return OK
	profile.base_zoom = old_zoom
	_standards.village_inherits_world = old_inheritance
	_save_standard_resource(profile)
	return save_error


func _accept_world_camera_zoom() -> Error:
	var camera_profile := _standards.world_camera_profile
	var scale_profile := _standards.scale_profile
	var old_camera_zoom := camera_profile.base_zoom
	var old_scale_zoom := scale_profile.camera_zoom
	var selected_zoom := CAMERA_ZOOM_VALUES[_selected_camera_zooms[0]]
	camera_profile.base_zoom = selected_zoom
	scale_profile.camera_zoom = selected_zoom
	var save_error := _save_standard_resource(camera_profile)
	if save_error == OK:
		save_error = _save_standard_resource(scale_profile)
	if save_error == OK:
		return OK
	camera_profile.base_zoom = old_camera_zoom
	scale_profile.camera_zoom = old_scale_zoom
	_save_standard_resource(camera_profile)
	_save_standard_resource(scale_profile)
	return save_error


func _accept_scale_property(property_name: StringName, value: Variant) -> Error:
	var scale_profile := _standards.scale_profile
	var old_value: Variant = scale_profile.get(property_name)
	scale_profile.set(property_name, value)
	var save_error := _save_standard_resource(scale_profile)
	if save_error != OK:
		scale_profile.set(property_name, old_value)
	return save_error


func _accept_hero_animation_standard() -> Error:
	if _selected_hero_fps == HeroFpsPreset.NEW:
		return ERR_INVALID_PARAMETER
	var old_frames := _standards.hero_frame_count
	var old_fps := _standards.hero_fps
	_standards.hero_frame_count = HERO_FPS_VALUES[_selected_hero_frames]
	_standards.hero_fps = _selected_hero_playback_fps()
	var save_error := _save_standard_resource(_standards)
	if save_error != OK:
		_standards.hero_frame_count = old_frames
		_standards.hero_fps = old_fps
	return save_error


func _accept_movement_property(setting_id: StringName) -> Error:
	if (
		_movement_standard == null
		or _movement_preview == null
		or setting_id not in VisualLabMenuScript.GAMEPLAY_SETTING_IDS
	):
		return ERR_INVALID_PARAMETER
	var old_value := float(_movement_standard.get(setting_id))
	_movement_standard.set(setting_id, float(_movement_preview.get(setting_id)))
	var save_error := _save_standard_resource(_movement_standard)
	if save_error != OK:
		_movement_standard.set(setting_id, old_value)
	return save_error


func _accept_atmosphere(is_fog: bool) -> Error:
	var world_state_id := StringName(WORLD_STATE_IDS[_selected_world_state])
	var old_id := (
		_standards.fog_id_for(world_state_id)
		if is_fog
		else _standards.light_id_for(world_state_id)
	)
	var selected_id := (
		world_state_preview.get_fog_variant_id(
			_selected_world_state,
			_selected_fog_variants[_selected_world_state],
		)
		if is_fog
		else world_state_preview.get_light_variant_id(
			_selected_world_state,
			_selected_light_variants[_selected_world_state],
		)
	)
	if is_fog:
		_standards.set_fog_id(world_state_id, selected_id)
	else:
		_standards.set_light_id(world_state_id, selected_id)
	var save_error := _save_standard_resource(_standards)
	if save_error == OK:
		return OK
	if is_fog:
		_standards.set_fog_id(world_state_id, old_id)
	else:
		_standards.set_light_id(world_state_id, old_id)
	return save_error


func _save_standard_resource(resource: Resource) -> Error:
	if not OS.is_debug_build() or resource == null:
		return ERR_UNAUTHORIZED
	if resource.resource_path.is_empty():
		return ERR_FILE_CANT_WRITE
	return ResourceSaver.save(resource)


func _finish_acceptance(subject: String, save_error: Error) -> void:
	if save_error == OK:
		controls_interface.show_feedback(
			"%s wurde als Spielstandard übernommen." % subject
		)
	else:
		controls_interface.show_feedback(
			_standard_save_error_message(save_error),
			true,
		)
	_refresh_menu()


func _standard_save_error_message(save_error: Error) -> String:
	match save_error:
		ERR_UNAUTHORIZED:
			return (
				"Übernahme ist nur in einem beschreibbaren "
				+ "Entwicklungsbuild verfügbar."
			)
		ERR_FILE_CANT_WRITE:
			return "Die Spielstandard-Ressource besitzt keinen Schreibpfad."
	return "Spielstandard konnte nicht geschrieben werden (Fehler %d)." % save_error


func _on_menu_close_requested() -> void:
	_set_controls_visible(false)


func _reference_resolution() -> Vector2i:
	return Vector2i(
		int(ProjectSettings.get_setting("display/window/size/viewport_width", 0)),
		int(ProjectSettings.get_setting("display/window/size/viewport_height", 0)),
	)


func _update_pixel_snap_render_alignment() -> void:
	if not _pixel_snap_enabled:
		var camera_was_aligned := not player_camera.position.is_equal_approx(
			_initial_camera_position
		) or player_camera.top_level != _initial_camera_top_level
		player_camera.top_level = _initial_camera_top_level
		hero_visual.top_level = _initial_hero_visual_top_level
		player_camera.position = _initial_camera_position
		hero_visual.position = _initial_hero_visual_position
		if camera_was_aligned:
			player_camera.force_update_scroll()
		return

	var world_grid_step := _pixel_snap_world_grid_step()
	var world_phase_bias := _pixel_snap_world_phase_bias()
	var raw_camera_position := hero_character.to_global(_initial_camera_position)
	var raw_visual_position := hero_character.to_global(_initial_hero_visual_position)
	var rendered_camera_position := _snap_position_to_grid(
		raw_camera_position - world_phase_bias,
		world_grid_step,
	) + world_phase_bias
	var rendered_visual_position := (
		rendered_camera_position
		+ raw_visual_position
		- raw_camera_position
		+ world_phase_bias
	)
	player_camera.top_level = _initial_camera_top_level
	hero_visual.top_level = _initial_hero_visual_top_level
	player_camera.position = hero_character.to_local(rendered_camera_position)
	hero_visual.position = hero_character.to_local(rendered_visual_position)
	player_camera.force_update_scroll()


func _pixel_snap_world_grid_step() -> Vector2:
	var stretch_scale := _pixel_snap_viewport.get_stretch_transform().get_scale()
	return Vector2(
		_world_grid_step_for_output_scale(
			player_camera.zoom.x * absf(stretch_scale.x)
		),
		_world_grid_step_for_output_scale(
			player_camera.zoom.y * absf(stretch_scale.y)
		),
	)


func _world_grid_step_for_output_scale(output_scale: float) -> float:
	if output_scale <= 0.0:
		return 1.0
	return 1.0 / output_scale


func _pixel_snap_world_phase_bias() -> Vector2:
	return _pixel_snap_world_grid_step() * OUTPUT_PIXEL_PHASE_BIAS


func _snap_position_to_grid(position: Vector2, grid_step: Vector2) -> Vector2:
	return Vector2(
		snappedf(position.x, grid_step.x),
		snappedf(position.y, grid_step.y),
	)


func _pixel_snap_grid_name() -> String:
	if not _pixel_snap_enabled:
		return "frei"
	var grid_step := _pixel_snap_world_grid_step()
	return "%s × %s Weltpixel" % [
		_format_position_component(grid_step.x),
		_format_position_component(grid_step.y),
	]


func _pixel_snap_phase_name() -> String:
	return "0,25 Ausgabepixel" if _pixel_snap_enabled else "frei"


func _format_stretch_scale(stretch_scale: Vector2) -> String:
	if is_equal_approx(stretch_scale.x, stretch_scale.y):
		return "%s×" % _format_camera_zoom(stretch_scale.x)
	return "x=%s× · y=%s×" % [
		_format_camera_zoom(stretch_scale.x),
		_format_camera_zoom(stretch_scale.y),
	]


func _update_window_size_status() -> void:
	var window_size := get_window().size
	window_size_status.text = "Fenster: %d × %d" % [window_size.x, window_size.y]
	_refresh_diagnostics_if_visible()


func _on_visual_lab_resized() -> void:
	_apply_camera_zoom()


func _on_main_window_size_changed() -> void:
	_update_window_size_status()
