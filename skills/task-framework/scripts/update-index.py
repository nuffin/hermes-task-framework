#!/usr/bin/env python3
"""
update-index.py — Update tasks/ root index files.

Regenerates both:
  1. tasks/README.md  — summary table (directory façade)
  2. tasks/TASKS.md   — aggregated checklist view (deep overview)

Usage:
  python3 scripts/update-index.py                     # default: configured root or ~/studio/hermes/tasks
  python3 scripts/update-index.py --tasks-dir /path   # custom path
"""

import os, sys, re, glob


# ── config resolution (shared with manage_task.py) ──

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
    # 1. Env var: HERMES_TASKS_ROOT (preferred) or HERMES_TASKS_DIR (legacy)
    env = os.environ.get("HERMES_TASKS_ROOT", "").strip()
    if not env:
        env = os.environ.get("HERMES_TASKS_DIR", "").strip()
    if env:
        return os.path.expanduser(env)

    # 2. Per-profile config
    from pathlib import Path
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

    # 4. Canonical fallback. Never populate the legacy ~/.hermes/tasks root.
    return os.path.expanduser("~/studio/hermes/tasks")


TASKS_ROOT = _resolve_tasks_root()

def gather_tasks(tasks_root):
    """Return sorted list of (dirname, ts, name, title, status, desc, checklist, notes, related_tasks, related_tickets, cluster_info)."""
    task_dirs = sorted(glob.glob(os.path.join(tasks_root, "2*/")))
    results = []
    for d in task_dirs:
        if os.path.islink(d.rstrip('/')):
            raise ValueError(f'symlinked task directory refused: {d}')
        for input_name in ('TASK.md', '.hermes-task.json'):
            candidate = os.path.join(d, input_name)
            if os.path.islink(candidate):
                raise ValueError(f'symlinked index input refused: {candidate}')
        dirname = os.path.basename(d.rstrip('/'))
        parts = dirname.split('.', 1)
        ts = parts[0]
        name = parts[1] if len(parts) > 1 else dirname

        task_md_path = os.path.join(d, "TASK.md")
        title = name
        status = "—"
        desc = ""
        checklist = []
        notes = []
        related_tasks = []
        related_tickets = []
        cluster_info = {"affinity": "", "claimed_by": ""}

        # Read .hermes-task.json for cluster fields
        meta_path = os.path.join(d, ".hermes-task.json")
        if os.path.exists(meta_path):
            try:
                import json
                with open(meta_path) as f:
                    meta = json.load(f)
                cluster_info["affinity"] = meta.get("affinity", "")
                cluster_info["claimed_by"] = meta.get("claimed_by", "") or ""
            except Exception:
                pass

        if os.path.exists(task_md_path):
            content = open(task_md_path, encoding='utf-8').read()

            # Title: # Task: <title> or first # heading
            m = re.search(r'^# Task:\s*(.+)$', content, re.MULTILINE)
            if m:
                title = m.group(1).strip()
            else:
                m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if m:
                    title = m.group(1).strip()

            # Status: ## Status or ## 状态
            m = re.search(r'^## (?:Status|状态)\s*\n\s*(.+?)\s*$', content, re.MULTILINE)
            if m:
                status = m.group(1).strip()

            # Goal / Description: ## Goal or ## 目标 or ## 概述
            m = re.search(r'^## (?:Goal|目标|概述)\s*\n\s*(.+?)\s*$', content, re.MULTILINE)
            if m:
                desc = m.group(1).strip()

            # Checklist: ## Checklist or ## 步骤 or ## Checklist（步骤）
            in_cl = False
            for line in content.split('\n'):
                if line.startswith('## Checklist') or line.startswith('## 步骤'):
                    in_cl = True
                    continue
                if in_cl:
                    if line.startswith('## '):
                        break
                    if line.strip().startswith('- ['):
                        checklist.append(line.strip())

            # Notes: ## Notes or ## 备注
            in_nt = False
            for line in content.split('\n'):
                if line.startswith('## Notes') or line.startswith('## 备注'):
                    in_nt = True
                    continue
                if in_nt and line.startswith('## '):
                    break
                if in_nt and line.strip():
                    notes.append(line.strip())

            # Related Tasks: ## Related Tasks table
            in_rt = False
            header_skipped = False
            for line in content.split('\n'):
                if line.startswith('## Related Tasks'):
                    in_rt = True
                    header_skipped = False
                    continue
                if in_rt:
                    if line.startswith('## '):
                        break
                    if not line.strip():
                        continue
                    # Skip header row and separator row
                    striped = line.strip()
                    if striped.startswith('|') and '---' in striped:
                        header_skipped = True
                        continue
                    if striped.startswith('|') and header_skipped:
                        # Parse table row: | type | task_path | description |
                        cols = [c.strip() for c in striped.strip('|').split('|')]
                        if len(cols) >= 3:
                            rtype = cols[0].strip()
                            task_path = cols[1].strip().strip('`')
                            rdesc = cols[2].strip()
                            related_tasks.append({
                                'type': rtype,
                                'task_path': task_path,
                                'description': rdesc
                            })

            # Related Tickets: ## Related Tickets table
            in_rti = False
            header_skipped_rti = False
            for line in content.split('\n'):
                if line.startswith('## Related Tickets'):
                    in_rti = True
                    header_skipped_rti = False
                    continue
                if in_rti:
                    if line.startswith('## '):
                        break
                    if not line.strip():
                        continue
                    striped = line.strip()
                    if striped.startswith('|') and '---' in striped:
                        header_skipped_rti = True
                        continue
                    if striped.startswith('|') and header_skipped_rti:
                        cols = [c.strip() for c in striped.strip('|').split('|')]
                        if len(cols) >= 2:
                            ticket_id = cols[0].strip().strip('`').lstrip('#')
                            rdesc_ti = cols[1].strip()
                            related_tickets.append({
                                'ticket_id': ticket_id,
                                'description': rdesc_ti
                            })

        results.append((dirname, ts, name, title, status, desc, checklist, notes, related_tasks, related_tickets, cluster_info))
    return results

