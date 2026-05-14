#!/usr/bin/env python3
"""AutoSkillsCC Command Hook — lightweight, pure stdlib, zero dependencies.

Handles --skill-* magic commands. Always runs BEFORE the heavy recommend.py hook.
Cannot crash on model load or API failure because it doesn't touch any of that.
"""
import json, sys
from pathlib import Path

if sys.platform == 'win32':
    for _s in (sys.stdin, sys.stdout):
        try:
            _s.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

DIR_PATH    = Path(__file__).parent.parent
STATE_FILE  = DIR_PATH / '.enabled'
SKILLS_JSON = DIR_PATH / 'skills.json'

SKILLS_ROOTS = [
    Path('/mnt/skills/public'),
    Path.home() / '.claude' / 'skills',
    DIR_PATH / 'skills',
]

MAGIC = {
    '--skill-off':    'off',
    '--skill-on':     'on',
    '--skill-list':   'list',
    '--skill-status': 'status',
    '--skill-debug':  'debug',
    '.skill-off':     'off',
    '.skill-on':      'on',
    '.skill-list':    'list',
    '.skill-status':  'status',
    '.skill-debug':   'debug',
}

def load_index():
    if not SKILLS_JSON.exists():
        return []
    try:
        raw = json.loads(SKILLS_JSON.read_text(encoding='utf-8'))
    except Exception:
        return []
    return raw if isinstance(raw, list) else []

def detect_magic(prompt):
    p = prompt.strip().lower()
    if p in MAGIC:
        return MAGIC[p]
    for key in MAGIC:
        if p.endswith(key):
            return MAGIC[key]
    return None

def inject(text):
    print(json.dumps({
        'continue': True,
        'prependUserPrompt': (
            '[System directive] Management command. '
            'Do NOT use any tools. Reply ONLY this exact output:\n' + text
        )
    }, ensure_ascii=False))
    sys.exit(0)

def ok():
    print(json.dumps({'continue': True}))
    sys.exit(0)

def extract_prompt(data):
    for field in ['prompt', 'user_prompt', 'userPrompt', 'message', 'text', 'input']:
        val = data.get(field)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, list):
            parts = [b.get('text', '') for b in val
                     if isinstance(b, dict) and b.get('type') == 'text']
            j = ' '.join(parts).strip()
            if j:
                return j
    return ''

def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        ok()

    prompt = extract_prompt(data)
    if not prompt:
        ok()

    cmd = detect_magic(prompt)
    if not cmd:
        ok()

    idx = load_index()
    n = len(idx)

    if cmd == 'off':
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        inject('>> 🔴 技能自动加载：已关闭 <<')

    elif cmd == 'on':
        STATE_FILE.touch()
        inject('>> 🟢 技能自动加载：已开启 <<')

    elif cmd == 'list':
        if idx:
            lines = [f'- **{s["name"]}**: {s.get("description", "")[:60]}' for s in idx]
        else:
            lines = ['(暂无已注册技能)']
        inject(f'>> 📋 已注册技能 ({n}) <<\n\n' + '\n'.join(lines))

    elif cmd == 'status':
        enabled = STATE_FILE.exists()
        icon = '🟢' if enabled else '🔴'
        status = '已开启' if enabled else '已关闭'
        inject(f'>> {icon} 技能状态：{status} | 已注册 {n} 个技能 <<')

    elif cmd == 'debug':
        lines = ['>> 🔍 AutoSkillsCC 诊断报告 <<\n']
        lines.append(f'状态: {"🟢 已开启" if STATE_FILE.exists() else "🔴 已关闭"}')
        lines.append(f'skills.json: {n} 个技能' + (' ✅' if n else ' ❌'))
        for root in SKILLS_ROOTS:
            mark = '✅' if root.is_dir() else '—'
            lines.append(f'技能目录 [{mark}] {root}')
        lines.append(f'\nPython: {sys.executable}')
        lines.append('\n可用: --skill-status | --skill-list | --skill-on | --skill-off | --skill-debug')
        inject('\n'.join(lines))

    ok()

if __name__ == '__main__':
    main()
