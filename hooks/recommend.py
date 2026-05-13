#!/usr/bin/env python3
"""SkillRouter v4 — Dynamic AI Router for Claude Code.

Routing layers (first match wins):
  1. Magic commands (--skill-*)              → 0ms
  2. Keyword matching (zero latency)          → <1ms
  3. LLM API routing (auto-detect user's AI)  → ~500ms
  4. Local bilingual semantic (BGE en+zh)     → ~50ms (after first load)

Dynamic AI: detects ANTHROPIC_API_KEY → OPENAI_API_KEY → DEEPSEEK_API_KEY
→ MOONSHOT_API_KEY. Routes via the same AI the user is already using.
No config needed — set SKILL_ROUTER_* env vars to override.
"""
import json, sys, io, os, re, traceback, warnings, logging, urllib.request
from pathlib import Path

# ── Environment setup ────────────────────────────────────────────────────
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
os.environ.setdefault('TRANSFORMERS_VERBOSITY', 'error')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
warnings.filterwarnings('ignore')
for _mod in ('sentence_transformers', 'transformers', 'tokenizers', 'tqdm', 'huggingface_hub'):
    logging.getLogger(_mod).setLevel(logging.ERROR)

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Constants ────────────────────────────────────────────────────────────
DIR_PATH            = Path(__file__).parent.parent
SKILLS_JSON         = DIR_PATH / 'skills.json'
STATE_FILE          = DIR_PATH / '.enabled'
VECTOR_DB_EN        = DIR_PATH / 'skills_vectors_en.npy'
VECTOR_DB_ZH        = DIR_PATH / 'skills_vectors_zh.npy'
MAX_SKILL_LEN       = 6000
MAX_PROMPT_LEN      = 300
KEYWORD_MIN_SCORE   = 1
SIMILARITY_THRESHOLD = 0.40

SKILLS_ROOTS = [
    Path('/mnt/skills/public'),
    Path.home() / '.claude' / 'skills',
    DIR_PATH / 'skills',
]

C = {'R': '\033[31m', 'G': '\033[32m', 'Y': '\033[33m',
     'C': '\033[36m', 'D': '\033[90m', 'X': '\033[0m'}

# ── Global cache ─────────────────────────────────────────────────────────
_model = None
_vecs  = None
_lang  = None

# ── Helpers ──────────────────────────────────────────────────────────────
def log(color, msg):
    sys.stderr.write(C[color] + '[SkillRouter] ' + msg + C['X'] + '\n')
    sys.stderr.flush()

def ok():
    print(json.dumps({'continue': True}))
    sys.exit(0)

def inject(prefix):
    print(json.dumps({'continue': True, 'prependUserPrompt': prefix}, ensure_ascii=False))
    sys.exit(0)

# ── skills.json loader ───────────────────────────────────────────────────
def load_index():
    if not SKILLS_JSON.exists():
        return []
    try:
        raw = json.loads(SKILLS_JSON.read_text(encoding='utf-8'))
    except Exception:
        log('R', 'skills.json parse failed')
        return []
    if not isinstance(raw, list):
        log('R', 'skills.json must be an array')
        return []
    valid = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or not entry.get('name'):
            log('Y', f'skills.json[{i}] missing "name", skipped')
            continue
        valid.append(entry)
    return valid

# ── Prompt extraction ────────────────────────────────────────────────────
def extract_prompt(data):
    raw = ''
    for field in ['prompt', 'user_prompt', 'userPrompt', 'message', 'text', 'input']:
        val = data.get(field)
        if isinstance(val, str) and val.strip():
            raw = val
            break
        if isinstance(val, list):
            parts = [b.get('text', '') for b in val
                     if isinstance(b, dict) and b.get('type') == 'text']
            j = ' '.join(parts).strip()
            if j:
                raw = j
                break
    if not raw:
        return ''
    segs = re.split(r'✻ \w+ for \d+s\.{0,3}\s*', raw)
    last = segs[-1].strip()
    result = last if last else raw.strip()
    if len(result) > MAX_PROMPT_LEN:
        result = result[-MAX_PROMPT_LEN:]
    return result

