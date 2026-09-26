extends RefCounted

const HERO_ROOM_SCENE_PATH := "res://test_scenes/environment/hero_room.tscn"
const APPLICATION_ROOT_SCENE := preload("res://scenes/app/application_root.tscn")
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const GUIDE_SCRIPT := preload(
	"res://test_scenes/characters/npc/guide/guide_companion.gd"
)
const INTERACTABLE_SCRIPT := preload(
	"res://shared/interactions/interactable_area.gd"
)
const INTERACT_ACTION := &"gameplay_interact"
const PROMPT_TEXT := "E / A: Ratgeber ansprechen"
const SPEAKER_TEXT := "Ratgeber"
const MESSAGE_TEXT := (
	"Du bist wach. Beweg dich erst einmal.\n"
	+ "Wir müssen einen Ausgang aus diesem Raum finden."
)
const HERO_START := Vector2(1280, 720)
const GUIDE_POSITION := Vector2(1440, 720)
const HERO_NEAR_GUIDE := Vector2(1344, 720)
const MOVEMENT_ACTIONS: Array[StringName] = [
	&"gameplay_move_left",
	&"gameplay_move_right",
	&"gameplay_move_up",
	&"gameplay_move_down",
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_release_movement_actions()
	_expect_input_mapping()
	await _test_interaction_contract(tree)
	await _test_escape_precedence(tree)
	_release_movement_actions()
	return failures


func _test_interaction_contract(tree: SceneTree) -> void:
	var packed_scene := load(HERO_ROOM_SCENE_PATH) as PackedScene
	_expect(packed_scene != null, "HeroRoom scene loads")
	if packed_scene == null:
		return

	var room_node := packed_scene.instantiate()
	_expect(room_node is Control, "HeroRoom instantiates for interaction test")
	if not room_node is Control:
		if room_node != null:
			room_node.free()
		return

	var hero_room := room_node as Control
	tree.root.add_child(hero_room)
	await tree.process_frame
	await tree.physics_frame
	await tree.physics_frame

	var world := hero_room.get_node_or_null("World") as Node2D
	var hero: HERO_SCRIPT = hero_room.get_node_or_null(
		"World/HeroCharacter"
	) as HERO_SCRIPT
	var guide: GUIDE_SCRIPT = hero_room.get_node_or_null(
		"World/GuideCompanion"
	) as GUIDE_SCRIPT
	var interaction_prompt := hero_room.get_node_or_null(
		"InterfaceLayer/InteractionPrompt"
	) as Label
	var dialogue_panel := hero_room.get_node_or_null(
		"InterfaceLayer/DialoguePanel"
	) as Panel
	var speaker := hero_room.get_node_or_null(
		"InterfaceLayer/DialoguePanel/Speaker"
	) as Label
	var message := hero_room.get_node_or_null(
		"InterfaceLayer/DialoguePanel/Message"
	) as Label

	_expect(world != null, "HeroRoom retains World")
	_expect(hero != null, "HeroRoom contains HeroCharacter")
	_expect(guide != null, "HeroRoom contains the visible GuideCompanion")
	_expect(interaction_prompt != null, "HeroRoom has an interaction prompt")
	_expect(dialogue_panel != null, "HeroRoom has a dialogue prototype panel")
	_expect(speaker != null and speaker.text == SPEAKER_TEXT, "panel names the guide")
	_expect(message != null and message.text == MESSAGE_TEXT, "panel has the exact message")
	if hero == null or guide == null or interaction_prompt == null or dialogue_panel == null:
		hero_room.queue_free()
		await tree.process_frame
		return

	_expect_guide_visual_contract(guide)
	_expect_hero_detector_contract(hero)
	_expect(guide.global_position == GUIDE_POSITION, "guide keeps its room position")
	_expect(hero.global_position == HERO_START, "hero starts outside guide range")
	_expect(not interaction_prompt.visible, "prompt starts hidden outside range")
	_expect(not dialogue_panel.visible, "message starts closed")
	_expect(not hero_room.is_guide_message_open(), "message state starts closed")
	_expect(hero.get_nearest_interactable() == null, "hero starts without a target")

	hero_room._unhandled_input(_pressed_key(KEY_E))
	_expect(not dialogue_panel.visible, "E cannot interact outside detector range")

	await _expect_nearest_valid_target(tree, world, hero, guide, interaction_prompt)
	_expect(interaction_prompt.visible, "prompt appears inside guide range")
	_expect(interaction_prompt.text == PROMPT_TEXT, "prompt explains E and A")

	hero_room._unhandled_input(_pressed_key(KEY_E))
	_expect(dialogue_panel.visible, "E opens the guide message")
	_expect(hero_room.is_guide_message_open(), "room tracks the open message")
	_expect(not interaction_prompt.visible, "open message hides interaction prompt")
	_expect(not hero.is_movement_enabled(), "open message disables hero movement")

	hero_room._unhandled_input(_pressed_key(KEY_E, true))
	_expect(dialogue_panel.visible, "held E does not immediately close the message")

	var blocked_position := hero.global_position
	await _hold_action(tree, &"gameplay_move_right", 3)
	_expect(
		hero.global_position.is_equal_approx(blocked_position),
		"hero remains still while the message is open",
	)
	_expect(hero.velocity.is_zero_approx(), "message clears hero movement velocity")

	hero_room._unhandled_input(_pressed_button(JOY_BUTTON_A))
	_expect(not dialogue_panel.visible, "Controller-A closes the guide message")
	_expect(not hero_room.is_guide_message_open(), "room tracks the closed message")
	_expect(hero.is_movement_enabled(), "closing message restores hero movement")
	_expect(interaction_prompt.visible, "closing message restores nearby prompt")

	var resumed_position := hero.global_position
	await _hold_action(tree, &"gameplay_move_left", 3)
	_expect(
		hero.global_position.x < resumed_position.x,
		"hero can move again after closing the message",
	)

	hero.global_position = HERO_NEAR_GUIDE
	await tree.physics_frame
	await tree.physics_frame
	hero_room._unhandled_input(_pressed_button(JOY_BUTTON_A))
	_expect(dialogue_panel.visible, "Controller-A opens the guide message")
	hero_room._unhandled_input(_pressed_key(KEY_E))
	_expect(not dialogue_panel.visible, "E closes the guide message")

	hero.global_position = HERO_START
	await tree.physics_frame
	await tree.physics_frame
	_expect(not interaction_prompt.visible, "prompt hides after leaving guide range")
	_expect(hero.get_nearest_interactable() == null, "target clears outside range")
	hero_room._unhandled_input(_pressed_button(JOY_BUTTON_A))
	_expect(not dialogue_panel.visible, "Controller-A cannot interact outside range")

	hero_room.queue_free()
	await tree.process_frame


func _expect_nearest_valid_target(
	tree: SceneTree,
	world: Node2D,
	hero: HERO_SCRIPT,
	guide: GUIDE_SCRIPT,
	interaction_prompt: Label,
) -> void:
	hero.global_position = Vector2(1360, 720)
	await tree.physics_frame
	await tree.physics_frame
	var guide_area := guide.get_interactable_area() as Area2D
	_expect(hero.get_nearest_interactable() == guide_area, "guide is selected in range")

	var alternative: INTERACTABLE_SCRIPT = INTERACTABLE_SCRIPT.new()
	alternative.name = "AlternativeInteractable"
	alternative.collision_layer = 2
	alternative.collision_mask = 0
	alternative.monitoring = false
	alternative.interaction_prompt = "Alternative"
	alternative.interaction_enabled = false
	var alternative_collision := CollisionShape2D.new()
	var alternative_shape := CircleShape2D.new()
	alternative_shape.radius = 8.0
	alternative_collision.shape = alternative_shape
	alternative.add_child(alternative_collision)
	world.add_child(alternative)
	alternative.global_position = Vector2(1376, 720)
	await tree.physics_frame
	await tree.physics_frame
	_expect(
		hero.get_nearest_interactable() == guide_area,
		"closer disabled area is not a valid target",
	)

	alternative.interaction_enabled = true
	await tree.physics_frame
	_expect(
		hero.get_nearest_interactable() == alternative,
		"nearest valid interaction partner is selected",
	)
	_expect(interaction_prompt.text == "Alternative", "prompt follows nearest target")

	alternative.global_position = Vector2(1272, 720)
	await tree.physics_frame
	await tree.physics_frame
	_expect(
		hero.get_nearest_interactable() == guide_area,
		"selection returns to guide when guide becomes nearest",
	)
	_expect(interaction_prompt.text == PROMPT_TEXT, "guide prompt is restored")

	alternative.queue_free()
	await tree.process_frame
	await tree.physics_frame


func _expect_guide_visual_contract(guide: GUIDE_SCRIPT) -> void:
	_expect(guide.visible, "GuideCompanion is visible")
	_expect(guide.find_child("Hat", true, false) is Node2D, "guide has a large hat")
	_expect(
		guide.find_child("LeftEye", true, false) is Polygon2D,
		"guide has a visible left eye",
	)
	_expect(
		guide.find_child("RightEye", true, false) is Polygon2D,
		"guide has a visible right eye",
	)
	_expect(
		guide.find_child("TinyBody", true, false) is Polygon2D,
		"guide has a very small body",
	)
	_expect(guide.find_child("Broom", true, false) is Node2D, "guide has a broom")
	_expect(
		guide.find_child("Shadow", true, false) is Polygon2D,
		"guide has a small hard-edged shadow",
	)
	_expect(
		guide.find_children("*", "Sprite2D", true, false).is_empty(),
		"guide prototype uses original project-native shapes",
	)

	var area: INTERACTABLE_SCRIPT = guide.get_node_or_null(
		"InteractableArea"
	) as INTERACTABLE_SCRIPT
	_expect(area != null, "guide owns an InteractableArea")
	if area == null:
		return
	_expect(area.interaction_prompt == PROMPT_TEXT, "guide provides exact prompt")
	_expect(area.collision_layer == 2, "guide area uses interactable layer")
	_expect(area.collision_mask == 0, "guide area scans no physics layers")
	_expect(not area.monitoring, "guide area does not scan other areas")
	_expect(
		guide.find_children("*", "StaticBody2D", true, false).is_empty(),
		"guide creates no physical blocker",
	)
	var collision := area.get_node_or_null("CollisionShape2D") as CollisionShape2D
	_expect(collision != null and collision.shape != null, "guide area has a shape")
	if collision != null:
		_expect(collision.shape is CircleShape2D, "guide area uses a compact circle")


func _expect_hero_detector_contract(hero: HERO_SCRIPT) -> void:
	var detector := hero.get_node_or_null("InteractionDetector") as Area2D
	var collision := hero.get_node_or_null(
		"InteractionDetector/CollisionShape2D"
	) as CollisionShape2D
	_expect(detector != null, "hero owns InteractionDetector")
	_expect(collision != null and collision.shape != null, "detector has a shape")
	if detector != null:
		_expect(detector.collision_layer == 0, "detector adds no collision layer")
		_expect(detector.collision_mask == 2, "detector scans interactable layer")
	if collision != null:
		var circle := collision.shape as CircleShape2D
		_expect(
			circle != null and is_equal_approx(circle.radius, 96.0),
			"detector range is 96 world pixels",
		)


func _test_escape_precedence(tree: SceneTree) -> void:
	var scene_router := tree.root.get_node_or_null("SceneRouter")
	_expect(scene_router != null, "SceneRouter Autoload is present")
	if scene_router == null:
		return
	_expect(not scene_router.is_configured(), "route test starts unconfigured")
	if scene_router.is_configured():
		return

	var application_root := APPLICATION_ROOT_SCENE.instantiate()
	tree.root.add_child(application_root)
	await tree.process_frame
	_expect(application_root.is_started(), "ApplicationRoot starts for route test")
	_expect(scene_router.navigate(&"hero_room") == OK, "hero_room route opens")
	var hero_room := scene_router.get_current_route() as Control
	var hero: HERO_SCRIPT = (
		hero_room.get_node_or_null("World/HeroCharacter") as HERO_SCRIPT
		if hero_room != null
		else null
	)
	_expect(hero_room != null and hero != null, "routed hero room has its hero")
	if hero_room != null and hero != null:
		hero.global_position = HERO_NEAR_GUIDE
		await tree.physics_frame
		await tree.physics_frame
		hero_room._unhandled_input(_pressed_action(INTERACT_ACTION))
		_expect(hero_room.is_guide_message_open(), "route opens guide message")

		hero_room._unhandled_input(_pressed_action(&"ui_cancel"))
		_expect(
			scene_router.get_current_route_id() == &"hero_room",
			"first Esc closes message without leaving hero room",
		)
		_expect(not hero_room.is_guide_message_open(), "Esc closes message first")
		_expect(hero.is_movement_enabled(), "Esc restores movement after message")

		hero_room._unhandled_input(_pressed_action(&"ui_cancel"))
		_expect(
			scene_router.get_current_route_id() == &"main_menu",
			"next Esc returns to main menu",
		)
	var route_host := application_root.get_node_or_null("RouteHost")
	if route_host != null:
		_expect(route_host.get_child_count() == 1, "RouteHost keeps one route")

	application_root.queue_free()
	await tree.process_frame
	_expect(not scene_router.is_configured(), "route test releases SceneRouter")


func _expect_input_mapping() -> void:
	_expect(InputMap.has_action(INTERACT_ACTION), "InputMap defines gameplay_interact")
	if not InputMap.has_action(INTERACT_ACTION):
		return
	_expect(
		is_equal_approx(InputMap.action_get_deadzone(INTERACT_ACTION), 0.5),
		"gameplay_interact uses the button deadzone",
	)
	_expect(_has_key_mapping(KEY_E), "gameplay_interact uses E")
	_expect(_has_button_mapping(JOY_BUTTON_A), "gameplay_interact uses Controller-A")


func _has_key_mapping(expected_key: Key) -> bool:
	for input_event in InputMap.action_get_events(INTERACT_ACTION):
		var key_event := input_event as InputEventKey
		if key_event != null and (
			key_event.keycode == expected_key
			or key_event.physical_keycode == expected_key
		):
			return true
	return false


func _has_button_mapping(expected_button: JoyButton) -> bool:
	for input_event in InputMap.action_get_events(INTERACT_ACTION):
		var button_event := input_event as InputEventJoypadButton
		if button_event != null and button_event.button_index == expected_button:
			return true
	return false


func _hold_action(tree: SceneTree, action: StringName, frame_count: int) -> void:
	Input.action_press(action)
	for _frame in range(frame_count):
		await tree.physics_frame
	Input.action_release(action)
	await tree.physics_frame


func _release_movement_actions() -> void:
	for action in MOVEMENT_ACTIONS:
		Input.action_release(action)


func _pressed_action(action: StringName) -> InputEventAction:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = true
	return event


func _pressed_key(key: Key, echo: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.physical_keycode = key
	event.pressed = true
	event.echo = echo
	return event


func _pressed_button(button: JoyButton) -> InputEventJoypadButton:
	var event := InputEventJoypadButton.new()
	event.button_index = button
	event.pressed = true
	return event


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("HeroRoomInteraction: %s" % description)
