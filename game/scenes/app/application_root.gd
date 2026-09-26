extends Node

signal startup_succeeded(initial_route_id: StringName)
signal startup_failed(error: Error, message: String)

const RouteTable := preload("res://shared/resources/route_table.gd")

@export var route_table: RouteTable
@export var initial_route_id: StringName = &""
@export_file("*.tres") var development_routes_path: String = (
	"res://test_scenes/helpers/development_routes.tres"
)

@onready var route_host: Node = $RouteHost

var _started := false
var _startup_error: Error = OK


func _ready() -> void:
	var routes_error := _prepare_routes()
	if routes_error != OK:
		_report_startup_failure(routes_error, "Development routes could not be loaded.")
		return
	var configuration_error := SceneRouter.configure(route_host, route_table)
	if configuration_error != OK:
		_report_startup_failure(
			configuration_error,
			"SceneRouter configuration failed with error %d." % configuration_error,
		)
		return

	var navigation_error := SceneRouter.navigate(initial_route_id)
	if navigation_error != OK:
		SceneRouter.unconfigure(route_host)
		_report_startup_failure(
			navigation_error,
			"Initial route '%s' failed with error %d."
			% [initial_route_id, navigation_error],
		)
		return

	_started = true
	startup_succeeded.emit(initial_route_id)


func _exit_tree() -> void:
	if is_instance_valid(route_host):
		SceneRouter.unconfigure(route_host)


func is_started() -> bool:
	return _started


func get_startup_error() -> Error:
	return _startup_error


func _prepare_routes() -> Error:
	if route_table == null:
		return ERR_INVALID_PARAMETER
	# Export presets exclude the entire test area, including debug exports.
	if (
		not OS.is_debug_build()
		or development_routes_path.is_empty()
		or not ResourceLoader.exists(development_routes_path)
	):
		return OK
	var development_routes := load(development_routes_path) as RouteTable
	if development_routes == null or not development_routes.is_valid():
		return ERR_INVALID_DATA
	var configured_routes := RouteTable.new()
	configured_routes.entries.assign(route_table.entries)
	for entry in development_routes.entries:
		configured_routes.entries.append(
			RouteTable.RouteEntry.new(entry.route_id, entry.scene, true)
		)
	route_table = configured_routes
	return OK


func _report_startup_failure(error: Error, message: String) -> void:
	_started = false
	_startup_error = error
	startup_failed.emit(error, message)
