# AutoSkillsCC

<p align="center">
  <b>打字就能自动加载 Claude Code 技能。不用每次手动指定。</b>
  <br>
  <i>Auto-load Claude Code skills by just typing. No manual skill selection needed.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Claude%20Code-Hook-green?logo=claude" alt="Claude Code Hook">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

## 它能干嘛？ / What does it do?

你用 Claude Code 写代码的时候，可能建了一些 `SKILL.md` 文件来规范 AI 的行为（比如前端规范、测试规范）。问题是每次都得手动告诉 CC "请按 XX 规范回答"，很烦。

You probably have some `SKILL.md` files to guide CC's behavior — frontend guidelines, testing rules, etc. But you have to tell it "follow the frontend guide" every single time. That gets old.

这个工具帮你自动干这件事。你在聊天框正常打字，它后台分析你想干嘛，匹配到合适的技能就自动注入到上下文里。你什么都不用做，AI 回复直接按规范来。

This tool does it automatically. You type, it figures out which skill you need, injects it silently. AI just follows the spec.

### 实际效果 / See it in action

```
你:   帮我写一个带搜索的表格组件
      ↓ 后台自动匹配 frontend-design + testing
AI:   >> ⚡ 技能已加载: frontend-design, testing <<
      [按前端规范和测试规范输出的代码]
```

### 开关控制 / Controls

直接在聊天框输入： / Type these in chat:

```
--skill-on        开启 / Enable
--skill-off       关闭 / Disable
--skill-status    看状态 / View status
--skill-list      列出所有技能 / List all skills
--skill-debug     诊断信息 / Diagnostics
```

---

## 安装 / Install

### 前提 / Prerequisites

需要 Python 3.10+，还需要 Claude Code CLI（终端版，Web 版和 IDE 插件版不支持 Hook）。

