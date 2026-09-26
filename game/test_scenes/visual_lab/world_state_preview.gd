extends Node2D

enum WorldState {
	DAMAGED,
	RESTORED,
}

const PREVIEW_SIZE := Vector2(1440, 810)
const DAMAGED_DEFAULT_FOG_VARIANT := 1
const RESTORED_DEFAULT_FOG_VARIANT := 1
const DAMAGED_DEFAULT_LIGHT_VARIANT := 1
const RESTORED_DEFAULT_LIGHT_VARIANT := 1
const DAMAGED_FOG_VARIANTS: Array[Dictionary] = [
	{
		"id": "low",
		"name": "Gering",
		"strength": 0.55,
	},
	{
		"id": "medium",
		"name": "Mittel",
		"strength": 0.82,
	},
	{
		"id": "high",
		"name": "Hoch",
		"strength": 1.0,
	},
]
const RESTORED_FOG_VARIANTS: Array[Dictionary] = [
	{
		"id": "off",
		"name": "Aus",
		"strength": 0.0,
	},
	{
		"id": "low",
		"name": "Gering",
		"strength": 0.55,
	},
	{
		"id": "medium",
		"name": "Mittel",
		"strength": 1.0,
	},
]
const DAMAGED_LIGHT_VARIANTS: Array[Dictionary] = [
	{
		"id": "cool_muted",
		"name": "Kühl und gedämpft",
		"brightness": "Dunkel",
		"contrast": "Niedrig",
		"mood": "Kühl / entsättigt",
		"state_modulate": Color(0.86, 0.90, 0.96, 1.0),
		"primary_color": Color(0.10, 0.18, 0.30, 0.10),
	},
	{
		"id": "cool_dark",
		"name": "Kühl und dunkel",
		"brightness": "Sehr dunkel",
		"contrast": "Mittel",
		"mood": "Kühl / entsättigt",
		"state_modulate": Color(0.70, 0.76, 0.86, 1.0),
		"primary_color": Color(0.03, 0.08, 0.16, 0.18),
	},
]
const RESTORED_LIGHT_VARIANTS: Array[Dictionary] = [
	{
		"id": "neutral_clear",
		"name": "Neutral und klar",
		"brightness": "Normal",
		"contrast": "Mittel",
		"mood": "Neutral",
		"state_modulate": Color(0.98, 1.0, 0.98, 1.0),
		"primary_color": Color(1.0, 0.92, 0.72, 0.025),
		"secondary_color": Color(0.64, 0.84, 0.80, 0.025),
	},
	{
		"id": "warm_clear",
		"name": "Warm und klar",
		"brightness": "Hell",
		"contrast": "Hoch",
		"mood": "Leicht warm",
		"state_modulate": Color(1.0, 0.97, 0.88, 1.0),
		"primary_color": Color(1.0, 0.72, 0.30, 0.075),
		"secondary_color": Color(0.64, 0.84, 0.80, 0.012),
	},
]

var current_state: int = WorldState.DAMAGED
var current_fog_variant := DAMAGED_DEFAULT_FOG_VARIANT
var current_light_variant := DAMAGED_DEFAULT_LIGHT_VARIANT
var preview_mode: StringName = &"all"

@onready var damaged_state: Node2D = $DamagedState
@onready var restored_state: Node2D = $RestoredState
@onready var damaged_fog: Sprite2D = $DamagedState/Fog/Sprite2D
@onready var damaged_light: Polygon2D = $DamagedState/ColdLight
@onready var restored_fog: Sprite2D = $RestoredState/Fog/Sprite2D
@onready var restored_clear_air: Polygon2D = $RestoredState/ClearAir
@onready var restored_light: Polygon2D = $RestoredState/WarmLight


func _ready() -> void:
	set_world_state(current_state)


func set_world_state(value: int) -> void:
	current_state = clampi(
		value,
		WorldState.DAMAGED,
		WorldState.RESTORED,
	)
	damaged_state.visible = current_state == WorldState.DAMAGED
	restored_state.visible = current_state == WorldState.RESTORED
	_apply_atmosphere()


func set_atmosphere_variants(fog_variant: int, light_variant: int) -> void:
	current_fog_variant = clampi(
		fog_variant,
		0,
		get_fog_variant_count(current_state) - 1,
	)
	current_light_variant = clampi(
		light_variant,
		0,
		get_light_variant_count(current_state) - 1,
	)
	_apply_atmosphere()


func set_preview_mode(mode: StringName) -> void:
	preview_mode = mode
	match mode:
		&"fog":
			$Title.text = "Nebel · Vergleich auf derselben Testfläche"
		&"day_night":
			$Title.text = "Tageszeit · Hell-Dunkel-Vergleich"
		&"world_state":
			$Title.text = "Weltzustand · Aufgebaut ↔ Zerstört"
	_apply_atmosphere()


