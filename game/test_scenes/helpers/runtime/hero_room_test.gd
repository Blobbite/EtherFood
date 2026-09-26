extends RefCounted

const HERO_ROOM_SCENE_PATH := "res://test_scenes/environment/hero_room.tscn"
const APPLICATION_ROOT_SCENE := preload("res://scenes/app/application_root.tscn")
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const CAMERA_CONTROLLER_SCRIPT := preload(
	"res://shared/camera/player_camera_controller.gd"
)
const SETTINGS_PATH_PROJECT_KEY := "etherfood/development/visual_lab_settings_path"
const DEFAULT_SETTINGS_PATH := "user://visual_lab_settings.cfg"
const ROOM_SIZE := Vector2(2560, 1440)
const HERO_SPAWN := Vector2(1280, 720)
const HERO_HEIGHT := 80.0
const CAMERA_ZOOM := Vector2(1.5, 1.5)
const MOVEMENT_ACTIONS: Array[StringName] = [
	&"gameplay_move_left",
	&"gameplay_move_right",
	&"gameplay_move_up",
	&"gameplay_move_down",
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_release_movement_actions()
	await _test_room_contract(tree)
	await _test_main_menu_return(tree)
	_release_movement_actions()
	return failures


func _test_room_contract(tree: SceneTree) -> void:
	var settings_path := str(
		ProjectSettings.get_setting(
			SETTINGS_PATH_PROJECT_KEY,
			DEFAULT_SETTINGS_PATH,
		)
	)
	_write_conflicting_visual_lab_settings(settings_path)

	var packed_scene := load(HERO_ROOM_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "HeroRoom scene loads")
	if packed_scene == null:
		DirAccess.remove_absolute(ProjectSettings.globalize_path(settings_path))
		return

	var room_node := packed_scene.instantiate()
	_expect(room_node is Control, "HeroRoom instantiates as Control")
	if not room_node is Control:
		if room_node != null:
			room_node.free()
		DirAccess.remove_absolute(ProjectSettings.globalize_path(settings_path))
		return

	var hero_room := room_node as Control
	tree.root.add_child(hero_room)
	await tree.process_frame
	await tree.physics_frame
	_expect(
		not _contains_label_text(hero_room, "Spielbarer Raum folgt"),
		"old playable-room placeholder is removed",
	)
	_expect(
		hero_room.get_visual_tile_size() == Vector2i(32, 32),
		"HeroRoom reads its fixed 32 by 32 grid from visual standards",
	)
	_expect(
		hero_room.get_node_or_null("BackgroundLayer") is CanvasLayer,
		"HeroRoom has a BackgroundLayer",
	)
	_expect(
		hero_room.get_node_or_null("BackgroundLayer/Background") is ColorRect,
		"BackgroundLayer has a viewport background",
	)
	var world := hero_room.get_node_or_null("World") as Node2D
	var floor := hero_room.get_node_or_null("World/Floor") as Polygon2D
	var room_bounds := hero_room.get_node_or_null("World/RoomBounds") as Node2D
	var obstacles := hero_room.get_node_or_null("World/Obstacles") as Node2D
	var hero_spawn := hero_room.get_node_or_null("World/HeroSpawn") as Marker2D
	var hero: HERO_SCRIPT = hero_room.get_node_or_null(
		"World/HeroCharacter"
	) as HERO_SCRIPT
	var player_camera: CAMERA_CONTROLLER_SCRIPT = hero_room.get_node_or_null(
		"World/HeroCharacter/PlayerCamera"
	) as CAMERA_CONTROLLER_SCRIPT
	var development_hint := hero_room.get_node_or_null(
		"InterfaceLayer/DevelopmentHint"
	) as Label

	_expect(world != null, "World exists")
	_expect(floor != null, "World has a polygonal stone floor")
	if floor != null:
		_expect(
			_polygon_bounds(floor.polygon) == Rect2(Vector2.ZERO, ROOM_SIZE),
			"floor covers the 2560 by 1440 room",
		)
	_expect(room_bounds != null, "World has RoomBounds")
	_expect(obstacles != null, "World has Obstacles")
	_expect(hero_spawn != null, "World has HeroSpawn")
	_expect(hero is CharacterBody2D, "HeroCharacter is instantiated as CharacterBody2D")
	_expect(player_camera != null, "HeroCharacter retains PlayerCamera")
	_expect(
		hero_room.get_node_or_null("InterfaceLayer") is CanvasLayer,
		"HeroRoom has an InterfaceLayer",
	)
	_expect(development_hint != null, "InterfaceLayer has DevelopmentHint")

	if hero_spawn != null:
		_expect(hero_spawn.global_position == HERO_SPAWN, "HeroSpawn is at room center")
	if hero != null and hero_spawn != null:
		_expect(
			hero.global_position.is_equal_approx(hero_spawn.global_position),
			"hero starts at HeroSpawn",
		)
		_expect(
			is_equal_approx(hero.get_appearance_height(), HERO_HEIGHT),
			"hero uses the fixed 80 world-pixel height",
		)
		var hero_collision := hero.get_node_or_null("CollisionShape2D") as CollisionShape2D
		_expect(
			hero_collision != null and hero_collision.shape != null,
			"hero retains its collision shape",
		)
		if hero_collision != null:
			var hero_rectangle := hero_collision.shape as RectangleShape2D
			_expect(
				hero_rectangle != null and hero_rectangle.size == Vector2(28, 16),
				"hero retains its 28 by 16 foot collision",
			)

	if player_camera != null:
		_expect(player_camera.enabled, "PlayerCamera is enabled")
		_expect(player_camera.is_current(), "PlayerCamera is current")
		_expect(player_camera.zoom == CAMERA_ZOOM, "camera uses active 1.50 zoom")
		_expect(
			is_equal_approx(player_camera.get_base_zoom(), 1.5),
			"camera receives the small-interior scene profile",
		)
		_expect(player_camera.limit_left == 0, "camera left limit is zero")
		_expect(player_camera.limit_top == 0, "camera top limit is zero")
		_expect(player_camera.limit_right == 2560, "camera right limit is 2560")
		_expect(player_camera.limit_bottom == 1440, "camera bottom limit is 1440")
		_expect(
			not player_camera.position_smoothing_enabled,
			"camera follows without position smoothing",
		)

	_expect_wall(
		room_bounds,
		&"LeftWall",
		Vector2(0, 720),
		Vector2(32, 1440),
	)
	_expect_wall(
		room_bounds,
		&"RightWall",
		Vector2(2560, 720),
		Vector2(32, 1440),
	)
	_expect_wall(
		room_bounds,
		&"TopWall",
		Vector2(1280, 0),
		Vector2(2560, 32),
	)
	_expect_wall(
		room_bounds,
		&"BottomWall",
		Vector2(1280, 1440),
		Vector2(2560, 32),
	)
	_expect_obstacle(obstacles, &"StoneBlockLeft", Vector2(800, 656))
	_expect_obstacle(obstacles, &"StoneBlockRight", Vector2(1760, 784))

	if development_hint != null:
		_expect(
			development_hint.visible == OS.is_debug_build(),
			"development hint visibility follows the debug build",
		)
		_expect(
			development_hint.text
				== (
					"HELDENRAUM · PROTOTYP\n"
					+ "WASD / Pfeile: laufen · Feststelltaste: gehen\n"
					+ "Doppel-Tap: rennen · Shift halten: sprinten\n"
					+ "Strg: schleichen · Leertaste: springen\n"
					+ "E / A: interagieren · Esc / B: Hauptmenü"
			),
			"development hint lists the provisional controls",
		)

	if hero != null:
		await _expect_movement_and_collisions(tree, hero, player_camera)

	hero_room.queue_free()
	await tree.process_frame
	DirAccess.remove_absolute(ProjectSettings.globalize_path(settings_path))


func _expect_movement_and_collisions(
	tree: SceneTree,
	hero: HERO_SCRIPT,
	player_camera: CAMERA_CONTROLLER_SCRIPT,
) -> void:
	hero.global_position = HERO_SPAWN
	var hero_start := hero.global_position
	var camera_start := (
		player_camera.global_position if player_camera != null else Vector2.ZERO
	)
	await _hold_action(tree, &"gameplay_move_right", 4)
	var hero_movement := hero.global_position - hero_start
	_expect(hero_movement.x > 0.0, "hero moves with gameplay input")
	if player_camera != null:
		_expect(
			(player_camera.global_position - camera_start).is_equal_approx(hero_movement),
			"camera follows the moving hero",
		)

	hero.global_position = Vector2(31, 720)
	await _hold_action(tree, &"gameplay_move_left", 4)
	_expect(hero.global_position.x >= 29.5, "left wall keeps hero inside")

	hero.global_position = Vector2(2529, 720)
	await _hold_action(tree, &"gameplay_move_right", 4)
	_expect(hero.global_position.x <= 2530.5, "right wall keeps hero inside")

	hero.global_position = Vector2(1280, 22)
	await _hold_action(tree, &"gameplay_move_up", 4)
	_expect(hero.global_position.y >= 20.5, "top wall keeps hero inside")

	hero.global_position = Vector2(1280, 1412)
	await _hold_action(tree, &"gameplay_move_down", 4)
	_expect(hero.global_position.y <= 1413.5, "bottom wall keeps hero inside")

	hero.global_position = Vector2(682, 656)
	await _hold_action(tree, &"gameplay_move_right", 8)
	_expect(hero.global_position.x <= 691.0, "left stone block stops hero")

	hero.global_position = Vector2(1878, 784)
	await _hold_action(tree, &"gameplay_move_left", 8)
	_expect(hero.global_position.x >= 1869.0, "right stone block stops hero")


func _test_main_menu_return(tree: SceneTree) -> void:
	var scene_router := tree.root.get_node_or_null("SceneRouter")
	_expect(scene_router != null, "SceneRouter Autoload is present")
	if scene_router == null:
		return
	_expect(not scene_router.is_configured(), "navigation test starts unconfigured")
	if scene_router.is_configured():
		return

	var application_root := APPLICATION_ROOT_SCENE.instantiate()
	tree.root.add_child(application_root)
	await tree.process_frame
	_expect(application_root.is_started(), "ApplicationRoot starts for navigation test")
	var route_host := application_root.get_node_or_null("RouteHost")
	_expect(route_host != null, "navigation test has RouteHost")
	_expect(scene_router.navigate(&"hero_room") == OK, "hero_room route opens")
	var hero_room := scene_router.get_current_route() as Control
	_expect(hero_room is Control, "active hero_room is a Control")
	if hero_room != null:
		hero_room._unhandled_input(_pressed_action(&"ui_cancel"))
	_expect(
		scene_router.get_current_route_id() == &"main_menu",
		"ui_cancel returns from hero room to main menu",
	)
	if route_host != null:
		_expect(route_host.get_child_count() == 1, "RouteHost keeps one active route")
		_expect(route_host.get_child(0).name == "MainMenu", "MainMenu is active")

	application_root.queue_free()
	await tree.process_frame
	_expect(not scene_router.is_configured(), "navigation test releases SceneRouter")


func _expect_wall(
	room_bounds: Node2D,
	wall_name: StringName,
	expected_position: Vector2,
	expected_size: Vector2,
) -> void:
	var wall := (
		room_bounds.get_node_or_null(NodePath(str(wall_name))) as StaticBody2D
		if room_bounds != null
		else null
	)
	_expect(wall != null, "%s is a StaticBody2D" % wall_name)
	if wall == null:
		return
	_expect(wall.position == expected_position, "%s is at the room edge" % wall_name)
	var collision := wall.get_node_or_null("CollisionShape2D") as CollisionShape2D
	_expect(collision != null and collision.shape != null, "%s has collision" % wall_name)
	if collision != null:
		var rectangle := collision.shape as RectangleShape2D
		_expect(
			rectangle != null and rectangle.size == expected_size,
			"%s spans the expected room edge" % wall_name,
		)


func _expect_obstacle(
	obstacles: Node2D,
	obstacle_name: StringName,
	expected_position: Vector2,
) -> void:
	var obstacle := (
		obstacles.get_node_or_null(NodePath(str(obstacle_name))) as StaticBody2D
		if obstacles != null
		else null
	)
	_expect(obstacle != null, "%s is a StaticBody2D" % obstacle_name)
	if obstacle == null:
		return
	_expect(
		obstacle.position == expected_position,
		"%s keeps its provisional position" % obstacle_name,
	)
	var collision := obstacle.get_node_or_null("CollisionShape2D") as CollisionShape2D
	_expect(
		collision != null and collision.shape != null,
		"%s has a collision shape" % obstacle_name,
	)
	if collision != null:
		var rectangle := collision.shape as RectangleShape2D
		_expect(
			rectangle != null and rectangle.size == Vector2(192, 128),
			"%s uses the expected stone-block collision" % obstacle_name,
		)


func _write_conflicting_visual_lab_settings(settings_path: String) -> void:
	var settings := ConfigFile.new()
	settings.set_value("visual_lab", "camera_zoom", "wide")
	settings.set_value("visual_lab", "hero_size", "small")
	settings.set_value("visual_lab", "tile_size", "large")
	settings.set_value("visual_lab", "world_state", "restored")
	_expect(
		settings.save(settings_path) == OK,
		"conflicting visual-lab settings can be prepared",
	)


func _hold_action(tree: SceneTree, action: StringName, frame_count: int) -> void:
	Input.action_press(action)
	for _frame in range(frame_count):
		await tree.physics_frame
	Input.action_release(action)
	await tree.physics_frame


func _release_movement_actions() -> void:
	for action in MOVEMENT_ACTIONS:
		Input.action_release(action)


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


func _contains_label_text(root_node: Node, expected_text: String) -> bool:
	for label_node in root_node.find_children("*", "Label", true, false):
		var label := label_node as Label
		if label != null and label.text.contains(expected_text):
			return true
	return false


func _pressed_action(action: StringName) -> InputEventAction:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = true
	return event


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("HeroRoom: %s" % description)
