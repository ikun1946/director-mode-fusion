#!/usr/bin/env python3
"""Release one skill with an independent version and skill-scoped Git tag."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import subprocess
import sys

from skill_common import REPO_ROOT, get_skill, run


REMOTE_URL = "https://github.com/ikun1946/codex-skill"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release one skill independently.")
    parser.add_argument("skill", help="skill directory name")
    parser.add_argument("version", help="new semantic version, for example 1.2.3")
    parser.add_argument("-m", "--message", required=True, help="release notes")
    parser.add_argument("--no-push", action="store_true", help="do not push")
    parser.add_argument(
        "--no-release",
        action="store_true",
        help="do not create a GitHub Release",
    )
    return parser.parse_args()


def normalize_version(value: str) -> str:
    version = value.strip().lstrip("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise ValueError(f"invalid semantic version: {value}")
    return version


def update_skill_version(skill_file: Path, version: str) -> None:
    lines = skill_file.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = next(
        (i for i in range(1, len(lines)) if lines[i].strip() == "---"),
        None,
    )
    if end is None:
        raise ValueError("SKILL.md frontmatter is not closed")

    top_version = None
    metadata_line = None
    metadata_version = None

    for index in range(1, end):
        line = lines[index]
        if line.startswith("version:"):
            top_version = index
        if line.startswith("metadata:"):
            metadata_line = index
            for child in range(index + 1, end):
                if lines[child] and not lines[child][0].isspace():
                    break
                if re.match(r"^[ \t]+version:\s*", lines[child]):
                    metadata_version = child
            break

    replacement = f'version: "{version}"\n'
    if top_version is not None:
        lines[top_version] = replacement
    elif metadata_version is not None:
        lines[metadata_version] = f"  {replacement}"
    elif metadata_line is not None:
        lines.insert(metadata_line + 1, f"  {replacement}")
    else:
        lines[end:end] = ["metadata:\n", f"  {replacement}"]

    skill_file.write_text("".join(lines), encoding="utf-8")


def update_changelog(skill_dir: Path, version: str, message: str) -> None:
    changelog = skill_dir / "CHANGELOG.md"
    existing = changelog.read_text(encoding="utf-8") if changelog.exists() else "# Changelog\n"
    if re.search(
        rf"^##\s+(?:\[{re.escape(version)}\]|{re.escape(version)}\b)",
        existing,
        re.MULTILINE,
    ):
        raise ValueError(f"changelog already contains version {version}")
    entry = f"## [{version}] - {date.today().isoformat()}\n\n- {message}\n\n"
    lines = existing.splitlines(keepends=True)
    if lines and lines[0].startswith("#"):
        insert_at = 1
        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1
        lines.insert(insert_at, entry)
        existing = "".join(lines)
    else:
        existing = "# Changelog\n\n" + entry + existing
    changelog.write_text(existing, encoding="utf-8")


def ensure_clean_worktree() -> None:
    result = run(["git", "status", "--porcelain"])
    if result.stdout.strip():
        raise ValueError(
            "working tree is not clean; commit or stash changes before releasing"
        )


def main() -> int:
    args = parse_args()
    try:
        version = normalize_version(args.version)
        skill = get_skill(args.skill)
        ensure_clean_worktree()
    except ValueError as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 2

    tag = f"{skill.name}-v{version}"
    branch_result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_result.stdout.strip()
    if branch not in ("master", "main"):
        print(f"[-] release from master/main only; current branch: {branch}", file=sys.stderr)
        return 2

    tags = run(["git", "tag", "-l"]).stdout.splitlines()
    if tag in tags:
        print(f"[-] tag already exists: {tag}", file=sys.stderr)
        return 2

    try:
        update_skill_version(skill.path / "SKILL.md", version)
        version_file = skill.path / "VERSION"
        if version_file.exists():
            version_file.write_text(f"{version}\n", encoding="utf-8")
        update_changelog(skill.path, version, args.message)
    except ValueError as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 1

    run(["git", "add", "--", str(skill.path.relative_to(REPO_ROOT))])
    run(["git", "commit", "-m", f"release({skill.name}): v{version} - {args.message}"])
    run(["git", "tag", "-a", tag, "-m", args.message])
    print(f"[ok] committed and tagged {tag}")

    if not args.no_push:
        run(["git", "push", "origin", branch])
        run(["git", "push", "origin", tag])
        print("[ok] pushed branch and tag")

    if not args.no_release and not args.no_push:
        result = subprocess.run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--title",
                f"{tag} - {args.message}",
                "--notes",
                f"{args.message}\n\nSee {skill.path.name}/CHANGELOG.md.",
            ],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"[ok] release: {REMOTE_URL}/releases/tag/{tag}")
        else:
            print(f"[-] GitHub Release failed: {result.stderr.strip()}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