func get_fog_variant_count(state: int) -> int:
	return _fog_variants_for_state(state).size()


func get_light_variant_count(state: int) -> int:
	return _light_variants_for_state(state).size()


func get_default_fog_variant(state: int) -> int:
	if state == WorldState.RESTORED:
		return RESTORED_DEFAULT_FOG_VARIANT
	return DAMAGED_DEFAULT_FOG_VARIANT


func get_default_light_variant(state: int) -> int:
	if state == WorldState.RESTORED:
		return RESTORED_DEFAULT_LIGHT_VARIANT
	return DAMAGED_DEFAULT_LIGHT_VARIANT


func find_fog_variant(state: int, variant_id: String, default_value: int) -> int:
	return _find_variant(_fog_variants_for_state(state), variant_id, default_value)


func find_light_variant(state: int, variant_id: String, default_value: int) -> int:
	return _find_variant(_light_variants_for_state(state), variant_id, default_value)


func get_fog_variant_id(state: int, variant: int) -> String:
	return str(_variant(_fog_variants_for_state(state), variant)["id"])


func get_fog_variant_name(state: int, variant: int) -> String:
	return str(_variant(_fog_variants_for_state(state), variant)["name"])


func get_light_variant_id(state: int, variant: int) -> String:
	return str(_variant(_light_variants_for_state(state), variant)["id"])


func get_light_variant_name(state: int, variant: int) -> String:
	return str(_variant(_light_variants_for_state(state), variant)["name"])


func get_active_fog_name() -> String:
	return str(_active_fog_variant()["name"])


func get_active_fog_strength() -> float:
	return float(_active_fog_variant()["strength"])


func get_active_light_name() -> String:
	return str(_active_light_variant()["name"])


func get_active_brightness_name() -> String:
	return str(_active_light_variant()["brightness"])


func get_active_contrast_name() -> String:
	return str(_active_light_variant()["contrast"])


func get_active_color_mood() -> String:
	return str(_active_light_variant()["mood"])


func get_active_state_modulate() -> Color:
	return _active_light_variant()["state_modulate"] as Color


func get_active_light_color() -> Color:
	return _active_light_variant()["primary_color"] as Color


func get_preview_size() -> Vector2:
	return PREVIEW_SIZE


func is_restored() -> bool:
	return current_state == WorldState.RESTORED


func _apply_atmosphere() -> void:
	if not is_node_ready():
		return
	var fog_variant := _active_fog_variant()
	var light_variant := _active_light_variant()
	var fog_strength := float(fog_variant["strength"])
	var state_modulate := light_variant["state_modulate"] as Color
	var primary_color := light_variant["primary_color"] as Color
	var combined_preview := preview_mode == &"all"
	damaged_fog.visible = combined_preview or preview_mode == &"fog"
	restored_fog.visible = combined_preview or preview_mode == &"fog"
	damaged_light.visible = combined_preview
	restored_light.visible = combined_preview
	restored_clear_air.visible = combined_preview
	if not combined_preview:
		state_modulate = Color.WHITE
	if current_state == WorldState.RESTORED:
		restored_fog.self_modulate = Color(1.0, 1.0, 1.0, fog_strength)
		restored_state.modulate = state_modulate
		restored_light.color = primary_color
		restored_clear_air.color = light_variant["secondary_color"] as Color
		return
	damaged_fog.self_modulate = Color(1.0, 1.0, 1.0, fog_strength)
	damaged_state.modulate = state_modulate
	damaged_light.color = primary_color


func _active_fog_variant() -> Dictionary:
	return _variant(_fog_variants_for_state(current_state), current_fog_variant)


func _active_light_variant() -> Dictionary:
	return _variant(_light_variants_for_state(current_state), current_light_variant)


func _fog_variants_for_state(state: int) -> Array[Dictionary]:
	if state == WorldState.RESTORED:
		return RESTORED_FOG_VARIANTS
	return DAMAGED_FOG_VARIANTS


func _light_variants_for_state(state: int) -> Array[Dictionary]:
	if state == WorldState.RESTORED:
		return RESTORED_LIGHT_VARIANTS
	return DAMAGED_LIGHT_VARIANTS


func _variant(variants: Array[Dictionary], variant: int) -> Dictionary:
	return variants[clampi(variant, 0, variants.size() - 1)]


func _find_variant(
		variants: Array[Dictionary],
		variant_id: String,
		default_value: int,
) -> int:
	for variant_index in range(variants.size()):
		if str(variants[variant_index]["id"]) == variant_id:
			return variant_index
	return clampi(default_value, 0, variants.size() - 1)
