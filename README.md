# AutoSkillsCC

<p align="center">
  <b>Better skill matching for Claude Code — multi-layer routing, multi-skill loading, works offline.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Claude%20Code-Hook-green?logo=claude" alt="Claude Code Hook">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

## What this is

Claude Code can natively auto-load skills from `~/.claude/skills/`. You put a folder with a `SKILL.md` in it, CC matches your input against each skill's description, and loads the best match. It's a solid feature.

AutoSkillsCC is an **enhancement layer** on top of it, installed as a CC Hook. You still manage your skill files the official way. AutoSkillsCC intercepts every message before it reaches the model and does more careful matching, then injects the matched skill content into the prompt.

Think of it as: CC native does basic matching. AutoSkillsCC does the same thing, but with a more sophisticated matching pipeline, plus a few things native doesn't do at all.

---

## What it adds over native

| | CC Native | AutoSkillsCC |
|---|---|---|
| **Matching** | Single semantic match on description | BM25 keyword + BGE bilingual vector + LLM, fused into one score |
| **How many skills** | 1 | Up to 3 at once, with MMR diversity to avoid loading similar skills |
| **Without SKILL.md** | Does nothing | 18 built-in keyword profiles still match and guide behavior |
| **Chinese input** | Relies on description text | Dedicated Chinese keyword library + Chinese BGE model |
| **Theory questions** | May falsely trigger | Intent filter automatically skips "what is / explain / why" type questions |
| **On/off** | None | `--skill-on` / `--skill-off` / `--skill-status` typed directly in chat |
| **Transparency** | You don't know what loaded | Reply starts with `>> ⚡ Skill loaded: skill-name` |

---

## Demo

Type normally. If your request matches any skill, it gets injected automatically:

```
You:  build a data table component with search and unit tests
      ↓ matches frontend-design + testing
AI:   >> ⚡ Skill loaded: frontend-design, testing <<
      [Code following your frontend and testing guidelines]
```

Built-in control commands — just type these in the chat:

```
--skill-on        Enable auto-loading
--skill-off       Disable auto-loading
--skill-status    Show status and registered skill count
--skill-list      List all skills
--skill-debug     Full diagnostic report
```

Example output:

```
>> 🟢 Skill Status: Enabled | 18 skills registered <<
```

---

## How matching works

When you send a message, three layers run in sequence. If a layer produces a confident match, the result is used. Otherwise it falls through to the next one.

```
Your message
    ↓
Magic command? → --skill-on/off/status handled instantly, no routing
    ↓
Intent filter → "what is / why / explain" questions skip entirely
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 1: BM25 Keyword (< 0.1ms)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Pure Python TF-IDF, zero dependencies
  Tokenizes both English words and individual CJK characters
  Scores each skill's name + description + keywords against your input
  Result cached to disk (~5ms on subsequent runs)
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 2: BGE Bilingual Vector (~50ms)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Auto-detects input language (Chinese or English)
  English → bge-small-en-v1.5 (33MB)
  Chinese → bge-small-zh-v1.5 (33MB)
  Computes cosine similarity between your input vector and all skill vectors
  First load takes 1-2 seconds (model download + warmup), then cached
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ensemble Fusion
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  final_score = BM25 × 0.3 + Vector × 0.7
  Both scores normalized to 0~1 before fusion
  Skills below 0.10 are discarded
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MMR Diversity Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  λ = 0.6 (60% relevance, 40% diversity)
  Greedy algorithm:
    1. Pick the highest-scoring skill
    2. For each remaining candidate, compute:
       mmr = 0.6 × relevance - 0.4 × max_similarity_to_selected
    3. Repeat until top 5 are selected
  Similarity matrix is precomputed → O(1) lookup
  This prevents loading 3 near-identical skills
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 3: LLM Refinement (~500ms)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Sends the top 5 MMR-diversified candidates to an LLM
  Prompt: "Pick the 1~3 most useful skills for this request"
  Uses whatever API key you have set (auto-detected)
  No API key? Falls back to MMR top-3 directly
    ↓
Read matched SKILL.md files → inject into prompt → AI responds ✅
```

