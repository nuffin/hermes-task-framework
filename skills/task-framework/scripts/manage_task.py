#!/usr/bin/env python3
"""
task-framework 任务生命周期管理工具

管理 ~/studio/hermes/tasks/ 下的任务文件（默认，可通过 config.yaml 配置）。
不再使用镜像目录——所有文件直接存放在任务目录下。

配置优先级（同 token-consumption-tracker 模式）：
  1. HERMES_TASKS_ROOT 或 HERMES_TASKS_DIR 环境变量
  2. 当前 profile config.yaml: tasks.data_dir
  3. 全局 ~/.hermes/config.yaml: tasks.data_dir
  4. Fallback: ~/studio/hermes/tasks

Commands:
    create    创建新任务（目录 + hash + 元数据 + 模板 + 可选 inbox 移入）
    accept    从 inbox 条目创建任务（文件/目录自动处理）
    decline   拒绝 inbox 条目，移到 declined/
    status    更新任务状态
    view      查看 README.md + TASK.md
    reset     重置任务（清 output/、重置 checkbox、重设状态）
    list      列出所有任务（直接扫描目录）
    reindex   重建索引文件（README.md + TASKS.md）
    init      为任务创建目录 + TASK.md + CHANGELOG.md + .hermes-task.json
    export    将任务打包为可移植 tar.gz
    import    从 tar.gz 恢复任务
    rebuild   按 hash 查找最近 tar.gz 并导入
    migrate   一次性迁移：将旧存储目录下的文件迁移到统一目录
    ensure-all 全量注册所有现有任务
"""
import os, sys, glob, json, shutil, re, tarfile, tempfile, hashlib, random, argparse, secrets
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


def _hash6():
    """Generate a cryptographically-secure 6-char hex hash."""
    return secrets.token_hex(3)


# Legacy alias for backward compat
def hash6():
    return _hash6()


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
    mem_f = os.path.join(task_dir, "CHANGELOG.md")
    meta_f = os.path.join(task_dir, ".hermes-task.json")

    if not os.path.exists(task_f):
        with open(task_f, 'w') as f:
            f.write("# Task: --\n\n## Status\n\nactive\n\n## Goal\n\n\n## Checklist\n\n")
        print(f"  Created: {task_f}")

    if not os.path.exists(mem_f):
        with open(mem_f, 'w') as f:
            f.write(f"# CHANGELOG.md -- {h}\n\n")
        print(f"  Created: {mem_f}")

    if not os.path.exists(meta_f):
        with open(meta_f, 'w') as f:
            json.dump({
                "hash": h,
                "name": "",
                "created_at": datetime.now().isoformat(timespec='seconds'),
                "outputs": {},
                "dependencies": [],
                "related": [],
                "supersedes": [],
                "affinity": "any",
                "claimed_by": None,
                "requires": [],
                "required_by": [],
                "priority": 2,
            }, f, indent=2, ensure_ascii=False)
        print(f"  Created: {meta_f}")

    for d in ['input', 'output']:
        dp = os.path.join(task_dir, d)
        os.makedirs(dp, exist_ok=True)

    return task_f, mem_f, meta_f


# ── safe file moves (cp + verify + rm, never raw mv) ──

def _safe_move_file(src, dst):
    """Copy file to dst, verify size match, then remove src.

    On verification failure: removes the partial copy, raises IOError,
    src is left untouched.
    On src removal failure: warns but does not raise (dst is verified good).
    """
    shutil.copy2(src, dst)
    src_size = os.path.getsize(src)
    dst_size = os.path.getsize(dst)
    if src_size != dst_size:
        os.remove(dst)
        raise IOError(f"Size mismatch: {src} ({src_size}) -> {dst} ({dst_size})")
    try:
        os.remove(src)
    except OSError as e:
        print(f"WARNING: dst verified but could not remove src {src}: {e}", file=sys.stderr)


