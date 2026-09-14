extends Node2D

const Palette := preload("res://scenes/dev/portal_lab/blueprint_palette.gd")
const BlueprintFloor := preload("res://scenes/dev/portal_lab/blueprint_floor.gd")
const PortalDoor := preload("res://scenes/dev/portal_lab/portal_door.gd")
const PortalGraphics := preload("res://scenes/dev/portal_lab/portal_graphics.gd")
const SoulScript := preload("res://scenes/dev/portal_lab/soul.gd")
const PORTAL_SCENE := preload("res://scenes/dev/portal_lab/portal_door.tscn")
const HERO_ROOT := "res://tests/assets/characters/heroes/green_hero/"

@export var room_kind: StringName = &"hub"
@export var world_size := Vector2(3840, 2160)
@export var return_portal_position := Vector2(1920, 1600)
@export var return_arrival_offset := Vector2(0, -180)

@onready var floor_grid: BlueprintFloor = $BlueprintFloor
@onready var portals: Node2D = $Portals
@onready var contents: Node2D = $Contents
@onready var ambient: CanvasModulate = $Ambient
@onready var soul: SoulScript = get_node_or_null("Contents/Soul") as SoulScript

var cycle_enabled := false
var cycle_phase := 0.0
var lamps_enabled := true
var particles_enabled := false
var graphics_variant: StringName = &"test"
var _lamps: Array[PointLight2D] = []
var _particles: Array[CPUParticles2D] = []
var _sample_bindings: Array[Dictionary] = []


func _ready() -> void:
	floor_grid.world_size = world_size
	floor_grid.circular = room_kind == &"hub"
	ambient.color = Color.WHITE
	_build_samples()
	set_process(room_kind == &"day_night")


func _process(delta: float) -> void:
	if cycle_enabled:
		cycle_phase = fposmod(cycle_phase + delta / 30.0, 1.0)
	_apply_daylight()


func set_graphics_variant(graphics_id: StringName) -> void:
	graphics_variant = PortalGraphics.variant_for_graphics(graphics_id)
	floor_grid.set_graphics_variant(graphics_variant)
	for door in portals.get_children():
		(door as PortalDoor).set_graphics_variant(graphics_variant)
	for binding in _sample_bindings:
		PortalGraphics.apply_sprite(
			binding["sprite"] as Sprite2D, binding["asset_key"] as StringName,
			graphics_variant, binding["size_factor"] as float,
		)
	for emitter in _particles:
		_apply_particle_texture(emitter)


func add_portal(
		target: StringName, return_key: StringName, title: String,
		point: Vector2, arrival: Vector2,
) -> PortalDoor:
	var door := PORTAL_SCENE.instantiate() as PortalDoor
	door.name = "Portal_%s" % return_key
	door.target_room = target
	door.return_id = return_key
	door.door_title = title
	door.position = point
	door.arrival_offset = arrival
	portals.add_child(door)
	door.set_graphics_variant(graphics_variant)
	return door


func set_heading(title: String, subtitle: String) -> void:
	var point := world_size / 2.0 + Vector2(0, -256)
	if room_kind != &"hub":
		point = Vector2(world_size.x / 2.0, 200)
		if room_kind in [&"lamps", &"sprites", &"monsters", &"shaders", &"particles"]:
			point.y = 640
	_add_label("RoomTitle", title, point, 32)
	_add_label("RoomDescription", subtitle, point + Vector2(0, 48), 18)


func build_tower_boundary(radius: float) -> void:
	var bounds := Node2D.new()
	bounds.name = "TowerBoundary"
	add_child(bounds)
	for index in range(64):
		var angle := TAU * float(index) / 64.0
		var body := StaticBody2D.new()
		body.position = world_size / 2.0 + Vector2.from_angle(angle) * (radius + 12.0)
		body.rotation = angle
		var collision := CollisionShape2D.new()
		var shape := RectangleShape2D.new()
		shape.size = Vector2(32, 2.0 * (radius + 28.0) * tan(PI / 64.0))
		collision.shape = shape
		body.add_child(collision)
		bounds.add_child(body)