**Provider auto-detection order:** `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` → `DEEPSEEK_API_KEY` → `MOONSHOT_API_KEY`

If none are set, Layers 1+2 still run perfectly offline.

**Total latency:** ~60ms without LLM, ~560ms with LLM. Not noticeable.

---

## Install

### Prerequisites

- **Python 3.10 or later** — check with `python --version`
- **Claude Code CLI** — terminal version only. The web app and VS Code / JetBrains extensions don't support hooks.

```bash
python --version        # should be ≥ 3.10
npm install -g @anthropic-ai/claude-code
```

### Setup

```bash
git clone https://github.com/sylvanlisayhi-cyber/AutoSkillsCC.git
cd AutoSkillsCC
pip install -r requirements.txt
python install.py
```

`install.py` does five things automatically:

1. **Scans for `--bare`** in your CC startup scripts. The `--bare` flag disables hooks entirely — if found, it removes it and backs up the original file.
2. **Scans `~/.claude/skills/`** for existing skill directories and registers them.
3. **Generates `skills.json`** — the skill registry used by the matching engine.
4. **Builds bilingual vector index** — encodes all skills with BGE models (English + Chinese). Requires `sentence-transformers`; if not installed, this step is skipped and only keyword matching runs.
5. **Writes hook config** to `~/.claude/settings.json` — registers `recommend.py` as a `UserPromptSubmit` hook, plus sets up `/skillstatus`, `/skillon`, etc. as custom CC commands.

After install, **restart Claude Code** and type:

```
--skill-status
```

If you see `>> 🟢 Skill Status: Enabled | 18 skills registered <<` — it's working.

No response? Your CC is likely running with `--bare`. Re-run `python install.py` and it'll fix it automatically.

### API Key (optional)

The keyword and local semantic layers work fully offline. No API key needed.

Adding one enables the LLM refinement layer (Layer 3), which improves multi-skill selection accuracy at the cost of ~500ms latency.

| Provider | Env variable | Get key at |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com |

Windows (PowerShell):

```powershell
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-xxx', 'User')
# Restart terminal after setting
```

macOS / Linux:

```bash
echo 'export DEEPSEEK_API_KEY=sk-xxx' >> ~/.zshrc
source ~/.zshrc
```

The tool auto-detects which provider you've configured. No extra config needed.

---

## Where skills go

Skills live in `~/.claude/skills/` — the same directory CC natively uses. Each skill is one folder containing one `SKILL.md` file.

```
~/.claude/skills/              # macOS / Linux
C:\Users\you\.claude\skills\   # Windows

├── frontend-design/
│   └── SKILL.md       ← folder name = skill name, file must be SKILL.md
├── testing/
│   └── SKILL.md
├── my-own-skill/
│   └── SKILL.md
└── ...
```

That's it. No config files, no registration ceremony. Just folders and markdown.

SKILL.md content is free-form — write whatever instructions you want the AI to follow when that skill is loaded. The file gets truncated to 6000 characters during injection to avoid blowing up the context window.

### Built-in skill profiles

Even if your `~/.claude/skills/` directory is completely empty, AutoSkillsCC ships with 18 keyword profiles that can still match and guide behavior:

| Skill | When it triggers |
|---|---|
| `frontend-design` | React, Vue, HTML, CSS, Tailwind, component, UI mentions |
| `docx` | Word document generation, .docx files |
| `pdf` | PDF generation, reading, parsing |
| `pptx` | PowerPoint, slides, presentations |
| `xlsx` | Excel, spreadsheets, CSV, data export |
| `python-dev` | Python, pip, FastAPI, Django, Flask |
| `database-design` | SQL, MySQL, PostgreSQL, MongoDB, database queries |
| `docker-container` | Docker, Dockerfile, Kubernetes, deployments |
| `debugging` | Bugs, errors, crash, stack trace, fixing code |
| `testing` | Unit tests, integration tests, E2E, pytest, Jest |
| `git-workflow` | Git, commits, branches, merge, PR |
| `api-design` | REST, GraphQL, endpoints, Swagger, OpenAPI |
| `performance-optimization` | Slow queries, caching, profiling, latency |
| `security-audit` | XSS, CSRF, JWT, auth, vulnerabilities |
| `refactoring` | Clean code, code quality, design patterns |
| `cli-tool` | CLI, terminal, bash, shell scripts |
| `data-analysis` | Pandas, NumPy, Matplotlib, data visualization |
| `ok-person` | ok person easter egg |

