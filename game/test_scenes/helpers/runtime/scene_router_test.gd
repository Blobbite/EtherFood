extends RefCounted

const ROUTER_SCRIPT := preload("res://services/scene_router.gd")
const ROUTE_ENTRY_SCRIPT := preload("res://shared/resources/route_entry.gd")
const ROUTE_TABLE_SCRIPT := preload("res://shared/resources/route_table.gd")
const NODE_ROUTE := preload("res://test_scenes/helpers/fixtures/routes/neutral_node_route.tscn")
const NODE_2D_ROUTE := preload(
	"res://test_scenes/helpers/fixtures/routes/neutral_node_2d_route.tscn"
)
const CONTROL_ROUTE := preload(
	"res://test_scenes/helpers/fixtures/routes/neutral_control_route.tscn"
)

var failures := PackedStringArray()


func run(tree: SceneTree) -> PackedStringArray:
	_test_route_table_validation()
	await _test_navigation_contract(tree)
	return failures


func _test_route_table_validation() -> void:
	var empty_id_table := ROUTE_TABLE_SCRIPT.new()
	empty_id_table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"", NODE_ROUTE))
	_expect(
		not empty_id_table.validation_errors().is_empty(),
		"RouteTable rejects an empty route ID",
	)

	var duplicate_id_table := ROUTE_TABLE_SCRIPT.new()
	duplicate_id_table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"same", NODE_ROUTE))
	duplicate_id_table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"same", CONTROL_ROUTE))
	_expect(
		not duplicate_id_table.validation_errors().is_empty(),
		"RouteTable rejects duplicate route IDs",
	)

	var missing_scene_table := ROUTE_TABLE_SCRIPT.new()
	missing_scene_table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"missing", null))
	_expect(
		not missing_scene_table.validation_errors().is_empty(),
		"RouteTable rejects a missing PackedScene",
	)

	var valid_table := _make_route_table()
	var ids := valid_table.route_ids()
	ids.clear()
	_expect(
		valid_table.route_ids().size() == 4,
		"RouteTable lookup data is not exposed through route_ids",
	)

	var build_filtered_table := ROUTE_TABLE_SCRIPT.new()
	var public_entry := ROUTE_ENTRY_SCRIPT.new(&"public", NODE_ROUTE)
	var development_entry := ROUTE_ENTRY_SCRIPT.new(&"visual_lab", CONTROL_ROUTE, true)
	build_filtered_table.entries.append(public_entry)
	build_filtered_table.entries.append(development_entry)
	_expect(
		not public_entry.development_only,
		"RouteEntry keeps existing constructor calls public",
	)
	_expect(
		development_entry.development_only,
		"RouteEntry constructor marks development-only routes",
	)
	_expect(
		development_entry.is_available(true),
		"development-only routes are available in debug builds",
	)
	_expect(
		not development_entry.is_available(false),
		"development-only routes are unavailable in release builds",
	)
	_expect(
		build_filtered_table.scene_for_build(&"visual_lab", true) == CONTROL_ROUTE,
		"RouteTable returns visual_lab for debug builds",
	)
	_expect(
		build_filtered_table.scene_for_build(&"visual_lab", false) == null,
		"RouteTable hides visual_lab from release builds",
	)
	_expect(
		build_filtered_table.scene_for_build(&"public", false) == NODE_ROUTE,
		"RouteTable keeps normal routes available in release builds",
	)
	_expect(
		build_filtered_table.route_ids_for_build(true) == [&"public", &"visual_lab"],
		"RouteTable lists development-only routes for debug builds",
	)
	_expect(
		build_filtered_table.route_ids_for_build(false) == [&"public"],
		"RouteTable omits development-only routes from release builds",
	)


