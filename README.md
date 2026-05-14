# AutoSkillsCC

<p align="center">
  <b>增强 Claude Code 的技能匹配——更准、更多样、离线也工作。</b>
  <br>
  <i>Better skill matching for Claude Code — more accurate, more diverse, works offline.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Claude%20Code-Hook-green?logo=claude" alt="Claude Code Hook">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

## 定位 / What this is

Claude Code 原生支持把 `SKILL.md` 放在 `~/.claude/skills/` 下，根据 description 自动匹配加载。这功能本身就不错。

AutoSkillsCC 是它的**增强层**，不是替代。你仍然用官方的方式管理技能文件，AutoSkillsCC 在 Hook 层做更精细的匹配和注入。

Claude Code natively auto-loads skills from `~/.claude/skills/` by matching your input against each skill's description. That works fine on its own.

AutoSkillsCC is a matching **upgrade** on top of it. You still manage skills the official way. AutoSkillsCC sits in the Hook layer and does more careful matching and injection.

---

## 比原生多了什么 / What it adds

| | CC 原生 | AutoSkillsCC |
|---|---|---|
| 匹配方式 | 语义匹配 | BM25 关键词 + BGE 双语向量 + LLM 精选，三层融合 |
| 一次加载几个 | 1 个 | 最多 3 个，MMR 保证不重复 |
| 没有 SKILL.md 时 | 不工作 | 18 个内置关键词库兜底，纯离线也能命中 |
| 中文支持 | 靠 description | 独立中文关键词库 + 中文 BGE 模型 |
| 理论问题 | 可能误触发 | 意图过滤器自动跳过"什么是/why"类问题 |
| 开关 | 无 | `--skill-on / --skill-off / --skill-status` |
| 可见性 | 不知道加载了啥 | 回复首行明确显示 `>> ⚡ 技能已加载: xxx` |

---

## 效果 / See it

```
你:   帮我写一个带搜索的表格组件
      ↓ 三层路由 → 匹配到 frontend-design + testing
AI:   >> ⚡ 技能已加载: frontend-design, testing <<
      [按前端规范 + 测试规范的代码]
```

控制命令，直接在聊天框输入：

```
--skill-on        开启
--skill-off       关闭
--skill-status    查看状态和技能数
--skill-list      列出所有技能
--skill-debug     诊断信息
```

---

## 安装 / Install

### 前提 / Prerequisites

Python 3.10+，Claude Code CLI（终端版，Web 版和 IDE 插件版不支持 Hook）。

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

`install.py` 会做：扫描并去除启动脚本的 `--bare`、扫描你的 `~/.claude/skills/` 目录、生成 `skills.json`、构建向量索引、写入 CC hook 配置。

It'll: fix `--bare` in your startup scripts, scan your skills directory, build the registry and vector index, write hook config.

装完重启 CC，输入 `--skill-status` 验证。没反应就再跑一次 `python install.py`。

Restart CC. Type `--skill-status`. If nothing happens, re-run install.py.

### API Key（可选 / Optional）

不配也能用。关键词和本地语义模型离线跑。配了 LLM 层更准（多 ~500ms）：

| 模型 | 环境变量 | 获取 |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com |

Windows：

```powershell
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-xxx', 'User')
```

macOS / Linux：

```bash
echo 'export DEEPSEEK_API_KEY=sk-xxx' >> ~/.zshrc
source ~/.zshrc
```

工具自动检测你配了哪个。 / Auto-detects whichever you set.

---

## 技能放哪里？ / Where skills live

和官方一样——放在 `~/.claude/skills/`。 / Same as official — `~/.claude/skills/`.

```
~/.claude/skills/              # macOS / Linux
C:\Users\你\.claude\skills\    # Windows

├── frontend-design/
│   └── SKILL.md       # 文件名固定，内容随便写
├── testing/
│   └── SKILL.md
└── 你的技能/
    └── SKILL.md
```

规则和官方一样：目录名就是技能名，文件必须叫 `SKILL.md`。

Same rules as official: folder name = skill name, file must be `SKILL.md`.

### 你没写 SKILL.md 也能用 / Works even without SKILL.md

系统内置了 18 个技能的关键词库。即使 `~/.claude/skills/` 是空的，你的输入匹配到关键词也能命中。

18 built-in keyword profiles that match even if you haven't written any SKILL.md files:

`frontend-design` `docx` `pdf` `pptx` `xlsx` `python-dev` `database-design` `docker-container` `debugging` `testing` `git-workflow` `api-design` `performance-optimization` `security-audit` `refactoring` `cli-tool` `data-analysis` `ok-person`

当然，如果你在对应目录下写了 `SKILL.md`，内容会被读取注入——和原生行为一致。

If you do write a `SKILL.md` in a matching folder, its content gets injected — same as native behavior.

### 注册你的技能 / Register your skill

```bash
mkdir -p ~/.claude/skills/my-skill
nano ~/.claude/skills/my-skill/SKILL.md

# 编辑 skills.json，加一条：
# {
#   "name": "my-skill",
#   "description": "一句话描述 / one-line description",
#   "keywords": ["关键词", "keyword"]
# }

python build_vector_index.py
# 不需要重启
```

---

## 怎么工作的 / How it works

```
你的消息 / Your message
    ↓
魔法指令？ → --skill-on/off 等直接处理
    ↓
意图过滤 → "什么是/why" 等理论问题直接跳过
    ↓
Layer 1: BM25 关键词 (< 0.1ms) — 纯 Python，磁盘缓存
    ↓
Layer 2: BGE 双语向量 (~50ms) — 中/英模型，首次加载后缓存
    ↓
Ensemble: BM25 × 0.3 + Vector × 0.7
    ↓
MMR 多样性（λ=0.6）→ 避免选出来全是相似技能
    ↓
Layer 3: LLM 精选 (~500ms) — TOP 5 → 挑 1~3 个
    ↓
读 SKILL.md → 注入 → AI 回复 ✅
```

Provider 检测：`ANTHROPIC → OPENAI → DEEPSEEK → MOONSHOT`。都没 Key 则只用前两层。

---

## 文件 / Files

```
AutoSkillsCC/
├── hooks/
│   ├── recommend.py       # 主 hook
│   └── cmd.py             # 轻量命令处理
├── build_vector_index.py  # 向量编译器
├── install.py             # 安装脚本
├── benchmark.py           # 27 个测试用例
├── skills.json            # 技能注册表
├── skills_vectors_en.npy  # 英文向量
├── skills_vectors_zh.npy  # 中文向量
└── requirements.txt       # numpy + sentence-transformers
```

---

## FAQ

**和 CC 原生技能加载什么关系？**
增强关系，不是替代。原生做基础匹配，AutoSkillsCC 做更精细的多层匹配 + 多技能并行 + 离线关键词兜底 + 可见性控制。

It's an enhancement, not a replacement. Native does basic matching. AutoSkillsCC adds multi-layer matching, multi-skill loading, offline keyword fallback, and visibility controls.

**装完没反应？**
CC 启动命令里有 `--bare`。再跑 `python install.py` 自动修，重启 CC。

**会拖慢吗？**
关键词 <1ms，语义 ~50ms，LLM ~500ms。体感不出来。

**没 API Key 能用？**
能。关键词和本地语义离线跑。

**怎么关？**
`--skill-off`，`--skill-on` 重开。

---

## License

MIT