These built-in profiles use keyword matching. They don't have SKILL.md content of their own — they trigger on keywords and guide the AI's domain focus. If you create a folder with the same name and write your own `SKILL.md`, your content overrides the built-in behavior and gets injected normally.

### Adding your own skill

```bash
# 1. Create the folder and write your instructions
mkdir -p ~/.claude/skills/my-skill
nano ~/.claude/skills/my-skill/SKILL.md
```

Example `SKILL.md`:

```markdown
Always follow these rules when writing Go code:
- Use explicit error handling, never panic
- Prefer composition over inheritance
- Name functions starting with the package's primary type
- Use table-driven tests
```

```bash
# 2. Register it in skills.json
# Add an entry like:
# {
#   "name": "my-skill",
#   "description": "Go coding guidelines — error handling, naming, testing",
#   "keywords": ["go", "golang", "error handling", "testing"]
# }

# 3. Rebuild the vector index
python build_vector_index.py
```

No restart needed. The hook picks up changes immediately.

---

## Project structure

```
AutoSkillsCC/
├── hooks/
│   ├── recommend.py       # Main hook — runs on every message
│   └── cmd.py             # Lightweight command handler (reserved, not registered)
├── build_vector_index.py  # Vector index compiler — run after adding skills
├── install.py             # One-command installer
├── benchmark.py           # 27 test cases for accuracy measurement
├── skills.json            # Skill registry (names, descriptions, keywords)
├── skills_vectors_en.npy  # Pre-computed English skill vectors
├── skills_vectors_zh.npy  # Pre-computed Chinese skill vectors
└── requirements.txt       # numpy (required), sentence-transformers (optional)
```

---

## Testing

```bash
python benchmark.py
```

Runs 27 test cases covering single-domain, multi-domain, tricky, and edge-case prompts. Reports Top-1, Top-3, Top-5, and MMR accuracy.

---

## FAQ

**How is this different from CC's native skill loading?**
It's an enhancement, not a replacement. CC native does single semantic matching on skill descriptions. AutoSkillsCC does multi-layer ensemble matching (keyword + vector + LLM), loads up to 3 diverse skills at once instead of 1, has 18 offline keyword profiles that work even with no SKILL.md files, a dedicated Chinese matching pipeline, an intent filter that skips theory questions, and visible on/off controls. They're compatible — your skills directory is the same, the file format is the same.

**Nothing happens after install. `--skill-status` returns nothing.**
Your CC is launched with `--bare`. Re-run `python install.py` and restart CC. It scans for and removes `--bare` from startup scripts automatically.

**Does it slow down Claude Code?**
No. Keyword matching takes under 1ms, semantic matching ~50ms, LLM call ~500ms. The user doesn't perceive any delay.

**Can I use it without an API key?**
Yes. Layers 1 (keyword) and 2 (local BGE model) run entirely offline. The LLM layer is optional.

**How do I know a skill was loaded?**
The AI's reply starts with `>> ⚡ Skill loaded: skill-name`. No line = nothing loaded.

**How do I turn it off?**
Type `--skill-off` in chat. Type `--skill-on` to re-enable. Perfect for theory discussions where you don't want skills injected.

**What platforms are supported?**
Windows, macOS, Linux. Python 3.10+.

**I added a new skill. Do I need to restart CC?**
No. Just run `python build_vector_index.py` after editing skills.json.

---

## License

MIT
