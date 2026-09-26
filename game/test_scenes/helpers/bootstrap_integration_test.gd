extends SceneTree

const EXPECTED_TITLE := "ETHERFOOD"
const EXPECTED_PROMPT := "Drücke eine Taste"
const EXPECTED_MAIN_MENU_HEADING := "Hauptmenü"
const EXPECTED_MAIN_MENU_BUTTONS := [
	"Fortsetzen",
	"Neues Spiel",
	"Einstellungen",
	"Mitwirkende",
	"Visuelles Testlabor",
	"Spiel beenden",
]
const EXPECTED_HERO_ROOM_HINT := (
	"HELDENRAUM · PROTOTYP\n"
	+ "WASD / Pfeile: laufen · Feststelltaste: gehen\n"
	+ "Doppel-Tap: rennen · Shift halten: sprinten\n"
	+ "Strg: schleichen · Leertaste: springen\n"
	+ "E / A: interagieren · Esc / B: Hauptmenü"
)
const EXPECTED_GUIDE_PROMPT := "E / A: Ratgeber ansprechen"
const EXPECTED_GUIDE_MESSAGE := (
	"Du bist wach. Beweg dich erst einmal.\n"
	+ "Wir müssen einen Ausgang aus diesem Raum finden."
)
const EXPECTED_VISUAL_LAB_TITLE := "VISUELLES TESTLABOR"
const EXPECTED_VISUAL_LAB_CAMERA_STATUS := (
	"Kamera: Außenwelt · Mittel · 1,00×"
)
const EXPECTED_VISUAL_LAB_HERO_SIZE_STATUS := "Figur: Mittel · 80 Weltpixel"
const EXPECTED_VISUAL_LAB_TILE_SIZE_STATUS := "Tiles: Klein · 32 × 32 Weltpixel"
const EXPECTED_VISUAL_LAB_WORLD_STATE_STATUS := "Weltzustand: Beschädigt"
const EXPECTED_REFERENCE_VIEWPORT_SIZE := Vector2(1920, 1080)
const EXPECTED_START_WINDOW_SIZE := Vector2(1280, 720)
const EXPECTED_SQUARE_WINDOW_SIZE := Vector2i(1000, 1000)
const EXPECTED_VISUAL_LAB_MENU_SIZE := Vector2(600, 684)
const EXPECTED_VISUAL_LAB_WORLD_BOUNDS := Rect2(0.0, 0.0, 3840.0, 2160.0)
const VISUAL_LAB_SETTINGS_PATH_PROJECT_KEY := (
	"etherfood/development/visual_lab_settings_path"
)
const VISUAL_LAB_SETTINGS_TEST_PATH := "user://visual_lab_settings_test.cfg"
const FORGE2D_PLACEHOLDER := "Forge2D"
const TEST_SUITES := [
	"res://test_scenes/helpers/runtime/scene_router_test.gd",
	"res://test_scenes/helpers/runtime/application_root_test.gd",
	"res://test_scenes/helpers/runtime/input_map_test.gd",
	"res://test_scenes/helpers/runtime/hero_character_test.gd",
	"res://test_scenes/helpers/runtime/green_hero_animation_test.gd",
	"res://test_scenes/helpers/runtime/green_hero_test_poses_test.gd",
	"res://test_scenes/helpers/runtime/portal_lab_test.gd",
	"res://test_scenes/helpers/runtime/portal_lab_graphics_test.gd",
	"res://test_scenes/helpers/runtime/portal_lab_soul_test.gd",
	"res://test_scenes/helpers/runtime/hero_movement_v0_test.gd",
	"res://test_scenes/helpers/runtime/hero_room_test.gd",
	"res://test_scenes/helpers/runtime/hero_room_interaction_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_zoom_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_hero_size_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_scale_reference_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_tile_size_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_world_state_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_atmosphere_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_diagnostics_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_performance_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_controls_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_pixel_snap_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_texture_filter_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_hero_graphics_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_settings_test.gd",
	"res://test_scenes/helpers/runtime/visual_lab_gameplay_test.gd",
	"res://test_scenes/helpers/runtime/touch_action_adapter_test.gd",
]

var failures: PackedStringArray = []
var _had_settings_path_override := false
var _original_settings_path: Variant = null


func _init() -> void:
	_had_settings_path_override = ProjectSettings.has_setting(
		VISUAL_LAB_SETTINGS_PATH_PROJECT_KEY
	)
	if _had_settings_path_override:
		_original_settings_path = ProjectSettings.get_setting(
			VISUAL_LAB_SETTINGS_PATH_PROJECT_KEY
		)
	ProjectSettings.set_setting(
		VISUAL_LAB_SETTINGS_PATH_PROJECT_KEY,
		VISUAL_LAB_SETTINGS_TEST_PATH,
	)
	call_deferred("_run")


func _run() -> void:
	await process_frame
	for suite_path in TEST_SUITES:
		_remove_visual_lab_test_settings()
		await _run_suite(suite_path)
	_remove_visual_lab_test_settings()
	await _test_bootstrap_contract()
	_remove_visual_lab_test_settings()
	_restore_visual_lab_settings_path()
	_finish()


