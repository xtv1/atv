#!/usr/bin/env python3
"""
同步脚本：读取根目录 url.txt，按行解析 [subdir]=<git-url>，
将远端仓库克隆到临时目录，移除 .git，然后覆盖到本仓库的 subdir 目录下。
最后在本仓库根目录做一次 commit/push（如果有变更）。

已修改：在处理完所有仓库后一次性提交（而不是多次提交）。提交信息会列出被更新的子目录。
注意：
- 依赖系统 git；
- 在 GitHub Actions 中运行时，actions/checkout 提供的凭证会被用以推送变更。
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

ROOT = os.getcwd()
URL_FILE = os.path.join(ROOT, "url.txt")
GIT = shutil.which("git") or "git"

LINE_RE = re.compile(r'^\s*\[([^\]]+)\]\s*=\s*(\S+)\s*$')

def log(*args, **kwargs):
    print("[sync]", *args, **kwargs)

def run(cmd, cwd=None, check=True):
    log(">", " ".join(cmd) if isinstance(cmd, (list, tuple)) else cmd)
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if res.stdout:
        print(res.stdout)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd} (cwd={cwd})")
    return res

def parse_url_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"url file not found: {path}")
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for idx, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = LINE_RE.match(line)
            if not m:
                log(f"WARNING: skip invalid line {idx}: {raw.strip()}")
                continue
            subdir, url = m.group(1).strip(), m.group(2).strip()
            entries.append((subdir, url))
    return entries

def safe_rmtree(path):
    if os.path.exists(path):
        shutil.rmtree(path)

def main():
    log("Working dir:", ROOT)
    try:
        entries = parse_url_file(URL_FILE)
    except Exception as e:
        log("Error reading url file:", e)
        sys.exit(1)

    if not entries:
        log("No valid entries found in url.txt — nothing to do.")
        return

    tmp_root = tempfile.mkdtemp(prefix="sync-repos-")
    log("Using temp root:", tmp_root)
    updated_subdirs = []

    for subdir, url in entries:
        log(f"Processing [{subdir}] = {url}")
        clone_path = os.path.join(tmp_root, subdir + "_clone")
        target_path = os.path.join(ROOT, subdir)

        # Ensure parent exists
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)

        # Remove any previous clone at temp
        safe_rmtree(clone_path)

        # Clone repository (shallow)
        try:
            run([GIT, "clone", "--depth", "1", url, clone_path])
        except Exception as e:
            log(f"ERROR: failed to clone {url}: {e}")
            continue

        # Remove .git from cloned repo
        gitdir = os.path.join(clone_path, ".git")
        if os.path.exists(gitdir):
            safe_rmtree(gitdir)

        # Remove target_path if exists, then move clone there
        if os.path.exists(target_path):
            log("Removing existing target:", target_path)
            safe_rmtree(target_path)

        # Move cloned content into repository
        try:
            shutil.move(clone_path, target_path)
            log("Moved cloned repo to", target_path)
            updated_subdirs.append(subdir)
        except Exception as e:
            log("ERROR moving cloned repo to target:", e)
            # Try fallback: copy tree
            try:
                shutil.copytree(clone_path, target_path)
                log("Copied cloned repo to", target_path)
                updated_subdirs.append(subdir)
            except Exception as e2:
                log("ERROR fallback copy failed:", e2)
                continue

    # Clean up temp
    try:
        safe_rmtree(tmp_root)
    except Exception:
        pass

    # Commit & push once if there were updates
    if not updated_subdirs:
        log("No repositories were updated — nothing to commit.")
        return

    try:
        # Configure git user for committing
        actor = os.environ.get("GITHUB_ACTOR", "github-actions[bot]")
        email = f"{actor}@users.noreply.github.com"
        run([GIT, "config", "user.name", actor], check=True)
        run([GIT, "config", "user.email", email], check=True)

        # Stage all changes
        run([GIT, "add", "-A"], check=True)

        # Double-check there are changes to commit
        status = subprocess.run([GIT, "status", "--porcelain"], stdout=subprocess.PIPE, text=True)
        if status.stdout.strip():
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            # Create a concise commit message listing updated subdirs
            # If too many subdirs, show count and first few names.
            max_list = 10
            display_list = updated_subdirs if len(updated_subdirs) <= max_list else updated_subdirs[:max_list]
            names = ", ".join(display_list)
            suffix = "" if len(updated_subdirs) <= max_list else f", and {len(updated_subdirs) - max_list} more"
            message = f"Sync external repos ({len(updated_subdirs)}): {names}{suffix}\n\nSynced at {now}"
            run([GIT, "commit", "-m", message], check=True)
            # Push using upstream from actions/checkout credential helper
            run([GIT, "push"], check=True)
            log("Pushed changes.")
        else:
            log("No changes to commit after staging.")
    except Exception as e:
        log("ERROR during git commit/push:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
