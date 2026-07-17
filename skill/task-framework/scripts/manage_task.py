#!/usr/bin/env python3
"""
task-framework 任务生命周期管理工具

管理 ~/studio/hermes/tasks/ 下的任务文件（默认，可通过 config.yaml 配置）。
不再使用 ~/.hermes/personal/tasks/ 镜像目录——所有文件直接存放在任务目录下。

配置优先级（同 token-consumption-tracker 模式）：
  1. HERMES_TASKS_DIR 环境变量
  2. 当前 profile config.yaml: tasks.data_dir
  3. 全局 ~/.hermes/config.yaml: tasks.data_dir
  4. Fallback: ~/studio/hermes/tasks

Commands:
    init      为任务创建目录 + TASK.md + TASK_MEMORY.md + .hermes-task.json
    export    将任务打包为可移植 tar.gz
    import    从 tar.gz 恢复任务
    rebuild   按 hash 查找最近 tar.gz 并导入
    reindex   重建 index.md
    list      列出所有任务状态
    migrate   一次性迁移：将 ~/.hermes/personal/tasks/ 下的文件迁移到统一目录
    ensure-all 全量注册所有现有任务
"""
import os, sys, glob, json, shutil, re, tarfile, tempfile, hashlib, random, argparse
from datetime import datetime
from pathlib import Path


# ── config resolution (mirrors token-consumption-tracker pattern) ──

def _read_config_yaml(config_path):
    if not config_path or not os.path.exists(str(config_path)):
        return {}
    try:
        import yaml
        with open(config_path) as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _resolve_tasks_root() -> str:
    """Priority chain: env → profile config → global config → fallback."""
    # 1. Env var
    env = os.environ.get("HERMES_TASKS_DIR", "").strip()
    if env:
        return os.path.expanduser(env)

    # 2. Per-profile config
    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        cfg = _read_config_yaml(Path(hermes_home) / "config.yaml")
        tasks_cfg = cfg.get("tasks", {})
        if isinstance(tasks_cfg, dict):
            val = tasks_cfg.get("data_dir")
            if val and isinstance(val, str):
                return os.path.expanduser(val)

    # 3. Global config
    global_cfg_path = Path(os.path.expanduser("~/.hermes/config.yaml"))
    if hermes_home:
        profile_cfg_path = (Path(hermes_home) / "config.yaml").resolve()
    else:
        profile_cfg_path = None
    if profile_cfg_path is None or global_cfg_path.resolve() != profile_cfg_path.resolve():
        cfg = _read_config_yaml(global_cfg_path)
        tasks_cfg = cfg.get("tasks", {})
        if isinstance(tasks_cfg, dict):
            val = tasks_cfg.get("data_dir")
            if val and isinstance(val, str):
                return os.path.expanduser(val)

    # 4. Fallback
    return os.path.expanduser("~/studio/hermes/tasks")


TASKS_ROOT = _resolve_tasks_root()


def hash6():
    return hashlib.md5(str(random.random()).encode()).hexdigest()[:6]


def _task_hash_from_dir(task_dir):
    name = os.path.basename(task_dir)
    m = re.search(r'-([a-z0-9]{6})$', name)
    return m.group(1) if m else None


def _find_task_dir_by_hash(h):
    if not os.path.isdir(TASKS_ROOT):
        return None
    for d in sorted(glob.glob(os.path.join(TASKS_ROOT, "2*")), reverse=True):
        if os.path.isdir(d) and _task_hash_from_dir(d) == h:
            return d
    return None


def _find_all_task_dirs():
    if not os.path.isdir(TASKS_ROOT):
        return []
    dirs = []
    for d in sorted(glob.glob(os.path.join(TASKS_ROOT, "2*")), reverse=True):
        if os.path.isdir(d) and (
            os.path.exists(os.path.join(d, ".hermes-task.json")) or
            os.path.exists(os.path.join(d, "TASK.md"))
        ):
            dirs.append(d)
    return dirs


def _suggest_dir_name(h, task_dir=None):
    meta = {}
    meta_path = None
    if task_dir and os.path.isdir(task_dir):
        meta_path = os.path.join(task_dir, ".hermes-task.json")
    if meta_path and os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except Exception:
            pass

    ts = meta.get('created_at', '')
    if not ts:
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    else:
        try:
            dt = datetime.fromisoformat(ts)
            ts = dt.strftime('%Y%m%d-%H%M%S')
        except Exception:
            ts = str(ts).replace(' ', '-').replace(':', '')[:15]

    name = meta.get('name', '')
    if not name:
        if task_dir:
            title = None
            task_md = os.path.join(task_dir, "TASK.md")
            if os.path.exists(task_md):
                m = re.search(r'^# Task:\s*(.+)', open(task_md).read(), re.MULTILINE)
                if m:
                    title = m.group(1).strip()
            if title:
                name = re.sub(r'[^a-z0-9-]', '', title.lower().replace(' ', '-'))
        if not name:
            name = f'task-{h}'
    name = re.sub(rf'-{re.escape(h)}$', '', name)
    return f"{ts}.{name}-{h}"