func get_local_state() -> Dictionary:
	var state := {
		"cycle_enabled": cycle_enabled, "cycle_phase": cycle_phase,
		"lamps_enabled": lamps_enabled, "particles_enabled": particles_enabled,
	}
	if soul != null:
		state["soul"] = soul.get_local_state()
	return state


func restore_local_state(state: Dictionary) -> void:
	cycle_enabled = bool(state.get("cycle_enabled", false))
	cycle_phase = float(state.get("cycle_phase", 0.0))
	lamps_enabled = bool(state.get("lamps_enabled", true))
	particles_enabled = bool(state.get("particles_enabled", false))
	if soul != null:
		soul.restore_local_state(state.get("soul", {}) as Dictionary)
	_apply_samples()


func activate_control(control_id: StringName) -> void:
	match control_id:
		&"lamps":
			lamps_enabled = not lamps_enabled
		&"particles":
			particles_enabled = not particles_enabled
		&"cycle":
			cycle_enabled = not cycle_enabled
		&"day", &"dusk", &"night":
			cycle_enabled = false
			cycle_phase = {&"day": 0.0, &"dusk": 0.25, &"night": 0.5}[control_id]
	_apply_samples()


func get_controls() -> Array[Dictionary]:
	match room_kind:
		&"lamps":
			return [{"id": &"lamps", "text": "Lampen aus" if lamps_enabled else "Lampen an"}]
		&"particles":
			return [{
				"id": &"particles",
				"text": "Partikel stoppen" if particles_enabled else "Partikel starten",
			}]
		&"day_night":
			return [
				{"id": &"day", "text": "Tag"}, {"id": &"dusk", "text": "Dämmerung"},
				{"id": &"night", "text": "Nacht"},
				{"id": &"cycle", "text": "Zyklus stoppen" if cycle_enabled else "Zyklus starten"},
			]
	return []


func _apply_samples() -> void:
	for light in _lamps:
		light.enabled = lamps_enabled
	for emitter in _particles:
		emitter.emitting = particles_enabled
	if room_kind == &"day_night":
		_apply_daylight()


func _apply_daylight() -> void:
	var darkness := (1.0 - cos(cycle_phase * TAU)) / 2.0
	ambient.color = Color.WHITE.lerp(Color(0.16, 0.22, 0.32), darkness)


func _build_samples() -> void:
	match room_kind:
		&"lamps":
			_build_lamps()
		&"sprites":
			_build_sprite_gallery()
		&"monsters":
			for index in range(3):
				var point := Vector2(1280 + index * 640, 1080)
				var size_factor := [0.75, 1.0, 1.5][index] as float
				_add_sample("Monster_%d" % index, "monster.svg", point, size_factor)
				_add_label("MonsterLabel_%d" % index, ["Klein", "Mittel", "Groß"][index],
					point + Vector2(0, 72), 22)
		&"objects", &"shaders":
			for index in range(3):
				var point := Vector2(1440 + index * 480, 680)
				if room_kind == &"shaders":
					point.y = 1080
				_add_sample("Sample_%d" % index, "crate.svg", point, 1.0)
				var title := "Objekt %02d" % (index + 1)
				if room_kind == &"shaders":
					title = ["Original", "Shader-Fläche A", "Shader-Fläche B"][index]
				_add_label("SampleLabel_%d" % index, title, point + Vector2(0, 64), 22)
		&"particles":
			_build_particles()
		&"day_night":
			for index in range(3):
				_add_sample("DaylightSample_%d" % index, "crate.svg",
					Vector2(1440 + index * 480, 1350), 1.0)