def gen_readme(tasks):
    """Generate README.md — summary table with ticket links."""
    lines = ["# Tasks", "",
             "Project tasks managed under `tasks/`. Each task is a self-contained unit of work.",
             "",
             "| Timestamp | Name | Status | Ticket | Description |",
             "|---|---|---|---|---|"]
    for dirname, ts, name, title, status, desc, _, _, _, related_tickets, cluster_info in tasks:
        s = status.replace('\n', ' ').strip()
        d = desc.replace('\n', ' ').strip()[:60]
        if not d:
            d = title[:60]
        ticket_tag = ""
        if related_tickets:
            ids = ", ".join(f"#{t['ticket_id']}" for t in related_tickets)
            ticket_tag = f"{ids}"
        cl_tag = ""
        if cluster_info.get("affinity") and cluster_info["affinity"] != "any":
            cl_tag = f"[{cluster_info['affinity']}]"
            if cluster_info.get("claimed_by"):
                cl_tag += f" →{cluster_info['claimed_by']}"
        lines.append(f"| {ts} | {name} | {s} {cl_tag} | {ticket_tag} | {d} |")

    # Inbox
    inbox_dir = os.path.join(TASKS_ROOT, "inbox")
    inbox_items = []
    if os.path.isdir(inbox_dir):
        inbox_items = sorted(os.listdir(inbox_dir))
    if inbox_items:
        lines.extend(["", "### Inbox"] + [f"- {item}" for item in inbox_items])

    lines.append("")
    return '\n'.join(lines)