func _run_suite(suite_path: String) -> void:
	var completion_sentinel := "runtime suite completes: %s" % suite_path
	failures.append(completion_sentinel)
	var suite_script := load(suite_path) as Script
	_expect(suite_script != null, "runtime suite loads: %s" % suite_path)
	if suite_script == null:
		return
	_expect(suite_script.can_instantiate(), "runtime suite parses: %s" % suite_path)
	if not suite_script.can_instantiate():
		return
	var suite: Variant = suite_script.new()
	var suite_failures: PackedStringArray = await suite.run(self)
	var sentinel_index := failures.find(completion_sentinel)
	if sentinel_index >= 0:
		failures.remove_at(sentinel_index)
	failures.append_array(suite_failures)


func _test_bootstrap_contract() -> void:
	var configured_viewport_size := Vector2(
		float(ProjectSettings.get_setting("display/window/size/viewport_width", 0)),
		float(ProjectSettings.get_setting("display/window/size/viewport_height", 0)),
	)
	var configured_window_size := Vector2(
		float(ProjectSettings.get_setting("display/window/size/window_width_override", 0)),
		float(ProjectSettings.get_setting("display/window/size/window_height_override", 0)),
	)
	_expect(
		configured_viewport_size == EXPECTED_REFERENCE_VIEWPORT_SIZE,
		"project uses the 1920 by 1080 reference viewport",
	)
	_expect(
		configured_window_size == EXPECTED_START_WINDOW_SIZE,
		"project uses the 1280 by 720 test window",
	)
	_expect(
		bool(ProjectSettings.get_setting("display/window/size/resizable", false)),
		"project window is resizable",
	)
	_expect(
		str(ProjectSettings.get_setting("display/window/stretch/mode", ""))
		== "canvas_items",
		"project stretches canvas items",
	)
	_expect(
		str(ProjectSettings.get_setting("display/window/stretch/aspect", "")) == "keep",
		"project keeps its 16:9 stretch aspect",
	)
	_expect(
		root.content_scale_size == Vector2i(EXPECTED_REFERENCE_VIEWPORT_SIZE),
		"main window exposes the configured reference viewport",
	)
	_expect(
		root.content_scale_mode == Window.CONTENT_SCALE_MODE_CANVAS_ITEMS,
		"main window uses canvas-items content scaling",
	)
	_expect(
		root.content_scale_aspect == Window.CONTENT_SCALE_ASPECT_KEEP,
		"main window keeps the reference aspect ratio",
	)

	var main_scene_path := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	_expect(not main_scene_path.is_empty(), "project configures a main scene")
	if main_scene_path.is_empty():
		return

	var main_scene := load(main_scene_path) as PackedScene
	_expect(main_scene != null, "configured main scene can be loaded")
	if main_scene == null:
		return

	var bootstrap := main_scene.instantiate()
	var composition_failures: Array[Array] = []
	bootstrap.composition_failed.connect(
		func(error: Error, message: String) -> void:
			composition_failures.append([error, message])
	)
	root.add_child(bootstrap)
	await process_frame

	_expect(bootstrap is Control, "main scene is a Control")
	_expect(bootstrap.get_parent() == root, "main scene remains attached after ready")
	var bootstrap_script: Script = bootstrap.get_script()
	_expect(bootstrap_script != null, "main scene has an attached script")
	if bootstrap_script != null:
		_expect(
			bootstrap_script.resource_path == "res://src/bootstrap.gd",
			"main scene uses the bootstrap script",
		)

	_expect(composition_failures.is_empty(), "Bootstrap reports no composition failure")
	_expect(bootstrap.get_child_count() == 1, "Bootstrap creates exactly one child")

	var application_root := bootstrap.get_node_or_null("ApplicationRoot")
	_expect(application_root != null, "Bootstrap creates ApplicationRoot")
	if application_root != null:
		var application_script: Script = application_root.get_script()
		_expect(application_script != null, "ApplicationRoot has an attached script")
		if application_script != null:
			_expect(
				application_script.resource_path == "res://scenes/app/application_root.gd",
				"Bootstrap uses the production ApplicationRoot",
			)
		_expect(application_root.is_started(), "ApplicationRoot completes startup")
		_expect(
			application_root.get_node_or_null("PersistentUI") is CanvasLayer,
			"ApplicationRoot has persistent UI CanvasLayer",
		)
		_expect(
			application_root.get_node_or_null("TransitionLayer") is CanvasLayer,
			"ApplicationRoot has transition CanvasLayer",
		)

	var route_host := bootstrap.get_node_or_null("ApplicationRoot/RouteHost")
	_expect(route_host != null, "ApplicationRoot owns RouteHost")
	if route_host != null:
		_expect(route_host.get_child_count() == 1, "RouteHost owns one active route")

	var scene_router := root.get_node_or_null("SceneRouter")
	_expect(scene_router != null, "SceneRouter is registered as an Autoload")
	if scene_router != null:
		_expect(
			scene_router.get_current_route_id() == &"title",
			"ApplicationRoot starts on the title route",
		)

	var title_screen := bootstrap.get_node_or_null(
		"ApplicationRoot/RouteHost/TitleScreen"
	)
	_expect(title_screen is Control, "initial route is the TitleScreen")
	var title_label := bootstrap.get_node_or_null(
		"ApplicationRoot/RouteHost/TitleScreen/Content/Text/Title"
	) as Label
	_expect(title_label != null, "TitleScreen has a title Label")
	if title_label != null:
		_expect(title_label.text == EXPECTED_TITLE, "TitleScreen displays ETHERFOOD")
	var prompt_label := bootstrap.get_node_or_null(
		"ApplicationRoot/RouteHost/TitleScreen/Content/Text/Prompt"
	) as Label
	_expect(prompt_label != null, "TitleScreen has a prompt Label")
	if prompt_label != null:
		_expect(prompt_label.text == EXPECTED_PROMPT, "TitleScreen displays its input prompt")
	var title_content := bootstrap.get_node_or_null(
		"ApplicationRoot/RouteHost/TitleScreen/Content"
	) as CenterContainer
	var title_text := bootstrap.get_node_or_null(
		"ApplicationRoot/RouteHost/TitleScreen/Content/Text"
	) as VBoxContainer
	_expect_centered_content(
		title_content,
		title_text,
		configured_viewport_size,
		"TitleScreen",
	)
	_expect(
		not _contains_label_text(bootstrap, FORGE2D_PLACEHOLDER),
		"no Forge2D placeholder text remains visible",
	)

	if title_screen != null and scene_router != null:
		title_screen._unhandled_input(_pressed_action(&"ui_accept"))
		_expect(
			scene_router.get_current_route_id() == &"main_menu",
			"ui_accept opens the main menu route",
		)
		await process_frame
		if route_host != null:
			_expect(
				route_host.get_child_count() == 1,
				"RouteHost owns one route after opening the main menu",
			)
		var main_menu := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu"
		)
		_expect(main_menu is Control, "main_menu route loads the MainMenu scene")
		var main_menu_title := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Title"
		) as Label
		_expect(main_menu_title != null, "MainMenu has a title Label")
		if main_menu_title != null:
			_expect(main_menu_title.text == EXPECTED_TITLE, "MainMenu displays ETHERFOOD")
		var main_menu_heading := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Heading"
		) as Label
		_expect(main_menu_heading != null, "MainMenu has a heading Label")
		if main_menu_heading != null:
			_expect(
				main_menu_heading.text == EXPECTED_MAIN_MENU_HEADING,
				"MainMenu displays its heading",
			)
		var main_menu_content := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content"
		) as CenterContainer
		var main_menu_text := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text"
		) as VBoxContainer
		_expect_centered_content(
			main_menu_content,
			main_menu_text,
			configured_viewport_size,
			"MainMenu",
		)
		var buttons := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons"
		) as VBoxContainer
		_expect(buttons != null, "MainMenu has a button list")
		if buttons != null:
			_expect(
				buttons.get_child_count() == EXPECTED_MAIN_MENU_BUTTONS.size(),
				"MainMenu has exactly six buttons in a debug build",
			)
			var inspected_button_count := mini(
				buttons.get_child_count(),
				EXPECTED_MAIN_MENU_BUTTONS.size(),
			)
			for index in range(inspected_button_count):
				var button := buttons.get_child(index) as Button
				_expect(button != null, "MainMenu child %d is a Button" % index)
				if button != null:
					_expect(
						button.text == EXPECTED_MAIN_MENU_BUTTONS[index],
						"MainMenu button %d has the expected text" % index,
					)
					_expect(
						button.is_visible_in_tree(),
						"MainMenu button '%s' is visible" % button.text,
					)

		var continue_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/ContinueButton"
		) as Button
		var new_game_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/NewGameButton"
		) as Button
		var settings_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/SettingsButton"
		) as Button
		var credits_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/CreditsButton"
		) as Button
		var visual_lab_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/VisualLabButton"
		) as Button
		var quit_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/QuitButton"
		) as Button
		_expect_disabled_menu_button(continue_button, "Fortsetzen")
		_expect_disabled_menu_button(settings_button, "Einstellungen")
		_expect_disabled_menu_button(credits_button, "Mitwirkende")
		_expect_disabled_menu_button(quit_button, "Spiel beenden")
		_expect(new_game_button != null, "MainMenu has the Neues Spiel button")
		if new_game_button != null:
			_expect(not new_game_button.disabled, "Neues Spiel is enabled")
			_expect(new_game_button.has_focus(), "Neues Spiel receives initial focus")
		_expect(visual_lab_button != null, "MainMenu has the visual laboratory button")
		if visual_lab_button != null:
			_expect(
				visual_lab_button.is_visible_in_tree(),
				"VisualLabButton is visible in a debug build",
			)
			_expect(not visual_lab_button.disabled, "VisualLabButton is enabled")
			_expect(
				visual_lab_button.focus_mode == Control.FOCUS_ALL,
				"VisualLabButton participates in debug-build focus navigation",
			)
			_expect(
				not visual_lab_button.has_focus(),
				"Neues Spiel keeps focus when VisualLabButton is available",
			)
			visual_lab_button.pressed.emit()

		_expect(
			scene_router.get_current_route_id() == &"visual_lab",
			"VisualLabButton opens the visual_lab route",
		)
		await process_frame
		if route_host != null:
			_expect(
				route_host.get_child_count() == 1,
				"RouteHost owns one route after opening the visual laboratory",
			)
		var visual_lab := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab"
		) as Control
		_expect(visual_lab is Control, "visual_lab route loads the VisualLab scene")
		var background_layer := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/BackgroundLayer"
		) as CanvasLayer
		_expect(background_layer != null, "VisualLab has a background CanvasLayer")
		if background_layer != null:
			_expect(background_layer.layer == -10, "VisualLab background layer is behind world")
			_expect(
				not background_layer.follow_viewport_enabled,
				"VisualLab background does not follow the viewport transform",
			)
		var background := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/BackgroundLayer/Background"
		) as ColorRect
		_expect(
			background != null and background.get_parent() == background_layer,
			"VisualLab background belongs to its CanvasLayer",
		)
		if background != null:
			_expect(
				background.size == configured_viewport_size,
				"VisualLab background covers the configured viewport",
			)
		var test_world := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/TestWorld"
		) as Node2D
		_expect(test_world != null, "VisualLab contains the test world")
		var floor := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/TestWorld/Floor"
		) as Polygon2D
		_expect(floor != null and floor.visible, "VisualLab contains a visible floor")
		if floor != null:
			var floor_bounds := _polygon_bounds(floor.polygon)
			_expect(
				floor_bounds == EXPECTED_VISUAL_LAB_WORLD_BOUNDS,
				"VisualLab floor covers the 3840 by 2160 test world",
			)
			_expect(
				floor_bounds.size.x > configured_viewport_size.x
				and floor_bounds.size.y > configured_viewport_size.y,
				"VisualLab test world is larger than the viewport",
			)
		var arena_bounds := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/TestWorld/ArenaBounds"
		) as Node2D
		_expect(arena_bounds != null, "VisualLab contains arena bounds")
		if arena_bounds != null:
			_expect(arena_bounds.get_child_count() == 4, "VisualLab has four arena walls")
			_expect_arena_wall(
				arena_bounds,
				&"LeftWall",
				Vector2(0, 1080),
				Vector2(32, 2160),
			)
			_expect_arena_wall(
				arena_bounds,
				&"RightWall",
				Vector2(3840, 1080),
				Vector2(32, 2160),
			)
			_expect_arena_wall(
				arena_bounds,
				&"TopWall",
				Vector2(1920, 0),
				Vector2(3840, 32),
			)
			_expect_arena_wall(
				arena_bounds,
				&"BottomWall",
				Vector2(1920, 2160),
				Vector2(3840, 32),
			)
		var navigation := visual_lab.get_node("LabNavigation")
		_expect(navigation.get("current_room_id") == &"hub", "VisualLab starts in the portal tower")
		var portal_room := navigation.get("current_room") as Node2D
		_expect(portal_room.get_node("Portals").get_child_count() == 9,
			"VisualLab has portals for all nine specialized rooms")
		var test_obstacle := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/TestWorld/TestObstacle"
		) as StaticBody2D
		_expect(test_obstacle != null, "VisualLab contains a test obstacle")
		if test_obstacle != null:
			_expect(
				EXPECTED_VISUAL_LAB_WORLD_BOUNDS.has_point(test_obstacle.position),
				"VisualLab test obstacle stays inside the enlarged world",
			)
			_expect(
				test_obstacle.get_node_or_null("Visual") is Polygon2D,
				"VisualLab test obstacle is visible",
			)
			var obstacle_collision := test_obstacle.get_node_or_null(
				"CollisionShape2D"
			) as CollisionShape2D
			_expect(
				obstacle_collision != null and obstacle_collision.shape != null,
				"VisualLab test obstacle has a collision shape",
			)
		var interface_layer := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer"
		) as CanvasLayer
		_expect(interface_layer != null, "VisualLab has an interface CanvasLayer")
		if interface_layer != null:
			_expect(interface_layer.layer == 10, "VisualLab interface layer is above world")
			_expect(
				not interface_layer.follow_viewport_enabled,
				"VisualLab interface does not follow the viewport transform",
			)
		var interface := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface"
		) as MarginContainer
		_expect(
			interface != null and interface.get_parent() == interface_layer,
			"VisualLab interface belongs to its CanvasLayer",
		)
		if interface != null:
			_expect(
				interface.size == EXPECTED_VISUAL_LAB_MENU_SIZE,
				"VisualLab menu stays a compact tool window",
			)
		var window_size_status := bootstrap.get_node_or_null(
			(
				"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/Pages/"
					+ "DiagnosticsPage/Content/WindowSizeStatus"
			)
		) as Label
		_expect(window_size_status != null, "VisualLab has a window-size Label")
		var original_window_size := root.size
		if window_size_status != null:
			_expect(
				window_size_status.text == _expected_window_size_status(original_window_size),
				"VisualLab displays the current main-window size",
			)
		root.size = EXPECTED_SQUARE_WINDOW_SIZE
		await process_frame
		_expect(root.size == EXPECTED_SQUARE_WINDOW_SIZE, "test window can be made square")
		_expect(
			root.content_scale_size == Vector2i(EXPECTED_REFERENCE_VIEWPORT_SIZE),
			"square window keeps the 16:9 reference content size",
		)
		if visual_lab != null:
			_expect(
				visual_lab.size == configured_viewport_size,
				"square window does not widen or heighten the game area",
			)
		if background != null:
			_expect(
				background.size == configured_viewport_size,
				"square window keeps the fixed background at reference size",
			)
		if interface != null:
			_expect(
				interface.size == EXPECTED_VISUAL_LAB_MENU_SIZE,
				"square window keeps the compact menu size",
			)
		if window_size_status != null:
			_expect(
				(
					window_size_status.text
					== _expected_window_size_status(EXPECTED_SQUARE_WINDOW_SIZE)
				),
				"VisualLab updates the displayed size after a window resize",
			)
		root.size = original_window_size
		await process_frame
		if window_size_status != null:
			_expect(
				window_size_status.text == _expected_window_size_status(original_window_size),
				"VisualLab updates the displayed size after restoring the window",
			)
		var hero_character := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/TestWorld/HeroCharacter"
		) as CharacterBody2D
		_expect(hero_character != null, "VisualLab contains HeroCharacter")
		var player_camera := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/TestWorld/HeroCharacter/PlayerCamera"
		) as Camera2D
		_expect(player_camera != null, "VisualLab contains PlayerCamera")
		if player_camera != null:
			_expect(player_camera.enabled, "VisualLab activates PlayerCamera")
			_expect(player_camera.is_current(), "VisualLab makes PlayerCamera current")
			_expect(
				player_camera.get_viewport().get_camera_2d() == player_camera,
				"VisualLab viewport uses PlayerCamera",
			)
			_expect(player_camera.limit_left == 0, "PlayerCamera has the left world limit")
			_expect(player_camera.limit_top == 0, "PlayerCamera has the top world limit")
			_expect(
				player_camera.limit_right == 3840,
				"PlayerCamera has the right world limit",
			)
			_expect(
				player_camera.limit_bottom == 2160,
				"PlayerCamera has the bottom world limit",
			)
			_expect(
				player_camera.zoom == Vector2.ONE,
				"PlayerCamera uses the selected Maßstab V0 zoom",
			)
			_expect(
				not player_camera.position_smoothing_enabled,
				"PlayerCamera follows without position smoothing",
			)
		if hero_character != null:
			_expect(
				hero_character.position == Vector2(1920, 1080),
				"VisualLab HeroCharacter starts at the enlarged world center",
			)
			var hero_collision := hero_character.get_node_or_null(
				"CollisionShape2D"
			) as CollisionShape2D
			_expect(
				hero_collision != null and hero_collision.shape != null,
				"VisualLab HeroCharacter has a collision shape",
			)
			var hero_start_position := hero_character.global_position
			var camera_start_position := Vector2.ZERO
			if player_camera != null:
				player_camera.force_update_scroll()
				camera_start_position = player_camera.global_position
			var interface_screen_position := Vector2.ZERO
			if interface != null:
				interface_screen_position = interface.get_screen_transform().origin
			var background_screen_position := Vector2.ZERO
			if background != null:
				background_screen_position = background.get_screen_transform().origin
			var movement_per_frame := (
				float(hero_character.call("get_current_speed"))
				/ Engine.physics_ticks_per_second
			)
			var movement_frame_count := maxi(
				4,
				ceili(
					visual_lab._pixel_snap_world_grid_step().x / movement_per_frame
				) + 2,
			)
			await _hold_action_for_physics_frames(
				&"gameplay_move_right",
				movement_frame_count,
			)
			await process_frame
			visual_lab._update_pixel_snap_render_alignment()
			if player_camera != null:
				player_camera.force_update_scroll()
			var hero_movement := hero_character.global_position - hero_start_position
			_expect(hero_movement.x > 0.0, "VisualLab HeroCharacter moves through the world")
			if player_camera != null:
				var camera_movement := player_camera.global_position - camera_start_position
				_expect(
					camera_movement.x > 0.0,
					"PlayerCamera follows HeroCharacter on the output-pixel grid",
				)
				var grid_step: Vector2 = visual_lab._pixel_snap_world_grid_step()
				_expect(
					absf(
						player_camera.global_position.x
						- hero_character.global_position.x
					) <= grid_step.x / 2.0 + 0.01,
					"PlayerCamera stays within half an output-pixel grid step",
				)
			if interface != null:
				_expect(
					interface.get_screen_transform().origin.is_equal_approx(
						interface_screen_position,
					),
					"VisualLab interface stays fixed while the hero moves",
				)
			if background != null:
				_expect(
					background.get_screen_transform().origin.is_equal_approx(
						background_screen_position,
					),
					"VisualLab background stays fixed while the hero moves",
				)

			navigation.call(&"enter_room", &"objects")
			hero_character.position = Vector2(2268, 1080)
			await _hold_action_for_physics_frames(&"gameplay_move_right", 4)
			_expect(
				hero_character.position.x <= 2271.5,
				"VisualLab obstacle stops HeroCharacter",
			)
			hero_character.position = Vector2(31, 1080)
			await _hold_action_for_physics_frames(&"gameplay_move_left", 4)
			_expect(
				hero_character.position.x >= 29.5,
				"VisualLab left wall stops HeroCharacter",
			)
			hero_character.position = Vector2(3809, 1080)
			await _hold_action_for_physics_frames(&"gameplay_move_right", 4)
			_expect(
				hero_character.position.x <= 3810.5,
				"VisualLab right wall stops HeroCharacter",
			)
			hero_character.position = Vector2(1920, 22)
			await _hold_action_for_physics_frames(&"gameplay_move_up", 4)
			_expect(
				hero_character.position.y >= 20.5,
				"VisualLab top wall stops HeroCharacter",
			)
			hero_character.position = Vector2(1920, 2132)
			await _hold_action_for_physics_frames(&"gameplay_move_down", 4)
			_expect(
				hero_character.position.y <= 2133.5,
				"VisualLab bottom wall stops HeroCharacter",
			)
			if player_camera != null:
				var viewport_half_size := configured_viewport_size / player_camera.zoom * 0.5
				hero_character.position = Vector2(30, 21)
				await physics_frame
				player_camera.force_update_scroll()
				_expect(
					player_camera.get_screen_center_position().is_equal_approx(
						viewport_half_size,
					),
					"PlayerCamera stops at the top and left world limits",
				)
				hero_character.position = Vector2(3810, 2133)
				await physics_frame
				player_camera.force_update_scroll()
				_expect(
					player_camera.get_screen_center_position().is_equal_approx(
						EXPECTED_VISUAL_LAB_WORLD_BOUNDS.end - viewport_half_size,
					),
					"PlayerCamera stops at the right and bottom world limits",
				)
		var visual_lab_title := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/"
			+ "Header/Title"
		) as Label
		var visual_lab_tabs := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/"
			+ "ThemeTabs"
		) as GridContainer
		var visual_lab_camera_status := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/Pages/"
			+ "CameraPage/Content/CameraStatus"
		) as Label
		var visual_lab_hero_status := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/Pages/"
			+ "ScalePage/Content/HeroSizeStatus"
		) as Label
		var visual_lab_tile_status := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/Pages/"
			+ "ScalePage/Content/TileSizeStatus"
		) as Label
		var visual_lab_world_status := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/Pages/"
			+ "WorldPage/Content/WorldStateStatus"
		) as Label
		var visual_lab_standard_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/Pages/"
			+ "CameraPage/Content/ZoomOptions/MediumButton"
		) as Button
		var visual_lab_accept_button := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/VisualLab/InterfaceLayer/Interface/Menu/"
			+ "Acceptance/AcceptButton"
		) as Button
		_expect(
			visual_lab_title != null
			and visual_lab_title.text == EXPECTED_VISUAL_LAB_TITLE,
			"VisualLab displays its themed menu title",
		)
		_expect(
			visual_lab_tabs != null and visual_lab_tabs.get_child_count() == 6,
			"VisualLab provides six extensible theme tabs",
		)
		_expect(
			visual_lab_camera_status != null
			and visual_lab_camera_status.text == EXPECTED_VISUAL_LAB_CAMERA_STATUS,
			"VisualLab displays its contextual camera status",
		)
		_expect(
			visual_lab_hero_status != null
			and visual_lab_hero_status.text == EXPECTED_VISUAL_LAB_HERO_SIZE_STATUS,
			"VisualLab displays its initial hero size",
		)
		_expect(
			visual_lab_tile_status != null
			and visual_lab_tile_status.text == EXPECTED_VISUAL_LAB_TILE_SIZE_STATUS,
			"VisualLab displays its initial tile size",
		)
		_expect(
			visual_lab_world_status != null
			and visual_lab_world_status.text == EXPECTED_VISUAL_LAB_WORLD_STATE_STATUS,
			"VisualLab displays its initial world state",
		)
		_expect(
			visual_lab_standard_button != null
			and visual_lab_standard_button.text.contains("★")
			and visual_lab_standard_button.text.contains("●"),
			"VisualLab marks game standard and current test value independently",
		)
		_expect(
			visual_lab_accept_button != null,
			"VisualLab exposes the visible game-standard action",
		)

		if visual_lab != null:
			_expect(
				not _contains_label_text(visual_lab, "Grafiktests folgen"),
				"VisualLab removes the old centered placeholder",
			)
			visual_lab._unhandled_input(_pressed_action(&"ui_cancel"))
			_expect_saved_visual_lab_settings(
				"medium",
				"medium",
				"small",
				"damaged",
				true,
				"nearest",
			)
		_expect(
			scene_router.get_current_route_id() == &"main_menu",
			"ui_cancel returns from the visual laboratory to the main menu",
		)
		if route_host != null:
			_expect(
				route_host.get_child_count() == 1,
				"RouteHost owns one route after leaving the visual laboratory",
			)
		var main_menu_after_visual_lab := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu"
		)
		_expect(
			main_menu_after_visual_lab is Control,
			"returning from the visual laboratory loads a fresh MainMenu scene",
		)
		var new_game_after_visual_lab := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/NewGameButton"
		) as Button
		_expect(
			new_game_after_visual_lab != null and new_game_after_visual_lab.has_focus(),
			"Neues Spiel regains focus after returning from the visual laboratory",
		)
		if new_game_after_visual_lab != null:
			new_game_after_visual_lab.pressed.emit()

		_expect(
			scene_router.get_current_route_id() == &"hero_room",
			"Neues Spiel opens the hero_room route",
		)
		if route_host != null:
			_expect(
				route_host.get_child_count() == 1,
				"RouteHost owns one route after opening the hero room",
			)
		var hero_room := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/HeroRoom"
		)
		_expect(hero_room is Control, "hero_room route loads the HeroRoom scene")
		var hero_room_world := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/HeroRoom/World"
		) as Node2D
		var hero_room_hero := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/HeroRoom/World/HeroCharacter"
		) as CharacterBody2D
		var hero_room_camera := bootstrap.get_node_or_null(
			(
				"ApplicationRoot/RouteHost/HeroRoom/World/HeroCharacter/"
				+ "PlayerCamera"
			)
		) as Camera2D
		var hero_room_hint := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/HeroRoom/InterfaceLayer/DevelopmentHint"
		) as Label
		var guide_companion := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/HeroRoom/World/GuideCompanion"
		) as Node2D
		var interaction_prompt := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/HeroRoom/InterfaceLayer/InteractionPrompt"
		) as Label
		var dialogue_panel := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/HeroRoom/InterfaceLayer/DialoguePanel"
		) as Panel
		var dialogue_message := bootstrap.get_node_or_null(
			(
				"ApplicationRoot/RouteHost/HeroRoom/InterfaceLayer/"
				+ "DialoguePanel/Message"
			)
		) as Label
		_expect(hero_room_world != null, "HeroRoom has a playable World")
		_expect(hero_room_hero != null, "HeroRoom instantiates HeroCharacter")
		_expect(
			hero_room_hero != null
			and hero_room_hero.position == Vector2(1280, 720),
			"HeroRoom places HeroCharacter at its center spawn",
		)
		_expect(
			hero_room_camera != null and hero_room_camera.enabled,
			"HeroRoom activates PlayerCamera",
		)
		_expect(
			hero_room_camera != null
			and hero_room_camera.zoom == Vector2(1.5, 1.5),
			"HeroRoom uses its fixed camera zoom",
		)
		_expect(hero_room_hint != null, "HeroRoom has a development hint")
		if hero_room_hint != null:
			_expect(
				hero_room_hint.text == EXPECTED_HERO_ROOM_HINT,
				"HeroRoom displays its provisional controls",
			)
		if hero_room != null:
			_expect(
				not _contains_label_text(hero_room, "Spielbarer Raum folgt"),
				"HeroRoom removes the old placeholder",
			)
		_expect(guide_companion != null, "HeroRoom contains GuideCompanion")
		_expect(interaction_prompt != null, "HeroRoom has an interaction prompt")
		_expect(
			interaction_prompt != null and not interaction_prompt.visible,
			"interaction prompt starts hidden outside guide range",
		)
		_expect(
			dialogue_panel != null and not dialogue_panel.visible,
			"guide message starts closed",
		)
		_expect(
			dialogue_message != null
			and dialogue_message.text == EXPECTED_GUIDE_MESSAGE,
			"HeroRoom contains the first guide message",
		)

		if hero_room != null and hero_room_hero != null:
			hero_room_hero.position = Vector2(1348, 720)
			await physics_frame
			await physics_frame
			_expect(
				interaction_prompt != null
				and interaction_prompt.visible
				and interaction_prompt.text == EXPECTED_GUIDE_PROMPT,
				"approaching the guide displays the interaction prompt",
			)
			hero_room._unhandled_input(_pressed_action(&"gameplay_interact"))
			_expect(
				dialogue_panel != null and dialogue_panel.visible,
				"interacting opens the first guide message",
			)
			hero_room._unhandled_input(_pressed_action(&"ui_cancel"))
			_expect(
				scene_router.get_current_route_id() == &"hero_room",
				"first ui_cancel closes the guide message in place",
			)
			_expect(
				dialogue_panel != null and not dialogue_panel.visible,
				"ui_cancel closes the guide message",
			)

		if hero_room != null:
			hero_room._unhandled_input(_pressed_action(&"ui_cancel"))
		_expect(
			scene_router.get_current_route_id() == &"main_menu",
			"ui_cancel returns from the hero room to the main menu",
		)
		if route_host != null:
			_expect(
				route_host.get_child_count() == 1,
				"RouteHost owns one route after returning to the main menu",
			)
		var main_menu_after_hero_room := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu"
		)
		_expect(
			main_menu_after_hero_room is Control,
			"returning from the hero room loads a fresh MainMenu scene",
		)
		var new_game_after_hero_room := bootstrap.get_node_or_null(
			"ApplicationRoot/RouteHost/MainMenu/Content/Text/Buttons/NewGameButton"
		) as Button
		_expect(
			new_game_after_hero_room != null and new_game_after_hero_room.has_focus(),
			"Neues Spiel regains focus after returning from the hero room",
		)

		if main_menu_after_hero_room != null:
			main_menu_after_hero_room._unhandled_input(_pressed_action(&"ui_cancel"))
		_expect(
			scene_router.get_current_route_id() == &"title",
			"ui_cancel returns from the main menu to the title route",
		)
		if route_host != null:
			_expect(
				route_host.get_child_count() == 1,
				"RouteHost owns one route after returning to the title",
			)
		_expect(
			bootstrap.get_node_or_null("ApplicationRoot/RouteHost/TitleScreen") is Control,
			"returning loads a fresh TitleScreen scene",
		)

	bootstrap.queue_free()
	await process_frame
	if scene_router != null:
		_expect(not scene_router.is_configured(), "Bootstrap shutdown clears SceneRouter")
		_expect(scene_router.get_current_route() == null, "shutdown releases route reference")


