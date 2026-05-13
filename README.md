# SkillRouter 🛜

<p align="center">
  <b>你打字，它猜你要什么技能。自动的。零操作。</b>
  <br>
  <i>Type normally. It figures out which skill you need. Automatically. Zero effort.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Claude%20Code-Hook-green?logo=claude" alt="Claude Code Hook">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/AI-Any%20Provider-purple" alt="Any AI">
</p>

---

## 🤔 这玩意儿干嘛的？ / What does this do?

你用 Claude Code 写代码。你有好多技能规范（SKILL.md）。但你不想每次都说"请按前端规范回答"——烦死了。

**SkillRouter 替你干这件事。**

你打字，它后台自动看你想干嘛，找到最合适的技能，无声注入。你甚至不知道它干活了——直到你看到 AI 回复得特别专业。

You have a bunch of skill files (SKILL.md) for Claude Code. You don't want to manually tell Claude "please follow the frontend guidelines" every single time.

**SkillRouter does it for you. Silently.**

You type. It watches. It matches. You get better results. You do nothing.

---

## 🎬 实际效果 / See It In Action

```
你:   帮我写个带搜索的表格组件
      ↓ (后台自动匹配 frontend-design 技能, 你零操作)
AI:   
```

<p align="center">
  <b>三次路由，一次命中。3 layers, 1 match.</b>
</p>

```
你:   --skill-status
AI:   >> 🟢 技能状态：已开启 | 已注册 18 个技能 <<

你:   --skill-off
AI:   >> 🔴 已关闭 <<

你:   --skill-on
AI:   >> 🟢 已开启 <<
```

---

## 📦 安装 / Install

### 前提 / Prerequisites

- Python 3.10+
- Claude Code（别开 `--bare` 模式！bare 会关掉所有 hooks）
- Claude Code (don't use `--bare` mode! It disables all hooks)

### 三步搞定 / 3 Steps

```bash
# 1. 克隆 / Clone
git clone https://github.com/sylvanlisayhi-cyber/SkillRouter.git
cd SkillRouter

# 2. 装依赖 / Install deps (numpy 必装, sentence-transformers 可选)
pip install numpy
pip install sentence-transformers  # 可选/optional — 本地语义路由

# 3. 一键安装 / One-click install
python install.py
```

**重启 Claude Code（不要 --bare！），搞定。**  
**Restart Claude Code (without --bare!), done.**

---

## 🎮 使用 / Usage

### 日常：什么都不做 / Daily: Do Nothing

正常聊天就行。当你的需求命中某个技能，AI 自动按技能规范执行。

Just chat. When your request matches a skill, the AI follows its guidelines automatically.

### 魔法指令 / Magic Commands

直接在聊天框里打：

| 指令 / Command | 干嘛的 / What |
|---|---|
| `--skill-status` | 查看状态 / View status |
| `--skill-list` | 列出所有技能 / List all skills |
| `--skill-on` | 开启自动加载 / Enable |
| `--skill-off` | 关闭自动加载 / Disable |
| `--skill-debug` | 完整诊断 / Full diagnostics |

也可以用 CC 自定义命令：`/skillstatus`、`/skilllist`、`/skillon`、`/skilloff`、`/skilldebug`

---

## 🧠 怎么做到的？/ How It Works

<p align="center">
  <b>三层路由，逐级兜底。永远有答案。</b>
  <br>
  <i>3 routing layers. Always has an answer.</i>
</p>

```
你的消息 / Your message
         ↓
┌─────────────────────────────────┐
│ Layer 1: 关键词匹配     < 0.1ms │  ← 零延迟，首先尝试
│           Keyword Match         │    Zero latency, tried first
├─────────────────────────────────┤
│ Layer 2: LLM API 路由   ~500ms  │  ← 动态检测你用的 AI
│           Dynamic AI Detection  │    Auto-detects your AI provider
├─────────────────────────────────┤
│ Layer 3: 本地语义模型   ~50ms   │  ← BGE 双语模型兜底
│           Local Bilingual BGE   │    Offline fallback
└─────────────────────────────────┘
         ↓
匹配 → 读 SKILL.md → 注入上下文 → AI 按规范执行 ✅
Match → Read SKILL.md → Inject → AI follows guidelines ✅
```

### 🎯 动态 AI 检测 / Dynamic AI Detection

**你用什么 AI，SkillRouter 就自动接入什么 AI。不需要配置。**

You use Claude? It uses Claude. You use DeepSeek? It uses DeepSeek. It just works.

检测顺序 / Detection order：
```
ANTHROPIC_API_KEY → OPENAI_API_KEY → DEEPSEEK_API_KEY → MOONSHOT_API_KEY
```

没有 API Key？没关系——本地 BGE 双语语义模型自动顶上。离线也能用。

No API key? No problem — local BGE bilingual model kicks in. Works offline.

---

## 📁 项目结构 / Project Structure

```
SkillRouter/
├── hooks/
│   └── recommend.py          ← 核心 hook，每次你打字都跑一次
│                               Core hook, runs every time you type
├── build_vector_index.py     ← 双语向量编译器（加新技能后跑一次）
│                               Bilingual vector compiler (run after adding skills)
├── skills.json               ← 技能注册表（name、description、keywords）
│                               Skill registry
├── install.py                ← 一键安装脚本
│                               One-click installer
├── .gitignore
└── README.md
```

---

## 🔧 添加你自己的技能 / Add Your Own Skills

```bash
# 1. 创建技能目录 / Create skill directory
mkdir -p ~/.claude/skills/my-awesome-skill
nano ~/.claude/skills/my-awesome-skill/SKILL.md
# （写下你的规范 / Write your guidelines）

# 2. 编辑 skills.json，加个条目 / Add an entry to skills.json:
# {
#   "name": "my-awesome-skill",
#   "description": "当用户要做X时，按Y规范执行",
#   "keywords": ["关键词1", "关键词2", "keyword3"]
# }

# 3. 重建向量索引 / Rebuild vector index
python build_vector_index.py

# 完成！无需重启 / Done! No restart needed.
```

---

## ❓ FAQ

<details>
<summary><b>Q: 会拖慢 Claude Code 吗？</b></summary>
关键词匹配 < 0.1ms，LLM 路由 ~500ms，语义匹配 ~50ms。几乎无感。首次加载模型需要 1-2 秒（之后走缓存）。
</details>

<details>
<summary><b>Q: 怎么知道技能到底加载了没？</b></summary>
AI 回复开头会显示 <code>>> ⚡ 技能已加载: xxx</code>。看不到这行就是没加载。
</details>

<details>
<summary><b>Q: 没有 API Key 怎么办？</b></summary>
没关系。关键词匹配永远可用。装 sentence-transformers 后，本地双语 BGE 模型也永远可用。纯离线都能跑。
</details>

<details>
<summary><b>Q: --bare 是什么？为什么不能用？</b></summary>
<code>claude --bare</code> 是 Claude Code 的"精简模式"，会<b>关掉所有 hooks</b>。SkillRouter 依赖 hooks 工作，所以必须用正常模式。直接打 <code>claude</code>（不加 --bare）就行。
</details>

<details>
<summary><b>Q: 支持哪些系统？</b></summary>
Windows / macOS / Linux，Python 3.10+。
</details>

---

## 📄 License

MIT — 随便用，随便改，随便发。

---

<p align="center">
  <sub>Made with ❤️ · 用 Claude Code 写 Claude Code 的插件</sub>
</p>
