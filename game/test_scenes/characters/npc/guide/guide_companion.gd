extends Node2D

signal interaction_requested(interactor: Node)

const InteractableAreaScript := preload(
	"res://shared/interactions/interactable_area.gd"
)

@onready var interactable_area: InteractableAreaScript = $InteractableArea


func _ready() -> void:
	interactable_area.interacted.connect(_on_interacted)


func get_interactable_area() -> InteractableAreaScript:
	return interactable_area


func _on_interacted(interactor: Node) -> void:
	interaction_requested.emit(interactor)
