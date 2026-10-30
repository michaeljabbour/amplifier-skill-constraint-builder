"""Structural validation tests for amplifier-bundle-autoharness.

Validates:
- bundle.md exists with valid YAML frontmatter
- behaviors/harness-machine.yaml exists with correct config
- All 8 mode files exist with correct structure
- All 11 agent files exist with correct structure
- All 6 recipe files exist and parse as valid YAML
- The canonical skill has SKILL.md and the three legacy reference guides remain
- Context files exist
- Template files exist
- Required directories exist
- All YAML files parse without errors
"""

import os

import pytest
import yaml

BUNDLE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_file(rel_path):
    """Read a file relative to bundle root."""
    full_path = os.path.join(BUNDLE_ROOT, rel_path)
    with open(full_path) as f:
        return f.read()


def read_frontmatter(filepath):
    """Extract YAML frontmatter from a markdown file."""
    with open(filepath) as f:
        content = f.read()
    if not content.startswith("---"):
        return None
    end = content.index("---", 3)
    return yaml.safe_load(content[3:end])


def _parse_frontmatter(content):
    """Extract and parse YAML frontmatter from markdown content."""
    parts = content.split("---")
    assert len(parts) >= 3, "File must have YAML frontmatter delimited by ---"
    return yaml.safe_load(parts[1])


# ---------------------------------------------------------------------------
# bundle.md tests
# ---------------------------------------------------------------------------


class TestBundleMd:
    def test_bundle_md_exists(self):
        assert os.path.isfile(os.path.join(BUNDLE_ROOT, "bundle.md"))

    def test_bundle_frontmatter_parses(self):
        fm = _parse_frontmatter(_read_file("bundle.md"))
        assert fm is not None
        assert isinstance(fm, dict)

    def test_bundle_name(self):
        fm = _parse_frontmatter(_read_file("bundle.md"))
        assert fm["bundle"]["name"] == "harness-machine"

    def test_bundle_version_exists(self):
        fm = _parse_frontmatter(_read_file("bundle.md"))
        assert "version" in fm["bundle"]
        assert fm["bundle"]["version"]

    def test_agents_include_has_eleven_entries(self):
        # bundle.md uses the thin bundle pattern — agents are registered in
        # behaviors/harness-machine.yaml, not duplicated in bundle.md.
        # This test verifies behaviors/harness-machine.yaml has all 11.
        import pathlib

        behavior_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "behaviors",
            "harness-machine.yaml",
        )
        import yaml as _yaml

        behavior = _yaml.safe_load(pathlib.Path(behavior_path).read_text())
        agents = behavior["agents"]["include"]
        assert len(agents) == 11

    def test_agents_include_contains_all_eleven_agents(self):
        # bundle.md uses the thin bundle pattern — agents are registered in
        # behaviors/harness-machine.yaml, not duplicated in bundle.md.
        # This test verifies behaviors/harness-machine.yaml has all 11.
        import pathlib

        behavior_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "behaviors",
            "harness-machine.yaml",
        )
        import yaml as _yaml

        behavior = _yaml.safe_load(pathlib.Path(behavior_path).read_text())
        agent_names = [entry.split(":")[-1] for entry in behavior["agents"]["include"]]
        for name in [
            "environment-analyst",
            "mission-architect",
            "capability-advisor",
            "spec-writer",
            "plan-writer",
            "harness-generator",
            "harness-critic",
            "harness-refiner",
            "harness-evaluator",
            "upgrade-checker",
            "upgrade-planner",
        ]:
            assert name in agent_names, (
                f"Agent {name!r} not found in behavior agents.include"
            )

    def test_includes_has_two_entries(self):
        fm = _parse_frontmatter(_read_file("bundle.md"))
        includes = fm["includes"]
        assert len(includes) == 2

    def test_includes_contains_foundation(self):
        fm = _parse_frontmatter(_read_file("bundle.md"))
        includes_str = str(fm["includes"])
        assert "foundation" in includes_str.lower()

    def test_body_mentions_all_seven_modes(self):
        content = _read_file("bundle.md")
        body = content.split("---", 2)[2]
        for mode in [
            "harness-explore",
            "harness-spec",
            "harness-plan",
            "harness-execute",
            "harness-verify",
            "harness-finish",
            "harness-debug",
        ]:
            assert mode in body, f"Mode {mode!r} not mentioned in bundle.md body"

    def test_body_mentions_foundation_context(self):
        content = _read_file("bundle.md")
        body = content.split("---", 2)[2]
        assert "@foundation:context/" in body


