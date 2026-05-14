#!/usr/bin/env python3
"""AutoSkillsCC v6 — BM25 + Ensemble + MMR + multi-skill injection.

Routing layers:
  1. Magic commands (--skill-*)                           → instant
  2. BM25 keyword scoring (zero latency, always available) → <1ms
  3. BGE vector semantic scoring (if model loaded)         → ~20ms
  4. Ensemble fusion (BM25 × vector, weighted)             → <1ms
  5. MMR diversification (prevents skill clusters)          → <1ms
  6. LLM multi-select (picks 1~3 from diverse TOP N)       → ~500ms

Multi-skill: up to 3 skills injected per request.
"""
import json, sys, io, os, re, math, hashlib, pickle, traceback, warnings, logging, urllib.request
from pathlib import Path

# ── Environment setup ────────────────────────────────────────────────────
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
os.environ.setdefault('TRANSFORMERS_VERBOSITY', 'error')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
warnings.filterwarnings('ignore')
for _mod in ('sentence_transformers', 'transformers', 'tokenizers', 'tqdm', 'huggingface_hub'):
    logging.getLogger(_mod).setLevel(logging.ERROR)

if sys.platform == 'win32':
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

# ── Constants ────────────────────────────────────────────────────────────
DIR_PATH            = Path(__file__).parent.parent
SKILLS_JSON         = DIR_PATH / 'skills.json'
STATE_FILE          = DIR_PATH / '.enabled'
VECTOR_DB_EN        = DIR_PATH / 'skills_vectors_en.npy'
VECTOR_DB_ZH        = DIR_PATH / 'skills_vectors_zh.npy'
MAX_SKILL_LEN       = 6000
MAX_PROMPT_LEN      = 300
TOP_N_LLM            = 5          # candidates sent to LLM
MAX_SKILLS           = 3          # max skills injected per request

# Ensemble weights (BM25 + vector)
BM25_W = 0.3
VEC_W  = 0.7

# MMR diversity coefficient (0 = pure diversity, 1 = pure relevance)
MMR_LAMBDA = 0.6

# Min ensemble score to consider a skill (normalized 0~1)
MIN_ENSEMBLE_SCORE = 0.10

# Cache directory
CACHE_DIR   = DIR_PATH / 'cache'
BM25_CACHE  = CACHE_DIR / 'bm25.pkl'
SIM_CACHE_EN = CACHE_DIR / 'skill_sim_en.npy'
SIM_CACHE_ZH = CACHE_DIR / 'skill_sim_zh.npy'
HASH_FILE   = CACHE_DIR / 'index_md5.txt'

SKILLS_ROOTS = [
    Path('/mnt/skills/public'),
    Path.home() / '.claude' / 'skills',
    DIR_PATH / 'skills',
]

C = {'R': '\033[31m', 'G': '\033[32m', 'Y': '\033[33m',
     'C': '\033[36m', 'D': '\033[90m', 'X': '\033[0m'}

# ── Global cache ─────────────────────────────────────────────────────────
_model      = None
_vecs       = None
_lang       = None
_sim_matrix = None

# ── Helpers ──────────────────────────────────────────────────────────────
def log(color, msg):
    sys.stderr.write(C[color] + '[AutoSkillsCC] ' + msg + C['X'] + '\n')
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

# ── Stale check ──────────────────────────────────────────
def check_skills_stale(index):
    """Quick check if skills on disk differ from skills.json registry.
    Returns list of missing/unregistered skill names, or empty list if fresh."""
    missing = []
    for root in SKILLS_ROOTS:
        if not root.is_dir():
            continue
        actual = set()
        for f in root.rglob('SKILL.md'):
            if not f.parent.name.startswith('.'):
                actual.add(f.parent.name)
        if not actual:
            continue
        registered = {s['name'] for s in index}
        diff = actual - registered
        if diff:
            missing.extend(sorted(diff))
    return missing

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
        lines = ['>> 🔍 AutoSkillsCC 诊断报告 <<\n']
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
    """Find SKILL.md by skill name. Recursively searches all SKILLS_ROOTS.
    Works for both flat (skills/name/SKILL.md) and nested (skills/category/name/SKILL.md)."""
    for root in SKILLS_ROOTS:
        if not root.is_dir():
            continue
        # First try direct path
        f = root / name / 'SKILL.md'
        if f.exists():
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
        # Recursive fallback: search subdirectories
        for f in root.rglob('SKILL.md'):
            if f.parent.name == name:
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