def _safe_move_dir(src_dir, dst_dir):
    """Copy directory tree to dst, verify all files, then remove src.

    On verification failure: removes the partial copy (rmtree dst),
    raises IOError, src is left untouched.
    On src removal failure: warns but does not raise.
    """
    if os.path.exists(dst_dir):
        raise IOError(f"Destination already exists: {dst_dir}")
    shutil.copytree(src_dir, dst_dir)
    # Verify every file in src exists in dst with matching size
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            src_f = os.path.join(root, f)
            rel = os.path.relpath(src_f, src_dir)
            dst_f = os.path.join(dst_dir, rel)
            if not os.path.exists(dst_f) or os.path.getsize(src_f) != os.path.getsize(dst_f):
                shutil.rmtree(dst_dir, ignore_errors=True)
                raise IOError(f"Verification failed: {src_f} -> {dst_f}")
    try:
        shutil.rmtree(src_dir)
    except OSError as e:
        print(f"WARNING: dst verified but could not remove src {src_dir}: {e}", file=sys.stderr)


# ── template / path helpers ──

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TEMPLATE_DIR = os.path.join(_SCRIPT_DIR, '..', 'templates')


def _load_template(name):
    """Load a template file from templates/, return content or empty string."""
    path = os.path.join(_TEMPLATE_DIR, name)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return ''


def _run_update_index():
    """Run update-index.py to regenerate README.md and TASKS.md."""
    import subprocess
    script = os.path.join(_SCRIPT_DIR, 'update-index.py')
    if os.path.exists(script):
        subprocess.run([sys.executable, script], check=True, capture_output=True, text=True)


def _resolve_task_dir(hash_or_dir):
    """Resolve hash6, directory path, or task name to task directory path."""
    if re.match(r'^[a-z0-9]{6}$', hash_or_dir):
        d = _find_task_dir_by_hash(hash_or_dir)
        if d:
            return d
    abs_path = os.path.abspath(hash_or_dir)
    if os.path.isdir(abs_path):
        return abs_path
    for pattern in [f"*.{hash_or_dir}*", f"*{hash_or_dir}*"]:
        matches = sorted(glob.glob(os.path.join(TASKS_ROOT, pattern)))
        if matches:
            return matches[0]
    return None


def _derive_name(inbox_item):
    """Derive a task name from an inbox item filename or directory name."""
    base = os.path.splitext(inbox_item)[0]
    base = re.sub(r'^\d{8}-', '', base)
    base = re.sub(r'[^a-z0-9-]', '', base.lower().replace(' ', '-'))
    return base.strip('-')


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
    """Rebuild all index files: README.md + TASKS.md (via update-index.py)."""
    _run_update_index()
    return True


def cmd_list():
    """List all tasks by scanning directories directly (not a cached index)."""
    task_dirs = _find_all_task_dirs()
    if not task_dirs:
        print("No tasks found.")
        return True

    # Header
    print(f"{'Timestamp':<20} {'Name':<40} {'Hash':<8} {'Status':<12} {'Done':>6}")
    print(f"{'-'*20} {'-'*40} {'-'*8} {'-'*12} {'-'*6}")

    for d in task_dirs:
        name = os.path.basename(d)
        parts = name.split('.', 1)
        ts = parts[0]
        task_name = parts[1] if len(parts) > 1 else name
        h = _task_hash_from_dir(d) or '?'
        status = '?'
        done_count = 0
        total_count = 0
        task_md = os.path.join(d, "TASK.md")
        if os.path.exists(task_md):
            content = open(task_md, encoding='utf-8').read()
            m = re.search(r'## Status\s*\n\s*(\w+)', content)
            if m:
                status = m.group(1)
            for line in content.split('\n'):
                if line.strip().startswith('- [x]'):
                    done_count += 1
                elif line.strip().startswith('- [ ]'):
                    total_count += 1
            total_count += done_count
        print(f"{ts:<20} {task_name:<40} {h:<8} {status:<12} {done_count}/{total_count}")

    # Inbox and declined
    inbox_dir = os.path.join(TASKS_ROOT, "inbox")
    declined_dir = os.path.join(TASKS_ROOT, "declined")
    inbox_items = sorted(os.listdir(inbox_dir)) if os.path.isdir(inbox_dir) else []
    declined_items = sorted(os.listdir(declined_dir)) if os.path.isdir(declined_dir) else []
    if inbox_items:
        print(f"\n=== Inbox ({len(inbox_items)}) ===")
        for item in inbox_items:
            print(f"  {item}")
    if declined_items:
        print(f"\n=== Declined ({len(declined_items)}) ===")
        for item in declined_items:
            print(f"  {item}")
    return True


