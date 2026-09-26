extends Node

const STAND_ACTION := &"stand"
const SLOW_WALK_ACTION := &"slowwalk"
const WALK_ACTION := &"walk"
const RUN_ACTION := &"run"
const SNEAK_ACTION := &"sneak"
const SPRINT_ACTION := &"sprint"
const JUMP_ACTION := &"jump"
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const ANIMATION_LIBRARY := preload(
	"res://test_scenes/characters/heroes/greenhero/green_hero_animation_library.gd"
)
const VISUAL_STANDARDS := preload(
	"res://shared/resources/visual_lab_standards_v0.tres"
)

@export var hero_path: NodePath = ^".."
@export var hero_sprite_path: NodePath = (
	^"../Visual/JumpVisual/Appearance/TextureScale/HeroSprite"
)

@onready var _hero: HERO_SCRIPT = get_node_or_null(hero_path) as HERO_SCRIPT
@onready var _hero_sprite: AnimatedSprite2D = (
	get_node_or_null(hero_sprite_path) as AnimatedSprite2D
)

var _current_action := &""


func _ready() -> void:
	if _hero == null or _hero_sprite == null:
		push_error("GreenHeroAnimationController could not resolve its hero or sprite.")
		set_physics_process(false)
		return
	if _hero_sprite.sprite_frames == null:
		_hero_sprite.sprite_frames = ANIMATION_LIBRARY.build(
			"comic_high",
			VISUAL_STANDARDS.hero_frame_count,
			VISUAL_STANDARDS.hero_fps,
		)
	if _hero_sprite.sprite_frames == null:
		push_error("GreenHeroAnimationController could not build Green Hero frames.")
		set_physics_process(false)
		return
	_hero_sprite.animation_changed.connect(apply_sprite_layout)
	_hero_sprite.sprite_frames_changed.connect(apply_sprite_layout)
	_apply_animation(STAND_ACTION, false)
	apply_sprite_layout()


func _physics_process(_delta: float) -> void:
	refresh_animation()


## Re-resolves the current action and direction after SpriteFrames are replaced.
func refresh_animation() -> void:
	if _hero.is_jumping():
		if _has_directional_animation(JUMP_ACTION):
			_apply_animation(JUMP_ACTION, false)
		else:
			_apply_animation(STAND_ACTION, true)
		return
	if _hero.is_ground_motion_active():
		var action := _ground_action()
		_apply_animation(action if _has_directional_animation(action) else WALK_ACTION, false)
		return
	_apply_animation(STAND_ACTION, false)


func _ground_action() -> StringName:
	match _hero.get_movement_state():
		HERO_SCRIPT.MovementState.SNEAK:
			return SNEAK_ACTION
		HERO_SCRIPT.MovementState.WALK:
			return SLOW_WALK_ACTION if Input.is_action_pressed(&"gameplay_sprint") else WALK_ACTION
		HERO_SCRIPT.MovementState.JOG:
			return SLOW_WALK_ACTION if Input.is_action_pressed(&"gameplay_sprint") else WALK_ACTION
		HERO_SCRIPT.MovementState.RUN:
			return RUN_ACTION
		HERO_SCRIPT.MovementState.SPRINT:
			return SPRINT_ACTION
	return WALK_ACTION


func _has_directional_animation(action: StringName) -> bool:
	return _hero_sprite.sprite_frames.has_animation(
		StringName("%s_%s" % [action, _hero.get_animation_direction_name()])
	)


## Returns the directional animation currently selected for the Green Hero.
func get_current_animation() -> StringName:
	if _hero_sprite == null:
		return &""
	return _hero_sprite.animation


## Applies the selected animation's source scale and foot anchor, when provided.
func apply_sprite_layout() -> void:
	if _hero_sprite == null or _hero_sprite.sprite_frames == null:
		return
	var layouts := _hero_sprite.sprite_frames.get_meta(&"animation_layouts", {}) as Dictionary
	var layout := layouts.get(_hero_sprite.animation, {}) as Dictionary
	if layout.is_empty():
		return
	var texture_scale := _hero_sprite.get_parent() as Node2D
	texture_scale.scale = layout["scale"] as Vector2
	_hero_sprite.offset = layout["offset"] as Vector2


func _apply_animation(action: StringName, freeze_first_frame: bool) -> void:
	var animation_name := StringName(
		"%s_%s" % [action, _hero.get_animation_direction_name()]
	)
	if not _hero_sprite.sprite_frames.has_animation(animation_name):
		push_error("Green Hero animation is unavailable: %s" % animation_name)
		set_physics_process(false)
		return
	freeze_first_frame = freeze_first_frame or (
		_hero_sprite.sprite_frames.get_frame_count(animation_name) == 1
		and not _hero_sprite.sprite_frames.get_animation_loop(animation_name)
	)

	if _hero_sprite.animation == animation_name:
		_current_action = action
		if freeze_first_frame:
			_hero_sprite.pause()
			_hero_sprite.set_frame_and_progress(0, 0.0)
		elif not _hero_sprite.is_playing():
			_hero_sprite.play()
		return

	var preserve_movement_phase := (
		action in [WALK_ACTION, RUN_ACTION, SNEAK_ACTION, SPRINT_ACTION]
		and _current_action == action
	)
	var previous_frame := _hero_sprite.frame
	var previous_progress := _hero_sprite.frame_progress
	_hero_sprite.play(animation_name)
	if preserve_movement_phase:
		var frame_count := _hero_sprite.sprite_frames.get_frame_count(animation_name)
		_hero_sprite.set_frame_and_progress(
			mini(previous_frame, frame_count - 1),
			previous_progress,
		)
	if freeze_first_frame:
		_hero_sprite.pause()
		_hero_sprite.set_frame_and_progress(0, 0.0)
	_current_action = action
