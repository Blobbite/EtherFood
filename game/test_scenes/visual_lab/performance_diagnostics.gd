extends RefCounted

const NOT_AVAILABLE := "nicht verfügbar"
const MEASURING := "Messung läuft"

var _previous_io: Dictionary[String, int] = {}
var _previous_time_usec := -1
var _hardware_lines: PackedStringArray = []


func reset() -> void:
	_previous_io.clear()
	_previous_time_usec = -1


func sample() -> String:
	if _hardware_lines.is_empty():
		_cache_hardware()
	var now_usec := Time.get_ticks_usec()
	var process_status := _read_proc_values("/proc/self/status")
	var current_io := _read_proc_values("/proc/self/io")
	var elapsed := float(now_usec - _previous_time_usec) / 1000000.0
	var rates := calculate_io_rates(_previous_io, current_io, elapsed)
	var fps := maxi(0, roundi(Performance.get_monitor(Performance.TIME_FPS)))
	var has_renderer := DisplayServer.get_name() != "headless"
	var lines := PackedStringArray([
		"FPS: %d" % fps,
		"Bilddauer (aus FPS): %s"
		% (_milliseconds(1.0 / float(fps)) if fps > 0 else MEASURING),
		"Framezeit (Godot): %s" % _milliseconds(
			Performance.get_monitor(Performance.TIME_PROCESS)
		),
		"Physikzeit (Godot): %s" % _milliseconds(
			Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)
		),
		"Physik-Takt: %d Hz" % Engine.physics_ticks_per_second,
		"FPS-Limit: %s · VSync: %s" % [
			str(Engine.max_fps) if Engine.max_fps > 0 else "offen",
			_vsync_name() if has_renderer else NOT_AVAILABLE,
		],
		"RAM System (inkl. Cache): %s" % format_system_memory(OS.get_memory_info()),
		"RAM Prozess (RSS): %s" % format_bytes(process_status.get("VmRSS", -1)),
		"RAM Godot: %s" % _engine_memory(Performance.MEMORY_STATIC),
		"RAM Godot Spitze: %s" % _engine_memory(Performance.MEMORY_STATIC_MAX),
		"VRAM (Godot, geschätzt): %s" % _render_memory(Performance.RENDER_VIDEO_MEM_USED),
		"Texturspeicher: %s" % _render_memory(Performance.RENDER_TEXTURE_MEM_USED),
		"Renderpuffer: %s" % _render_memory(Performance.RENDER_BUFFER_MEM_USED),
		"Datenträger Lesen (Prozess): %s" % _io_rate_text(rates, current_io, "read_bytes"),
		"Datenträger Schreiben (Prozess): %s"
		% _io_rate_text(rates, current_io, "write_bytes"),
		"Datenträger frei (Spielerdaten): %s" % _disk_free(),
		"Draw Calls: %s" % _render_count(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		"Renderobjekte: %s" % _render_count(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
		"Primitive: %s" % _render_count(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		"Objekte / Nodes / Ressourcen: %d / %d / %d" % [
			int(Performance.get_monitor(Performance.OBJECT_COUNT)),
			int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)),
			int(Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT)),
		],
		"2D-Kollisionspaare: %d" % int(
			Performance.get_monitor(Performance.PHYSICS_2D_COLLISION_PAIRS)
		),
	])
	lines.append_array(_hardware_lines)
	_previous_io = current_io
	_previous_time_usec = now_usec
	return "\n".join(lines)


static func parse_proc_values(contents: String) -> Dictionary[String, int]:
	var values: Dictionary[String, int] = {}
	for line in contents.split("\n", false):
		var colon := line.find(":")
		if colon < 1:
			continue
		var fields := line.substr(colon + 1).strip_edges().split(" ", false)
		if fields.is_empty() or not fields[0].is_valid_int():
			continue
		var value := fields[0].to_int()
		if value < 0:
			continue
		if fields.size() > 1 and fields[1] == "kB":
			value *= 1024
		values[line.left(colon)] = value
	return values


