extends RefCounted

const LAB_SCENE := preload("res://scenes/dev/visual_lab.tscn")
const LabScript := preload("res://scenes/dev/visual_lab.gd")
const SoulScript := preload("res://scenes/dev/portal_lab/soul.gd")
const HeroScript := preload("res://scenes/gameplay/hero/hero_character.gd")
const SETTINGS_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_PATH := "user://portal_lab_soul_test.cfg"
const INTERACT_ACTION := &"gameplay_interact"

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	var had_override := ProjectSettings.has_setting(SETTINGS_KEY)
	var previous: Variant = ProjectSettings.get_setting(SETTINGS_KEY, null)
	ProjectSettings.set_setting(SETTINGS_KEY, SETTINGS_PATH)
	_remove_settings()
	_release_input()
	var lab := LAB_SCENE.instantiate() as LabScript
	tree.root.add_child(lab)
	await _settle_physics(tree)
	var soul := lab.lab_navigation.current_room.soul
	_expect(soul != null, "portal tower contains the soul scene")
	if soul != null:
		_expect_assets(soul)
		await _test_first_conversation(tree, lab, soul)
		await _test_departure_and_revisit(tree, lab)
	lab.queue_free()
	await tree.process_frame
	lab = LAB_SCENE.instantiate() as LabScript
	tree.root.add_child(lab)
	await _settle_physics(tree)
	soul = lab.lab_navigation.current_room.soul
	if soul != null:
		_expect(soul.visible and not soul.has_spoken and soul.phase == SoulScript.Phase.IDLE,
			"a new laboratory visit resets the soul")
		await _test_cancel_and_interrupted_departure(tree, lab, soul)
	lab.queue_free()
	await tree.process_frame
	_release_input()
	_remove_settings()
	ProjectSettings.set_setting(SETTINGS_KEY, previous if had_override else null)
	return failures


func _expect_assets(soul: SoulScript) -> void:
	var frames := soul.sprite.sprite_frames
	_expect(frames.get_animation_names().size() == 3, "all three soul phases are available")
	for animation: StringName in [&"idle", &"interact", &"depart"]:
		_expect(frames.get_frame_count(animation) == 8, "%s contains eight frames" % animation)
		_expect(frames.get_animation_loop(animation) == (animation == &"idle"),
			"only idle loops")
		for index in range(frames.get_frame_count(animation)):
			var frame := frames.get_frame_texture(animation, index) as AtlasTexture
			_expect(frame != null, "each soul frame references an atlas region")
			if frame == null:
				continue
			_expect(frame.atlas.resource_path.ends_with(
				"sools/soul_%s_spritesheet_4x2.png" % animation),
				"each phase uses its exact supplied PNG")
			_expect(frame.region == Rect2((index % 4) * 256, (index / 4) * 256, 256, 256),
				"eight 256-pixel frames follow the 4 by 2 sheet in reading order")
	_expect(soul.glow.enabled and soul.glow.energy > 0.0 and soul.glow.energy < 0.5,
		"soul provides a gentle local light")
	_expect(soul.glow.texture != null, "local light has a soft falloff texture")
	_expect(soul.find_children("*", "StaticBody2D", true, false).is_empty(),
		"the floating soul creates no movement blocker")
	var glyphs := soul.dialogue.get_node("Panel/SoulScript") as TextureRect
	_expect(glyphs.texture != null and glyphs.texture.get_width() >= 1024,
		"dialogue uses original HD glyph art independent of installed fonts")
	_expect(glyphs.texture.resource_path.ends_with("sools/soul_script.svg"),
		"the dialogue contains the invented soul script")