func _expect_centered_content(
	container: CenterContainer,
	content: Control,
	viewport_size: Vector2,
	description: String,
) -> void:
	_expect(container != null, "%s has a CenterContainer" % description)
	_expect(content != null, "%s has readable content" % description)
	if container == null or content == null:
		return
	_expect(container.size == viewport_size, "%s covers the reference viewport" % description)
	var content_center := content.position + content.size * 0.5
	_expect(
		content_center.distance_to(viewport_size * 0.5) <= 1.0,
		"%s content remains centered" % description,
	)
	_expect(
		content.size.x > 0.0
		and content.size.y > 0.0
		and content.position.x >= 0.0
		and content.position.y >= 0.0
		and content.position.x + content.size.x <= viewport_size.x
		and content.position.y + content.size.y <= viewport_size.y,
		"%s content remains inside the readable area" % description,
	)


func _expected_window_size_status(window_size: Vector2i) -> String:
	return "Fenster: %d × %d" % [window_size.x, window_size.y]


func _expect_saved_visual_lab_settings(
	camera_zoom_id: String,
	hero_size_id: String,
	tile_size_id: String,
	world_state_id: String,
	pixel_snap_enabled: bool,
	texture_filter_id: String,
) -> void:
	var settings := ConfigFile.new()
	_expect(
		settings.load(VISUAL_LAB_SETTINGS_TEST_PATH) == OK,
		"leaving VisualLab saves its settings to the isolated test path",
	)
	_expect(
		settings.get_value("meta", "version", 0) == 4,
		"saved VisualLab settings use version 4",
	)
	_expect(
		settings.get_value("visual_lab", "camera_zoom_world", "") == camera_zoom_id,
		"saved VisualLab settings use the expected camera ID",
	)
	_expect(
		settings.get_value("visual_lab", "camera_context", "") == "world",
		"saved VisualLab settings keep the active camera context",
	)
	_expect(
		settings.get_value("visual_lab", "camera_zoom_village", "") == "medium"
		and settings.get_value("visual_lab", "camera_zoom_dungeon", "") == "medium"
		and settings.get_value(
			"visual_lab",
			"camera_zoom_small_interior",
			"",
		) == "near",
		"saved VisualLab settings keep all contextual camera values",
	)
	_expect(
		settings.get_value("visual_lab", "hero_size", "") == hero_size_id,
		"saved VisualLab settings use the expected hero-size ID",
	)
	_expect(
		settings.get_value("visual_lab", "tile_size", "") == tile_size_id,
		"saved VisualLab settings use the expected tile-size ID",
	)
	_expect(
		settings.get_value("visual_lab", "world_state", "") == world_state_id,
		"saved VisualLab settings use the expected world-state ID",
	)
	_expect(
		settings.get_value("visual_lab", "pixel_snap", null) == pixel_snap_enabled,
		"saved VisualLab settings use the expected pixel-snap value",
	)
	_expect(
		settings.get_value("visual_lab", "texture_filter", "") == texture_filter_id,
		"saved VisualLab settings use the expected texture-filter ID",
	)


