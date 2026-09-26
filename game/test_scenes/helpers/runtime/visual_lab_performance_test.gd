extends RefCounted

const DiagnosticsScript := preload("res://test_scenes/visual_lab/performance_diagnostics.gd")
const LabScript := preload("res://test_scenes/visual_lab/visual_lab.gd")
const SETTINGS_KEY := "etherfood/development/visual_lab_settings_path"
const SETTINGS_PATH := "user://visual_lab_performance_test.cfg"

var failures: PackedStringArray = []


func run(tree: SceneTree) -> PackedStringArray:
	_expect_measurements()
	var had_override := ProjectSettings.has_setting(SETTINGS_KEY)
	var previous_override: Variant = ProjectSettings.get_setting(SETTINGS_KEY)
	ProjectSettings.set_setting(SETTINGS_KEY, SETTINGS_PATH)
	_remove_settings()
	var scene := load("res://test_scenes/visual_lab/visual_lab.tscn") as PackedScene
	var lab := scene.instantiate() as LabScript
	tree.root.add_child(lab)
	await tree.process_frame
	await _expect_overlays(tree, lab)
	lab.queue_free()
	await tree.process_frame
	var reopened := scene.instantiate() as LabScript
	tree.root.add_child(reopened)
	await tree.process_frame
	_expect(not reopened.performance_panel.visible, "F12 starts hidden after reopening")
	_expect(not reopened.diagnostics_panel.visible, "F11 starts hidden after reopening")
	reopened.queue_free()
	await tree.process_frame
	_remove_settings()
	ProjectSettings.set_setting(SETTINGS_KEY, previous_override if had_override else null)
	return failures


func _expect_measurements() -> void:
	var counters := DiagnosticsScript.parse_proc_values(
		"read_bytes: 1024\nwrite_bytes: 2048\nVmRSS:\t1536 kB\n"
		+ "Threads:\t4\nName:\tgodot\nbroken\nnegative: -8\nempty:\n"
	)
	_expect(counters.get("VmRSS") == 1572864, "process RSS converts kernel KiB to bytes")
	_expect(counters.get("read_bytes") == 1024, "disk counters retain byte units")
	_expect(counters.get("Threads") == 4, "unitless proc counters remain integers")
	_expect(
		not counters.has("Name") and not counters.has("negative") and not counters.has("empty"),
		"missing and malformed proc values are not treated as zero",
	)
	var previous := {"read_bytes": 1024, "write_bytes": 2048}
	var current := {"read_bytes": 3072, "write_bytes": 10240}
	var rates := DiagnosticsScript.calculate_io_rates(previous, current, 0.5)
	_expect(rates["read_bytes"] == 4096.0, "read rate uses elapsed time and counter delta")
	_expect(rates["write_bytes"] == 16384.0, "write rate uses its own counter delta")
	_expect(
		DiagnosticsScript.calculate_io_rates({}, current, 0.5)["read_bytes"] < 0.0,
		"first sample has no fabricated rate",
	)
	_expect(
		DiagnosticsScript.calculate_io_rates(previous, {}, 0.5)["write_bytes"] < 0.0,
		"unavailable counter does not fabricate zero I/O",
	)
	_expect(
		DiagnosticsScript.calculate_io_rates(previous, current, 0.0)["read_bytes"] < 0.0,
		"zero sample interval avoids division by zero",
	)
	_expect(
		DiagnosticsScript.calculate_io_rates(current, previous, 0.5)["read_bytes"] < 0.0,
		"reset counters do not produce negative transfer rates",
	)
	_expect(
		DiagnosticsScript.calculate_io_rates(previous, previous, 0.5)["write_bytes"] == 0.0,
		"idle disk has a measured zero rate",
	)
	_expect(DiagnosticsScript.format_bytes(1572864) == "1,5 MiB", "memory units are binary")
	_expect(
		DiagnosticsScript.format_bytes(-1) == DiagnosticsScript.NOT_AVAILABLE,
		"unknown byte values are clearly labelled",
	)
	_expect(
		DiagnosticsScript.format_system_memory({"physical": 4096, "free": 1024})
		== "3,0 KiB / 4,0 KiB (75 %)",
		"system RAM shows used, total and percentage",
	)
	for memory in [{}, {"physical": -1, "free": -1}, {"physical": 0, "free": 0}]:
		_expect(
			DiagnosticsScript.format_system_memory(memory) == DiagnosticsScript.NOT_AVAILABLE,
			"unknown system RAM avoids a fabricated percentage",
		)
	var diagnostics := DiagnosticsScript.new()
	var first := diagnostics.sample()
	_expect(first.contains("FPS: "), "live sampler includes FPS")
	if OS.get_name() == "Linux" and FileAccess.file_exists("/proc/self/io"):
		_expect(
			first.contains("Datenträger Lesen (Prozess): Messung läuft"),
			"live procfs read succeeds despite the file reporting zero size",
		)
		_expect(
			not first.contains("RAM Prozess (RSS): nicht verfügbar"),
			"live Linux sampler provides resident process memory",
		)
	if DisplayServer.get_name() == "headless":
		_expect(
			first.contains("VRAM (Godot, geschätzt): nicht verfügbar"),
			"headless renderer does not pretend to measure VRAM",
		)


