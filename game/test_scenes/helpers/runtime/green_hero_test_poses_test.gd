extends RefCounted

const HERO_SCENE := preload("res://test_scenes/characters/heroes/greenhero/hero_character.tscn")
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const SPRITE_PATH := "Visual/JumpVisual/Appearance/TextureScale/HeroSprite"

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	var hero := HERO_SCENE.instantiate() as HERO_SCRIPT
	tree.root.add_child(hero)
	await tree.physics_frame
	var sprite := hero.get_node(SPRITE_PATH) as AnimatedSprite2D
	var controller := hero.get_node("AnimationController")
	controller.set_physics_process(false)
	hero.set_physics_process(false)
	hero.animation_direction = HERO_SCRIPT.AnimationDirection.NORTH_EAST
	hero.set("_ground_motion_active", true)
	var direction_cases := {
		Vector2(-1.0, 1.0): &"SW",
		Vector2(1.0, 1.0): &"SO",
		Vector2(-1.0, -1.0): &"NW",
		Vector2(1.0, -1.0): &"NO",
	}
	for direction in direction_cases:
		hero.call(&"_update_animation_direction", direction)
		_expect(
			hero.get_animation_direction_name() == direction_cases[direction],
			"diagonal direction selects %s" % direction_cases[direction],
		)
	hero.call(&"_update_animation_direction", Vector2(-1.0, 1.0))
	hero.set("_movement_state", HERO_SCRIPT.MovementState.WALK)
	sprite.animation = &"walk_SO"
	sprite.play()
	controller.call(&"_physics_process", 0.0)
	_expect(sprite.animation == &"walk_SW", "Walk SW selects walk_SW")
	var walk_sw_frame := sprite.sprite_frames.get_frame_texture(&"walk_SW", 0) as AtlasTexture
	_expect(walk_sw_frame != null, "Walk SW has an atlas frame")
	if walk_sw_frame != null:
		_expect(
			walk_sw_frame.atlas.resource_path.ends_with(
				"/walk/comic_high/spritesheet-fram8/greenhero_hd_walk_spritesheet_SW_4x2_o.png"
			),
			"Walk SW loads the SW sheet instead of SO",
		)
	hero.call(&"_update_animation_direction", Vector2(1.0, -1.0))
	for state in HERO_SCRIPT.MovementState.values():
		hero.set("_movement_state", state)
		controller.call(&"_physics_process", 0.0)
		var expected := {
			HERO_SCRIPT.MovementState.SNEAK: &"sneak_NO",
			HERO_SCRIPT.MovementState.WALK: &"walk_NO",
			HERO_SCRIPT.MovementState.JOG: &"walk_NO",
			HERO_SCRIPT.MovementState.RUN: &"run_NO",
			HERO_SCRIPT.MovementState.SPRINT: &"sprint_NO",
		}[state] as StringName
		_expect(sprite.animation == expected, "movement state selects %s" % expected)
		_expect(sprite.is_playing(), "%s loops" % expected)
	hero.set("_jump_state", HERO_SCRIPT.JumpState.STAND)
	controller.call(&"_physics_process", 0.0)
	_expect(sprite.animation == &"jump_NO", "jump selects its single pose")
	_expect(not sprite.is_playing() and sprite.frame == 0, "jump pose is frozen")
	hero.queue_free()
	await tree.process_frame
	return failures


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("GreenHeroTestPoses: %s" % description)