# ── Magic commands ───────────────────────────────────────────────────────
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

def _reply_magic(text):
    inject(
        '[System directive] Management command. '
        'Do NOT use any tools. Reply ONLY this exact output:\n' + text
    )

def handle_magic(prompt):
    p = prompt.strip().lower()
    cmd = MAGIC.get(p)
    if not cmd:
        for key in MAGIC:
            if p.endswith(key):
                cmd = MAGIC[key]
                break
    if not cmd:
        return False

    idx = load_index()
    n = len(idx)

    if cmd == 'off':
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        log('Y', '🔴 Disabled')
        _reply_magic('>> 🔴 技能自动加载：已关闭 <<')

    elif cmd == 'on':
        STATE_FILE.touch()
        log('G', '🟢 Enabled')
        _reply_magic('>> 🟢 技能自动加载：已开启 <<')

    elif cmd == 'list':
        lines = [f'- **{s["name"]}**: {s.get("description", "")[:60]}' for s in idx] if idx else ['(暂无已注册技能)']
        _reply_magic(f'>> 📋 已注册技能 ({n}) <<\n\n' + '\n'.join(lines))

    elif cmd == 'status':
        enabled = STATE_FILE.exists()
        icon = '🟢' if enabled else '🔴'
        status = '已开启' if enabled else '已关闭'
        _reply_magic(f'>> {icon} 技能状态：{status} | 已注册 {n} 个技能 <<')

    elif cmd == 'debug':
        lines = ['>> 🔍 SkillRouter 诊断报告 <<\n']
        lines.append(f'状态: {"🟢 已开启" if STATE_FILE.exists() else "🔴 已关闭"}')
        lines.append(f'skills.json: {n} 个技能' + (' ✅' if n else ' ❌'))
        for root in SKILLS_ROOTS:
            mark = '✅' if root.is_dir() else '—'
            lines.append(f'技能目录 [{mark}] {root}')
        lines.append('向量库:')
        for label, path in [('EN', VECTOR_DB_EN), ('ZH', VECTOR_DB_ZH)]:
            if path.exists():
                try:
                    import numpy as np
                    v = np.load(path)
                    ok_str = '✅' if v.shape[0] == n else f'⚠️ 数量不匹配({v.shape[0]}≠{n})'
                    lines.append(f'  {label}: shape={v.shape} {ok_str}')
                except Exception:
                    lines.append(f'  {label}: ✅ 存在 (无法读取shape)')
            else:
                lines.append(f'  {label}: ❌ 不存在')
        lines.append('LLM 路由（自动检测）:')
        for env_key, prov, model, endpoint in _LLM_PROVIDERS:
            found = '✅' if os.environ.get(env_key) else '—'
            det = f' → {prov}/{model}'
            if endpoint:
                det += f' [{endpoint}]'
            lines.append(f'  {found} {env_key}{det}')
        provider, key, model, _ep = _get_llm_config()
        lines.append(f'  当前生效: {"❌ 无 API Key" if not key else f"{provider}/{model}"}')
        lines.append(f'\nPython: {sys.executable}')
        lines.append('\n可用: --skill-status | --skill-list | --skill-on | --skill-off | --skill-debug')
        _reply_magic('\n'.join(lines))

    return True

# ── Skill file reader ────────────────────────────────────────────────────
def read_skill(name):
    for root in SKILLS_ROOTS:
        if not root.is_dir():
            continue
        f = root / name / 'SKILL.md'
        if not f.exists():
            continue
        try:
            c = f.read_text(encoding='utf-8', errors='replace')
            if len(c) > MAX_SKILL_LEN:
                c = c[:MAX_SKILL_LEN]
                nl = c.rfind('\n')
                if nl > MAX_SKILL_LEN // 2:
                    c = c[:nl]
                c += '\n\n[...truncated]'
            return c
        except Exception:
            continue
    return None