def _ensure_task_files(task_dir, h):
    """Create real files directly in the task directory (no symlinks, no mirror)."""
    os.makedirs(task_dir, exist_ok=True)

    task_f = os.path.join(task_dir, "TASK.md")
    mem_f = os.path.join(task_dir, "TASK_MEMORY.md")
    meta_f = os.path.join(task_dir, ".hermes-task.json")

    if not os.path.exists(task_f):
        with open(task_f, 'w') as f:
            f.write("# Task: --\n\n## Status\n\nactive\n\n## Goal\n\n\n## Checklist\n\n")
        print(f"  Created: {task_f}")

    if not os.path.exists(mem_f):
        with open(mem_f, 'w') as f:
            f.write(f"# TASK_MEMORY.md -- {h}\n\n")
        print(f"  Created: {mem_f}")

    if not os.path.exists(meta_f):
        with open(meta_f, 'w') as f:
            json.dump({
                "hash": h, "name": "",
                "created_at": datetime.now().isoformat(),
                "outputs": {}, "dependencies": []
            }, f, indent=2, ensure_ascii=False)
        print(f"  Created: {meta_f}")

    for d in ['input', 'output']:
        dp = os.path.join(task_dir, d)
        os.makedirs(dp, exist_ok=True)

    return task_f, mem_f, meta_f


# ── commands ──────────────────────────────────────────────────────

def cmd_init(hash_or_dir):
    if re.match(r'^[a-z0-9]{6}$', hash_or_dir):
        h = hash_or_dir
        task_dir = _find_task_dir_by_hash(h)
        if not task_dir:
            task_dir = os.path.join(TASKS_ROOT, _suggest_dir_name(h))
    else:
        task_dir = os.path.abspath(hash_or_dir)
        h = _task_hash_from_dir(task_dir)
    if not h:
        print(f"Cannot determine hash from '{hash_or_dir}'")
        return False
    print(f"  hash={h}  task={task_dir}")
    _ensure_task_files(task_dir, h)
    return True


def cmd_export(hash_or_dir):
    if re.match(r'^[a-z0-9]{6}$', hash_or_dir):
        h = hash_or_dir
        task_dir = _find_task_dir_by_hash(h)
    else:
        task_dir = os.path.abspath(hash_or_dir)
        h = _task_hash_from_dir(task_dir)
    if not h:
        print(f"Cannot determine hash from '{hash_or_dir}'")
        return False
    if not task_dir or not os.path.isdir(task_dir):
        print(f"Task directory not found for hash {h}")
        return False

    dir_name = os.path.basename(task_dir)
    with tempfile.TemporaryDirectory(prefix=f"task-export-{h}-") as tmp:
        staging = os.path.join(tmp, dir_name)
        _copytree_deref(task_dir, staging, ignore=['.git'])
        archive_name = f"{dir_name}.tar.gz"
        archive_path = os.path.join(os.path.dirname(task_dir), archive_name)
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(staging, arcname=os.path.basename(staging))
        print(f"Exported: {archive_path}")
    return True


def _copytree_deref(src, dst, ignore=None):
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        if ignore and item in ignore:
            continue
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            _copytree_deref(s, d, ignore)
        else:
            shutil.copy2(s, d)


def cmd_import(archive_path):
    archive_path = os.path.abspath(archive_path)
    if not os.path.exists(archive_path):
        print(f"Archive not found: {archive_path}")
        return False
    with tempfile.TemporaryDirectory(prefix="task-import-") as tmp:
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(path=tmp)
        extracted = os.listdir(tmp)
        print(f"Extracted: {extracted}")

        task_dir_name = None
        for item in extracted:
            item_path = os.path.join(tmp, item)
            if os.path.isdir(item_path):
                contents = os.listdir(item_path)
                if any(f in contents for f in ['TASK.md', '.hermes-task.json']):
                    task_dir_name = item
                    break

        if not task_dir_name:
            print("No recognizable task directory found in archive")
            return False

        task_dir_path = os.path.join(tmp, task_dir_name)
        h = _task_hash_from_dir(task_dir_path)
        if not h:
            # Try from meta.json
            meta_path = os.path.join(task_dir_path, ".hermes-task.json")
            if os.path.exists(meta_path):
                try:
                    meta = json.load(open(meta_path))
                    h = meta.get('hash', '')
                except Exception:
                    pass
        if not h:
            print(f"Cannot determine hash from '{task_dir_name}'")
            return False

        dest_name = task_dir_name if _task_hash_from_dir(task_dir_name) == h else _suggest_dir_name(h, task_dir_path)
        task_dest = os.path.join(TASKS_ROOT, dest_name)
        if os.path.exists(task_dest):
            alt = f"{dest_name}-imported-{hash6()}"
            task_dest = os.path.join(TASKS_ROOT, alt)
            print(f"Using alternative: {task_dest}")

        os.makedirs(task_dest, exist_ok=True)
        for item in os.listdir(task_dir_path):
            s = os.path.join(task_dir_path, item)
            d = os.path.join(task_dest, item)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        print(f"\nImported: {task_dest}")
    return True


