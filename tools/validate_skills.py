#!/usr/bin/env python3
"""Validate the monorepo layout and, optionally, run each skill's tests."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from skill_common import REPO_ROOT, SKILLS_ROOT, discover_skills


QUICK_VALIDATE = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "skill-creator"
    / "scripts"
    / "quick_validate.py"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate every skill in the monorepo.")
    parser.add_argument(
        "--tests",
        action="store_true",
        help="also run each skill's unittest suite",
    )
    return parser.parse_args()


def test_command(skill_dir: Path) -> list[str] | None:
    tests_dir = skill_dir / "tests"
    scripts_dir = skill_dir / "scripts"
    if tests_dir.is_dir() and any(tests_dir.glob("test_*.py")):
        return [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ]
    if scripts_dir.is_dir() and any(scripts_dir.glob("test_*.py")):
        return [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "scripts",
            "-p",
            "test_*.py",
            "-v",
        ]
    return None


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    if (REPO_ROOT / "SKILL.md").exists():
        errors.append("repository root must not contain SKILL.md")
    if not SKILLS_ROOT.is_dir():
        errors.append("missing skills/ directory")

    try:
        skills = discover_skills()
    except ValueError as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 1

    if not skills:
        errors.append("no skills found")

    names: set[str] = set()
    for skill in skills:
        if skill.name in names:
            errors.append(f"duplicate skill name: {skill.name}")
        names.add(skill.name)
        print(f"[ok] {skill.name} {skill.version} ({skill.path})")

        if QUICK_VALIDATE.is_file():
            result = subprocess.run(
                [sys.executable, str(QUICK_VALIDATE), str(skill.path)],
                cwd=str(REPO_ROOT),
                text=True,
                capture_output=True,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                errors.append(f"{skill.name}: quick validation failed: {detail}")

        if args.tests:
            command = test_command(skill.path)
            if command is None:
                print(f"[skip] {skill.name}: no tests/test_*.py")
                continue
            print(f"[test] {skill.name}: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=str(skill.path),
                text=True,
                capture_output=True,
            )
            if result.returncode != 0:
                detail = (result.stdout + "\n" + result.stderr).strip()
                errors.append(f"{skill.name}: tests failed\n{detail}")
            else:
                print(f"[ok] {skill.name}: tests passed")

    if errors:
        print("\nValidation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"\nValidated {len(skills)} independent skill(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