# ── Intent filter ────────────────────────────────────────────────────────
_THEORY_PREFIX = re.compile(
    r'^('
    r'什么是|是什么|为什么|怎么理解|如何理解|请解释|解释一下|能解释吗|'
    r'讲一下|讲讲|说说|介绍一下|介绍下|帮我理解|帮我解释|'
    r'what is |what are |what\'s |why is |why does |why do |'
    r'explain |how does |how do |tell me about |describe |'
    r'what\'s the difference|difference between|compare '
    r')',
    re.IGNORECASE,
)

_THEORY_ANYWHERE = re.compile(
    r'('
    r'是什么[？?]?$|为什么[？?]?$|有什么区别|区别是什么|'
    r'原理是什么|概念是什么|八股|面试题|底层原理|实现原理'
    r')',
    re.IGNORECASE,
)

def is_just_asking(prompt):
    p = prompt.strip()
    if _THEORY_PREFIX.match(p[:50]):
        return True
    if len(p) <= 30 and _THEORY_ANYWHERE.search(p):
        return True
    return False

# ── Language detection ───────────────────────────────────────────────────
def detect_lang(text):
    cn = len(re.findall(r'[一-鿿]', text))
    return 'zh' if cn / max(len(text), 1) > 0.10 else 'en'

# ── Layer 1: Keyword matching ────────────────────────────────────────────
def match_keyword(prompt, index):
    pl = prompt.lower()
    best_score, best_entry = 0, None
    for entry in index:
        score = sum(1 for kw in entry.get('keywords', []) if kw.lower() in pl)
        if score > best_score:
            best_score, best_entry = score, entry
    return best_entry if best_score >= KEYWORD_MIN_SCORE else None

# ── Layer 2: LLM API routing (dynamic AI detection) ──────────────────────
_LLM_PROVIDERS = [
    ('ANTHROPIC_API_KEY', 'anthropic', 'claude-haiku-4-5-20251001', ''),
    ('OPENAI_API_KEY',     'openai',    'gpt-4o-mini',            ''),
    ('DEEPSEEK_API_KEY',   'openai',    'deepseek-chat',          'https://api.deepseek.com/v1/chat/completions'),
    ('MOONSHOT_API_KEY',   'openai',    'moonshot-v1-8k',         'https://api.moonshot.cn/v1/chat/completions'),
]

def _get_llm_config():
    provider = os.environ.get('SKILL_ROUTER_PROVIDER', '')
    if provider:
        return (
            provider,
            os.environ.get('SKILL_ROUTER_API_KEY') or os.environ.get('ANTHROPIC_API_KEY', ''),
            os.environ.get('SKILL_ROUTER_MODEL', 'claude-haiku-4-5-20251001'),
            os.environ.get('SKILL_ROUTER_ENDPOINT', ''),
        )
    for env_key, prov, model, endpoint in _LLM_PROVIDERS:
        if os.environ.get(env_key):
            return prov, os.environ[env_key], model, endpoint
    return '', '', '', ''

