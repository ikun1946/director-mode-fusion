#!/usr/bin/env python3
"""Install one or more self-contained skills into local Codex skill directories."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import uuid

from skill_common import copy_skill, discover_skills, get_skill


DEFAULT_TARGETS = (
    Path.home() / ".codex" / "skills",
    Path.home() / ".gemini" / "config" / "skills",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install selected self-contained skills from this repository."
    )
    parser.add_argument("skills", nargs="*", help="skill directory names")
    parser.add_argument("--all", action="store_true", help="install every skill")
    parser.add_argument(
        "--target-dir",
        action="append",
        type=Path,
        help="override target skill root; may be supplied multiple times",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing installed skill directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="show actions only")
    return parser.parse_args()


def select_skills(names: list[str], install_all: bool):
    if install_all and names:
        raise ValueError("use either skill names or --all, not both")
    if install_all:
        selected = discover_skills()
    elif names:
        selected = [get_skill(name) for name in names]
    else:
        raise ValueError("specify at least one skill name or use --all")
    if not selected:
        raise ValueError("no skills found")
    return selected


def sync_one(source: Path, destination: Path, force: bool, dry_run: bool) -> None:
    print(f"[+] {source.name}: {source} -> {destination}")
    if dry_run:
        return
    if destination.exists() and not force:
        raise FileExistsError(
            f"destination exists: {destination}; rerun with --force to replace it"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    temporary = destination.parent / f".{destination.name}.tmp-{token}"
    backup = destination.parent / f".{destination.name}.old-{token}"
    copy_skill(source, temporary)

    moved_existing = False
    try:
        if destination.exists():
            destination.rename(backup)
            moved_existing = True
        temporary.rename(destination)
        if moved_existing:
            shutil.rmtree(backup)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        if moved_existing and backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    print(f"[ok] installed {source.name}")


def main() -> int:
    args = parse_args()
    try:
        selected = select_skills(args.skills, args.all)
    except ValueError as exc:
        print(f"[-] {exc}", file=sys.stderr)
        return 2

    targets = tuple(args.target_dir) if args.target_dir else DEFAULT_TARGETS
    had_error = False
    for target_root in targets:
        if not args.target_dir and not target_root.parent.exists():
            print(f"[skip] target parent does not exist: {target_root.parent}")
            continue
        for skill in selected:
            try:
                sync_one(skill.path, target_root / skill.name, args.force, args.dry_run)
            except Exception as exc:
                had_error = True
                print(f"[-] {skill.name}: {exc}", file=sys.stderr)
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
