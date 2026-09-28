@tool
extends Node2D

const Palette := preload("res://test_scenes/environment/portal_lab/blueprint_palette.gd")
const PortalGraphics := preload("res://test_scenes/environment/portal_lab/portal_graphics.gd")
const BORDER_WIDTH := 32.0

@export var world_size := Vector2(3840.0, 2160.0):
	set(value):
		world_size = value
		queue_redraw()
@export var circular := false:
	set(value):
		circular = value
		queue_redraw()
@export var radius := 1000.0:
	set(value):
		radius = value
		queue_redraw()
@export_range(16, 128, 1) var tile_size := 32:
	set(value):
		tile_size = maxi(value, 16)
		queue_redraw()

var portal_positions: Array[Vector2] = []
var graphics_variant: StringName = &"comic_high"
var floor_id := "ornate"
var floor_texture: Texture2D = PortalGraphics.get_temple_texture(&"floors", graphics_variant)
var wall_texture: Texture2D = PortalGraphics.get_temple_texture(&"walls", graphics_variant)
var roof_texture: Texture2D = PortalGraphics.get_temple_texture(&"roofs", graphics_variant)


func _ready() -> void:
	texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST


func set_graphics_variant(graphics_id: StringName) -> void:
	graphics_variant = PortalGraphics.temple_variant(graphics_id)
	floor_texture = PortalGraphics.get_temple_texture(&"floors", graphics_variant, floor_id)
	wall_texture = PortalGraphics.get_temple_texture(&"walls", graphics_variant)
	roof_texture = PortalGraphics.get_temple_texture(&"roofs", graphics_variant)
	queue_redraw()


func set_floor_motif(motif_id: String) -> void:
	floor_id = motif_id if motif_id in PortalGraphics.FLOOR_IDS else PortalGraphics.FLOOR_IDS[0]
	floor_texture = PortalGraphics.get_temple_texture(&"floors", graphics_variant, floor_id)
	queue_redraw()


func _draw() -> void:
	var center := world_size / 2.0
	var smooth_guides := not String(graphics_variant).begins_with("pixel_")
	if circular:
		var points := PackedVector2Array()
		for index in range(256):
			points.append(center + Vector2.from_angle(float(index) * TAU / 256.0) * radius)
		_draw_surface(points, center - Vector2.ONE * radius, floor_texture)
		_draw_texture_ring(center, radius, wall_texture)
		_draw_texture_ring(center, radius + BORDER_WIDTH, roof_texture)
		_draw_circular_grid(center)
		for ring in [radius, radius - 56.0, radius - 260.0, 144.0, 120.0]:
			draw_arc(center, ring, 0.0, TAU, 256, Palette.EDGE, 2.0, smooth_guides)
		for target in portal_positions:
			var direction := (target - center).normalized()
			draw_line(center + direction * 192.0, target - direction * 96.0,
				Palette.EDGE, 3.0, smooth_guides)
		for index in range(48):
			var direction := Vector2.from_angle(float(index) * TAU / 48.0)
			var length := 28.0 if index % 4 == 0 else 12.0
			draw_line(
				center + direction * (radius - length), center + direction * radius,
				Palette.BRIGHT, 2.0,
			)
	else:
		var bounds := Rect2(Vector2(64, 64), world_size - Vector2(128, 128))
		_draw_textured_rect(bounds, floor_texture)
		_draw_rectangular_border(bounds, wall_texture)
		_draw_rectangular_border(bounds.grow(BORDER_WIDTH), roof_texture)
		for x in range(64, int(world_size.x) - 63, tile_size):
			draw_line(Vector2(x, 64), Vector2(x, world_size.y - 64), Palette.GRID)
		for y in range(64, int(world_size.y) - 63, tile_size):
			draw_line(Vector2(64, y), Vector2(world_size.x - 64, y), Palette.GRID)
		draw_rect(bounds, Palette.EDGE, false, 4.0)
		draw_rect(bounds.grow(-24.0), Palette.GRID, false, 2.0)
	_draw_cross(center, 32.0)


func _draw_surface(points: PackedVector2Array, origin: Vector2, texture: Texture2D) -> void:
	var uvs := PackedVector2Array()
	for point in points:
		uvs.append((point - origin) / float(tile_size * 4))
	draw_colored_polygon(points, Color.WHITE, uvs, texture)


func _draw_textured_rect(bounds: Rect2, texture: Texture2D) -> void:
	_draw_surface(PackedVector2Array([
		bounds.position, Vector2(bounds.end.x, bounds.position.y),
		bounds.end, Vector2(bounds.position.x, bounds.end.y),
	]), Vector2(64, 64), texture)


func _draw_rectangular_border(bounds: Rect2, texture: Texture2D) -> void:
	var outer := bounds.grow(BORDER_WIDTH)
	for strip: Rect2 in [
		Rect2(outer.position, Vector2(outer.size.x, BORDER_WIDTH)),
		Rect2(Vector2(outer.position.x, bounds.end.y), Vector2(outer.size.x, BORDER_WIDTH)),
		Rect2(Vector2(outer.position.x, bounds.position.y), Vector2(BORDER_WIDTH, bounds.size.y)),
		Rect2(Vector2(bounds.end.x, bounds.position.y), Vector2(BORDER_WIDTH, bounds.size.y)),
	]:
		_draw_textured_rect(strip, texture)


func _draw_texture_ring(center: Vector2, inner_radius: float, texture: Texture2D) -> void:
	var origin := center - Vector2.ONE * radius
	for index in range(128):
		var start := Vector2.from_angle(TAU * float(index) / 128.0)
		var end := Vector2.from_angle(TAU * float(index + 1) / 128.0)
		_draw_surface(PackedVector2Array([
			center + start * inner_radius,
			center + start * (inner_radius + BORDER_WIDTH),
			center + end * (inner_radius + BORDER_WIDTH),
			center + end * inner_radius,
		]), origin, texture)


func _draw_circular_grid(center: Vector2) -> void:
	for offset in range(-int(radius), int(radius) + 1, tile_size):
		var reach := sqrt(maxf(0.0, radius * radius - float(offset * offset)))
		draw_line(
			center + Vector2(offset, -reach), center + Vector2(offset, reach), Palette.GRID,
		)
		draw_line(
			center + Vector2(-reach, offset), center + Vector2(reach, offset), Palette.GRID,
		)


func _draw_cross(center: Vector2, extent: float) -> void:
	draw_line(center - Vector2(extent, 0), center + Vector2(extent, 0), Palette.BRIGHT, 3.0)
	draw_line(center - Vector2(0, extent), center + Vector2(0, extent), Palette.BRIGHT, 3.0)