func _test_navigation_contract(tree: SceneTree) -> void:
	var router := ROUTER_SCRIPT.new()
	router.name = "SceneRouterUnderTest"
	tree.root.add_child(router)

	var failures_seen: Array[Array] = []
	router.transition_failed.connect(
		func(route_id: StringName, error: Error, message: String) -> void:
			failures_seen.append([route_id, error, message])
	)

	_expect(
		router.navigate(&"node") == ERR_UNCONFIGURED,
		"SceneRouter rejects navigation before configuration",
	)

	var invalid_host := Node.new()
	_expect(
		router.configure(invalid_host, _make_route_table()) == ERR_INVALID_PARAMETER,
		"SceneRouter rejects a route host outside the SceneTree",
	)
	invalid_host.free()

	var host := Node.new()
	host.name = "RouteHostUnderTest"
	tree.root.add_child(host)
	var table := _make_route_table()
	var invalid_table: ROUTE_TABLE_SCRIPT = ROUTE_TABLE_SCRIPT.new()
	invalid_table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"duplicate", NODE_ROUTE))
	invalid_table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"duplicate", CONTROL_ROUTE))
	_expect(
		router.configure(host, invalid_table) == ERR_INVALID_DATA,
		"SceneRouter rejects an invalid RouteTable",
	)
	_expect(router.configure(host, table) == OK, "SceneRouter accepts valid configuration")

	var started_ids: Array[StringName] = []
	var completed_ids: Array[StringName] = []
	router.transition_started.connect(
		func(route_id: StringName) -> void:
			started_ids.append(route_id)
	)
	router.transition_completed.connect(
		func(route_id: StringName, _route: Node) -> void:
			completed_ids.append(route_id)
	)

	_expect(router.navigate(&"node") == OK, "SceneRouter activates a valid Node route")
	var first_route := router.get_current_route()
	_expect(first_route is Node, "active Node route is available")
	_expect(first_route.name == "NeutralNodeRoute", "requested Node fixture is active")
	_expect(host.get_child_count() == 1, "route host contains exactly one active route")

	_expect(
		router.configure(host, table) == OK,
		"repeating identical SceneRouter configuration is safe",
	)
	_expect(
		router.get_current_route() == first_route and host.get_child_count() == 1,
		"repeat configuration preserves the active route",
	)
	_expect(
		router.configure(host, _make_route_table()) == ERR_ALREADY_IN_USE,
		"active configuration cannot be replaced implicitly",
	)
	_expect(
		router.get_current_route() == first_route and host.get_child_count() == 1,
		"rejected reconfiguration preserves the active route",
	)

	var first_exit_count := [0]
	first_route.tree_exiting.connect(
		func() -> void:
			first_exit_count[0] += 1
	)
	var first_route_reference: WeakRef = weakref(first_route)
	_expect(
		router.navigate(&"control") == OK,
		"SceneRouter replaces a route with a Control route",
	)
	var control_route := router.get_current_route()
	_expect(control_route is Control, "Control-first route roots are supported")
	_expect(host.get_child_count() == 1, "previous route leaves the host immediately")
	await tree.process_frame
	_expect(first_route_reference.get_ref() == null, "previous route is freed")
	_expect(first_exit_count[0] == 1, "previous route exits the tree exactly once")

	var active_before_failure := router.get_current_route()
	_expect(
		router.navigate(&"unknown") == ERR_DOES_NOT_EXIST,
		"SceneRouter rejects an unknown route ID",
	)
	_expect(
		router.get_current_route() == active_before_failure,
		"unknown route leaves the active route intact",
	)
	_expect(
		router.navigate(&"invalid_scene") == ERR_CANT_CREATE,
		"SceneRouter rejects an uninstantiable PackedScene",
	)
	_expect(
		router.get_current_route() == active_before_failure,
		"failed instantiation leaves the active route intact",
	)

	var nested_results: Array[int] = []
	var nested_unconfigure_results: Array[int] = []
	router.transition_started.connect(
		func(route_id: StringName) -> void:
			if route_id == &"node_2d":
				nested_unconfigure_results.append(router.unconfigure(host))
				nested_results.append(router.navigate(&"node"))
	)
	_expect(
		router.navigate(&"node_2d") == OK,
		"SceneRouter activates a valid Node2D route",
	)
	_expect(router.get_current_route() is Node2D, "Node2D-first route roots are supported")
	_expect(
		nested_results == [ERR_BUSY],
		"re-entrant navigation is rejected deterministically",
	)
	_expect(
		nested_unconfigure_results == [ERR_BUSY],
		"configuration cannot be cleared during a transition",
	)
	_expect(
		started_ids == [&"node", &"control", &"node_2d"],
		"transition_started is emitted for each accepted request",
	)
	_expect(
		completed_ids == [&"node", &"control", &"node_2d"],
		"transition_completed is emitted for each successful request",
	)
	_expect(failures_seen.size() >= 4, "failed requests emit transition_failed")

	var route_before_unconfigure := router.get_current_route()
	var unconfigured_route_exit_count := [0]
	route_before_unconfigure.tree_exiting.connect(
		func() -> void:
			unconfigured_route_exit_count[0] += 1
	)
	var unconfigured_route_reference: WeakRef = weakref(route_before_unconfigure)
	_expect(router.unconfigure(host) == OK, "configured host can unconfigure SceneRouter")
	_expect(host.get_child_count() == 0, "unconfigure removes the active route from a live host")
	_expect(not router.is_configured(), "unconfigure clears the router host")
	_expect(router.get_route_host() == null, "unconfigure releases the host reference")
	_expect(router.get_current_route() == null, "unconfigure releases the route reference")
	_expect(router.get_current_route_id() == &"", "unconfigure clears the route ID")

	_expect(
		router.configure(host, _make_route_table()) == OK,
		"SceneRouter can reuse the same live host after teardown",
	)
	_expect(router.navigate(&"node") == OK, "reconfigured SceneRouter can navigate")
	_expect(host.get_child_count() == 1, "reused host contains only the new active route")
	await tree.process_frame
	_expect(unconfigured_route_reference.get_ref() == null, "unconfigured route is freed")
	_expect(
		unconfigured_route_exit_count[0] == 1,
		"unconfigured route exits the tree exactly once",
	)

	host.queue_free()
	await tree.process_frame
	_expect(
		not router.is_configured() and router.get_current_route() == null,
		"route-host exit clears application-owned references",
	)

	router.queue_free()
	await tree.process_frame


func _make_route_table() -> ROUTE_TABLE_SCRIPT:
	var table: ROUTE_TABLE_SCRIPT = ROUTE_TABLE_SCRIPT.new()
	table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"node", NODE_ROUTE))
	table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"node_2d", NODE_2D_ROUTE))
	table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"control", CONTROL_ROUTE))
	table.entries.append(ROUTE_ENTRY_SCRIPT.new(&"invalid_scene", PackedScene.new()))
	return table


func _expect(condition: bool, description: String) -> void:
	if not condition:
		failures.append("SceneRouter: %s" % description)
