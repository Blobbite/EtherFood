extends Node2D

const HERO_FILL := Color(0.24, 0.78, 0.91, 0.28)
const HERO_OUTLINE := Color(0.46, 0.91, 1.0, 0.95)
const OBSTACLE_FILL := Color(0.95, 0.38, 0.28, 0.24)
const OBSTACLE_OUTLINE := Color(1.0, 0.56, 0.4, 0.95)
const BOUNDARY_FILL := Color(0.95, 0.72, 0.22, 0.16)
const BOUNDARY_OUTLINE := Color(1.0, 0.84, 0.38, 0.95)
const OUTLINE_WIDTH := 3.0

@export var hero_collision_path: NodePath
@export var obstacle_collision_path: NodePath
@export var arena_bounds_path: NodePath
var extra_collision_root: Node2D

@onready var _hero_collision := get_node_or_null(hero_collision_path) as CollisionShape2D
@onready var _obstacle_collision := (
	get_node_or_null(obstacle_collision_path) as CollisionShape2D
)
@onready var _arena_bounds := get_node_or_null(arena_bounds_path) as Node2D


func _ready() -> void:
	visible = false
	set_process(false)


func _process(_delta: float) -> void:
	queue_redraw()


func _draw() -> void:
	_draw_debug_rect(get_hero_collision_rect(), HERO_FILL, HERO_OUTLINE)
	_draw_debug_rect(get_obstacle_collision_rect(), OBSTACLE_FILL, OBSTACLE_OUTLINE)
	for boundary_rect in get_world_boundary_rects():
		_draw_debug_rect(boundary_rect, BOUNDARY_FILL, BOUNDARY_OUTLINE)


func set_debug_visible(debug_visible: bool) -> void:
	visible = debug_visible
	set_process(debug_visible)
	if debug_visible:
		queue_redraw()


func get_hero_collision_rect() -> Rect2:
	return _rect_for_collision(_hero_collision)


func get_obstacle_collision_rect() -> Rect2:
	if _obstacle_collision != null and _obstacle_collision.disabled:
		return Rect2()
	return _rect_for_collision(_obstacle_collision)


func get_world_boundary_rects() -> Array[Rect2]:
	var rectangles: Array[Rect2] = []
	if _arena_bounds == null:
		return rectangles
	for child in _arena_bounds.get_children():
		var body := child as StaticBody2D
		if body == null:
			continue
		var collision := body.get_node_or_null("CollisionShape2D") as CollisionShape2D
		if collision != null:
			rectangles.append(_rect_for_collision(collision))
	if is_instance_valid(extra_collision_root):
		for collision in extra_collision_root.find_children("*", "CollisionShape2D", true, false):
			if collision.get_parent() is StaticBody2D:
				rectangles.append(_rect_for_collision(collision as CollisionShape2D))
	return rectangles


func _rect_for_collision(collision: CollisionShape2D) -> Rect2:
	if collision == null:
		return Rect2()
	var rectangle_shape := collision.shape as RectangleShape2D
	if rectangle_shape == null:
		return Rect2()
	var relative_transform := global_transform.affine_inverse() * collision.global_transform
	var half_size := rectangle_shape.size * 0.5
	var corners := [
		relative_transform * Vector2(-half_size.x, -half_size.y),
		relative_transform * Vector2(half_size.x, -half_size.y),
		relative_transform * Vector2(half_size.x, half_size.y),
		relative_transform * Vector2(-half_size.x, half_size.y),
	]
	var rectangle := Rect2(corners[0], Vector2.ZERO)
	for corner in corners.slice(1):
		rectangle = rectangle.expand(corner)
	return rectangle


func _draw_debug_rect(rectangle: Rect2, fill: Color, outline: Color) -> void:
	if not rectangle.has_area():
		return
	draw_rect(rectangle, fill, true)
	draw_rect(rectangle, outline, false, OUTLINE_WIDTH, false)
