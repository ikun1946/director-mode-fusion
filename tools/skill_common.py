"""Shared repository helpers for the codex-skill monorepo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"

COPY_IGNORE_PATTERNS = (
    ".git",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.bak-*",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)


@dataclass(frozen=True)
class SkillInfo:
    name: str
    version: str
    description: str
    path: Path


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_frontmatter(content: str) -> tuple[dict[str, str], dict[str, str]]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc

    top: dict[str, str] = {}
    metadata: dict[str, str] = {}
    in_metadata = False

    for raw_line in lines[1:end]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indented = raw_line[0].isspace()
        if not indented:
            in_metadata = False
            if ":" not in raw_line:
                continue
            key, value = raw_line.split(":", 1)
            key = key.strip()
            value = unquote(value)
            if key == "metadata" and not value:
                in_metadata = True
            else:
                top[key] = value
            continue
        if in_metadata and ":" in raw_line:
            key, value = raw_line.strip().split(":", 1)
            metadata[key.strip()] = unquote(value)

    return top, metadata


def read_skill_info(skill_dir: Path) -> SkillInfo:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"missing SKILL.md: {skill_file}")
    top, metadata = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    name = top.get("name", "").strip()
    version = top.get("version", "").strip() or metadata.get("version", "").strip()
    description = top.get("description", "").strip()
    if not name:
        raise ValueError(f"missing skill name: {skill_file}")
    if not version:
        raise ValueError(f"missing skill version: {skill_file}")
    if not description:
        raise ValueError(f"missing skill description: {skill_file}")
    if name != skill_dir.name:
        raise ValueError(
            f"skill name '{name}' does not match directory '{skill_dir.name}'"
        )
    return SkillInfo(name=name, version=version, description=description, path=skill_dir)


def discover_skills() -> list[SkillInfo]:
    if not SKILLS_ROOT.is_dir():
        return []
    skills: list[SkillInfo] = []
    for child in sorted(SKILLS_ROOT.iterdir(), key=lambda path: path.name):
        if child.is_dir() and (child / "SKILL.md").is_file():
            skills.append(read_skill_info(child))
    return skills


def get_skill(name: str) -> SkillInfo:
    path = SKILLS_ROOT / name
    if not path.is_dir():
        raise ValueError(f"unknown skill: {name}")
    return read_skill_info(path)


def copy_skill(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(*COPY_IGNORE_PATTERNS),
    )


def run(
    cmd: list[str],
    cwd: Path = REPO_ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=check,
    )