func _build_lamps() -> void:
	ambient.color = Color(0.38, 0.46, 0.58)
	var gradient := Gradient.new()
	gradient.colors = PackedColorArray([Color.WHITE, Color(1, 1, 1, 0)])
	var glow := GradientTexture2D.new()
	glow.width = 256
	glow.height = 256
	glow.gradient = gradient
	glow.fill = GradientTexture2D.FILL_RADIAL
	glow.fill_from = Vector2(0.5, 0.5)
	glow.fill_to = Vector2(0.5, 1.0)
	for index in range(3):
		var point := Vector2(1280 + index * 640, 1080)
		_add_sample("Lamp_%d" % index, "lamp.svg", point, 1.0)
		var light := PointLight2D.new()
		light.position = point + Vector2(0, -100)
		light.texture = glow
		light.texture_scale = 2.0
		light.energy = [0.5, 1.0, 1.5][index]
		light.color = Palette.TEXT
		contents.add_child(light)
		_lamps.append(light)
		_add_label("LampLabel_%d" % index, "Lichtstärke %.1f" % light.energy,
			point + Vector2(0, 72), 22)


func _build_particles() -> void:
	for index in range(3):
		var emitter := CPUParticles2D.new()
		emitter.name = "ParticleSample_%d" % index
		emitter.position = Vector2(1280 + index * 640, 1080)
		_apply_particle_texture(emitter)
		emitter.amount = 24
		emitter.lifetime = 2.0
		emitter.direction = Vector2.UP
		emitter.spread = [10.0, 45.0, 180.0][index]
		emitter.gravity = Vector2.ZERO
		emitter.initial_velocity_min = 30.0
		emitter.initial_velocity_max = 60.0
		emitter.emitting = false
		contents.add_child(emitter)
		_particles.append(emitter)
		_add_label("ParticleLabel_%d" % index, ["Strahl", "Fächer", "Streuung"][index],
			emitter.position + Vector2(0, 80), 22)


func _build_sprite_gallery() -> void:
	var variants: Array[String] = ["hd", "pixel_art", "ultra", "test"]
	for index in range(variants.size()):
		var variant := variants[index]
		var frames := load(
			HERO_ROOT + "%s/green_hero_stand_walk_%s.tres" % [variant, variant]
		) as SpriteFrames
		var sprite := AnimatedSprite2D.new()
		sprite.name = "Sprite_%s" % variant
		sprite.position = Vector2(1320 + index * 400, 1080)
		sprite.sprite_frames = frames
		sprite.animation = &"stand_S"
		sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		var layouts := frames.get_meta(&"animation_layouts", {}) as Dictionary
		var layout := layouts.get(&"stand_S", {}) as Dictionary
		sprite.scale = layout.get("scale", Vector2.ONE * (80.0 / 245.0)) as Vector2
		sprite.offset = layout.get("offset", Vector2(0, -122.5)) as Vector2
		contents.add_child(sprite)
		_add_label("SpriteLabel_%s" % variant, ["HD", "Pixel Art", "Ultra", "Testversion"][index],
			sprite.position + Vector2(0, 64), 22)
	_add_label("SpriteHint", "Die steuerbare Figur nutzt deine Auswahl unter F5 → Darstellung.",
		Vector2(1920, 840), 22)


func _add_sample(node_name: String, file: String, point: Vector2, size_factor: float) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.name = node_name
	sprite.position = point
	var asset_key := StringName(file.get_basename())
	PortalGraphics.apply_sprite(sprite, asset_key, graphics_variant, size_factor)
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	contents.add_child(sprite)
	_sample_bindings.append({
		"sprite": sprite, "asset_key": asset_key, "size_factor": size_factor,
	})
	return sprite


func _apply_particle_texture(emitter: CPUParticles2D) -> void:
	emitter.texture = PortalGraphics.get_texture(&"particle", graphics_variant)
	emitter.scale_amount_min = 12.0 / float(emitter.texture.get_width())
	emitter.scale_amount_max = emitter.scale_amount_min


func _add_label(node_name: String, text: String, point: Vector2, font_size: int) -> void:
	var label := Label.new()
	label.name = node_name
	label.text = text
	label.position = point - Vector2(640, 0)
	label.size = Vector2(1280, 48)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", Palette.TEXT)
	contents.add_child(label)