func _remove_visual_lab_test_settings() -> void:
	if not FileAccess.file_exists(VISUAL_LAB_SETTINGS_TEST_PATH):
		return
	var remove_error := DirAccess.remove_absolute(
		ProjectSettings.globalize_path(VISUAL_LAB_SETTINGS_TEST_PATH)
	)
	_expect(remove_error == OK, "isolated VisualLab test settings can be removed")


func _restore_visual_lab_settings_path() -> void:
	if _had_settings_path_override:
		ProjectSettings.set_setting(
			VISUAL_LAB_SETTINGS_PATH_PROJECT_KEY,
			_original_settings_path,
		)
		return
	ProjectSettings.set_setting(VISUAL_LAB_SETTINGS_PATH_PROJECT_KEY, null)


func _polygon_bounds(points: PackedVector2Array) -> Rect2:
	if points.is_empty():
		return Rect2()
	var minimum := points[0]
	var maximum := points[0]
	for point in points:
		minimum.x = minf(minimum.x, point.x)
		minimum.y = minf(minimum.y, point.y)
		maximum.x = maxf(maximum.x, point.x)
		maximum.y = maxf(maximum.y, point.y)
	return Rect2(minimum, maximum - minimum)


func _expect_arena_wall(
		arena_bounds: Node2D,
		wall_name: StringName,
		expected_position: Vector2,
		expected_size: Vector2,
) -> void:
	var wall := arena_bounds.get_node_or_null(NodePath(str(wall_name))) as StaticBody2D
	_expect(wall != null, "arena wall %s is a StaticBody2D" % wall_name)
	if wall == null:
		return
	_expect(wall.position == expected_position, "arena wall %s is at world edge" % wall_name)
	var wall_collision := wall.get_node_or_null("CollisionShape2D") as CollisionShape2D
	_expect(
		wall_collision != null and wall_collision.shape != null,
		"arena wall %s has a collision shape" % wall_name,
	)
	if wall_collision == null:
		return
	var rectangle := wall_collision.shape as RectangleShape2D
	_expect(rectangle != null, "arena wall %s uses a rectangle shape" % wall_name)
	if rectangle != null:
		_expect(rectangle.size == expected_size, "arena wall %s spans world edge" % wall_name)


func _hold_action_for_physics_frames(action: StringName, frame_count: int) -> void:
	Input.action_press(action)
	for _frame in range(frame_count):
		await physics_frame
	Input.action_release(action)
	await physics_frame


func _contains_label_text(root_node: Node, expected_text: String) -> bool:
	var label_nodes: Array[Node] = root_node.find_children("*", "Label", true, false)
	for label_node in label_nodes:
		var label := label_node as Label
		if label != null and label.text.contains(expected_text):
			return true
	return false


func _pressed_action(action: StringName) -> InputEventAction:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = true
	return event


func _expect_disabled_menu_button(button: Button, button_text: String) -> void:
	_expect(button != null, "MainMenu has the %s button" % button_text)
	if button == null:
		return
	_expect(button.disabled, "%s is disabled" % button_text)
	_expect(
		button.focus_mode == Control.FOCUS_NONE,
		"%s cannot receive focus" % button_text,
	)
	_expect(not button.has_focus(), "%s is not selected" % button_text)


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append(description)


func _finish() -> void:
	if failures.is_empty():
		print("EtherFood bootstrap integration test: passed")
		quit(0)
		return

	for failure in failures:
		push_error("Bootstrap integration test failed: %s" % failure)
	quit(1)
