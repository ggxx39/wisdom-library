#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-click Importer for Colab-generated Wisdom Assets.
Usage:
    python3 tools/import_colab_bundle.py ~/Downloads/wisdom_library_day1_assets.zip
"""

import sys
import os
import shutil
import zipfile
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def import_bundle(zip_path_str: str):
    zip_path = Path(zip_path_str).expanduser().resolve()
    if not zip_path.exists() or not zip_path.suffix.lower() == '.zip':
        print(f"❌ 错误：找不到有效的 zip 资产包：{zip_path}")
        sys.exit(1)

    print(f"📦 正在解压资产包: {zip_path.name} -> {REPO_ROOT} ...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        for member in z.infolist():
            # Extract only canonical domain directories
            if any(member.filename.startswith(f"0{i}_") for i in range(1, 7)):
                z.extract(member, REPO_ROOT)
                print(f"  • 解压: {member.filename}")

    # Check git status
    subprocess.run(["git", "status", "-s"], cwd=REPO_ROOT)
    
    # Prompt or auto-commit
    commit_msg = f"feat(library): import publication-grade dual-assets from {zip_path.name}"
    print(f"\n🚀 正在提交并推送到 GitHub (origin main)...")
    subprocess.run(["git", "add", "."], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
    print("\n🎉 资产已完美同步并推送到 GitHub 线上仓库！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default check ~/Downloads
        downloads = Path.home() / "Downloads"
        candidates = list(downloads.glob("wisdom_library*.zip"))
        if candidates:
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            print(f"💡 自动检测到最新下载的资产包: {latest}")
            import_bundle(str(latest))
        else:
            print("用法: python3 tools/import_colab_bundle.py /path/to/wisdom_assets.zip")
            sys.exit(1)
    else:
        import_bundle(sys.argv[1])
