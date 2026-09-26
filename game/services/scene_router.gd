extends Node

signal transition_started(route_id: StringName)
signal transition_completed(route_id: StringName, route: Node)
signal transition_failed(route_id: StringName, error: Error, message: String)

const RouteTable := preload("res://shared/resources/route_table.gd")

var _route_host: Node
var _route_table: RouteTable
var _current_route: Node
var _current_route_id: StringName = &""
var _transition_in_progress := false
var _host_exit_callback := Callable()


func configure(route_host: Node, route_table: RouteTable) -> Error:
	if _transition_in_progress:
		return ERR_BUSY
	if not is_instance_valid(route_host) or not route_host.is_inside_tree():
		return ERR_INVALID_PARAMETER
	if route_table == null:
		return ERR_INVALID_PARAMETER
	if not route_table.validation_errors().is_empty():
		return ERR_INVALID_DATA

	if _route_host == route_host and _route_table == route_table:
		return OK
	if is_configured():
		return ERR_ALREADY_IN_USE

	_reset_references(true)
	_route_host = route_host
	_route_table = route_table
	_host_exit_callback = Callable(self, "_on_route_host_tree_exiting").bind(route_host)
	if not route_host.tree_exiting.is_connected(_host_exit_callback):
		route_host.tree_exiting.connect(_host_exit_callback)
	return OK


func navigate(route_id: StringName) -> Error:
	if _transition_in_progress:
		return _report_failure(
			route_id,
			ERR_BUSY,
			"A route transition is already in progress.",
		)
	if not is_configured():
		return _report_failure(
			route_id,
			ERR_UNCONFIGURED,
			"SceneRouter must be configured before navigation.",
		)
	if route_id == &"":
		return _report_failure(route_id, ERR_INVALID_PARAMETER, "Route ID is empty.")

	var packed_scene := _route_table.scene_for(route_id)
	if packed_scene == null:
		return _report_failure(
			route_id,
			ERR_DOES_NOT_EXIST,
			"Route ID '%s' is not configured." % route_id,
		)
	if not packed_scene.can_instantiate():
		return _report_failure(
			route_id,
			ERR_CANT_CREATE,
			"Route '%s' cannot be instantiated." % route_id,
		)

	_transition_in_progress = true
	transition_started.emit(route_id)
	if not is_configured():
		_transition_in_progress = false
		return _report_failure(
			route_id,
			ERR_UNCONFIGURED,
			"SceneRouter was cleared during the route transition.",
		)

	var next_route := packed_scene.instantiate()
	if next_route == null:
		_transition_in_progress = false
		return _report_failure(
			route_id,
			ERR_CANT_CREATE,
			"Route '%s' failed to instantiate." % route_id,
		)

	_route_host.add_child(next_route)
	if next_route.get_parent() != _route_host or next_route.is_queued_for_deletion():
		if is_instance_valid(next_route):
			if next_route.get_parent() == _route_host:
				_route_host.remove_child(next_route)
			next_route.queue_free()
		_transition_in_progress = false
		return _report_failure(
			route_id,
			ERR_CANT_CREATE,
			"Route '%s' did not become ready in the route host." % route_id,
		)

	var previous_route := _current_route
	_current_route = next_route
	_current_route_id = route_id
	if is_instance_valid(previous_route):
		if previous_route.get_parent() == _route_host:
			_route_host.remove_child(previous_route)
		previous_route.queue_free()

	_transition_in_progress = false
	transition_completed.emit(route_id, next_route)
	return OK


func unconfigure(route_host: Node) -> Error:
	if _transition_in_progress:
		return ERR_BUSY
	if _route_host != route_host:
		return ERR_INVALID_PARAMETER
	_release_current_route()
	_reset_references(true)
	return OK


func is_configured() -> bool:
	return (
		is_instance_valid(_route_host)
		and _route_host.is_inside_tree()
		and _route_table != null
	)


func has_route(route_id: StringName) -> bool:
	return is_configured() and route_id in _route_table.route_ids()


func get_route_host() -> Node:
	return _route_host if is_instance_valid(_route_host) else null


func get_current_route() -> Node:
	return _current_route if is_instance_valid(_current_route) else null


func get_current_route_id() -> StringName:
	return _current_route_id


func _exit_tree() -> void:
	_reset_references(true)


func _on_route_host_tree_exiting(route_host: Node) -> void:
	if _route_host != route_host:
		return
	_route_host = null
	_route_table = null
	_current_route = null
	_current_route_id = &""
	_transition_in_progress = false
	_host_exit_callback = Callable()


func _release_current_route() -> void:
	if not is_instance_valid(_current_route):
		return
	if is_instance_valid(_route_host) and _current_route.get_parent() == _route_host:
		_route_host.remove_child(_current_route)
	if not _current_route.is_queued_for_deletion():
		_current_route.queue_free()


func _reset_references(disconnect_host: bool) -> void:
	if (
		disconnect_host
		and is_instance_valid(_route_host)
		and _host_exit_callback.is_valid()
		and _route_host.tree_exiting.is_connected(_host_exit_callback)
	):
		_route_host.tree_exiting.disconnect(_host_exit_callback)
	_route_host = null
	_route_table = null
	_current_route = null
	_current_route_id = &""
	_transition_in_progress = false
	_host_exit_callback = Callable()


func _report_failure(route_id: StringName, error: Error, message: String) -> Error:
	transition_failed.emit(route_id, error, message)
	return error
