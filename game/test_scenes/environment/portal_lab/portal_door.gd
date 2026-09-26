extends Area2D

signal passage_requested(target_room: StringName, return_id: StringName)

const HERO_GROUP := &"test_lab_hero"
const Palette := preload("res://test_scenes/environment/portal_lab/blueprint_palette.gd")
const PortalGraphics := preload("res://test_scenes/environment/portal_lab/portal_graphics.gd")

@export var target_room: StringName = &"hub"
@export var return_id: StringName = &""
@export var door_title := "Zum Portalturm"
@export var arrival_offset := Vector2(0, -180)

var armed := false


func _ready() -> void:
	$Title.text = door_title
	$Title.add_theme_color_override("font_color", Palette.BRIGHT)
	body_entered.connect(_on_body_entered)


func set_graphics_variant(graphics_id: StringName) -> void:
	PortalGraphics.apply_sprite($Door, &"door", graphics_id)


func get_arrival_position() -> Vector2:
	return position + arrival_offset


func has_hero_inside() -> bool:
	for body in get_overlapping_bodies():
		if body.is_in_group(HERO_GROUP):
			return true
	return false


func _on_body_entered(body: Node2D) -> void:
	if not armed or not body.is_in_group(HERO_GROUP):
		return
	armed = false
	passage_requested.emit(target_room, return_id)
