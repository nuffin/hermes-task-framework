#!/usr/bin/env python3
"""
Unified task runner — single entry point for all phases.

Usage:
    ./run.py                    — auto: find first unchecked item & execute
    ./run.py phase<N>           — run specific phase
    ./run.py list               — show checklist status

Auto mode (no args):
    1. Read TASK.md checklist, find first unchecked item
    2. If it's a BREAK, mark it done, continue to next Phase(s)
    3. Execute Phase(s) until next BREAK or end of list
"""

import sys, os, subprocess, re

TASK_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_MD = os.path.join(TASK_DIR, "TASK.md")
SCRIPTS = os.path.join(TASK_DIR, "scripts")
VENV_PY = os.path.expanduser("~/.venvs/playwright/bin/python")
PY = VENV_PY if os.path.exists(VENV_PY) else sys.executable


# ── Phase runners ──

def run_script(name, label):
    path = os.path.join(SCRIPTS, name)
    if not os.path.exists(path):
        print(f"  ❌ Script not found: {path}")
        return False
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    return subprocess.run([PY, path], cwd=TASK_DIR).returncode == 0


def phase1():
    return run_script("gen_tts.py", "Phase 1: Text-to-Speech")


def phase2():
    return run_script("record_timeline.py", "Phase 2: Browser Recording")


def phase3():
    # Example: inline call with generate_timeline_chart
    cmd = [
        PY, "-c",
        "import sys, os; "
        "sys.path.insert(0, os.path.expanduser('~/.hermes/personal-suite/skills/video-audio-compositing/scripts')); "
        "from utils.timeline import generate_timeline_chart; "
        "generate_timeline_chart('COMPOSITING.md', 'timeline-chart-xxxxxx/timeline_chart.txt', format='both')"
    ]
    print(f"\n{'='*60}")
    print(f"  Phase 3: Timeline Chart Preview")
    print(f"{'='*60}")
    return subprocess.run(cmd, cwd=TASK_DIR).returncode == 0


def phase4():
    return run_script("composite.py", "Phase 4: Compositing")


def phase5():
    print("  ⏭  Phase 5 not implemented yet — skipping")
    return True


def phase6():
    print("  ⏭  Phase 6 not implemented yet — skipping")
    return True


def phase7():
    print("  ⏭  Phase 7 not implemented yet — skipping")
    return True


PHASES = {
    "phase1": phase1, "phase2": phase2, "phase3": phase3,
    "phase4": phase4, "phase5": phase5, "phase6": phase6, "phase7": phase7,
}


# ── TASK.md checklist helpers ──

def parse_checklist():
    with open(TASK_MD) as f:
        lines = f.readlines()
    items = []
    for i, line in enumerate(lines):
        m = re.match(r'^- \[([ x])\] (.+)', line)
        if m:
            items.append((i, m.group(2), m.group(1) == 'x'))
    return items, lines


def mark_done(line_idx, lines):
    lines[line_idx] = lines[line_idx].replace("- [ ]", "- [x]", 1)
    with open(TASK_MD, 'w') as f:
        f.writelines(lines)
    return lines


def find_phase_num(text):
    m = re.search(r'Phase (\d+)', text)
    return int(m.group(1)) if m else None


def is_break(text):
    return text.strip().startswith("BREAK")


# ── Auto mode ──

def run_auto():
    items, lines = parse_checklist()
    unchecked = [(idx, txt) for idx, txt, chk in items if not chk]
    if not unchecked:
        print("✅ All checklist items completed!")
        return True

    idx, txt = unchecked[0]
    print(f"📋 First unchecked: {txt}")

    if is_break(txt):
        print(f"  → Marking BREAK complete, continuing...")
        lines = mark_done(idx, lines)
        items, lines = parse_checklist()
        unchecked = [(idx, txt) for idx, txt, chk in items if not chk]
        if not unchecked:
            print("✅ All items completed after marking BREAK!")
            return True
        idx, txt = unchecked[0]
        print(f"  → Next: {txt}")

    for idx, txt in unchecked:
        if is_break(txt):
            print(f"  ⏸  Stopping at BREAK: {txt}")
            break
        pnum = find_phase_num(txt)
        if pnum is None:
            print(f"  ⏭  Skipping (not a phase): {txt}")
            continue
        phase_key = f"phase{pnum}"
        fn = PHASES.get(phase_key)
        if fn is None:
            print(f"  ❌ No runner for {phase_key}")
            continue
        print(f"\n  ▶  Running {phase_key}...")
        ok = fn()
        if not ok:
            print(f"  ❌ {phase_key} failed!")
            return False
        lines = mark_done(idx, lines)

    print(f"\n{'='*60}")
    print(f"  ✅ Auto-run complete")
    print(f"{'='*60}")
    return True


def cmd_list():
    items, _ = parse_checklist()
    for _, txt, chk in items:
        status = "✅" if chk else "⬜"
        print(f"  {status} {txt}")


def main():
    if len(sys.argv) >= 2:
        cmd = sys.argv[1].strip().lower()
        if cmd == "list":
            cmd_list()
            return 0
        fn = PHASES.get(cmd)
        if fn:
            return 0 if fn() else 1
        print(f"❌ Unknown: {cmd}\n")
        print(__doc__)
        return 1
    return 0 if run_auto() else 1


if __name__ == "__main__":
    sys.exit(main())