func _expect_overlays(tree: SceneTree, lab: LabScript) -> void:
	var game_overlay := lab.diagnostics_panel
	var performance_overlay := lab.performance_panel
	_expect_text_overlay(game_overlay)
	_expect_text_overlay(performance_overlay)
	_expect(
		not game_overlay.visible and not performance_overlay.visible,
		"both overlays start hidden",
	)
	_expect(
		not game_overlay.get_global_rect().intersects(performance_overlay.get_global_rect()),
		"simultaneous diagnostics occupy separate columns",
	)
	lab._process(1.0)
	_expect(lab.performance_values.text.is_empty(), "hidden F12 does not start sampling")
	lab._unhandled_input(_key(KEY_F3))
	_expect(
		not game_overlay.visible and not performance_overlay.visible,
		"F3 opens neither overlay",
	)
	lab._unhandled_input(_key(KEY_F12))
	_expect(performance_overlay.visible and not game_overlay.visible, "F12 opens independently")
	_expect(
		lab.performance_values.text.begins_with("FPS: "),
		"F12 has values immediately after opening",
	)
	lab._unhandled_input(_key(KEY_F12, true))
	_expect(performance_overlay.visible, "held F12 does not retrigger")
	lab._unhandled_input(_key(KEY_F11))
	_expect(game_overlay.visible and performance_overlay.visible, "F11 and F12 can coexist")
	_expect(not lab.diagnostics_values.text.contains("FPS:"), "F11 has no FPS duplication")
	for game_line in lab.diagnostics_values.text.split("\n"):
		var prefix := game_line.get_slice(":", 0) + ":"
		_expect(
			not lab.performance_values.text.contains(prefix),
			"performance overlay does not repeat game metric '%s'" % prefix,
		)
	lab.performance_values.text = "pending"
	await tree.create_timer(0.6).timeout
	_expect(lab.performance_values.text != "pending", "visible F12 refreshes periodically")
	if OS.get_name() == "Linux" and FileAccess.file_exists("/proc/self/io"):
		for prefix in ["Datenträger Lesen (Prozess): ", "Datenträger Schreiben (Prozess): "]:
			var line := _line_with_prefix(lab.performance_values.text, prefix)
			_expect(line.ends_with("/s"), "live disk rate has byte-per-second units")
	var hero_position := lab.hero_character.position
	Input.action_press(&"gameplay_move_right")
	await tree.physics_frame
	await tree.physics_frame
	Input.action_release(&"gameplay_move_right")
	_expect(lab.hero_character.position != hero_position, "both overlays allow hero movement")
	lab._unhandled_input(_key(KEY_F11))
	_expect(
		not game_overlay.visible and performance_overlay.visible,
		"hiding F11 leaves F12 visible",
	)
	lab._unhandled_input(_key(KEY_F12))
	_expect(not performance_overlay.visible, "second F12 press hides performance")
	var last_values := lab.performance_values.text
	lab._process(1.0)
	_expect(lab.performance_values.text == last_values, "hidden F12 stops updating")
	_expect(
		lab._performance_diagnostics._previous_time_usec == -1,
		"hiding F12 clears I/O baseline",
	)
	lab._unhandled_input(_key(KEY_F12))
	if OS.get_name() == "Linux" and FileAccess.file_exists("/proc/self/io"):
		_expect(
			lab.performance_values.text.contains("Datenträger Lesen (Prozess): Messung läuft"),
			"reopening F12 starts a fresh rate interval",
		)
	_expect_menu(lab)
	await tree.process_frame
	_expect(
		lab.performance_values.get_minimum_size().y <= performance_overlay.size.y - 42.0,
		"performance text fits its column",
	)


func _expect_menu(lab: LabScript) -> void:
	lab._unhandled_input(_key(KEY_F5))
	var menu := lab.controls_interface
	var tab := menu.get_node("Menu/ThemeTabs/DiagnosticsTab") as Button
	tab.pressed.emit()
	var options := "Menu/Pages/DiagnosticsPage/Content/PerformanceOptions/"
	var off := menu.get_node(options + "OffButton") as Button
	var on := menu.get_node(options + "OnButton") as Button
	_expect(on.button_pressed, "F12 synchronizes the performance menu switch")
	off.pressed.emit()
	_expect(not lab.performance_panel.visible, "menu can hide performance")
	on.pressed.emit()
	_expect(lab.performance_panel.visible, "menu can show performance")
	on.grab_focus()
	_expect(
		not lab._focused_setting_can_be_accepted(&"performance"),
		"F12 is never a game standard",
	)
	lab._save_settings()
	var settings := ConfigFile.new()
	_expect(settings.load(SETTINGS_PATH) == OK, "isolated preview settings can be read")
	for key in ["diagnostics", "performance", "diagnostics_visible", "performance_visible"]:
		_expect(
			not settings.has_section_key("visual_lab", key),
			"overlays are not persisted: %s" % key,
		)
	lab._unhandled_input(_key(KEY_F5))
	_expect(lab.performance_panel.visible, "closing F5 leaves F12 visible")


func _expect_text_overlay(overlay: Control) -> void:
	_expect(overlay.get_class() == "Control", "diagnostic overlay has no drawn panel")
	_expect(overlay.mouse_filter == Control.MOUSE_FILTER_IGNORE, "diagnostic overlay ignores mouse")
	for node_name in ["Title", "Values"]:
		var label := overlay.get_node(node_name) as Label
		_expect(label.get_theme_color("font_color") == Color.WHITE, "diagnostic text is white")
		_expect(label.get_theme_constant("outline_size") == 0, "diagnostic text has no outline")
		_expect(label.mouse_filter == Control.MOUSE_FILTER_IGNORE, "diagnostic label ignores mouse")


func _key(keycode: Key, echo: bool = false) -> InputEventKey:
	var event := InputEventKey.new()
	event.keycode = keycode
	event.pressed = true
	event.echo = echo
	return event


func _line_with_prefix(contents: String, prefix: String) -> String:
	for line in contents.split("\n"):
		if line.begins_with(prefix):
			return line
	return ""


func _remove_settings() -> void:
	if FileAccess.file_exists(SETTINGS_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_PATH))


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("VisualLab performance: %s" % description)
