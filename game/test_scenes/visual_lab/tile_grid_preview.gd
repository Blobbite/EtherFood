extends Node2D

const PREVIEW_SIZE := Vector2(768.0, 384.0)
const BACKGROUND_COLOR := Color(0.08, 0.11, 0.13, 0.96)
const CELL_COLOR_LIGHT := Color(0.22, 0.32, 0.33, 0.72)
const CELL_COLOR_DARK := Color(0.17, 0.26, 0.28, 0.72)
const GRID_COLOR := Color(0.48, 0.6, 0.58, 0.62)
const BORDER_COLOR := Color(0.88, 0.75, 0.42, 0.95)

var tile_size: int = 48


func set_tile_size(value: int) -> void:
	tile_size = value
	queue_redraw()


func get_column_count() -> int:
	return int(PREVIEW_SIZE.x / tile_size)


func get_row_count() -> int:
	return int(PREVIEW_SIZE.y / tile_size)


func _draw() -> void:
	var preview_rect := Rect2(Vector2.ZERO, PREVIEW_SIZE)
	draw_rect(preview_rect, BACKGROUND_COLOR)

	for row in range(get_row_count()):
		for column in range(get_column_count()):
			var cell_position := Vector2(column, row) * float(tile_size)
			var cell_rect := Rect2(cell_position, Vector2.ONE * float(tile_size))
			var cell_color := CELL_COLOR_LIGHT if (column + row) % 2 == 0 else CELL_COLOR_DARK
			draw_rect(cell_rect, cell_color)

	for column in range(get_column_count() + 1):
		var line_x := float(column * tile_size)
		draw_line(
			Vector2(line_x, 0.0),
			Vector2(line_x, PREVIEW_SIZE.y),
			GRID_COLOR,
			1.0,
		)
	for row in range(get_row_count() + 1):
		var line_y := float(row * tile_size)
		draw_line(
			Vector2(0.0, line_y),
			Vector2(PREVIEW_SIZE.x, line_y),
			GRID_COLOR,
			1.0,
		)

	draw_rect(preview_rect, BORDER_COLOR, false, 4.0)