# ---------------------------------------------------------------------------
# behaviors/harness-machine.yaml tests
# ---------------------------------------------------------------------------


class TestBehaviorYaml:
    def test_behavior_file_exists(self):
        assert os.path.isfile(
            os.path.join(BUNDLE_ROOT, "behaviors", "harness-machine.yaml")
        )

    def test_behavior_yaml_parses(self):
        content = _read_file("behaviors/harness-machine.yaml")
        data = yaml.safe_load(content)
        assert data is not None
        assert isinstance(data, dict)

    def test_behavior_yaml_has_bundle_key(self):
        data = yaml.safe_load(_read_file("behaviors/harness-machine.yaml"))
        assert "bundle" in data

    def test_hooks_mode_configured(self):
        data = yaml.safe_load(_read_file("behaviors/harness-machine.yaml"))
        hooks = data.get("hooks", [])
        hook_modules = [h["module"] for h in hooks]
        assert "hooks-mode" in hook_modules

    def test_hooks_mode_search_paths_contain_harness_machine_modes(self):
        data = yaml.safe_load(_read_file("behaviors/harness-machine.yaml"))
        hooks = data.get("hooks", [])
        hooks_mode = [h for h in hooks if h["module"] == "hooks-mode"][0]
        search_paths = hooks_mode["config"]["search_paths"]
        assert any("@harness-machine:modes" in p for p in search_paths)

    def test_tool_mode_gate_policy_warn(self):
        data = yaml.safe_load(_read_file("behaviors/harness-machine.yaml"))
        tools = data.get("tools", [])
        tool_mode = [t for t in tools if t["module"] == "tool-mode"][0]
        assert tool_mode["config"]["gate_policy"] == "warn"

    def test_tool_skills_configured(self):
        data = yaml.safe_load(_read_file("behaviors/harness-machine.yaml"))
        tools = data.get("tools", [])
        tool_modules = [t["module"] for t in tools]
        assert "tool-skills" in tool_modules

    def test_agents_include_has_eleven_entries(self):
        data = yaml.safe_load(_read_file("behaviors/harness-machine.yaml"))
        agents = data["agents"]["include"]
        assert len(agents) == 11

    def test_context_include_has_entries(self):
        data = yaml.safe_load(_read_file("behaviors/harness-machine.yaml"))
        context_includes = data["context"]["include"]
        assert len(context_includes) >= 1


# ---------------------------------------------------------------------------
# Mode file tests
# ---------------------------------------------------------------------------

ALL_MODES = [  # 8 modes
    "harness-explore",
    "harness-spec",
    "harness-plan",
    "harness-execute",
    "harness-verify",
    "harness-finish",
    "harness-debug",
    "harness-upgrade",
]

FINISH_MODE = "harness-finish"


class TestModes:
    @pytest.mark.parametrize("mode_name", ALL_MODES)
    def test_mode_file_exists(self, mode_name):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{mode_name}.md")
        assert os.path.isfile(path), f"Mode file modes/{mode_name}.md does not exist"

    @pytest.mark.parametrize("mode_name", ALL_MODES)
    def test_mode_has_frontmatter(self, mode_name):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{mode_name}.md")
        fm = read_frontmatter(path)
        assert fm is not None, f"modes/{mode_name}.md has no YAML frontmatter"
        assert isinstance(fm, dict)

    @pytest.mark.parametrize("mode_name", ALL_MODES)
    def test_mode_name_matches_filename(self, mode_name):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{mode_name}.md")
        fm = read_frontmatter(path)
        assert fm["mode"]["name"] == mode_name

    @pytest.mark.parametrize("mode_name", ALL_MODES)
    def test_mode_tools_safe_is_list(self, mode_name):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{mode_name}.md")
        fm = read_frontmatter(path)
        assert isinstance(fm["mode"]["tools"]["safe"], list)

    @pytest.mark.parametrize("mode_name", ALL_MODES)
    def test_mode_allowed_transitions_is_list(self, mode_name):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{mode_name}.md")
        fm = read_frontmatter(path)
        assert isinstance(fm["mode"]["allowed_transitions"], list)

    @pytest.mark.parametrize("mode_name", ALL_MODES)
    def test_mode_default_action_exists(self, mode_name):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{mode_name}.md")
        fm = read_frontmatter(path)
        assert "default_action" in fm["mode"]
        assert fm["mode"]["default_action"]

    def test_harness_finish_allow_clear_true(self):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{FINISH_MODE}.md")
        fm = read_frontmatter(path)
        assert fm["mode"]["allow_clear"] is True

    @pytest.mark.parametrize("mode_name", [m for m in ALL_MODES if m != FINISH_MODE])
    def test_non_finish_modes_allow_clear_false(self, mode_name):
        path = os.path.join(BUNDLE_ROOT, "modes", f"{mode_name}.md")
        fm = read_frontmatter(path)
        assert fm["mode"]["allow_clear"] is False, (
            f"modes/{mode_name}.md should have allow_clear: false"
        )