func _test_first_conversation(tree: SceneTree, lab: LabScript, soul: SoulScript) -> void:
	var hero := lab.hero_character
	_expect(soul.position == lab.lab_navigation.current_room.world_size / 2.0 + soul.HUB_OFFSET,
		"soul stands near the center away from the hero spawn and portals")
	_expect(soul.sprite.animation == &"idle" and soul.sprite.is_playing(), "idle starts looping")
	_expect(not soul.prompt.visible and not soul.dialogue.visible, "UI starts hidden out of range")
	_press(lab, INTERACT_ACTION)
	_expect(not soul.has_spoken, "E cannot address the soul outside interaction range")
	await soul.sprite.animation_looped
	_expect(soul.phase == SoulScript.Phase.IDLE and not soul.has_spoken,
		"idle never advances to conversation by itself")
	hero.position = soul.position + Vector2(-80, 0)
	await _settle_physics(tree)
	_expect(hero.get_nearest_interactable() == soul.interactable_area,
		"existing hero detector selects the nearby soul")
	_expect(soul.prompt.visible, "nearby soul shows the E and controller hint")
	_press(lab, &"dev_controls_toggle")
	_press(lab, INTERACT_ACTION)
	_expect(not soul.has_spoken and not soul.prompt.visible, "F5 blocks a new conversation")
	_press(lab, &"dev_controls_toggle")
	_press(lab, INTERACT_ACTION)
	_expect(soul.phase == SoulScript.Phase.INTERACT and soul.sprite.animation == &"interact",
		"first E plays the interaction sheet")
	_expect(not soul.dialogue.visible, "soul speaks after its interaction animation")
	_expect(not soul.prompt.visible and not hero.is_movement_enabled(),
		"conversation hides the prompt and pauses movement")
	var position_before := hero.position
	Input.action_press(&"gameplay_move_up")
	await _settle_physics(tree)
	Input.action_release(&"gameplay_move_up")
	_expect(hero.position == position_before and hero.velocity.is_zero_approx(),
		"held movement cannot carry the player away during conversation")
	_press(lab, INTERACT_ACTION)
	_expect(soul.sprite.animation == &"interact", "another E cannot interrupt or skip to departure")
	await _wait_until(tree, func() -> bool: return soul.dialogue.visible, 3.0,
		"interaction animation opens the glyph message")
	_press(lab, INTERACT_ACTION)
	_expect(soul.is_conversation_active(), "E during the message is not a second conversation")
	_press(lab, &"dev_controls_toggle")
	_expect(not soul.dialogue.is_visible_in_tree(), "F5 hides the soul message behind its menu")
	var remaining := soul.dialogue_timer.time_left
	await _settle_physics(tree)
	_expect(is_equal_approx(soul.dialogue_timer.time_left, remaining),
		"reading time pauses while F5 is open")
	lab._set_hero_graphics(lab.HeroGraphicsPreset.PIXEL_ART)
	lab._set_texture_filter(lab.TextureFilterPreset.NEAREST)
	_expect(soul.sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
		"F5 nearest filter also applies to soul frames")
	lab._set_texture_filter(lab.TextureFilterPreset.SOFT)
	_expect(soul.sprite.texture_filter == CanvasItem.TEXTURE_FILTER_LINEAR,
		"F5 soft filter also applies to soul frames")
	_press(lab, &"dev_controls_toggle")
	_expect(soul.dialogue.is_visible_in_tree() and not hero.is_movement_enabled(),
		"closing F5 resumes the current conversation")
	await _wait_until(tree, func() -> bool: return soul.phase == SoulScript.Phase.IDLE, 5.0,
		"message closes automatically and soul returns to idle")
	_expect(soul.has_spoken and soul.visible and not soul.dialogue.visible,
		"first conversation leaves the soul present")
	_expect(hero.is_movement_enabled() and soul.sprite.animation == &"idle",
		"idle and hero movement resume after speaking")
	var repeat_event := InputMap.action_get_events(INTERACT_ACTION)[0].duplicate() as InputEvent
	repeat_event.set("pressed", true)
	repeat_event.set("echo", true)
	lab._unhandled_input(repeat_event)
	_expect(soul.phase == SoulScript.Phase.IDLE, "held E cannot count as a fresh second press")
	hero.position += Vector2(-320, 0)
	await _settle_physics(tree)
	_press(lab, INTERACT_ACTION)
	_expect(soul.phase == SoulScript.Phase.IDLE and not soul.prompt.visible,
		"second conversation also requires proximity")


