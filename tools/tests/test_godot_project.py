"""Static consistency tests for the Godot project boundary."""

from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GODOT_ROOT = REPOSITORY_ROOT / "game"


class GodotProjectTests(unittest.TestCase):
    def test_display_uses_reviewed_16_9_reference_contract(self) -> None:
        project = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        expected_settings = (
            "window/size/viewport_width=1920",
            "window/size/viewport_height=1080",
            "window/size/window_width_override=1280",
            "window/size/window_height_override=720",
            "window/size/resizable=true",
            'window/stretch/mode="canvas_items"',
            'window/stretch/aspect="keep"',
        )

        self.assertIn("\n[display]\n", project)
        for setting in expected_settings:
            with self.subTest(setting=setting):
                self.assertIn(setting, project)

    def test_input_map_defines_semantic_actions_and_reviewed_deadzones(self) -> None:
        project = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        actions = {
            "ui_up": 0.5,
            "ui_down": 0.5,
            "ui_left": 0.5,
            "ui_right": 0.5,
            "ui_accept": 0.5,
            "ui_cancel": 0.5,
            "gameplay_move_up": 0.2,
            "gameplay_move_down": 0.2,
            "gameplay_move_left": 0.2,
            "gameplay_move_right": 0.2,
            "app_pause": 0.5,
        }

        self.assertIn("\n[input]\n", project)
        for action, deadzone in actions.items():
            with self.subTest(action=action):
                body = self._input_action(project, action)
                self.assertIn(f'"deadzone": {deadzone}', body)
                self.assertIn("InputEventKey", body)
                self.assertIn("InputEventJoypadButton", body)
                events = re.findall(r"Object\(InputEvent[^)]+\)", body)
                self.assertTrue(events)
                self.assertTrue(
                    all('"device":-1' in event for event in events),
                    f"{action} must accept any matching input device",
                )

    def test_direction_actions_map_keyboard_dpad_and_left_stick(self) -> None:
        project = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        mappings = {
            "gameplay_move_up": (87, 4194320, 11, 1, -1.0),
            "gameplay_move_down": (83, 4194322, 12, 1, 1.0),
            "gameplay_move_left": (65, 4194319, 13, 0, -1.0),
            "gameplay_move_right": (68, 4194321, 14, 0, 1.0),
        }

        for action, mapping in mappings.items():
            physical_key, arrow_key, button, axis, axis_value = mapping
            with self.subTest(action=action):
                body = self._input_action(project, action)
                self.assertIn(f'"physical_keycode":{physical_key}', body)
                self.assertIn(f'"keycode":{arrow_key}', body)
                self.assertIn(f'"button_index":{button}', body)
                self.assertIn(
                    f'"axis":{axis},"axis_value":{axis_value}',
                    body,
                )

        ui_actions = ("ui_up", "ui_down", "ui_left", "ui_right")
        for action in ui_actions:
            with self.subTest(action=action):
                body = self._input_action(project, action)
                self.assertIn("InputEventKey", body)
                self.assertIn("InputEventJoypadButton", body)
                self.assertIn("InputEventJoypadMotion", body)

    def test_accept_cancel_and_pause_have_keyboard_and_controller_bindings(self) -> None:
        project = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        expected = {
            "ui_accept": ('"keycode":4194309', '"keycode":32', '"button_index":0'),
            "ui_cancel": ('"keycode":4194305', '"button_index":1'),
            "app_pause": (
                '"keycode":4194305',
                '"physical_keycode":80',
                '"button_index":6',
            ),
        }

        for action, fragments in expected.items():
            with self.subTest(action=action):
                body = self._input_action(project, action)
                for fragment in fragments:
                    self.assertIn(fragment, body)

    def test_movement_actions_have_reviewed_keyboard_bindings(self) -> None:
        project = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        mappings = {
            "gameplay_jump": ('"keycode":32', '"location":0'),
            "gameplay_sneak": ('"physical_keycode":4194326',),
            "gameplay_sprint": ('"physical_keycode":4194325',),
            "gameplay_walk_toggle": ('"physical_keycode":4194329',),
        }

        for action, fragments in mappings.items():
            with self.subTest(action=action):
                body = self._input_action(project, action)
                self.assertIn('"deadzone": 0.5', body)
                for fragment in fragments:
                    self.assertIn(fragment, body)
                self.assertNotIn("InputEventJoypad", body)

        for action in ("gameplay_sneak", "gameplay_sprint"):
            with self.subTest(action=action):
                body = self._input_action(project, action)
                self.assertEqual(body.count("InputEventKey"), 2)
                self.assertIn('"location":1', body)
                self.assertIn('"location":2', body)

    def test_visual_lab_uses_menu_and_keeps_reviewed_global_shortcuts(self) -> None:
        project = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        retained_mappings = {
            "dev_diagnostics_toggle": 4194342,
            "dev_performance_toggle": 4194343,
            "dev_collision_debug_toggle": 4194335,
            "dev_controls_toggle": 4194336,
        }

        for action, keycode in retained_mappings.items():
            with self.subTest(action=action):
                body = self._input_action(project, action)
                self.assertIn('"deadzone": 0.5', body)
                self.assertIn(f'"keycode":{keycode}', body)

        accept_body = self._input_action(project, "dev_accept_visual_standard")
        self.assertIn('"physical_keycode":69', accept_body)
        self.assertIn('"alt_pressed":true', accept_body)
        self.assertIn('"ctrl_pressed":true', accept_body)

        removed_actions = (
            "dev_camera_zoom_out",
            "dev_camera_zoom_in",
            "dev_hero_size_decrease",
            "dev_hero_size_increase",
            "dev_tile_size_decrease",
            "dev_tile_size_increase",
            "dev_world_state_toggle",
            "dev_fog_variant_cycle",
            "dev_light_variant_cycle",
            "dev_pixel_snap_toggle",
            "dev_texture_filter_toggle",
        )
        for action in removed_actions:
            with self.subTest(action=action):
                self.assertNotRegex(project, rf"(?m)^{re.escape(action)}=\{{")

    def test_visual_lab_tools_stay_compact_transparent_and_non_blocking(self) -> None:
        scene = (GODOT_ROOT / "scenes" / "dev" / "visual_lab.tscn").read_text(
            encoding="utf-8"
        )
        menu_scene = (
            GODOT_ROOT / "scenes" / "dev" / "visual_lab_menu.tscn"
        ).read_text(encoding="utf-8")
        script = (GODOT_ROOT / "scenes" / "dev" / "visual_lab.gd").read_text(
            encoding="utf-8"
        )

        hud = self._scene_node(scene, "HudPanel", "InterfaceLayer")
        self.assertIn("offset_right = 636.0", hud)
        self.assertIn("offset_bottom = 716.0", hud)
        self.assertNotIn("anchor_right = 1.0", hud)
        interface = self._scene_node(scene, "Interface", "InterfaceLayer")
        self.assertIn("offset_left = 26.0", interface)
        self.assertIn("offset_right = 626.0", interface)
        self.assertIn("offset_bottom = 708.0", interface)

        diagnostics = self._scene_node(scene, "DiagnosticsPanel", "InterfaceLayer")
        self.assertIn("offset_left = -466.0", diagnostics)
        self.assertIn("offset_bottom = 636.0", diagnostics)
        self.assertNotIn("StyleBoxFlat_diagnostics_panel", scene)
        for overlay in ("DiagnosticsPanel", "PerformancePanel"):
            with self.subTest(overlay=overlay):
                self.assertIn(
                    f'[node name="{overlay}" type="Control" parent="InterfaceLayer"]',
                    scene,
                )
                body = self._scene_node(scene, overlay, "InterfaceLayer")
                self.assertIn("visible = false", body)
                self.assertIn("mouse_filter = 2", body)
                self.assertNotIn("theme_override_styles/panel", body)
        self.assertIn(
            '[node name="ThemeTabs" type="GridContainer" parent="Menu"]',
            menu_scene,
        )
        self.assertIn("offset_right = 600.0", menu_scene)
        self.assertIn("offset_bottom = 684.0", menu_scene)
        self.assertNotIn(
            "hero_character.set_movement_enabled(not controls_visible)", script
        )

    def test_touch_adapter_uses_only_semantic_action_boundaries(self) -> None:
        adapter = (
            GODOT_ROOT / "shared" / "input" / "touch_action_adapter.gd"
        ).read_text(encoding="utf-8")

        self.assertIn("InputMap.has_action(action)", adapter)
        self.assertIn("Input.action_press(action, normalized_strength)", adapter)
        self.assertIn("Input.action_release(action)", adapter)
        self.assertIn("func _exit_tree() -> void:", adapter)
        for forbidden in ("InputEvent", "Vector2", "func _input(", "event.position"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, adapter)

    def test_reviewed_export_presets_cover_all_desktop_targets(self) -> None:
        presets = (GODOT_ROOT / "export_presets.cfg").read_text(encoding="utf-8")
        expected = (
            (
                "Linux",
                "Linux",
                "../artifacts/exports/linux/Forge2D-Template.x86_64",
            ),
            (
                "Windows",
                "Windows Desktop",
                "../artifacts/exports/windows/Forge2D-Template.exe",
            ),
            (
                "macOS",
                "macOS",
                "../artifacts/exports/macos/Forge2D-Template.zip",
            ),
        )

        self.assertEqual(presets.count("[preset."), 6)
        for name, platform, output in expected:
            with self.subTest(name=name):
                self.assertIn(f'name="{name}"', presets)
                self.assertIn(f'platform="{platform}"', presets)
                self.assertIn(f'export_path="{output}"', presets)

    def test_export_presets_keep_credentials_and_machine_paths_out_of_git(self) -> None:
        presets = (GODOT_ROOT / "export_presets.cfg").read_text(encoding="utf-8")
        forbidden = (
            "codesign/identity=",
            "codesign/password=",
            "codesign/certificate_file=",
            "codesign/certificate_password=",
            "codesign/apple_team_id=",
            "notarization/apple_id_name=",
            "notarization/apple_id_password=",
            "notarization/api_key=",
        )

        for setting in forbidden:
            self.assertNotIn(setting, presets)
        self.assertNotRegex(presets, r'export_path="(?:/|[A-Za-z]:[\\/])')
        self.assertEqual(presets.count('custom_template/release=""'), 3)
        self.assertIn("codesign/enable=false", presets)
        self.assertIn("codesign/codesign=1", presets)
        self.assertIn("notarization/notarization=0", presets)

    def test_universal_macos_export_has_required_texture_format(self) -> None:
        project = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        presets = (GODOT_ROOT / "export_presets.cfg").read_text(encoding="utf-8")

        self.assertIn('binary_format/architecture="universal"', presets)
        self.assertIn(
            "textures/vram_compression/import_etc2_astc=true",
            project,
        )

    def test_generated_export_root_is_ignored(self) -> None:
        ignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("\n/artifacts/\n", ignore)

    def test_every_gdscript_has_a_unique_versioned_uid(self) -> None:
        scripts = sorted(GODOT_ROOT.rglob("*.gd"))
        uid_values: list[str] = []

        for script in scripts:
            sidecar = script.with_suffix(".gd.uid")
            with self.subTest(script=script.relative_to(GODOT_ROOT)):
                self.assertTrue(sidecar.is_file())
                value = sidecar.read_text(encoding="utf-8").strip()
                self.assertRegex(value, r"^uid://[a-z0-9]+$")
                uid_values.append(value)
        self.assertEqual(len(uid_values), len(set(uid_values)))

    def test_project_has_existing_main_scene(self) -> None:
        project_text = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        match = re.search(r'run/main_scene="res://([^\"]+)"', project_text)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertTrue((GODOT_ROOT / match.group(1)).is_file())

    def test_bootstrap_scene_references_existing_script(self) -> None:
        scene_text = (GODOT_ROOT / "scenes" / "bootstrap.tscn").read_text(
            encoding="utf-8"
        )
        match = re.search(r'path="res://([^\"]+\.gd)"', scene_text)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertTrue((GODOT_ROOT / match.group(1)).is_file())
        self.assertNotIn("res://addons/", scene_text)

    def test_bootstrap_composes_the_application_root(self) -> None:
        scene_text = (GODOT_ROOT / "scenes" / "bootstrap.tscn").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'path="res://scenes/app/application_root.tscn"', scene_text
        )
        self.assertIn("application_root_scene = ExtResource", scene_text)
        self.assertNotIn('[node name="Background"', scene_text)

    def test_application_root_has_the_minimal_composition_nodes(self) -> None:
        scene = GODOT_ROOT / "scenes" / "app" / "application_root.tscn"
        self.assertTrue(scene.is_file())
        scene_text = scene.read_text(encoding="utf-8")

        self.assertIn('[node name="ApplicationRoot" type="Node"]', scene_text)
        self.assertEqual(scene_text.count('[node name="RouteHost"'), 1)
        self.assertEqual(scene_text.count('[node name="PersistentUI"'), 1)
        self.assertEqual(scene_text.count('[node name="TransitionLayer"'), 1)
        self.assertIn('initial_route_id = &"title"', scene_text)
        self.assertIn('path="res://scenes/menu/title_screen.tscn"', scene_text)
        self.assertIn('path="res://scenes/menu/main_menu.tscn"', scene_text)
        self.assertNotIn("template_home", scene_text)

    def test_scene_router_is_the_only_autoload(self) -> None:
        project_text = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
        section = re.search(
            r"(?ms)^\[autoload\]\s*$\n(?P<body>.*?)(?=^\[[^]]+\]\s*$|\Z)",
            project_text,
        )

        self.assertIsNotNone(section)
        assert section is not None
        entries = re.findall(
            r'(?m)^([A-Za-z_][A-Za-z0-9_]*)="\*(res://[^"]+)"$',
            section.group("body"),
        )
        self.assertEqual(
            entries,
            [("SceneRouter", "res://services/scene_router.gd")],
        )
        self.assertTrue((GODOT_ROOT / "services" / "scene_router.gd").is_file())

    def test_route_resources_and_initial_menu_routes_exist(self) -> None:
        required = (
            GODOT_ROOT / "shared" / "resources" / "route_entry.gd",
            GODOT_ROOT / "shared" / "resources" / "route_table.gd",
            GODOT_ROOT / "scenes" / "menu" / "title_screen.gd",
            GODOT_ROOT / "scenes" / "menu" / "title_screen.tscn",
            GODOT_ROOT / "scenes" / "menu" / "main_menu.tscn",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        self.assertFalse(
            (GODOT_ROOT / "scenes" / "app" / "template_home.tscn").exists()
        )

    def test_bootstrap_scene_uses_the_production_bootstrap_script(self) -> None:
        script_text = (GODOT_ROOT / "src" / "bootstrap.gd").read_text(
            encoding="utf-8"
        )

        self.assertIn("class_name Forge2DTemplateBootstrap", script_text)
        self.assertIn("signal composition_failed(error: Error, message: String)", script_text)
        self.assertIn("if application_root_scene == null:", script_text)
        self.assertIn("push_error", script_text)
        self.assertIn("composition_failed.emit(error, message)", script_text)
        self.assertNotIn("get_tree().quit", script_text)

    def test_bootstrap_has_a_dedicated_integration_test_runner(self) -> None:
        runner = GODOT_ROOT / "tests" / "bootstrap_integration_test.gd"
        self.assertTrue(runner.is_file())
        runner_text = runner.read_text(encoding="utf-8")
        self.assertIn('ProjectSettings.get_setting("application/run/main_scene"', runner_text)
        self.assertIn("bootstrap.get_script()", runner_text)
        self.assertIn("bootstrap.get_node_or_null", runner_text)
        self.assertNotIn("Forge2DTemplateBootstrap", runner_text)
        self.assertIn("res://tests/runtime/scene_router_test.gd", runner_text)
        self.assertIn("res://tests/runtime/application_root_test.gd", runner_text)
        self.assertIn("res://tests/runtime/input_map_test.gd", runner_text)
        self.assertIn("res://tests/runtime/hero_movement_v0_test.gd", runner_text)
        self.assertIn("res://tests/runtime/visual_lab_atmosphere_test.gd", runner_text)
        self.assertIn("res://tests/runtime/touch_action_adapter_test.gd", runner_text)
        self.assertIn("ApplicationRoot/RouteHost/TitleScreen", runner_text)
        self.assertIn('scene_router.get_current_route_id() == &"main_menu"', runner_text)
        self.assertIn("EtherFood bootstrap integration test: passed", runner_text)
        self.assertIn("quit(1)", runner_text)

    def _input_action(self, project: str, action: str) -> str:
        match = re.search(
            rf"(?ms)^{re.escape(action)}=\{{\n(?P<body>.*?)^\}}$",
            project,
        )
        self.assertIsNotNone(match, f"InputMap action is missing: {action}")
        assert match is not None
        return match.group("body")

    def _scene_node(self, scene: str, name: str, parent: str) -> str:
        match = re.search(
            rf'(?ms)^\[node name="{re.escape(name)}"[^]]*'
            rf'parent="{re.escape(parent)}"[^]]*\]\n'
            r"(?P<body>.*?)(?=^\[node |\Z)",
            scene,
        )
        self.assertIsNotNone(match, f"Scene node is missing: {parent}/{name}")
        assert match is not None
        return match.group("body")


if __name__ == "__main__":
    unittest.main()
