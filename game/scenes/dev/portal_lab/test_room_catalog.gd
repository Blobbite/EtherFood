extends Resource

const RoomDefinition := preload("res://scenes/dev/portal_lab/test_room_definition.gd")

@export var rooms: Array[RoomDefinition] = []


func validation_errors() -> PackedStringArray:
	var errors: PackedStringArray = []
	var seen: Array[StringName] = []
	for room in rooms:
		if room == null:
			errors.append("Missing room definition.")
			continue
		if room.room_id == &"" or room.room_id == &"hub" or room.room_id in seen:
			errors.append("Invalid or duplicate room ID: %s" % room.room_id)
		seen.append(room.room_id)
		if room.title.is_empty() or room.scene == null:
			errors.append("Room %s requires a title and scene." % room.room_id)
	return errors


func find_room(room_id: StringName) -> RoomDefinition:
	for room in rooms:
		if room != null and room.room_id == room_id:
			return room
	return null
