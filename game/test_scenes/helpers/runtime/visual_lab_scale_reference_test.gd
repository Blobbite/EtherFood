extends RefCounted

const VISUAL_LAB_SCENE_PATH := "res://test_scenes/visual_lab/visual_lab.tscn"
const HERO_SCRIPT := preload("res://test_scenes/characters/heroes/greenhero/hero_character.gd")
const BASELINE_WORLD_Y := 1760.0
const WORLD_BOUNDS := Rect2(0, 0, 3840, 2160)
const HEIGHT_TOLERANCE := 1.0
const REFERENCE_SPECS := [
	{
		"node_name": "SmallEnemyReference",
		"label": "Kleiner Gegner · 56 px",
		"height": 56.0,
	},
	{
		"node_name": "DoorReference",
		"label": "Tür · 112 px",
		"height": 112.0,
	},
	{
		"node_name": "HouseWallReference",
		"label": "Hauswand · 144 px",
		"height": 144.0,
	},
	{
		"node_name": "LargeEnemyReference",
		"label": "Großer Gegner · 128 px",
		"height": 128.0,
	},
	{
		"node_name": "TreeReference",
		"label": "Baum · 192 px",
		"height": 192.0,
	},
]

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	var visual_lab_scene := load(VISUAL_LAB_SCENE_PATH) as PackedScene
	_expect(visual_lab_scene != null, "VisualLab scene loads")
	if visual_lab_scene == null:
		return failures

	var visual_lab_node := visual_lab_scene.instantiate()
	_expect(visual_lab_node is Control, "VisualLab instantiates as Control")
	if not visual_lab_node is Control:
		if visual_lab_node != null:
			visual_lab_node.free()
		return failures

	var visual_lab := visual_lab_node as Control
	tree.root.add_child(visual_lab)
	visual_lab.get_node("LabNavigation").call(&"enter_room", &"objects")
	await tree.process_frame

	var test_world := visual_lab.get_node_or_null("TestWorld") as Node2D
	var scale_comparison := visual_lab.get_node_or_null(
		"TestWorld/ScaleComparison"
	) as Node2D
	var baseline := visual_lab.get_node_or_null(
		"TestWorld/ScaleComparison/Baseline"
	) as Line2D
	var ground_strip := visual_lab.get_node_or_null(
		"TestWorld/ScaleComparison/GroundStrip"
	) as Sprite2D
	var hero_marker := visual_lab.get_node_or_null(
		"TestWorld/ScaleComparison/HeroStandMarker"
	) as Polygon2D
	var hero_marker_label := visual_lab.get_node_or_null(
		"TestWorld/ScaleComparison/HeroStandMarker/Label"
	) as Label
	var hud_panel := visual_lab.get_node_or_null("InterfaceLayer/HudPanel") as Panel

	_expect(test_world != null, "VisualLab has TestWorld")
	_expect(scale_comparison != null, "TestWorld has ScaleComparison")
	_expect(baseline != null, "ScaleComparison has a Baseline")
	_expect(ground_strip != null, "ScaleComparison has a pixel-art GroundStrip")
	_expect(hero_marker != null, "ScaleComparison has a HeroStandMarker")
	_expect(hero_marker_label != null, "HeroStandMarker has a Label")
	_expect(hud_panel != null, "VisualLab has a framed HUD panel")

	if scale_comparison == null:
		visual_lab.queue_free()
		await tree.process_frame
		return failures

	_expect(
		scale_comparison.get_parent() == test_world,
		"ScaleComparison is directly under TestWorld",
	)
	_expect(test_world == null or test_world.y_sort_enabled, "TestWorld enables Y-sorting")
	_expect(scale_comparison.y_sort_enabled, "ScaleComparison enables nested Y-sorting")
	_expect(
		scale_comparison.global_position.y == BASELINE_WORLD_Y,
		"ScaleComparison uses the proportional lower-world baseline",
	)
	_expect(
		BASELINE_WORLD_Y > WORLD_BOUNDS.get_center().y,
		"ScaleComparison lies in the lower half of the enlarged world",
	)
	if ground_strip != null:
		_expect(ground_strip.texture != null, "GroundStrip has a texture")
		_expect(ground_strip.visible, "GroundStrip is visible")
		_expect(
			ground_strip.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
			"GroundStrip uses nearest-neighbor filtering",
		)
		_expect(ground_strip.scale == Vector2.ONE, "GroundStrip is not pre-scaled")
		_expect(ground_strip.rotation == 0.0, "GroundStrip is not rotated")
		if ground_strip.texture != null:
			var ground_image := ground_strip.texture.get_image()
			_expect(
				ground_image != null and not ground_image.has_mipmaps(),
				"GroundStrip texture has no mipmaps",
			)
	if hud_panel != null:
		var panel_style := hud_panel.get_theme_stylebox("panel") as StyleBoxFlat
		_expect(panel_style != null, "HUD panel uses a flat pixel style")
		if panel_style != null:
			_expect(panel_style.border_width_left > 0, "HUD panel has a visible border")
			_expect(panel_style.corner_radius_top_left == 0, "HUD panel has square corners")

	if baseline != null:
		_expect(baseline.get_parent() == scale_comparison, "Baseline is directly grouped")
		_expect(baseline.visible and baseline.width > 0.0, "Baseline is clearly visible")
		_expect(baseline.points.size() >= 2, "Baseline spans the comparison area")
		for point in baseline.points:
			_expect(
				is_equal_approx(baseline.to_global(point).y, BASELINE_WORLD_Y),
				"every Baseline point uses the shared world Y coordinate",
			)

	if hero_marker != null:
		_expect(
			is_equal_approx(hero_marker.global_position.y, BASELINE_WORLD_Y),
			"HeroStandMarker sits on the shared baseline",
		)
		_expect(hero_marker.visible, "HeroStandMarker is visible")
	if hero_marker_label != null:
		_expect(
			hero_marker_label.get_parent() == hero_marker,
			"HeroStandMarker Label is a direct child",
		)
		_expect(hero_marker_label.text == "Held · steuerbar", "HeroStandMarker is labeled")
		_expect(
			hero_marker_label.z_index >= 50 and not hero_marker_label.z_as_relative,
			"HeroStandMarker Label stays above Y-sorted world objects",
		)

	var previous_reference_x := -INF
	for reference_spec in REFERENCE_SPECS:
		var reference_name := str(reference_spec["node_name"])
		var reference := scale_comparison.get_node_or_null(reference_name) as Node2D
		_expect(reference != null, "ScaleComparison has %s" % reference_name)
		if reference == null:
			continue
		_expect(
			reference.get_parent() == scale_comparison,
			"%s is directly grouped" % reference_name,
		)
		_expect(
			is_equal_approx(reference.global_position.y, BASELINE_WORLD_Y),
			"%s origin sits on the shared baseline" % reference_name,
		)
		_expect(
			reference.position.x > previous_reference_x,
			"%s follows the left-to-right comparison order" % reference_name,
		)
		previous_reference_x = reference.position.x

		var sprite := reference.get_node_or_null("Sprite2D") as Sprite2D
		var label := reference.get_node_or_null("Label") as Label
		_expect(sprite != null, "%s has a Sprite2D" % reference_name)
		_expect(label != null, "%s has a Label" % reference_name)
		if sprite != null:
			_expect(
				sprite.get_parent() == reference,
				"%s Sprite2D is a direct child" % reference_name,
			)
			_expect(sprite.visible, "%s Sprite2D is visible" % reference_name)
			_expect(sprite.texture != null, "%s Sprite2D has a texture" % reference_name)
			_expect(
				sprite.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST,
				"%s uses nearest-neighbor filtering" % reference_name,
			)
			_expect(sprite.scale == Vector2.ONE, "%s uses its source scale" % reference_name)
			_expect(sprite.rotation == 0.0, "%s is not rotated" % reference_name)
			var vertical_bounds := _sprite_world_vertical_bounds(sprite)
			var expected_height := float(reference_spec["height"])
			_expect(
				absf(vertical_bounds.y - vertical_bounds.x - expected_height)
				<= HEIGHT_TOLERANCE,
				"%s Sprite2D has the intended visible height" % reference_name,
			)
			_expect(
				absf(vertical_bounds.y - BASELINE_WORLD_Y) <= HEIGHT_TOLERANCE,
				"%s Sprite2D grows upward from the shared baseline" % reference_name,
			)
			if sprite.texture != null:
				var image := sprite.texture.get_image()
				_expect(
					image != null and image.get_used_rect().has_area(),
					"%s texture contains visible pixels" % reference_name,
				)
				_expect(
					image != null and not image.has_mipmaps(),
					"%s texture has no mipmaps" % reference_name,
				)
			for point in _sprite_world_corners(sprite):
				_expect(
					WORLD_BOUNDS.has_point(point),
					"%s Sprite2D stays inside TestWorld" % reference_name,
				)
		if label != null:
			_expect(label.get_parent() == reference, "%s Label is a direct child" % reference_name)
			_expect(
				label.text == str(reference_spec["label"]),
				"%s Label states its provisional height" % reference_name,
			)
			_expect(
				label.z_index >= 50 and not label.z_as_relative,
				"%s Label stays above Y-sorted world objects" % reference_name,
			)

	_expect_reference_order(scale_comparison, hero_marker)
	_expect(
		scale_comparison.find_children("*", "CollisionObject2D", true, false).is_empty(),
		"reference objects contain no collision bodies or areas",
	)
	_expect(
		scale_comparison.find_children("*", "CollisionShape2D", true, false).is_empty(),
		"reference objects contain no collision shapes",
	)
	_expect(
		scale_comparison.find_children("*", "CollisionPolygon2D", true, false).is_empty(),
		"reference objects contain no collision polygons",
	)

	_expect_hero_sizes_still_work(visual_lab)
	visual_lab.queue_free()
	await tree.process_frame
	return failures