# ---------------------------------------------------------------------------
# Agent file tests
# ---------------------------------------------------------------------------

ALL_AGENTS = [  # 11 agents
    "environment-analyst",
    "mission-architect",
    "capability-advisor",
    "spec-writer",
    "plan-writer",
    "harness-generator",
    "harness-critic",
    "harness-refiner",
    "harness-evaluator",
    "upgrade-checker",
    "upgrade-planner",
]


class TestAgents:
    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    def test_agent_file_exists(self, agent_name):
        path = os.path.join(BUNDLE_ROOT, "agents", f"{agent_name}.md")
        assert os.path.isfile(path), f"Agent file agents/{agent_name}.md does not exist"

    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    def test_agent_has_frontmatter(self, agent_name):
        path = os.path.join(BUNDLE_ROOT, "agents", f"{agent_name}.md")
        fm = read_frontmatter(path)
        assert fm is not None, f"agents/{agent_name}.md has no YAML frontmatter"
        assert isinstance(fm, dict)

    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    def test_agent_name_matches_filename(self, agent_name):
        path = os.path.join(BUNDLE_ROOT, "agents", f"{agent_name}.md")
        fm = read_frontmatter(path)
        assert fm["meta"]["name"] == agent_name

    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    def test_agent_description_is_non_empty_string(self, agent_name):
        path = os.path.join(BUNDLE_ROOT, "agents", f"{agent_name}.md")
        fm = read_frontmatter(path)
        desc = fm["meta"]["description"]
        assert isinstance(desc, str)
        assert len(desc.strip()) > 0, f"agents/{agent_name}.md has empty description"


# ---------------------------------------------------------------------------
# Recipe file tests
# ---------------------------------------------------------------------------

ALL_RECIPES = [  # 6 recipes
    "harness-single-iteration",
    "harness-refinement-loop",
    "harness-development-cycle",
    "harness-factory-generation",
    "check-upgrade",
    "execute-upgrade",
]


class TestRecipes:
    @pytest.mark.parametrize("recipe_name", ALL_RECIPES)
    def test_recipe_file_exists(self, recipe_name):
        path = os.path.join(BUNDLE_ROOT, "recipes", f"{recipe_name}.yaml")
        assert os.path.isfile(path), (
            f"Recipe file recipes/{recipe_name}.yaml does not exist"
        )

    @pytest.mark.parametrize("recipe_name", ALL_RECIPES)
    def test_recipe_parses_as_valid_yaml_dict(self, recipe_name):
        path = os.path.join(BUNDLE_ROOT, "recipes", f"{recipe_name}.yaml")
        with open(path) as f:
            data = yaml.safe_load(f.read())
        assert isinstance(data, dict), (
            f"recipes/{recipe_name}.yaml did not parse as a dict"
        )


# ---------------------------------------------------------------------------
# Skills tests
# ---------------------------------------------------------------------------

ALL_SKILLS = [
    "constraint-builder",
]


class TestSkills:
    @pytest.mark.parametrize("reference", ["harness-reference", "constraint-design", "convergence-debugging"])
    def test_legacy_reference_guide_is_preserved(self, reference):
        path = os.path.join(BUNDLE_ROOT, "skills", reference, "REFERENCE.md")
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 0

    @pytest.mark.parametrize("skill_name", ALL_SKILLS)
    def test_skill_directory_exists(self, skill_name):
        path = os.path.join(BUNDLE_ROOT, "skills", skill_name)
        assert os.path.isdir(path), (
            f"Skill directory skills/{skill_name}/ does not exist"
        )

    @pytest.mark.parametrize("skill_name", ALL_SKILLS)
    def test_skill_has_skill_md(self, skill_name):
        path = os.path.join(BUNDLE_ROOT, "skills", skill_name, "SKILL.md")
        assert os.path.isfile(path), f"skills/{skill_name}/SKILL.md does not exist"


# ---------------------------------------------------------------------------
# Context file tests
# ---------------------------------------------------------------------------

CONTEXT_FILES = [
    "instructions.md",
    "philosophy.md",
    "pattern.md",
    "harness-format.md",
    "templates-reference.md",
    "constraint-spec-template.md",
]


