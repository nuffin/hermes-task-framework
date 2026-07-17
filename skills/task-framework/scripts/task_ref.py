"""Task reference resolution utilities.

Usage:
    from task_ref import resolve_ref, check_cycles, create_task_meta
"""
import os, glob, json, hashlib, random, datetime, re, sys, subprocess

TASKS_ROOT = os.path.expanduser(os.environ.get("HERMES_TASKS_ROOT", "~/studio/hermes/tasks"))

def _hash6():
    return hashlib.md5(str(random.random()).encode()).hexdigest()[:6]

def resolve_ref(ref_str):
    """Resolve ref:hash/output_name to absolute path."""
    if not ref_str.startswith('ref:'):
        return ref_str
    parts = ref_str[4:].split('/', 1)
    hash_id = parts[0]
    output_name = parts[1] if len(parts) > 1 else None
    
    matches = glob.glob(os.path.join(TASKS_ROOT, f'*{hash_id}*'))
    if not matches:
        raise FileNotFoundError(f'Task with hash {hash_id} not found in {TASKS_ROOT}')
    
    task_dir = matches[0]
    meta_path = os.path.join(task_dir, '.hermes-task.json')
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f'.hermes-task.json not found in {task_dir}')
    
    with open(meta_path) as f:
        meta = json.load(f)
    
    if output_name:
        if output_name not in meta.get('outputs', {}):
            raise KeyError(f'Output "{output_name}" not declared in {task_dir}/.hermes-task.json. '
                           f'Available: {list(meta.get("outputs", {}).keys())}')
        return os.path.join(task_dir, meta['outputs'][output_name])
    
    return task_dir

def check_cycles(meta):
    """Walk dependency graph, raise ValueError on cycles."""
    seen = [meta['hash']]
    stack = list(meta.get('dependencies', []))
    while stack:
        h = stack.pop()
        if h in seen:
            raise ValueError(f'Cycle detected: {h} already in path {" → ".join(seen)}')
        seen.append(h)
        matches = glob.glob(os.path.join(TASKS_ROOT, f'*{h}*'))
        if matches:
            dep_meta_path = os.path.join(matches[0], '.hermes-task.json')
            if os.path.exists(dep_meta_path):
                dep_meta = json.load(open(dep_meta_path))
                stack.extend(dep_meta.get('dependencies', []))
    return True

def create_task_meta(task_dir, name, dependencies=None, related=None, supersedes=None, board="default"):
    """Create .hermes-task.json in a task directory. Returns the hash.
    Also creates a kanban card on the specified board and stores the card ID."""
    h = _hash6()
    meta = {
        "hash": h,
        "name": name,
        "created_at": datetime.datetime.now().isoformat(),
        "outputs": {},
        "dependencies": dependencies or [],
        "related": related or [],
        "supersedes": supersedes or [],
        "kanban_card_id": "",
    }
    
    # Check cycles before writing
    if meta['dependencies']:
        check_cycles(meta)
    
    meta_path = os.path.join(task_dir, '.hermes-task.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    # Create kanban card
    dirname = os.path.basename(task_dir)
    title = f"{name} [task:{dirname}]"
    env = {**os.environ}
    env.pop("HERMES_KANBAN_BOARD", None)  # Avoid env leak override
    try:
        result = subprocess.run(
            ["hermes", "kanban", "boards", "switch", board],
            capture_output=True, text=True, timeout=10, env=env,
        )
        result = subprocess.run(
            ["hermes", "kanban", "create", title, "--assignee", "default"],
            capture_output=True, text=True, timeout=15, env=env,
        )
        if result.returncode == 0:
            # Parse card ID from output: "Created t_xxx  (ready, ...)"
            out = result.stdout.strip()
            m = re.search(r'Created (t_[a-f0-9]+)', out)
            if m:
                card_id = m.group(1)
                meta["kanban_card_id"] = card_id
                # Update .hermes-task.json with card id
                with open(meta_path, 'w') as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  ⚠ kanban card creation failed: {e}", file=sys.stderr)
    
    return h

def set_output(task_dir, name, path):
    """Register a named output in .hermes-task.json."""
    meta_path = os.path.join(task_dir, '.hermes-task.json')
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f'No .hermes-task.json in {task_dir}')
    with open(meta_path) as f:
        meta = json.load(f)
    meta['outputs'][name] = path
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
