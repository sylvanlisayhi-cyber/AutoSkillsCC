#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook - semantic skill router with magic commands."""
import json, sys, io, os, traceback, warnings, logging
from pathlib import Path

# ═══ 环境静音：消灭 HuggingFace/tqdm 的终端噪音 ═══
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
os.environ.setdefault('TRANSFORMERS_VERBOSITY', 'error')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
warnings.filterwarnings('ignore')
for _mod in ('sentence_transformers', 'transformers', 'tokenizers', 'tqdm', 'huggingface_hub'):
    logging.getLogger(_mod).setLevel(logging.ERROR)

if sys.platform == 'win32':
    sys.stdin  = io.TextIOWrapper(sys.stdin.buffer,  encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DIR_PATH    = Path(__file__).parent.parent
SKILLS_JSON = DIR_PATH / 'skills.json'
VECTOR_DB   = DIR_PATH / 'skills_vectors.npy'
STATE_FILE  = DIR_PATH / '.enabled'
MAX_SKILL_LEN = 6000
SKILLS_ROOTS = [
    Path.home() / '.claude' / 'skills',
    DIR_PATH / 'skills',
]
SIMILARITY_THRESHOLD = 0.40

C = {'R': '\033[31m', 'G': '\033[32m', 'Y': '\033[33m', 'C': '\033[36m', 'D': '\033[90m', 'X': '\033[0m'}

_model = None
_vecs  = None

def log(color, msg):
    sys.stderr.write(C[color] + '[AI Router] ' + msg + C['X'] + '\n')
    sys.stderr.flush()

def ok():
    print(json.dumps({'continue': True}))
    sys.exit(0)

def inject(prefix):
    """将提示注入到 Claude 上下文（走聊天窗口，用户可见）"""
    print(json.dumps({'continue': True, 'prependUserPrompt': prefix}, ensure_ascii=False))
    sys.exit(0)

def find_skills_root():
    for p in SKILLS_ROOTS:
        if p.is_dir():
            return p
    return None

def load_index():
    if not SKILLS_JSON.exists():
        log('Y', 'skills.json not found')
        return []
    try:
        with open(SKILLS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log('R', 'Failed to load skills.json: ' + str(e))
        return []

def extract_prompt(data):
    for field in ['prompt', 'user_prompt', 'userPrompt', 'message', 'text', 'input']:
        val = data.get(field)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, list):
            parts = [b.get('text', '') for b in val if isinstance(b, dict) and b.get('type') == 'text']
            j = ' '.join(parts).strip()
            if j:
                return j
    return ''

MAGIC = {
    '--skill-off':  'off',
    '--skill-on':   'on',
    '--skill-list': 'list',
    '--skill-status': 'status',
}

def handle_magic(prompt):
    p = prompt.strip().lower()
    cmd = MAGIC.get(p)
    if not cmd:
        for key in MAGIC:
            if p.startswith(key):
                cmd = MAGIC[key]
                break
    if not cmd:
        return None

    if cmd == 'off':
        existed = STATE_FILE.exists()
        if existed:
            STATE_FILE.unlink()
        log('Y', chr(0x1f534) + ' Auto-load disabled')
        inject(
            '[System directive] The user sent a management command. '
            'Ignore their original message. Your ENTIRE response must be ONLY: '
            + ('"🟢 技能自动加载已关闭"' if existed else '"⚠️ 技能自动加载已经是关闭状态"')
        )

    elif cmd == 'on':
        existed = STATE_FILE.exists()
        if not existed:
            STATE_FILE.touch()
        log('G', chr(0x1f7e2) + ' Auto-load enabled')
        inject(
            '[System directive] The user sent a management command. '
            'Ignore their original message. Your ENTIRE response must be ONLY: '
            + ('"🟢 技能自动加载已开启"' if not existed else '"⚠️ 技能自动加载已经是开启状态"')
        )

    elif cmd == 'list':
        idx = load_index()
        if idx:
            lines = []
            for s in idx:
                name = s.get('name', '?')
                desc = s.get('description', '')[:60]
                lines.append(f'- **{name}**: {desc}')
            body = '\n'.join(lines)
        else:
            body = '(无已注册技能)'
        log('C', f'Listed {len(idx) if idx else 0} skills')
        inject(
            '[System directive] The user sent a management command. '
            'Ignore their original message. Your ENTIRE response must be ONLY the following markdown, '
            'translated to Chinese labels:\n\n'
            f'## 📋 已注册技能 ({len(idx) if idx else 0})\n\n{body}'
        )

    elif cmd == 'status':
        enabled = STATE_FILE.exists()
        idx = load_index()
        n = len(idx) if idx else 0
        status_icon = '🟢' if enabled else '🔴'
        status_text = '已开启' if enabled else '已关闭'
        log('G' if enabled else 'Y', f'Status: {"ENABLED" if enabled else "DISABLED"}, {n} skills')
        inject(
            '[System directive] The user sent a management command. '
            'Ignore their original message. Your ENTIRE response must be ONLY: '
            f'"{status_icon} 技能自动加载：{status_text} | 已注册 {n} 个技能"'
        )
    return None

def read_skill(name, root):
    f = root / name / 'SKILL.md'
    if not f.exists():
        log('Y', 'SKILL.md missing for: ' + name)
        return None
    try:
        c = f.read_text(encoding='utf-8', errors='replace')
        if len(c) > MAX_SKILL_LEN:
            c = c[:MAX_SKILL_LEN]
            last_nl = c.rfind('\n')
            if last_nl > MAX_SKILL_LEN // 2:
                c = c[:last_nl]
            c += '\n\n[...content truncated]'
        return c
    except Exception as e:
        log('R', 'Read failed for ' + name + ': ' + str(e))
        return None

# ═══ Keyword fallback ═══
def match_keyword(prompt, index):
    pl = prompt.lower()
    best_score, best_entry = 0, None
    for entry in index:
        score = sum(1 for kw in entry.get('keywords', []) if kw.lower() in pl)
        if score > best_score:
            best_score, best_entry = score, entry
    return best_entry if best_score > 0 else None

# ═══ Intent filter ═══
def is_just_asking(prompt):
    question_words = [
        '是什么', '为什么', '怎么理解', '对比', '区别',
        '八股文', '原理', '什么是', '如何理解', '因为'
    ]
    return any(w in prompt for w in question_words)

# ═══ Semantic matching ═══
def cosine_similarity(v1, v2):
    import numpy as np
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

def _ensure_model():
    global _model, _vecs
    if _model is not None:
        return True

    if not VECTOR_DB.exists():
        return False

    import numpy as np
    try:
        _vecs = np.load(VECTOR_DB)
    except Exception as e:
        log('R', 'Vector DB load failed: ' + str(e))
        return False

    try:
        _saved = sys.stderr
        _devnull = open(os.devnull, 'w')
        sys.stderr = _devnull
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        finally:
            sys.stderr = _saved
            _devnull.close()
        return True
    except Exception as e:
        log('R', 'Model load failed: ' + str(e))
        return False

def match_semantic(prompt, index):
    if not _ensure_model():
        return None

    import numpy as np

    if _vecs is None or len(index) != len(_vecs):
        log('Y', 'Index/vector mismatch, skipping semantic match')
        return None

    try:
        prompt_vec = _model.encode([prompt])[0]
    except Exception as e:
        log('R', 'Encode failed: ' + str(e))
        return None

    best_score, best_idx = -1.0, -1
    for i, db_vec in enumerate(_vecs):
        score = cosine_similarity(prompt_vec, db_vec)
        if score > best_score:
            best_score, best_idx = score, i

    if best_score >= SIMILARITY_THRESHOLD and best_idx >= 0:
        entry = index[best_idx]
        log('C', chr(0x26a1) + ' Semantic match: ' + entry['name'] +
            ' (confidence: ' + f'{best_score:.2f}' + ')')
        return entry

    if best_score > 0:
        log('D', 'No high-confidence match (best ' + f'{best_score:.2f}' +
            ' < threshold ' + str(SIMILARITY_THRESHOLD) + ')')
    return None

# ═══ Main ═══
def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        log('R', 'Parse error: ' + str(e))
        ok()
        return

    prompt = extract_prompt(data)
    if not prompt:
        ok()
        return

    # 1. Magic commands first
    if handle_magic(prompt) is not None:
        return

    # 2. State file check
    if not STATE_FILE.exists():
        ok()
        return

    # 3. Load index
    index = load_index()
    if not index:
        ok()
        return

    # 4. Intent filter: theoretical questions
    if is_just_asking(prompt):
        log('Y', chr(0x1f9e0) + ' Theoretical question detected, skipping skill load')
        ok()
        return

    # 5. Try semantic matching (falls back to keyword if vector DB unavailable)
    match = match_semantic(prompt, index)
    if match is None:
        match = match_keyword(prompt, index)
        if match:
            log('C', chr(0x26a1) + ' Keyword match: ' + match['name'])

    if not match:
        ok()
        return

    # 6. Load skill content
    root = find_skills_root()
    if not root:
        log('Y', 'No skills directory found')
        ok()
        return

    content = read_skill(match['name'], root)
    if not content:
        ok()
        return

    # 7. Inject into context (visible confirmation in chat)
    nl = '\n'
    prefix = (
        '[System] Auto-loaded skill: [' + match['name'] + ']' + nl +
        'At the very start of your reply, output this exact line (green styled):' + nl +
        '> 🪄 技能已加载: **' + match['name'] + '**' + nl + nl +
        'Strictly follow these instructions:' + nl + nl +
        content + nl + nl +
        '---' + nl +
        'User question:' + nl
    )
    print(json.dumps({'continue': True, 'prependUserPrompt': prefix}, ensure_ascii=False))

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({'continue': True}))