class TestContextFiles:
    @pytest.mark.parametrize("filename", CONTEXT_FILES)
    def test_context_file_exists(self, filename):
        path = os.path.join(BUNDLE_ROOT, "context", filename)
        assert os.path.isfile(path), f"context/{filename} does not exist"

    def test_six_example_files_exist(self):
        examples_dir = os.path.join(BUNDLE_ROOT, "context", "examples")
        examples = [
            f
            for f in os.listdir(examples_dir)
            if os.path.isfile(os.path.join(examples_dir, f))
        ]
        assert len(examples) == 6, (
            f"Expected 6 example files in context/examples/, found {len(examples)}: {examples}"
        )

    def test_tier_specific_examples_exist(self):
        examples_dir = os.path.join(BUNDLE_ROOT, "context", "examples")
        for filename in [
            "pico-filesystem-sandbox.md",
            "nano-tumor-genome-to-vaccine.md",
            "micro-k8s-platform-engineer.md",
        ]:
            path = os.path.join(examples_dir, filename)
            assert os.path.isfile(path), (
                f"Tier-specific example context/examples/{filename} does not exist"
            )


# ---------------------------------------------------------------------------
# Template file tests
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_state_yaml_exists(self):
        assert os.path.isfile(os.path.join(BUNDLE_ROOT, "templates", "STATE.yaml"))

    def test_context_transfer_md_exists(self):
        assert os.path.isfile(
            os.path.join(BUNDLE_ROOT, "templates", "CONTEXT-TRANSFER.md")
        )

    def test_scratch_md_exists(self):
        assert os.path.isfile(os.path.join(BUNDLE_ROOT, "templates", "SCRATCH.md"))

    def test_two_recipe_templates_exist(self):
        recipes_dir = os.path.join(BUNDLE_ROOT, "templates", "recipes")
        recipe_files = [
            f
            for f in os.listdir(recipes_dir)
            if os.path.isfile(os.path.join(recipes_dir, f)) and f.endswith(".yaml")
        ]
        assert len(recipe_files) == 2, (
            f"Expected 2 recipe templates, found {len(recipe_files)}: {recipe_files}"
        )

    def test_dockerfile_exists(self):
        path = os.path.join(BUNDLE_ROOT, "templates", "harness-machine.Dockerfile")
        assert os.path.isfile(path)

    def test_docker_compose_exists(self):
        path = os.path.join(
            BUNDLE_ROOT, "templates", "docker-compose.harness-machine.yaml"
        )
        assert os.path.isfile(path)

    def test_three_scripts_exist(self):
        scripts_dir = os.path.join(BUNDLE_ROOT, "templates", "scripts")
        expected = {
            "entrypoint.sh",
            "harness-machine-watchdog.sh",
            "harness-machine-monitor.sh",
        }
        actual = {
            f
            for f in os.listdir(scripts_dir)
            if os.path.isfile(os.path.join(scripts_dir, f))
        }
        for script in expected:
            assert script in actual, f"templates/scripts/{script} does not exist"


# ---------------------------------------------------------------------------
# Directory structure tests
# ---------------------------------------------------------------------------

ALL_DIRECTORIES = [
    "agents",
    "modes",
    "context",
    os.path.join("context", "examples"),
    "skills",
    "recipes",
    "templates",
    os.path.join("templates", "recipes"),
    os.path.join("templates", "scripts"),
    "behaviors",
]


class TestDirectories:
    @pytest.mark.parametrize("dirname", ALL_DIRECTORIES)
    def test_directory_exists(self, dirname):
        full_path = os.path.join(BUNDLE_ROOT, dirname)
        assert os.path.isdir(full_path), f"Directory {dirname}/ does not exist"


# ---------------------------------------------------------------------------
# YAML validity tests
# ---------------------------------------------------------------------------


class TestYamlValidity:
    def test_behavior_yaml_valid_dict_with_bundle_key(self):
        content = _read_file("behaviors/harness-machine.yaml")
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "bundle" in data

    def test_bundle_frontmatter_valid_dict_with_bundle_key(self):
        fm = _parse_frontmatter(_read_file("bundle.md"))
        assert isinstance(fm, dict)
        assert "bundle" in fm

    @pytest.mark.parametrize("recipe_name", ALL_RECIPES)
    def test_recipe_yaml_valid_dict(self, recipe_name):
        path = os.path.join(BUNDLE_ROOT, "recipes", f"{recipe_name}.yaml")
        with open(path) as f:
            data = yaml.safe_load(f.read())
        assert isinstance(data, dict), (
            f"recipes/{recipe_name}.yaml did not parse as a dict"
        )