def cmd_migrate():
    """One-shot migration: copy files from old personal storage to task dir."""
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
            ("memory.md", "CHANGELOG.md"),
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


# ── create / accept / decline ─────────────────────────────────────

def cmd_create(name, from_inbox=None, description=None):
    """Create a new task: directory + hash + meta + templates + (optional inbox file/dir move)."""
    h = hash6()
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    slug = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-')).strip('-')
    if not slug:
        slug = 'task'
    dir_name = f"{ts}.{slug}-{h}"
    task_dir = os.path.join(TASKS_ROOT, dir_name)
    os.makedirs(task_dir, exist_ok=True)

    # Subdirs
    for sub in ['input', os.path.join('output', 'docs'), os.path.join('output', 'logs'), 'scripts']:
        os.makedirs(os.path.join(task_dir, sub), exist_ok=True)

    # .hermes-task.json
    meta = {
        "hash": h,
        "name": slug,
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "outputs": {},
        "dependencies": [],
        "related": [],
        "supersedes": [],
        "affinity": "any",
        "claimed_by": None,
        "requires": [],
        "required_by": [],
        "priority": 2,
    }
    meta_path = os.path.join(task_dir, ".hermes-task.json")
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # TASK.md from template
    task_tmpl = _load_template('TASK.md')
    if task_tmpl:
        task_content = task_tmpl.replace('<Name>', slug)
        if description:
            task_content = task_content.replace(
                '<one-liner>',
                description.replace('\\n', '\n'))
    else:
        task_content = f"# Task: {slug}\n\n## Status\n\nactive\n\n## Goal\n\n{description or ''}\n\n## Checklist\n\n"
    with open(os.path.join(task_dir, 'TASK.md'), 'w') as f:
        f.write(task_content)

    # CHANGELOG.md from template
    cl_tmpl = _load_template('CHANGELOG.md')
    if cl_tmpl:
        cl_content = cl_tmpl.replace(
            '## 2026-06-06 HH:MM',
            f"## {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    else:
        cl_content = f"# CHANGELOG.md -- {h}\n"
    with open(os.path.join(task_dir, 'CHANGELOG.md'), 'w') as f:
        f.write(cl_content)

    # README.md
    readme_content = f"# {slug}\n\nTask hash: {h}\n\n{description or ''}\n"
    with open(os.path.join(task_dir, 'README.md'), 'w') as f:
        f.write(readme_content)

    # Move inbox source if requested
    inbox_info = ''
    if from_inbox:
        inbox_path = os.path.join(TASKS_ROOT, 'inbox', from_inbox)
        if not os.path.exists(inbox_path):
            print(f"WARNING: inbox item not found: {inbox_path}")
        else:
            input_dir = os.path.join(task_dir, 'input')
            if os.path.isfile(inbox_path):
                _safe_move_file(inbox_path, os.path.join(input_dir, os.path.basename(inbox_path)))
            else:
                _safe_move_dir(inbox_path, os.path.join(input_dir, os.path.basename(from_inbox)))
            inbox_info = f"\n  inbox source moved to input/: {from_inbox}"

    _run_update_index()
    print(f"Created task:\n  hash={h}\n  dir={task_dir}{inbox_info}")
    return True


def cmd_accept(inbox_item, name=None):
    """Accept an inbox item: create task + move inbox file/dir into input/.

    If inbox_item is a directory, its contents are merged into input/.
    If name is not given, derive from the inbox item name.
    """
    inbox_path = os.path.join(TASKS_ROOT, 'inbox', inbox_item)
    if not os.path.exists(inbox_path):
        print(f"Inbox item not found: {inbox_path}")
        return False
    if not name:
        name = _derive_name(inbox_item)
    return cmd_create(name, from_inbox=inbox_item)


def cmd_decline(inbox_item, reason=''):
    """Move an inbox item to declined/ with a DECLINED.md stub."""
    inbox_path = os.path.join(TASKS_ROOT, 'inbox', inbox_item)
    if not os.path.exists(inbox_path):
        print(f"Inbox item not found: {inbox_path}")
        return False

    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    declined_dir = os.path.join(TASKS_ROOT, 'declined')
    os.makedirs(declined_dir, exist_ok=True)
    # Use basename to prevent path injection from inbox_item containing separators
    safe_name = os.path.basename(inbox_item)
    dest = os.path.join(declined_dir, f"{ts}.{safe_name}")
    if os.path.isfile(inbox_path):
        _safe_move_file(inbox_path, dest)
        # For files: DECLINED.md is a sibling, not a child
        declined_md = os.path.join(declined_dir, f"{ts}.DECLINED-{safe_name}.md")
        with open(declined_md, 'w') as f:
            f.write(f"# Declined: {inbox_item}\n\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\nReason: {reason}\n")
    else:
        _safe_move_dir(inbox_path, dest)
        # For directories: DECLINED.md goes inside
        with open(os.path.join(dest, 'DECLINED.md'), 'w') as f:
            f.write(f"# Declined: {inbox_item}\n\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\nReason: {reason}\n")
    print(f"Declined: {inbox_item} -> declined/{ts}.{safe_name}")
    return True


# ── status / view / reset ─────────────────────────────────────────

def cmd_status(hash_or_dir, new_status, reason=''):
    """Update the ## Status line in TASK.md."""
    task_dir = _resolve_task_dir(hash_or_dir)
    if not task_dir:
        print(f"Task not found: {hash_or_dir}")
        return False
    task_md = os.path.join(task_dir, 'TASK.md')
    if not os.path.exists(task_md):
        print(f"TASK.md not found: {task_md}")
        return False

    content = open(task_md, encoding='utf-8').read()
    valid = ['active', 'paused', 'completed', 'cancelled', 'failed',
             'pending', 'claimed', 'in_progress', 'pending_review', 'done']
    if new_status not in valid:
        print(f"Invalid status '{new_status}'. Valid: {', '.join(valid)}")
        return False

    suffix = f" — {reason}" if reason else ""
    replacement = f"{new_status}{suffix}"
    new_content = re.sub(
        r'(^## Status\s*\n\s*).+',
        lambda m: m.group(1) + replacement,
        content, count=1, flags=re.MULTILINE)
    if new_content == content:
        new_content = content.rstrip() + f"\n\n## Status\n\n{replacement}\n"
    with open(task_md, 'w') as f:
        f.write(new_content)

    _run_update_index()
    print(f"Status updated: {new_status}{suffix}")
    print(f"  task: {task_dir}")
    return True


def cmd_view(hash_or_dir):
    """Locate task by hash/dir/name and print README.md + TASK.md."""
    task_dir = _resolve_task_dir(hash_or_dir)
    if not task_dir:
        print(f"Task not found: {hash_or_dir}")
        return False
    readme = os.path.join(task_dir, 'README.md')
    task_md = os.path.join(task_dir, 'TASK.md')
    if os.path.exists(readme):
        print(open(readme, encoding='utf-8').read())
        print("---")
    if os.path.exists(task_md):
        print(open(task_md, encoding='utf-8').read())
    return True


def cmd_reset(hash_or_dir, hard=True):
    """Reset a task: clear output/ (hard), reset checkboxes, set status to active."""
    task_dir = _resolve_task_dir(hash_or_dir)
    if not task_dir:
        print(f"Task not found: {hash_or_dir}")
        return False

    # 1. Clear output/ (hard mode)
    output_dir = os.path.join(task_dir, 'output')
    if hard and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        for sub in ['docs', 'logs']:
            os.makedirs(os.path.join(output_dir, sub), exist_ok=True)
        print(f"  Cleared output/")

    # 2. Reset checkboxes [x] → [ ] (preserve [x] DONE:)
    task_md = os.path.join(task_dir, 'TASK.md')
    if os.path.exists(task_md):
        content = open(task_md, encoding='utf-8').read()
        new_content = re.sub(r'- \[x\](?!\s*DONE:)', '- [ ]', content)
        with open(task_md, 'w') as f:
            f.write(new_content)
        if new_content != content:
            print(f"  Reset checkboxes [x] → [ ]")

    # 3. Reset status to active
    h = _task_hash_from_dir(task_dir) or ''
    cmd_status(task_dir, 'active')

    _run_update_index()
    print(f"Reset complete: {task_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Task lifecycle management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
new commands:
  create <name> [--from-inbox <file-or-dir>] [--desc <text>]   Create a new task
  accept <inbox_item> [--name <task-name>]                     Accept inbox item into a new task
  decline <inbox_item> [--reason <text>]                       Move inbox item to declined/
  status <hash_or_dir> <status> [--reason <text>]             Update task status
  view <hash_or_dir>                                           Print README.md + TASK.md
  reset <hash_or_dir> [--no-hard]                              Reset task (clear output, checkboxes, status)
""")
    parser.add_argument('action', choices=[
        'init', 'export', 'import', 'rebuild',
        'reindex', 'list', 'migrate', 'ensure-all',
        'create', 'accept', 'decline', 'status', 'view', 'reset'
    ])
    parser.add_argument('args', nargs='*', default=[], help='positional args for the action')
    parser.add_argument('--from-inbox', dest='from_inbox', default=None,
                        help='(create) inbox file or directory to move into input/')
    parser.add_argument('--desc', dest='description', default=None,
                        help='(create) task goal / description text')
    parser.add_argument('--name', dest='task_name', default=None,
                        help='(accept) override auto-derived task name')
    parser.add_argument('--reason', dest='reason', default='',
                        help='(status/decline) reason text')
    parser.add_argument('--no-hard', dest='hard', action='store_false', default=True,
                        help='(reset) do NOT clear output/, only reset checkboxes + status')
    args = parser.parse_args()

    actions = {
        'init':       lambda: cmd_init(args.args[0]) if args.args else False,
        'export':     lambda: cmd_export(args.args[0]) if args.args else False,
        'import':     lambda: cmd_import(args.args[0]) if args.args else False,
        'rebuild':    lambda: cmd_rebuild(args.args[0]) if args.args else False,
        'reindex':    cmd_reindex,
        'list':       cmd_list,
        'migrate':    cmd_migrate,
        'ensure-all': cmd_ensure_all,
        'create':     lambda: cmd_create(args.args[0], from_inbox=args.from_inbox, description=args.description) if args.args else False,
        'accept':     lambda: cmd_accept(args.args[0], name=args.task_name) if args.args else False,
        'decline':    lambda: cmd_decline(args.args[0], reason=args.reason) if args.args else False,
        'status':     lambda: cmd_status(args.args[0], args.args[1], reason=args.reason) if len(args.args) >= 2 else False,
        'view':       lambda: cmd_view(args.args[0]) if args.args else False,
        'reset':      lambda: cmd_reset(args.args[0], hard=args.hard) if args.args else False,
    }
    fn = actions.get(args.action)
    ok = fn() if fn else False
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
