#!/usr/bin/env python3
"""Operational tool for on-demand language bootstrapping (solorepo's DR-206).

Instantiates a new Project from a language Bootstrap (such as Python or Rust),
substitutes package manifests, and wires the new Project into assertions/structure.yaml.

    just bootstrap <lang> <destination> [name]
    python3 .meta/bootstrap.py <lang> <destination> [name]

Examples:
    just bootstrap python products/api api_service
    just bootstrap rust crates/engine
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    cmd = ["uvx", "--with", "pyyaml", "python", str(pathlib.Path(__file__).resolve()), *sys.argv[1:]]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

META = pathlib.Path(__file__).resolve().parent
ROOT = META.parent

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SUPPORTED_LANGUAGES = ("python", "rust")


def sanitize_name(dest: pathlib.Path) -> str:
    """Derive a canonical package/crate name from the destination path."""
    raw = dest.name.lower().replace("-", "_")
    cleaned = re.sub(r"[^a-z0-9_]", "", raw)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"pkg_{cleaned}"
    return cleaned or "pkg"


def find_structure_file() -> pathlib.Path | None:
    """Finds the active structure.yaml assertion file."""
    for cand in [ROOT / "assertions" / "structure.yaml", ROOT / ".meta" / "assertions" / "structure.yaml"]:
        if cand.is_file():
            return cand
    return None


def find_bootstrap_dir(lang: str) -> pathlib.Path | None:
    """Finds the bootstrap template directory locally or in .meta."""
    for cand in [ROOT / "bootstraps" / lang, ROOT / ".meta" / "bootstraps" / lang]:
        if cand.is_dir():
            return cand
    return None


def fetch_upstream_bootstrap(lang: str, target_dir: pathlib.Path) -> bool:
    """Fetches a language bootstrap from upstream caindy/solorepo if not present locally."""
    print(f"[*] Fetching '{lang}' bootstrap from upstream solorepo (caindy/solorepo)...")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            cmd = [
                "git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                "https://github.com/caindy/solorepo.git", str(tmp_path / "repo")
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "sparse-checkout", "set", f"bootstraps/{lang}"],
                cwd=str(tmp_path / "repo"),
                check=True,
                capture_output=True,
                text=True,
            )
            src = tmp_path / "repo" / "bootstraps" / lang
            if src.is_dir():
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copytree(src, target_dir)
                return True
    except Exception as e:
        print(f"[!] Warning: Unable to fetch upstream bootstrap automatically: {e}", file=sys.stderr)
    return False


def register_project(
    structure_path: pathlib.Path,
    project_slug: str,
    dest_rel: str,
    package_name: str,
    lang: str,
) -> bool:
    """Registers the new Project in structure.yaml."""
    raw_text = structure_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text) or {}
    projects = data.get("projects") or []
    for p in projects:
        if p.get("id") == f"work:project/{project_slug}" or p.get("name") == dest_rel:
            print(f"[*] Project '{dest_rel}' already registered in {structure_path.relative_to(ROOT)}.")
            return False

    gate_cmd = f"cd {dest_rel} && uv run gate" if lang == "python" else f"cd {dest_rel} && cargo xtask gate"

    project_block = (
        f"\n  - id: work:project/{project_slug}\n"
        f"    name: {dest_rel}\n"
        f"    description: Project {package_name} bootstrapped in {lang.capitalize()}.\n"
        f"    language: {lang.capitalize()}\n"
        f"    gate: {gate_cmd}\n"
    )

    if "\nprojects:" in raw_text:
        proj_idx = raw_text.index("\nprojects:")
        rest = raw_text[proj_idx + len("\nprojects:"):]
        m = re.search(r"\n\n+(?=(?:#[^\n]*\n)*[a-z_]+:)", rest)
        if m:
            insert_pos = proj_idx + len("\nprojects:") + m.start()
            updated_text = raw_text[:insert_pos] + project_block + raw_text[insert_pos:]
        else:
            updated_text = raw_text + project_block
    else:
        updated_text = raw_text + "\nprojects:" + project_block

    structure_path.write_text(updated_text, encoding="utf-8")
    print(f"[*] Registered 'work:project/{project_slug}' in {structure_path.relative_to(ROOT)}.")
    return True


def install_bootstrap_apm_package(lang: str) -> None:
    """Brings in the language bootstrap APM package when a project is bootstrapped (solorepo's DR-208)."""
    if lang != "python":
        return
    bootstrap_dir = find_bootstrap_dir("python")
    if not bootstrap_dir:
        return
    python_skills_dir = bootstrap_dir / ".apm" / "skills"
    if not python_skills_dir.is_dir():
        return

    apm_manifest_file = ROOT / ".meta" / "apm.yml"
    if apm_manifest_file.is_file():
        raw_text = apm_manifest_file.read_text(encoding="utf-8")
        if "solorepo-python" not in raw_text:
            dep_block = "dependencies:\n  solorepo-python:\n    path: ../bootstraps/python\n"
            if "dependencies:" in raw_text:
                dep_block = "  solorepo-python:\n    path: ../bootstraps/python\n"
                raw_text = raw_text.replace("dependencies:\n", "dependencies:\n" + dep_block)
            else:
                raw_text = raw_text.rstrip() + "\n" + dep_block
            apm_manifest_file.write_text(raw_text, encoding="utf-8")
            print(f"[*] Registered 'solorepo-python' APM package dependency in {apm_manifest_file.relative_to(ROOT)}.")

    for harness_skills in [ROOT / ".claude" / "skills", ROOT / ".gemini" / "skills"]:
        if harness_skills.parent.is_dir():
            harness_skills.mkdir(parents=True, exist_ok=True)
            for skill_dir in python_skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                target = harness_skills / skill_dir.name
                if not target.exists():
                    import shutil
                    shutil.copytree(skill_dir, target)
                    print(f"[*] Projected skill '{skill_dir.name}' into {target.relative_to(ROOT)}.")



def resolve_destination(destination: str) -> tuple[pathlib.Path, str] | str:
    """The absolute destination and its path relative to the repository root, or the error to print: a destination outside the root, or one that already exists."""
    dest = pathlib.Path(destination)
    if not dest.is_absolute():
        dest = (ROOT / dest).resolve()
    try:
        dest_rel = str(dest.relative_to(ROOT))
    except ValueError:
        return f"error: destination '{destination}' must reside within repository root '{ROOT}'"
    if dest.exists():
        return f"error: destination '{dest_rel}' already exists; bootstraps only render into an empty place"
    return dest, dest_rel


def resolve_bootstrap_dir(lang: str) -> pathlib.Path | None:
    """The bootstrap directory for `lang`, found locally or fetched from upstream into `.meta/bootstraps/`, or None where neither succeeds."""
    bootstrap_dir = find_bootstrap_dir(lang)
    if bootstrap_dir:
        return bootstrap_dir
    fetched_dir = ROOT / ".meta" / "bootstraps" / lang
    return fetched_dir if fetch_upstream_bootstrap(lang, fetched_dir) else None


def bootstrap(lang: str, destination: str, name: str | None = None) -> int:
    """Executes on-demand bootstrapping for a specified language and path."""
    lang = lang.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        print(
            f"error: unsupported language '{lang}'. Supported bootstraps: {', '.join(SUPPORTED_LANGUAGES)}",
            file=sys.stderr,
        )
        return 1

    resolved = resolve_destination(destination)
    if isinstance(resolved, str):
        print(resolved, file=sys.stderr)
        return 1
    dest, dest_rel = resolved

    package_name = name.strip() if name else sanitize_name(dest)
    if not NAME_RE.match(package_name) or package_name in ("seed", "gate"):
        print(
            f"error: '{package_name}' is not a valid package/crate name (must match ^[a-z][a-z0-9_]*$ and not be 'seed' or 'gate')",
            file=sys.stderr,
        )
        return 1

    project_slug = package_name.replace("_", "-")

    bootstrap_dir = resolve_bootstrap_dir(lang)
    if not bootstrap_dir:
        print(f"error: bootstrap for '{lang}' not found locally and could not be fetched from upstream", file=sys.stderr)
        return 1

    render_script = bootstrap_dir / "render"
    if not render_script.is_file():
        print(f"error: bootstrap render script '{render_script}' not found", file=sys.stderr)
        return 1

    print(f"[*] Instantiating {lang.capitalize()} project at '{dest_rel}' with name '{package_name}'...")
    res = subprocess.run([sys.executable, str(render_script), str(dest), package_name], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"error: render failed:\n{res.stderr}", file=sys.stderr)
        return res.returncode

    if res.stdout:
        print(res.stdout.strip())

    struct_file = find_structure_file()
    if struct_file:
        register_project(struct_file, project_slug, dest_rel, package_name, lang)

        render_py = META / "render.py"
        if render_py.is_file():
            print("[*] Re-rendering repository operator surface (just render)...")
            subprocess.run(["python3", str(render_py)], capture_output=True, text=True)
    else:
        print("[!] Warning: structure.yaml not found; skipping project registration.")

    install_bootstrap_apm_package(lang)

    print(f"\n[+] Successfully bootstrapped {lang.capitalize()} Project '{package_name}' at '{dest_rel}'.")
    gate_cmd = "uv run gate" if lang == "python" else "cargo xtask gate"
    print(f"    Verification gate: cd {dest_rel} && {gate_cmd}")
    print(f"    Run via repository gate: just gate {project_slug}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for on-demand project bootstrapping (solorepo's DR-206)."""
    parser = argparse.ArgumentParser(
        description="Instantiate a Project from a language Bootstrap on demand (solorepo's DR-206)."
    )
    parser.add_argument("language", choices=["python", "rust"], help="The bootstrap language (python, rust).")
    parser.add_argument("destination", help="Target destination directory (e.g. products/api or services/backend).")
    parser.add_argument("name", nargs="?", default=None, help="Optional package/crate name (default: derived from destination).")

    args = parser.parse_args(argv)
    return bootstrap(args.language, args.destination, args.name)


if __name__ == "__main__":
    sys.exit(main())