static func calculate_io_rates(
		previous: Dictionary,
		current: Dictionary,
		elapsed_seconds: float,
) -> Dictionary[String, float]:
	var rates: Dictionary[String, float] = {}
	for counter in ["read_bytes", "write_bytes"]:
		rates[counter] = -1.0
		if elapsed_seconds <= 0.0 or not previous.has(counter) or not current.has(counter):
			continue
		var before := int(previous[counter])
		var after := int(current[counter])
		if before >= 0 and after >= before:
			rates[counter] = float(after - before) / elapsed_seconds
	return rates


static func format_bytes(value: float) -> String:
	if value < 0.0:
		return NOT_AVAILABLE
	var units := ["B", "KiB", "MiB", "GiB", "TiB"]
	var unit := 0
	while value >= 1024.0 and unit < units.size() - 1:
		value /= 1024.0
		unit += 1
	return "%s %s" % [("%.1f" % value).replace(".", ","), units[unit]]


static func format_system_memory(memory: Dictionary) -> String:
	var total := int(memory.get("physical", -1))
	var free := int(memory.get("free", -1))
	if total <= 0 or free < 0 or free > total:
		return NOT_AVAILABLE
	var used := total - free
	return "%s / %s (%d %%)" % [
		format_bytes(used), format_bytes(total), roundi(100.0 * float(used) / float(total)),
	]


func _cache_hardware() -> void:
	var has_renderer := DisplayServer.get_name() != "headless"
	_hardware_lines = PackedStringArray([
		"CPU: %s" % _available_name(OS.get_processor_name()),
		"Logische CPU-Kerne: %d" % OS.get_processor_count(),
		"GPU: %s" % (
			_available_name(RenderingServer.get_video_adapter_name())
			if has_renderer else NOT_AVAILABLE
		),
		"Renderer: %s" % (
			"%s · %s" % [
				RenderingServer.get_current_rendering_method(),
				RenderingServer.get_current_rendering_driver_name(),
			] if has_renderer else "Headless"
		),
		"System: %s · Godot %s" % [OS.get_name(), Engine.get_version_info()["string"]],
	])


func _io_rate_text(rates: Dictionary, current: Dictionary, counter: String) -> String:
	if not current.has(counter):
		return NOT_AVAILABLE
	var rate := float(rates.get(counter, -1.0))
	if _previous_time_usec < 0 or rate < 0.0:
		return MEASURING
	return "%s/s" % format_bytes(rate)


func _read_proc_values(path: String) -> Dictionary[String, int]:
	if OS.get_name() != "Linux":
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	# procfs files report a zero length; read lines instead of get_as_text().
	var lines := PackedStringArray()
	while not file.eof_reached():
		lines.append(file.get_line())
	file.close()
	return parse_proc_values("\n".join(lines))


func _engine_memory(monitor: Performance.Monitor) -> String:
	if not OS.is_debug_build():
		return NOT_AVAILABLE
	return format_bytes(Performance.get_monitor(monitor))


func _render_memory(monitor: Performance.Monitor) -> String:
	if DisplayServer.get_name() == "headless":
		return NOT_AVAILABLE
	return format_bytes(Performance.get_monitor(monitor))


func _render_count(monitor: Performance.Monitor) -> String:
	if DisplayServer.get_name() == "headless":
		return NOT_AVAILABLE
	return str(int(Performance.get_monitor(monitor)))


func _disk_free() -> String:
	var directory := DirAccess.open("user://")
	if directory == null:
		return NOT_AVAILABLE
	var space := directory.get_space_left()
	# Godot also returns zero when the platform query fails.
	return format_bytes(space) if space > 0 else "voll oder nicht verfügbar"


func _milliseconds(seconds: float) -> String:
	return "%s ms" % ("%.2f" % (seconds * 1000.0)).replace(".", ",")


func _available_name(value: String) -> String:
	return value if not value.is_empty() else NOT_AVAILABLE


func _vsync_name() -> String:
	match DisplayServer.window_get_vsync_mode():
		DisplayServer.VSYNC_DISABLED:
			return "AUS"
		DisplayServer.VSYNC_ENABLED:
			return "AN"
		DisplayServer.VSYNC_ADAPTIVE:
			return "Adaptiv"
		DisplayServer.VSYNC_MAILBOX:
			return "Mailbox"
	return NOT_AVAILABLE