func _test_departure_and_revisit(tree: SceneTree, lab: LabScript) -> void:
	var navigation := lab.lab_navigation
	navigation.enter_room(&"lamps")
	_expect(navigation.current_room.soul == null, "soul is exclusive to the portal tower")
	navigation.enter_room(&"hub", &"lamps")
	var soul := navigation.current_room.soul
	_expect(soul.has_spoken and soul.phase == SoulScript.Phase.IDLE,
		"returning through a portal remembers the first conversation")
	lab.hero_character.position = soul.position + Vector2(-80, 0)
	await _settle_physics(tree)
	_press(lab, INTERACT_ACTION)
	_expect(soul.phase == SoulScript.Phase.DEPART and soul.sprite.animation == &"depart",
		"second E starts the exact supplied departure animation")
	_expect(soul.visible and not soul.dialogue.visible,
		"departure begins visibly without a message")
	_expect(lab.hero_character.is_movement_enabled(), "player can move during departure")
	var seen_frames: Array[int] = [soul.sprite.frame]
	var observer := func() -> void: seen_frames.append(soul.sprite.frame)
	soul.sprite.frame_changed.connect(observer)
	_press(lab, INTERACT_ACTION)
	await _wait_until(tree, func() -> bool: return soul.sprite.frame >= 4, 2.0,
		"departure advances through the source frames")
	_expect(soul.visible and soul.glow.energy < soul.GLOW_ENERGY,
		"light fades with departure while the animation remains visible")
	await _wait_until(tree, func() -> bool: return soul.phase == SoulScript.Phase.DEPARTED, 2.0,
		"departure finishes once")
	soul.sprite.frame_changed.disconnect(observer)
	_expect(seen_frames.size() >= 8, "the entire departure sequence was displayed")
	for index in range(mini(8, seen_frames.size())):
		_expect(seen_frames[index] == index, "no departure frame is skipped or restarted")
	_expect(not soul.visible and not soul.glow.enabled and not soul.sprite.is_playing(),
		"soul, animation and light stop after the last departure frame")
	_expect(not soul.interactable_area.interaction_enabled,
		"departed soul no longer accepts interaction")
	_press(lab, INTERACT_ACTION)
	_expect(soul.phase == SoulScript.Phase.DEPARTED, "later E cannot respawn the soul")
	navigation.enter_room(&"monsters")
	navigation.enter_room(&"hub", &"monsters")
	soul = navigation.current_room.soul
	_expect(soul.phase == SoulScript.Phase.DEPARTED and not soul.visible and not soul.glow.enabled,
		"departed soul stays absent after a room round trip")


func _test_cancel_and_interrupted_departure(
		tree: SceneTree, lab: LabScript, soul: SoulScript,
) -> void:
	lab.hero_character.position = soul.position + Vector2(-80, 0)
	await _settle_physics(tree)
	_press(lab, INTERACT_ACTION)
	_press(lab, &"ui_cancel")
	_expect(soul.phase == SoulScript.Phase.IDLE and not soul.dialogue.visible,
		"Esc closes the first conversation and restores idle")
	_expect(not lab._navigation_requested and lab.hero_character.is_movement_enabled(),
		"Esc closes conversation before leaving the laboratory")
	_press(lab, INTERACT_ACTION)
	_expect(soul.phase == SoulScript.Phase.DEPART, "next fresh interaction begins departure")
	lab.lab_navigation.enter_room(&"objects")
	lab.lab_navigation.enter_room(&"hub", &"objects")
	soul = lab.lab_navigation.current_room.soul
	_expect(soul.phase == SoulScript.Phase.DEPARTED and not soul.visible,
		"leaving during departure cannot replay or resurrect it on return")
	_expect(lab.hero_character.is_movement_enabled(), "room change leaves movement usable")


func _press(lab: LabScript, action: StringName) -> void:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = true
	lab._unhandled_input(event)


func _settle_physics(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.physics_frame
	await tree.process_frame
	await tree.process_frame


func _wait_until(
		tree: SceneTree, condition: Callable, seconds: float, description: String,
) -> void:
	var deadline := Time.get_ticks_msec() + int(seconds * 1000.0)
	while not bool(condition.call()) and Time.get_ticks_msec() < deadline:
		await tree.process_frame
	_expect(bool(condition.call()), description)


func _release_input() -> void:
	for action in HeroScript.MOVEMENT_ACTIONS:
		Input.action_release(action)
	Input.action_release(INTERACT_ACTION)


func _remove_settings() -> void:
	if FileAccess.file_exists(SETTINGS_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_PATH))


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("PortalLabSoul: %s" % description)
