#!/usr/bin/env python3
"""Version Manager for director-mode-fusion.

Features:
- List all available versions (Git tags).
- Switch/Rollback to any historical version and sync to Antigravity config directory.
- Release a new version with changelog, git tag, and GitHub Release.
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_SKILL_DIRS = [
    Path.home() / ".codex" / "skills" / "director-mode-fusion",
    Path.home() / ".gemini" / "config" / "skills" / "director-mode-fusion",
]
SKILL_FILE = REPO_ROOT / "SKILL.md"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"


def run_cmd(cmd, cwd=REPO_ROOT, check=True):
    """Run shell command and return stdout string."""
    res = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[-] 命令执行失败: {cmd}\n[-] 错误信息: {res.stderr.strip()}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout.strip()


def get_current_version():
    """Read current version from SKILL.md."""
    if not SKILL_FILE.exists():
        return "unknown"
    content = SKILL_FILE.read_text(encoding="utf-8")
    m = re.search(r"^version:\s*([^\s\n]+)", content, re.MULTILINE)
    return m.group(1) if m else "unknown"


def sync_to_antigravity():
    """Copy current repository skill files to Codex and Antigravity config directories."""
    exclude_items = {".git", ".gitignore", "director-mode-fusion-optimized.zip", "__pycache__"}
    synced_any = False
    for target_dir in CONFIG_SKILL_DIRS:
        if not target_dir.parent.exists():
            continue
        print(f"[+] 正在同步 Skill 到配置目录: {target_dir} ...")
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        # Clean destination except .git if any
        for item in target_dir.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Copy files
        for item in REPO_ROOT.iterdir():
            if item.name in exclude_items:
                continue
            dest = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print(f"[✓] 同步完成: {target_dir}")
        synced_any = True

    if not synced_any:
        print("[-] 未找到有效的目标配置目录进行同步。")


def list_versions():
    """List all available versions in Git."""
    tags_output = run_cmd("git tag -l -n1", check=False)
    current_ver = get_current_version()
    current_branch = run_cmd("git rev-parse --abbrev-ref HEAD", check=False)
    
    print("=" * 60)
    print(f"📦 director-mode-fusion 版本清单")
    print(f"当前工作分支: {current_branch}  |  当前 SKILL.md 版本: v{current_ver}")
    print("=" * 60)
    
    if not tags_output:
        print("暂无已发布的版本标签 (Git Tags)。")
        return

    print("已发布版本 (可在任何时候一键切换/回退到任一版本):")
    for line in tags_output.splitlines():
        tag = line.split()[0] if line else ""
        desc = line[len(tag):].strip()
        mark = "--> [当前激活]" if tag.lstrip("v") == current_ver or tag == current_branch else "   "
        print(f"  {mark} {tag:<12} {desc}")
    print("-" * 60)
    print("切换版本命令: python scripts/version_manager.py switch <版本号/tag/master>")


def switch_version(target):
    """Switch Git repo to specific version tag or branch and sync to Antigravity."""
    tag_or_branch = target.strip()
    if not tag_or_branch.startswith("v") and tag_or_branch not in ("master", "main") and "." in tag_or_branch:
        tag_or_branch = f"v{tag_or_branch}"

    # Check uncommitted changes
    status = run_cmd("git status --porcelain", check=False)
    if status:
        print("[-] 警告: 本地有未提交的改动，请先提交或保存后再切换版本！", file=sys.stderr)
        print(status, file=sys.stderr)
        sys.exit(1)

    print(f"[+] 正在切换至版本: {tag_or_branch} ...")
    run_cmd(f"git checkout {tag_or_branch}")
    
    new_ver = get_current_version()
    print(f"[✓] Git 仓库已成功切换至: {tag_or_branch} (SKILL 版本: {new_ver})")
    
    # Sync to Antigravity
    sync_to_antigravity()


def release_version(version_str, message):
    """Publish a new version with changelog update, git commit, tag, and GitHub release."""
    ver = version_str.strip().lstrip("v")
    tag = f"v{ver}"

    # Ensure master branch
    branch = run_cmd("git rev-parse --abbrev-ref HEAD")
    if branch != "master" and branch != "main":
        print(f"[-] 只能在 master/main 主分支上发布新版本 (当前分支: {branch})", file=sys.stderr)
        sys.exit(1)

    # Check existing tag
    existing_tags = run_cmd("git tag -l").splitlines()
    if tag in existing_tags:
        print(f"[-] 错误: 版本标签 {tag} 已存在，请指定新的递增版本号！", file=sys.stderr)
        sys.exit(1)

    print(f"[+] 准备发布新版本: {tag}")
    
    # 1. Update SKILL.md version
    skill_content = SKILL_FILE.read_text(encoding="utf-8")
    if re.search(r"^version:\s*[^\s\n]+", skill_content, re.MULTILINE):
        skill_content = re.sub(r"^version:\s*[^\s\n]+", f"version: {ver}", skill_content, count=1, flags=re.MULTILINE)
    else:
        skill_content = re.sub(r"^(name:\s*director-mode-fusion)", f"\\1\nversion: {ver}", skill_content, count=1, flags=re.MULTILINE)
    SKILL_FILE.write_text(skill_content, encoding="utf-8")
    print(f"[✓] 已更新 SKILL.md 版本为: {ver}")

    # 2. Update CHANGELOG.md if not already containing this version header
    today = datetime.now().strftime("%Y-%m-%d")
    changelog_content = CHANGELOG_FILE.read_text(encoding="utf-8") if CHANGELOG_FILE.exists() else "# Changelog\n"
    if f"## [{ver}]" not in changelog_content:
        entry = f"\n## [{ver}] - {today}\n\n### 变更说明\n- {message}\n"
        # Insert after the main title
        if "\n---\n" in changelog_content:
            parts = changelog_content.split("\n---\n", 1)
            changelog_content = parts[0] + "\n---\n" + entry + parts[1]
        else:
            changelog_content += entry
        CHANGELOG_FILE.write_text(changelog_content, encoding="utf-8")
        print(f"[✓] 已在 CHANGELOG.md 中记录版本 [{ver}]")

    # 3. Git commit
    run_cmd("git add .")
    run_cmd(f'git commit -m "release: {tag} - {message}"')
    print(f"[✓] 已创建 Git 提交: release: {tag}")

    # 4. Git Tag
    run_cmd(f'git tag -a {tag} -m "{message}"')
    print(f"[✓] 已创建 Git 标签: {tag}")

    # 5. Git Push to remote
    print("[+] 正在推送提交和标签到 GitHub 远程仓库 ...")
    run_cmd(f"git push origin {branch}")
    run_cmd(f"git push origin {tag}")
    print("[✓] 远程推送成功！")

    # 6. GitHub Release via gh CLI
    print("[+] 正在创建 GitHub Release ...")
    gh_cmd = f'gh release create {tag} --title "{tag} - {message}" --notes "{message}\n\n详见 CHANGELOG.md"'
    run_cmd(gh_cmd, check=False)
    print(f"[✓] GitHub Release 创建成功: https://github.com/ikun1946/director-mode-fusion/releases/tag/{tag}")

    # 7. Sync to Antigravity config
    sync_to_antigravity()
    print("\n🎉 发布圆满完成！")


def main():
    parser = argparse.ArgumentParser(description="director-mode-fusion 版本管理工具")
    subparsers = parser.add_subparsers(dest="action", help="执行操作")

    # list
    subparsers.add_parser("list", help="列出所有可用版本 (Tags)")

    # switch
    switch_parser = subparsers.add_parser("switch", help="一键回退/切换至指定版本 (例如 v1.0.0 或 master)")
    switch_parser.add_argument("target", help="目标版本号、Tag 名或分支名")

    # sync
    subparsers.add_parser("sync", help="将当前仓库的代码同步至本地 Antigravity 配置目录")

    # release
    release_parser = subparsers.add_parser("release", help="发布新版本并打 tag 推送到 GitHub")
    release_parser.add_argument("version", help="版本号 (如 1.1.0)")
    release_parser.add_argument("-m", "--message", required=True, help="该版本的更新说明与改动要点")

    args = parser.parse_args()

    if args.action == "list":
        list_versions()
    elif args.action == "switch":
        switch_version(args.target)
    elif args.action == "sync":
        sync_to_antigravity()
    elif args.action == "release":
        release_version(args.version, args.message)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
