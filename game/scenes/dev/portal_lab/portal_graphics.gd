extends RefCounted

const ASSET_ROOT := "res://tests/assets/prototypes/portal_lab/"
const DEFAULT_TEXTURES := {
	&"floor_tile": preload("res://tests/assets/prototypes/portal_lab/test/floor_tile.svg"),
	&"door": preload("res://tests/assets/prototypes/portal_lab/test/door.svg"),
	&"lamp": preload("res://tests/assets/prototypes/portal_lab/test/lamp.svg"),
	&"crate": preload("res://tests/assets/prototypes/portal_lab/test/crate.svg"),
	&"monster": preload("res://tests/assets/prototypes/portal_lab/test/monster.svg"),
	&"particle": preload("res://tests/assets/prototypes/portal_lab/test/particle.svg"),
}
const WORLD_SIZES := {
	&"door": Vector2(112, 128),
	&"lamp": Vector2(72, 128),
	&"crate": Vector2(128, 112),
	&"monster": Vector2(112, 128),
	&"particle": Vector2(12, 12),
}


static func variant_for_graphics(graphics_id: StringName) -> StringName:
	return &"pixelart" if graphics_id in [&"pixel_art", &"pixelart"] else &"test"


static func get_texture(asset_key: StringName, graphics_id: StringName) -> Texture2D:
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
	match graphics_id:
		&"pixel_art", &"pixelart":
			return "Portal-Labor: Pixel Art"
		&"hd":
			return "Portal-Labor: Testvorlagen (für HD)"
		&"ultra":
			return "Portal-Labor: Testvorlagen (für Ultra)"
	return "Portal-Labor: Testversion"