# ── BM25 (pure Python, no deps) ─────────────────────────────────────────
class BM25:
    def __init__(self, documents, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [self._tokenize(d) for d in documents]
        self.n = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / max(self.n, 1)
        self.df = {}
        for doc in self.docs:
            for token in set(doc):
                self.df[token] = self.df.get(token, 0) + 1
        self.idf = {t: math.log((self.n - f + 0.5) / (f + 0.5) + 1)
                    for t, f in self.df.items()}

    @staticmethod
    def _tokenize(text):
        # English words + individual CJK characters
        return re.findall(r'[a-zA-Z0-9]+|[一-鿿]', text.lower())

    def score(self, query):
        tokens = self._tokenize(query)
        if not tokens:
            return [0.0] * self.n
        scores = []
        for doc in self.docs:
            doc_len = max(len(doc), 1)
            tf = {}
            for t in doc:
                tf[t] = tf.get(t, 0) + 1
            s = 0.0
            for t in tokens:
                if t not in self.idf:
                    continue
                f = tf.get(t, 0)
                s += self.idf[t] * (f * (self.k1 + 1)) / (
                    f + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
            scores.append(s)
        return scores


def _get_index_hash(index):
    raw = json.dumps([e['name'] for e in index], sort_keys=True, ensure_ascii=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _build_bm25(index):
    """Build BM25 with disk cache. Cache hit → ~5ms pickle load vs ~100ms build."""
    h = _get_index_hash(index)

    if BM25_CACHE.exists() and HASH_FILE.exists():
        if HASH_FILE.read_text().strip() == h:
            try:
                with open(BM25_CACHE, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                pass

    docs = []
    for e in index:
        doc = f"{e['name'].replace('-', ' ')}. {e.get('description', '')}. {' '.join(e.get('keywords', []))}"
        docs.append(doc)
    bm25 = BM25(docs)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(BM25_CACHE, 'wb') as f:
        pickle.dump(bm25, f)
    HASH_FILE.write_text(h)
    return bm25


# ── Vector model loader ──────────────────────────────────────────────────
def _ensure_vectors(lang, index):
    global _model, _vecs, _lang
    if _model is not None and _lang == lang and _vecs is not None and len(index) == len(_vecs):
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

    if len(_vecs_data) != len(index):
        log('Y', f'Vector/skill count mismatch ({len(_vecs_data)}≠{len(index)}), run build_vector_index.py')
        return False

    if _model is not None and _lang == lang:
        _vecs = _vecs_data
        _load_sim_matrix(lang, index)
        return True

    model_name = 'BAAI/bge-small-zh-v1.5' if lang == 'zh' else 'BAAI/bge-small-en-v1.5'
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
        _vecs = _vecs_data
        _lang = lang
        _load_sim_matrix(lang, index)
        return True
    except Exception as e:
        log('Y', f'Model load failed ({model_name}): {e}')
        return False


def _load_sim_matrix(lang, index):
    """Load or compute skill-skill similarity matrix. Cached to disk per language."""
    global _sim_matrix
    import numpy as np

    sim_path = SIM_CACHE_ZH if lang == 'zh' else SIM_CACHE_EN
    skill_n = len(index)

    if _sim_matrix is not None and _sim_matrix.shape[0] == skill_n:
        return

    h = _get_index_hash(index)
    hash_ok = HASH_FILE.exists() and HASH_FILE.read_text().strip() == h

    if hash_ok and sim_path.exists():
        try:
            _sim_matrix = np.load(sim_path)
            if _sim_matrix.shape[0] == skill_n:
                return
        except Exception:
            pass

    if _vecs is None or len(_vecs) != skill_n:
        return

    # Compute: vecs are L2-normalized, so dot = cosine similarity
    _sim_matrix = _vecs @ _vecs.T
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(sim_path, _sim_matrix)


# ── Ensemble scoring (BM25 + vector fusion) ──────────────────────────────
def get_ensemble_scores(prompt, index):
    """Returns (ensemble: np.array [num_skills], vecs_available: bool)."""
    import numpy as np

    num = len(index)
    if num == 0:
        return None, False

    bm25 = _build_bm25(index)
    bm25_arr = np.array(bm25.score(prompt), dtype=np.float32)

    def _norm(arr):
        mn, mx = arr.min(), arr.max()
        if mx - mn < 1e-8:
            return np.zeros_like(arr)
        return (arr - mn) / (mx - mn + 1e-8)

    bm25_n = _norm(bm25_arr)

    lang = detect_lang(prompt)
    has_vecs = _ensure_vectors(lang, index)

    if has_vecs:
        try:
            pv = _model.encode([prompt], normalize_embeddings=True)[0]
            vec_raw = np.dot(_vecs, pv)
            ensemble = BM25_W * bm25_n + VEC_W * _norm(vec_raw)
        except Exception as e:
            log('Y', f'Vector encode failed: {e}')
            ensemble = bm25_n
            has_vecs = False
    else:
        ensemble = bm25_n

    return ensemble, has_vecs


# ── MMR selection ────────────────────────────────────────────────────────
def mmr_select(ensemble, index, vecs_available, k=MAX_SKILLS, lam=MMR_LAMBDA):
    """Iteratively select up to k skills, penalising similarity to already-selected."""
    import numpy as np

    n = len(ensemble)
    if n == 0 or k <= 0:
        return []
    k = min(k, n)

    selected = []
    remaining = list(range(n))

    while len(selected) < k:
        best_i, best_mmr = -1, -float('inf')
        for i in remaining:
            rel = float(ensemble[i])
            if rel < MIN_ENSEMBLE_SCORE:
                continue
            if selected and vecs_available and _sim_matrix is not None:
                # O(1) lookup from precomputed matrix
                sim = max(float(_sim_matrix[i, j]) for j in selected)
            elif selected:
                # no vectors → Jaccard on keywords
                ki = set(index[i].get('keywords', []))
                sim = 0.0
                for j in selected:
                    kj = set(index[j].get('keywords', []))
                    u = len(ki | kj)
                    if u > 0:
                        sim = max(sim, len(ki & kj) / u)
            else:
                sim = 0.0

            mmr = lam * rel - (1 - lam) * sim
            if mmr > best_mmr:
                best_mmr, best_i = mmr, i

        if best_i < 0:
            break
        selected.append(best_i)
        remaining.remove(best_i)

    return selected


# ── LLM multi-select ─────────────────────────────────────────────────────
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


def match_llm_multi(prompt, candidates, max_pick=MAX_SKILLS):
    """LLM picks 1~max_pick most useful skills from the diversified shortlist."""
    provider, api_key, model, endpoint = _get_llm_config()
    if not api_key or not candidates:
        return []

    skills_summary = '\n'.join(
        f'{i+1}. {e["name"]}: {e.get("description", "")[:100]}'
        for i, (e, _) in enumerate(candidates)
    )
    names_dict = {e["name"].lower(): e for e, _ in candidates}
    names_str = ', '.join(e["name"] for e, _ in candidates)

    system_msg = "You are a skill router. Pick ALL skills relevant to the user's request."
    user_msg = (
        f"User request: {prompt}\n\n"
        f"Candidates:\n{skills_summary}\n\n"
        f"Select the 1~{max_pick} most useful skills. "
        f"Reply ONLY with skill names separated by commas (e.g. \"frontend-design, testing\"), "
        f"or \"none\". Valid names: {names_str}."
    )

    try:
        if provider == 'openai':
            body = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 50,
                "temperature": 0,
            }).encode('utf-8')
            url = endpoint or 'https://api.openai.com/v1/chat/completions'
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
        else:
            body = json.dumps({
                "model": model,
                "system": system_msg,
                "messages": [{"role": "user", "content": user_msg}],
                "max_tokens": 50,
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
        return []

    if text == 'none' or not text:
        return []

    selected = []
    for name in re.split(r'[,，\s]+', text):
        name = name.strip().strip('"').strip("'")
        if name in names_dict:
            selected.append(names_dict[name])

    if selected:
        log('C', f'⚡ LLM [{provider}/{model}]: {", ".join(e["name"] for e in selected)}')
    return selected

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

    # 1. Magic commands
    if handle_magic(prompt):
        return

    # 2. State check
    if not STATE_FILE.exists():
        ok()

    # 3. Load registry
    index = load_index()
    if not index:
        ok()

    # 3b. Stale check
    stale_skills = check_skills_stale(index)
    if stale_skills:
        names = ', '.join(stale_skills)
        log('Y', f'⚠️  skills.json 过期 — 以下技能未注册: {names} | python install.py --refresh')

    # 4. Intent filter
    if is_just_asking(prompt):
        log('Y', '🧠 Theory question, skip')
        ok()

    # 5. Ensemble scoring (BM25 + vector fusion)
    import numpy as np
    ensemble, vecs_available = get_ensemble_scores(prompt, index)
    if ensemble is None:
        ok()

    lang = detect_lang(prompt)

    # 6. Build TOP N candidates from ensemble
    top_k = min(TOP_N_LLM, len(ensemble))
    top_indices = np.argsort(ensemble)[::-1][:top_k]
    candidates = [(index[int(i)], float(ensemble[int(i)])) for i in top_indices
                  if float(ensemble[int(i)]) >= MIN_ENSEMBLE_SCORE]

    if not candidates:
        log('Y', f'No skills above threshold ({MIN_ENSEMBLE_SCORE:.2f})')
        ok()

    log('D', f'Ensemble [{lang}] top{len(candidates)}: ' +
        ', '.join(f'{e["name"]}({s:.3f})' for e, s in candidates[:5]))

    # 7. MMR diversification → pick diverse TOP N for LLM
    mmr_indices = mmr_select(ensemble, index, vecs_available, k=TOP_N_LLM, lam=MMR_LAMBDA)

    # 8. LLM multi-select from MMR-diversified candidates
    mmr_candidates = [(index[i], float(ensemble[i])) for i in mmr_indices]
    matched = match_llm_multi(prompt, mmr_candidates, max_pick=MAX_SKILLS)

    if not matched:
        # LLM failed or no key → use MMR directly
        mmr_picks = mmr_select(ensemble, index, vecs_available, k=MAX_SKILLS, lam=MMR_LAMBDA)
        if mmr_picks:
            matched = [index[i] for i in mmr_picks
                       if float(ensemble[i]) >= MIN_ENSEMBLE_SCORE]
            if matched:
                log('C', f'⚡ MMR direct: {", ".join(e["name"] for e in matched)}')

    if not matched:
        ok()

    # 9. Read SKILL.md for each matched skill
    contents = []
    for entry in matched:
        c = read_skill(entry['name'])
        if c:
            contents.append((entry['name'], c))
            log('G', f'  ✅ {entry["name"]}')

    if not contents:
        log('Y', 'No SKILL.md found for matched skills')
        ok()

    # 10. Build multi-skill injection prefix
    skill_names = [name for name, _ in contents]
    names_str = ', '.join(skill_names)

    # Skill content blocks with priority order
    skill_blocks = (
        '\n\n---\n'.join(
            f'## Skill {i+1}: {name} (priority: {"highest" if i == 0 else str(i+1)})\n{c}'
            for i, (name, c) in enumerate(contents)
        )
    )

    prefix = (
        f'[System] Auto-loaded skills ({len(contents)}): {names_str}\n'
        f'At the very start of your reply, output this exact line:\n'
        f'>> ⚡ 技能已加载: **{names_str}** <<\n\n'
        f'Then strictly follow these instructions, in priority order '
        f'(higher-numbered priority = most important):\n\n'
        + skill_blocks + '\n\n'
        '---\n'
        'Conflict resolution: If multiple skill guidelines conflict, '
        'higher-priority skill takes precedence.\n'
        '---\n'
        'At the very end of your reply, add this footnote on its own line '
        '(plain text, no markdown):\n'
        f'[AutoSkillsCC] Loaded: {names_str}\n\n'
        'User question:\n'
    )
    print(json.dumps({'continue': True, 'prependUserPrompt': prefix}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({'continue': True}))