def cmd_rebuild(hash_or_archive):
    if tarfile.is_tarfile(hash_or_archive):
        return cmd_import(hash_or_archive)
    h = hash_or_archive
    if not re.match(r'^[a-z0-9]{6}$', h):
        print(f"Invalid hash: {h}")
        return False
    pattern = os.path.join(TASKS_ROOT, f"*{h}*.tar.gz")
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not matches:
        print(f"No tar.gz found for hash {h} in {TASKS_ROOT}")
        return False
    archive = matches[0]
    print(f"Found: {archive}")
    return cmd_import(archive)


def cmd_reindex():
    index_path = os.path.join(TASKS_ROOT, "index.md")
    task_dirs = _find_all_task_dirs()
    lines = [
        "# Task Index",
        "",
        "| Timestamp | Name | Hash | Status | TASK.md | MEMORY.md | Meta |",
        "|-----------|------|------|--------|---------|-----------|------|",
    ]
    for d in task_dirs:
        name = os.path.basename(d)
        parts = name.split('.', 1)
        ts = parts[0] if len(parts) > 1 else name
        task_name = parts[1] if len(parts) > 1 else name
        h = _task_hash_from_dir(d)
        status = "?"
        task_md = os.path.join(d, "TASK.md")
        if os.path.exists(task_md):
            m = re.search(r'## Status\s*\n\s*(\w+)', open(task_md).read())
            if m:
                status = m.group(1)
        task_ok = "Y" if os.path.exists(os.path.join(d, "TASK.md")) else "N"
        mem_ok = "Y" if os.path.exists(os.path.join(d, "TASK_MEMORY.md")) else "N"
        meta_ok = "Y" if os.path.exists(os.path.join(d, ".hermes-task.json")) else "N"
        lines.append(f"| {ts} | {task_name} | {h or '?'} | {status} | {task_ok} | {mem_ok} | {meta_ok} |")

    with open(index_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"Reindexed {len(task_dirs)} tasks -> {index_path}")
    return True


def cmd_list():
    index_path = os.path.join(TASKS_ROOT, "index.md")
    if os.path.exists(index_path):
        print(open(index_path).read())
    else:
        print("index.md not found. Run `reindex` first.")
    return True


def cmd_migrate():
    """One-shot migration: copy files from ~/.hermes/personal/tasks/<hash>/ to task dir."""
    old_root = os.path.expanduser("~/.hermes/personal/tasks")
    if not os.path.isdir(old_root):
        print("No old personal/tasks directory to migrate from.")
        return True

    migrated = 0
    for hd_name in os.listdir(old_root):
        hd = os.path.join(old_root, hd_name)
        if not os.path.isdir(hd) or not re.match(r'^[a-z0-9]{6}$', hd_name):
            continue
        h = hd_name
        task_dir = _find_task_dir_by_hash(h)
        if not task_dir:
            # Create new task dir
            task_dir = os.path.join(TASKS_ROOT, _suggest_dir_name(h))
            os.makedirs(task_dir, exist_ok=True)

        # Copy files from old mirror to task dir, if task dir doesn't already have them
        for old_name, new_name in [
            ("task.md", "TASK.md"),
            ("memory.md", "TASK_MEMORY.md"),
            ("meta.json", ".hermes-task.json"),
        ]:
            src = os.path.join(hd, old_name)
            dst = os.path.join(task_dir, new_name)
            if os.path.exists(src):
                # Symlinks pass os.path.exists — check explicitly so we don't skip
                if os.path.islink(dst):
                    os.remove(dst)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    print(f"  {old_name} -> {new_name}")

        migrated += 1

    cmd_reindex()
    print(f"\nMigrated {migrated} tasks from {old_root}")
    return True


def cmd_ensure_all():
    task_dirs = _find_all_task_dirs()
    for d in task_dirs:
        h = _task_hash_from_dir(d)
        if h:
            cmd_init(h)
    cmd_reindex()
    print(f"\nAll {len(task_dirs)} tasks registered.")


def main():
    parser = argparse.ArgumentParser(description='Task lifecycle management')
    parser.add_argument('action', choices=[
        'init', 'export', 'import', 'rebuild',
        'reindex', 'list', 'migrate', 'ensure-all'
    ])
    parser.add_argument('arg', nargs='?', default='')
    args = parser.parse_args()

    actions = {
        'init': lambda: cmd_init(args.arg),
        'export': lambda: cmd_export(args.arg),
        'import': lambda: cmd_import(args.arg) if args.arg else False,
        'rebuild': lambda: cmd_rebuild(args.arg) if args.arg else False,
        'reindex': cmd_reindex,
        'list': cmd_list,
        'migrate': cmd_migrate,
        'ensure-all': cmd_ensure_all,
    }
    fn = actions.get(args.action)
    if fn:
        ok = fn()
    else:
        ok = False

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