def gen_tasks_md(tasks):
    """Generate TASKS.md — aggregated checklist view with relationship display."""
    lines = ["# Tasks 聚合索引", "",
             "所有任务的状态、Checklist 和关联关系汇总。由 `scripts/update-index.py` 自动生成，无需手动编辑。",
             "", "---", ""]
    for dirname, ts, name, title, status, desc, checklist, notes, related_tasks, related_tickets, cluster_info in tasks:
        lines.append(f"## [{name}]({dirname}/)")
        lines.append("")
        lines.append(f"**状态:** {status.replace(chr(10), ' ').strip()}")
        if cluster_info.get("affinity"):
            cl_line = f"**Cluster:** affinity={cluster_info['affinity']}"
            if cluster_info.get("claimed_by"):
                cl_line += f", claimed_by={cluster_info['claimed_by']}"
            lines.append(cl_line)
            lines.append("")
        if desc:
            lines.append("")
            lines.append(f"**目标:** {desc}")
        lines.append("")
        lines.append(f"**目录:** `{dirname}/`")

        # TODO intake is shown separately from the executable checklist.
        task_path = os.path.join(TASKS_ROOT, dirname, "TASK.md")
        try:
            from todo_lifecycle import parse_todos, validate_todos
            todo_text = open(task_path, encoding="utf-8").read()
            todo_items = parse_todos(todo_text)
            todo_errors = validate_todos(todo_text)
        except (OSError, ImportError):
            todo_items, todo_errors = [], []
        if todo_items or todo_errors:
            unresolved = sum(item["status"] == "open" for item in todo_items) + len(todo_errors)
            lines.append("")
            lines.append(f"### TODO ({unresolved}/{len(todo_items) + len(todo_errors)} unresolved)")
            for item in todo_items:
                lines.append(f"- `{item['id']}` [{item['status']}; {item['scope']}] {item['requirement']} → {item['route'] or 'needs routing'}")
            for error in todo_errors:
                lines.append(f"- ⚠ invalid TODO: {error}")

        # Related tasks display
        if related_tasks:
            lines.append("")
            lines.append("**关联任务:**")
            lines.append("")
            lines.append("| 关系 | 任务 | 说明 |")
            lines.append("|------|------|------|")
            for rt in related_tasks:
                t = rt['type']
                p = rt['task_path']
                d = rt['description']
                lines.append(f"| {t} | `{p}` | {d} |")

        # Related tickets display
        if related_tickets:
            lines.append("")
            lines.append("**关联 Ticket:**")
            for rti in related_tickets:
                tid = rti['ticket_id']
                td = rti['description']
                lines.append(f"- #{tid} — {td}")

        # Nested subtasks are shown under their root parent, never as root rows.
        child_root = os.path.join(TASKS_ROOT, dirname, "subtasks")
        # Legacy children may not have a timestamp prefix.  Only enumerate
        # real, marked direct children; never follow symlinks outside parent.
        child_dirs = []
        if os.path.isdir(child_root) and not os.path.islink(child_root):
            expected = os.path.realpath(child_root)
            for entry in os.scandir(child_root):
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    continue
                real = os.path.realpath(entry.path)
                try:
                    contained = os.path.commonpath([expected, real]) == expected
                except ValueError:
                    contained = False
                if (contained and real != expected and os.path.dirname(real) == expected
                        and (os.path.isfile(os.path.join(entry.path, "TASK.md"))
                             or os.path.isfile(os.path.join(entry.path, ".hermes-task.json")))):
                    child_dirs.append(entry.path)
        child_dirs.sort()
        if child_dirs:
            lines.append("")
            lines.append("### Subtasks")
            for child in child_dirs:
                child_name = os.path.basename(child)
                child_status = "—"
                child_md = os.path.join(child, "TASK.md")
                if os.path.islink(child_md):
                    raise ValueError(f'symlinked child index input refused: {child_md}')
                if os.path.exists(child_md):
                    cm = re.search(r'^## (?:Status|状态)\s*\n\s*(.+?)\s*$', open(child_md, encoding='utf-8').read(), re.MULTILINE)
                    if cm:
                        child_status = cm.group(1).strip()
                lines.append(f"- [{child_name}]({dirname}/subtasks/{child_name}/) — {child_status}")

        if checklist:
            done = sum(1 for c in checklist if c.startswith('- [x]'))
            total = len(checklist)
            lines.append("")
            lines.append(f"### Checklist ({done}/{total} done)")
            for item in checklist:
                lines.append(f"- {item}")

        if notes:
            lines.append("")
            lines.append("### Notes")
            for n in notes[:5]:
                lines.append(f"- {n}")

        lines.extend(["", "---", ""])
    return '\n'.join(lines)

def get_inbox(tasks_root):
    inbox_dir = os.path.join(tasks_root, "inbox")
    items = []
    if os.path.isdir(inbox_dir):
        items = [f for f in os.listdir(inbox_dir)
                 if os.path.isfile(os.path.join(inbox_dir, f)) or os.path.isdir(os.path.join(inbox_dir, f))]
    return sorted(items)

def _write_index_atomically(tasks_root, name, content):
    """Replace a regular root index without following symlinks or hardlinks."""
    import tempfile
    import stat
    root = os.path.realpath(tasks_root)
    path = os.path.join(root, name)
    if os.path.lexists(path):
        mode = os.lstat(path).st_mode
        if not stat.S_ISREG(mode):
            raise ValueError(f'index target must be a regular file: {path}')
    descriptor, temporary = tempfile.mkstemp(prefix='.task-index-', dir=root)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o644)
        # rename replaces a raced symlink itself; never opens its target for writing.
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def write_readme(tasks_root):
    tasks = gather_tasks(tasks_root)
    content = gen_readme(tasks)
    path = _write_index_atomically(tasks_root, 'README.md', content)
    return path, len(content)

def write_tasks_md(tasks_root):
    tasks = gather_tasks(tasks_root)
    content = gen_tasks_md(tasks)
    path = _write_index_atomically(tasks_root, 'TASKS.md', content)
    return path, len(content)

def main():
    tasks_root = TASKS_ROOT
    for i, arg in enumerate(sys.argv[1:]):
        if arg == '--tasks-dir' and i+2 < len(sys.argv):
            tasks_root = os.path.abspath(sys.argv[i+2])

    if not os.path.isdir(tasks_root):
        print(f"Error: tasks root not found: {tasks_root}", file=sys.stderr)
        sys.exit(1)

    from task_write_lock import task_writer_lock
    with task_writer_lock(tasks_root):
        p1, s1 = write_readme(tasks_root)
        p2, s2 = write_tasks_md(tasks_root)
    tasks = gather_tasks(tasks_root)
    print(f"Updated:")
    print(f"  {p1}  ({s1}B)")
    print(f"  {p2}  ({s2}B)")
    print(f"  Found {len(tasks)} active tasks")

if __name__ == '__main__':
    main()
