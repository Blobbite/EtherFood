extends RefCounted

const ASSET_ROOT := "res://test_assets/environment/locations/portal_lab/"
const TEMPLE_ROOT := "res://test_assets/environment/tilesets/temple/"
const GRAPHICS_IDS: Array[StringName] = [
	&"comic_high", &"comic_mid", &"comic_low", &"pixel_high", &"pixel_low",
]
const GRAPHICS_NAMES: Array[String] = [
	"Comic High", "Comic Mittel", "Comic Low", "Pixel Art High", "Pixel Art Low",
]
const FLOOR_IDS: Array[String] = [
	"ornate", "plain", "cyan_ornate", "cyan_panels", "framed_stone",
	"octagonal_stone", "riveted_metal", "staggered_stone", "stone_grid",
]
const FLOOR_NAMES: Array[String] = [
	"Ornamente", "Schlicht", "Cyan-Ornamente", "Cyan-Platten", "Gerahmter Stein",
	"Achteckiger Stein", "Genietetes Metall", "Versetzter Stein", "Steinraster",
]
const DEFAULT_TEXTURES := {
	&"door": preload("res://test_assets/environment/locations/portal_lab/test/door.svg"),
	&"lamp": preload("res://test_assets/environment/locations/portal_lab/test/lamp.svg"),
	&"crate": preload("res://test_assets/environment/locations/portal_lab/test/crate.svg"),
	&"monster": preload("res://test_assets/environment/locations/portal_lab/test/monster.svg"),
	&"particle": preload("res://test_assets/environment/locations/portal_lab/test/particle.svg"),
}
const WORLD_SIZES := {
	&"door": Vector2(112, 128),
	&"lamp": Vector2(72, 128),
	&"crate": Vector2(128, 112),
	&"monster": Vector2(112, 128),
	&"particle": Vector2(12, 12),
}


static func variant_for_graphics(graphics_id: StringName) -> StringName:
	return &"pixelart" if graphics_id in [
		&"pixel_high", &"pixel_low", &"pixel_art", &"pixelart",
	] else &"test"


## Keeps the five temple resolutions distinct; legacy IDs remain readable.
static func temple_variant(graphics_id: StringName) -> StringName:
	if graphics_id in GRAPHICS_IDS:
		return graphics_id
	if graphics_id in [&"pixel_art", &"pixelart"]:
		return &"pixel_high"
	return &"comic_high"


## Loads a supplied surface at its native resolution; unknown IDs use Comic High / Ornamente.
static func get_temple_texture(
		surface: StringName, graphics_id: StringName, floor_id: String = "ornate",
) -> Texture2D:
	var variant := temple_variant(graphics_id)
	var file: String
	match surface:
		&"floors":
			if floor_id not in FLOOR_IDS:
				floor_id = FLOOR_IDS[0]
			file = "blueprinttempel_floor_blueprint_%s.png" % floor_id
		&"walls":
			file = "blueprinttempel_wall_blueprint_cyan_blocks.png"
		&"roofs":
			file = "blueprinttempel_roof_texture_stone_shingles.png"
		_:
			return null
	return load(TEMPLE_ROOT + "%s/blueprint/%s/%s" % [surface, variant, file]) as Texture2D


static func get_texture(asset_key: StringName, graphics_id: StringName) -> Texture2D:
	if asset_key == &"floor_tile":
		return get_temple_texture(&"floors", graphics_id)
	if not DEFAULT_TEXTURES.has(asset_key):
		return null
	var variant := variant_for_graphics(graphics_id)
	for extension in ["png", "svg"]:
		var path := ASSET_ROOT + "%s/%s.%s" % [variant, asset_key, extension]
		if ResourceLoader.exists(path, "Texture2D"):
			var texture := load(path) as Texture2D
			if texture != null:
				return texture
	return DEFAULT_TEXTURES[asset_key] as Texture2D


static func apply_sprite(
		sprite: Sprite2D, asset_key: StringName, graphics_id: StringName, size_factor: float = 1.0,
) -> void:
	var texture := get_texture(asset_key, graphics_id)
	if texture == null or not WORLD_SIZES.has(asset_key):
		return
	sprite.texture = texture
	sprite.offset = Vector2(0, -float(texture.get_height()) / 2.0)
	sprite.scale = (WORLD_SIZES[asset_key] as Vector2) / texture.get_size() * size_factor


static func status_text(graphics_id: StringName) -> String:
	var variant := temple_variant(graphics_id)
	var name := GRAPHICS_NAMES[GRAPHICS_IDS.find(variant)]
	var props := "Pixel Art" if variant_for_graphics(variant) == &"pixelart" else "Testvorlagen"
	return "Blueprint-Tempel: %s · Boden, Wand und Dach\nTüren und Testobjekte: %s" % [name, props]