def match_llm(prompt, index):
    provider, api_key, model, endpoint = _get_llm_config()
    if not api_key:
        return None

    skills_summary = '\n'.join(
        f'- {s["name"]}: {s.get("description", "")[:100]}'
        for s in index
    )
    example_name = index[0]["name"]
    system_msg = "You are a skill router. Reply with EXACTLY one word — the skill name or \"none\"."
    user_msg = (
        f"Available skills:\n{skills_summary}\n\n"
        f"User message: {prompt}\n\n"
        f"Which skill matches? Reply ONLY \"{example_name}\" or \"none\"."
    )

    try:
        if provider == 'openai':
            body = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 30,
                "temperature": 0,
            }).encode('utf-8')
            url = endpoint or 'https://api.openai.com/v1/chat/completions'
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
        else:
            body = json.dumps({
                "model": model,
                "system": system_msg,
                "messages": [{"role": "user", "content": user_msg}],
                "max_tokens": 30,
                "temperature": 0,
            }).encode('utf-8')
            url = endpoint or 'https://api.anthropic.com/v1/messages'
            headers = {"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}

        req = urllib.request.Request(url, data=body, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())

        if provider == 'openai':
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
        else:
            text = result.get("content", [{}])[0].get("text", "").strip().lower()
    except Exception as e:
        log('Y', f'LLM route failed: {e}')
        return None

    for entry in index:
        if entry["name"].lower() == text:
            log('C', f'⚡ LLM [{provider}/{model}]: {entry["name"]}')
            return entry
    return None

# ── Layer 3: Local bilingual semantic matching ──────────────────────────
def _ensure_model(lang):
    global _model, _vecs, _lang
    if _model is not None and _lang == lang:
        return True

    vec_path = VECTOR_DB_ZH if lang == 'zh' else VECTOR_DB_EN
    if not vec_path.exists():
        return False

    try:
        import numpy as np
        _vecs_data = np.load(vec_path)
    except Exception as e:
        log('Y', f'vector load failed: {e}')
        return False

    model_name = 'BAAI/bge-small-zh-v1.5' if lang == 'zh' else 'BAAI/bge-small-en-v1.5'
    try:
        from sentence_transformers import SentenceTransformer
        old_err = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        try:
            _model = SentenceTransformer(model_name)
        finally:
            sys.stderr.close()
            sys.stderr = old_err
        _vecs = _vecs_data
        _lang = lang
        return True
    except Exception as e:
        log('Y', f'Model load failed ({model_name}): {e}')
        return False

def match_semantic(prompt, index):
    """Bilingual semantic matching using BGE models."""
    lang = detect_lang(prompt)
    if not _ensure_model(lang):
        return None

    import numpy as np

    if _vecs is None or len(index) != len(_vecs):
        log('Y', f'Vector/skill mismatch ({len(_vecs) if _vecs is not None else 0}≠{len(index)}), run build_vector_index.py')
        return None

    try:
        pv = _model.encode([prompt], normalize_embeddings=True)[0]
    except Exception as e:
        log('Y', f'Encode failed: {e}')
        return None

    scores = np.dot(_vecs, pv)
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score >= SIMILARITY_THRESHOLD:
        entry = index[best_idx]
        log('C', f'⚡ Semantic [{lang}]: {entry["name"]} ({best_score:.2f})')
        return entry

    log('D', f'Semantic miss: best {best_score:.2f} < {SIMILARITY_THRESHOLD}')
    return None

# ═══ Main ════════════════════════════════════════════════════════════════
def main():
    try:
        raw = sys.stdin.buffer.read().decode('utf-8', errors='replace')
        data = json.loads(raw)
    except Exception as e:
        log('R', f'stdin parse: {e}')
        ok()

    prompt = extract_prompt(data)
    if not prompt:
        ok()

    # 1. Magic commands (highest priority)
    if handle_magic(prompt):
        return

    # 2. State check
    if not STATE_FILE.exists():
        ok()

    # 3. Load registry
    index = load_index()
    if not index:
        ok()

    # 4. Intent filter
    if is_just_asking(prompt):
        log('Y', '🧠 Theory question, skip')
        ok()

    # 5. Layer 1: Keyword matching (zero latency)
    match = match_keyword(prompt, index)
    if match:
        log('C', f'⚡ Keyword: {match["name"]}')
    else:
        # 6. Layer 2: LLM API routing (dynamic AI)
        match = match_llm(prompt, index)

    # 7. Layer 3: Local semantic (fallback)
    if not match:
        match = match_semantic(prompt, index)

    if not match:
        ok()

    # 8. Read SKILL.md
    content = read_skill(match['name'])
    if not content:
        log('Y', f'No SKILL.md for: {match["name"]}')
        ok()

    # 9. Inject
    prefix = (
        '[System] Auto-loaded skill: [' + match['name'] + ']\n'
        'At the very start of your reply, output this exact line:\n'
        '>> ⚡ 技能已加载: **' + match['name'] + '** <<\n\n'
        'Then strictly follow these instructions:\n\n'
        + content + '\n\n---\nUser question:\n'
    )
    print(json.dumps({'continue': True, 'prependUserPrompt': prefix}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({'continue': True}))