func _expect_reference_order(scale_comparison: Node2D, hero_marker: Polygon2D) -> void:
	if hero_marker == null:
		return
	var ordered_names := [
		"SmallEnemyReference",
		"HeroStandMarker",
		"DoorReference",
		"HouseWallReference",
		"LargeEnemyReference",
		"TreeReference",
	]
	var previous_x := -INF
	for node_name in ordered_names:
		var comparison_node := scale_comparison.get_node_or_null(node_name) as Node2D
		if comparison_node == null:
			return
		_expect(
			comparison_node.position.x > previous_x,
			"%s appears in the documented comparison order" % node_name,
		)
		previous_x = comparison_node.position.x


func _expect_hero_sizes_still_work(visual_lab: Control) -> void:
	var hero: HERO_SCRIPT = visual_lab.get_node_or_null(
		"TestWorld/HeroCharacter"
	) as HERO_SCRIPT
	_expect(hero != null, "VisualLab retains the scalable HeroCharacter")
	if hero == null:
		return
	_expect(
		is_equal_approx(hero.get_appearance_height(), 80.0),
		"hero starts at the 80-world-pixel default",
	)
	visual_lab._change_hero_size(-1)
	_expect(
		is_equal_approx(hero.get_appearance_height(), 64.0),
		"hero still reaches 64 world pixels",
	)
	visual_lab._change_hero_size(-1)
	_expect(
		is_equal_approx(hero.get_appearance_height(), 64.0),
		"hero size still stops at 64 world pixels",
	)
	visual_lab._change_hero_size(1)
	_expect(
		is_equal_approx(hero.get_appearance_height(), 80.0),
		"hero still reaches 80 world pixels",
	)
	visual_lab._change_hero_size(1)
	_expect(
		is_equal_approx(hero.get_appearance_height(), 96.0),
		"hero still reaches 96 world pixels",
	)


func _sprite_world_vertical_bounds(sprite: Sprite2D) -> Vector2:
	var local_rect := _sprite_local_alpha_rect(sprite)
	return Vector2(
		sprite.to_global(Vector2(0.0, local_rect.position.y)).y,
		sprite.to_global(Vector2(0.0, local_rect.end.y)).y,
	)


func _sprite_world_corners(sprite: Sprite2D) -> PackedVector2Array:
	var local_rect := _sprite_local_alpha_rect(sprite)
	return PackedVector2Array([
		sprite.to_global(local_rect.position),
		sprite.to_global(Vector2(local_rect.end.x, local_rect.position.y)),
		sprite.to_global(local_rect.end),
		sprite.to_global(Vector2(local_rect.position.x, local_rect.end.y)),
	])


func _sprite_local_alpha_rect(sprite: Sprite2D) -> Rect2:
	if sprite.texture == null:
		return Rect2()
	var image := sprite.texture.get_image()
	if image == null:
		return Rect2()
	var used_rect := image.get_used_rect()
	var texture_rect := sprite.get_rect()
	return Rect2(texture_rect.position + Vector2(used_rect.position), Vector2(used_rect.size))


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLabScaleReference: %s" % description)
