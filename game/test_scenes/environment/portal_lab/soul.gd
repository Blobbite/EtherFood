extends Node2D

## One conversation and one departure per laboratory visit; rooms persist the two flags.
signal conversation_changed(active: bool)

enum Phase { IDLE, INTERACT, DEPART, DEPARTED }

const InteractableArea := preload("res://shared/interactions/interactable_area.gd")
const HUB_OFFSET := Vector2(224, 32)
const GLOW_ENERGY := 0.35

var phase: Phase = Phase.IDLE
var has_spoken: bool = false

@onready var sprite: AnimatedSprite2D = $SoulSprite
@onready var glow: PointLight2D = $Glow
@onready var interactable_area: InteractableArea = $InteractableArea
@onready var prompt: Label = $InteractionPrompt
@onready var dialogue: Control = $SoulInterface/Dialogue
@onready var dialogue_timer: Timer = $DialogueTimer

var _interface_visible := true


func _ready() -> void:
	interactable_area.interacted.connect(_on_interacted)
	sprite.animation_finished.connect(_on_animation_finished)
	sprite.frame_changed.connect(_on_frame_changed)
	dialogue_timer.timeout.connect(dismiss_dialogue)
	_play_idle()


func is_conversation_active() -> bool:
	return phase == Phase.INTERACT


func update_prompt(target: Area2D) -> void:
	prompt.visible = (
		_interface_visible and phase == Phase.IDLE and target == interactable_area
	)


func set_interface_visible(interface_visible: bool) -> void:
	_interface_visible = interface_visible
	$SoulInterface.visible = interface_visible
	dialogue_timer.paused = not interface_visible
	if not interface_visible:
		prompt.hide()


func dismiss_dialogue() -> void:
	if not is_conversation_active():
		return
	dialogue_timer.stop()
	dialogue.hide()
	_play_idle()
	conversation_changed.emit(false)


func get_local_state() -> Dictionary:
	return {"has_spoken": has_spoken, "departed": phase in [Phase.DEPART, Phase.DEPARTED]}


func restore_local_state(state: Dictionary) -> void:
	has_spoken = bool(state.get("has_spoken", false))
	dialogue_timer.stop()
	dialogue.hide()
	if bool(state.get("departed", false)):
		_finish_departure()
	else:
		_play_idle()


func _play_idle() -> void:
	phase = Phase.IDLE
	show()
	glow.enabled = true
	glow.energy = GLOW_ENERGY
	interactable_area.interaction_enabled = true
	interactable_area.interaction_prompt = (
		"E / A: Seele erneut ansprechen" if has_spoken else "E / A: Seele ansprechen"
	)
	prompt.text = interactable_area.interaction_prompt
	sprite.play(&"idle")


func _on_interacted(_interactor: Node) -> void:
	if phase != Phase.IDLE:
		return
	interactable_area.interaction_enabled = false
	prompt.hide()
	if has_spoken:
		phase = Phase.DEPART
		sprite.play(&"depart")
	else:
		has_spoken = true
		phase = Phase.INTERACT
		conversation_changed.emit(true)
		sprite.play(&"interact")


func _on_animation_finished() -> void:
	if phase == Phase.INTERACT:
		dialogue.show()
		dialogue_timer.start()
	elif phase == Phase.DEPART:
		_finish_departure()


func _on_frame_changed() -> void:
	if phase == Phase.DEPART:
		var last_frame := sprite.sprite_frames.get_frame_count(&"depart") - 1
		glow.energy = GLOW_ENERGY * (1.0 - float(sprite.frame) / float(last_frame))


func _finish_departure() -> void:
	phase = Phase.DEPARTED
	sprite.stop()
	glow.enabled = false
	glow.energy = 0.0
	interactable_area.interaction_enabled = false
	prompt.hide()
	dialogue.hide()
	hide()