Python 3.10+ and Claude Code CLI (terminal version only — Web and IDE extensions don't support hooks).

```bash
python --version        # ≥ 3.10
npm install -g @anthropic-ai/claude-code
```

### 安装 / Setup

```bash
git clone https://github.com/sylvanlisayhi-cyber/AutoSkillsCC.git
cd AutoSkillsCC
pip install -r requirements.txt
python install.py
```

`install.py` 会做这些事 / What install.py does:

- 扫描你的 CC 启动脚本，有 `--bare` 就自动去掉（bare 会禁用 hook）
- 扫描 `~/.claude/skills/` 目录，注册已有技能
- 生成 `skills.json`
- 构建中英文向量索引（需 sentence-transformers）
- 写入 hook 配置到 `~/.claude/settings.json`

Scans your startup scripts for `--bare` and removes it. Scans your skills directory. Builds the skill registry and vector index. Writes CC hook config.

装完 **重启 Claude Code**，输入 `--skill-status`。没反应的话 99% 是 `--bare` 没去掉，再跑一次安装脚本。

Restart CC after install. Type `--skill-status` to verify. No response? Re-run `python install.py` — it'll fix `--bare`.

### API Key（可选 / Optional）

不配也能用。关键词匹配和本地语义模型永远生效，纯离线跑。

Works without it. Keyword matching + local semantic model run offline always.

配了的话 LLM 精选层会更准（多 ~500ms）： / With an API key, the LLM layer gets more accurate:

| 模型 | 环境变量 | 获取地址 |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com |

Windows PowerShell:

```powershell
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-xxx', 'User')
```

macOS / Linux:

```bash
echo 'export DEEPSEEK_API_KEY=sk-xxx' >> ~/.zshrc
source ~/.zshrc
```

工具自动检测你配了哪个 Key。 / The tool auto-detects whichever key you've set.

---

## 技能放哪里？ / Where to put skills

一个技能 = 一个目录 + 一个 `SKILL.md`。全放在 `~/.claude/skills/`。

One skill = one folder + one `SKILL.md`. Put them all under `~/.claude/skills/`.

```
~/.claude/skills/              # macOS / Linux
C:\Users\你\.claude\skills\    # Windows

├── frontend-design/
│   └── SKILL.md       ← 文件名必须是 SKILL.md
├── testing/
│   └── SKILL.md
└── 你自己建的/
    └── SKILL.md
```

就两条规则 / Two rules:
1. 目录名 = 技能名 / Folder name = skill name
2. 文件夹里放 `SKILL.md` / File must be named `SKILL.md`

### 内置技能 / Built-in skills

就算目录是空的，系统内置了 18 个技能的关键词能匹配常见需求：

Even with an empty directory, 18 skills are built-in and match by keyword:

`frontend-design` `docx` `pdf` `pptx` `xlsx` `python-dev` `database-design` `docker-container` `debugging` `testing` `git-workflow` `api-design` `performance-optimization` `security-audit` `refactoring` `cli-tool` `data-analysis` `ok-person`

内置技能靠关键词就能触发。如果自己建了同名目录写了 `SKILL.md`，内容会被读取注入。

Built-in skills trigger by keyword. Add your own `SKILL.md` in a same-named folder and the content gets injected.

### 添加技能 / Add your own

```bash
mkdir -p ~/.claude/skills/my-skill
nano ~/.claude/skills/my-skill/SKILL.md

# 然后在 skills.json 加一条：
# {
#   "name": "my-skill",
#   "description": "一句话描述 / one-line description",
#   "keywords": ["关键词", "keyword"]
# }

python build_vector_index.py   # 重建索引
# 不需要重启 CC / No restart needed
```

---

## 怎么工作的 / How it works

三层路由，一层没命中就落到下一层。3 routing layers, fall through on miss:

```
你的消息 / Your message
    ↓
Layer 1: 关键词匹配 / Keyword (< 0.1ms)
    BM25，纯 Python，磁盘缓存
    ↓ miss?
Layer 2: LLM API (~500ms)
    自动检测你的 API Key，用对应模型精选
    Auto-detects your API provider
    ↓ no key or miss?
Layer 3: 本地语义 / Local semantic (~50ms)
    BGE 双语模型（中/英），首次加载 1-2s 之后缓存
    Bilingual BGE models, cached after first load
    ↓
Ensemble: BM25 × 0.3 + Vector × 0.7
    ↓
MMR 多样性选择（λ=0.6，避免全是相似技能）
    ↓
LLM 精选（TOP 5 → 1~3 个最合适的）
    ↓
读 SKILL.md → 注入上下文 → AI 按规范回复 ✅
```

Provider 检测顺序：`ANTHROPIC → OPENAI → DEEPSEEK → MOONSHOT`。都没有就用本地模型。

---

## 文件 / Files

```
AutoSkillsCC/
├── hooks/
│   ├── recommend.py       # 主 hook，每次消息触发 / main hook
│   └── cmd.py             # 轻量命令 hook / lightweight command handler
├── build_vector_index.py  # 向量编译器 / vector compiler
├── install.py             # 一键安装 / one-click installer
├── benchmark.py           # 27 个测试用例 / 27 test cases
├── skills.json            # 技能注册 / skill registry
├── skills_vectors_en.npy  # 英文向量 / English vectors
├── skills_vectors_zh.npy  # 中文向量 / Chinese vectors
└── requirements.txt       # numpy + sentence-transformers
```

---

## FAQ

**装完没反应？ / No response after install?**
CC 启动命令里有 `--bare`。`python install.py` 自动修，重启 CC。
You have `--bare` in your startup command. Re-run install.py.

**会拖慢吗？ / Does it slow things down?**
不会。关键词 <1ms，语义 ~50ms，LLM ~500ms。
No. Keyword <1ms, semantic ~50ms, LLM ~500ms.

**技能加载了没？ / Did a skill load?**
AI 回复第一行有 `>> ⚡ 技能已加载: xxx`，没看到就是没加载。
Reply starts with `>> ⚡ Skill loaded: xxx`. No line = not loaded.

**没 API Key 能用？ / Works without API key?**
能。关键词和本地语义永远在线，纯离线。
Yes. Keyword + local semantic run entirely offline.

**怎么关？ / How to disable?**
打 `--skill-off`。`--skill-on` 重开。
Type `--skill-off` to disable, `--skill-on` to re-enable.

---

## License

MIT