# ---------------------------------------------------------------------------
# Hook module structural tests
# ---------------------------------------------------------------------------


class TestHookModule:
    def test_modules_dir_exists(self):
        assert os.path.isdir(os.path.join(BUNDLE_ROOT, "modules"))

    def test_hooks_harness_dir_exists(self):
        assert os.path.isdir(os.path.join(BUNDLE_ROOT, "modules", "hooks-harness"))

    def test_hooks_harness_pyproject_exists(self):
        path = os.path.join(BUNDLE_ROOT, "modules", "hooks-harness", "pyproject.toml")
        assert os.path.isfile(path)

    def test_hooks_harness_package_dir_exists(self):
        path = os.path.join(
            BUNDLE_ROOT, "modules", "hooks-harness", "amplifier_module_hooks_harness"
        )
        assert os.path.isdir(path)

    def test_hooks_harness_init_exists(self):
        path = os.path.join(
            BUNDLE_ROOT,
            "modules",
            "hooks-harness",
            "amplifier_module_hooks_harness",
            "__init__.py",
        )
        assert os.path.isfile(path)

    def test_hooks_harness_init_exports_mount(self):
        content = _read_file(
            "modules/hooks-harness/amplifier_module_hooks_harness/__init__.py"
        )
        assert "def mount(" in content

    def test_hooks_harness_pyproject_has_entry_point(self):
        content = _read_file("modules/hooks-harness/pyproject.toml")
        assert "amplifier.modules" in content


# ---------------------------------------------------------------------------
# Runtime structural tests
# ---------------------------------------------------------------------------


class TestRuntime:
    # ---------------------------------------------------------------------------
    # Three-tier directory structure
    # ---------------------------------------------------------------------------

    def test_runtime_dir_exists(self):
        assert os.path.isdir(os.path.join(BUNDLE_ROOT, "runtime"))

    def test_pico_dir_exists(self):
        path = os.path.join(BUNDLE_ROOT, "runtime", "pico")
        assert os.path.isdir(path)

    def test_nano_dir_exists(self):
        path = os.path.join(BUNDLE_ROOT, "runtime", "nano")
        assert os.path.isdir(path)

    def test_micro_dir_exists(self):
        path = os.path.join(BUNDLE_ROOT, "runtime", "micro")
        assert os.path.isdir(path)

    # ---------------------------------------------------------------------------
    # Pico tier — cli / runtime / tools existence
    # ---------------------------------------------------------------------------

    def test_pico_has_cli_py(self):
        path = os.path.join(BUNDLE_ROOT, "runtime", "pico", "cli.py")
        assert os.path.isfile(path)

    def test_pico_has_runtime_py(self):
        path = os.path.join(BUNDLE_ROOT, "runtime", "pico", "runtime.py")
        assert os.path.isfile(path)

    def test_pico_has_tools_py(self):
        path = os.path.join(BUNDLE_ROOT, "runtime", "pico", "tools.py")
        assert os.path.isfile(path)

    # ---------------------------------------------------------------------------
    # Pico tier — rich rendering
    # ---------------------------------------------------------------------------

    def test_pico_cli_uses_rich_rendering(self):
        content = _read_file("runtime/pico/cli.py")
        assert "rich" in content

    # ---------------------------------------------------------------------------
    # Pico tier — constraint gate
    # ---------------------------------------------------------------------------

    def test_pico_gate_has_constraint_gate(self):
        content = _read_file("runtime/pico/gate.py")
        assert "ConstraintGate" in content

    # ---------------------------------------------------------------------------
    # Pico tier — pyproject harness_name
    # ---------------------------------------------------------------------------

    def test_pico_pyproject_template_has_harness_name(self):
        content = _read_file("runtime/pico/pyproject.toml.template")
        assert "{{harness_name}}" in content

    # ---------------------------------------------------------------------------
    # Pico tier — dockerfile
    # ---------------------------------------------------------------------------

    def test_pico_dockerfile_template_exists(self):
        path = os.path.join(BUNDLE_ROOT, "runtime", "pico", "Dockerfile.template")
        assert os.path.isfile(path)

    # ---------------------------------------------------------------------------
    # Pico tier — docker-compose project_root
    # ---------------------------------------------------------------------------

    def test_pico_docker_compose_has_project_root(self):
        content = _read_file("runtime/pico/docker-compose.template.yaml")
        assert "{{project_root}}" in content
