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

### ⚠️ 装前必读 — 别让安装白费 / Read Before Installing

**99% 的"装了没用"都是同一个原因：启动了 `--bare` 模式。**

好消息：**install.py 会自动检测并修复你脚本里的 --bare。** 如果你是从终端直接打 `claude --bare`，读完下面自查一下就行。

When you run `python install.py`, it **automatically scans** your Claude Code startup scripts for `--bare` and fixes them. If you manually type `claude --bare` in the terminal — just stop doing that.

| 你的启动方式 | 怎么做 |
|---|---|
| 终端打 `claude` | ✅ 正常 |
| 终端打 `claude --bare` | ❌ **不要加 --bare** |
| 终端打 `claude-ds` / `claude-opus` / 任意名字 | ✅ 正常，名字无所谓 |
| 桌面快捷方式 / .cmd / .sh 脚本 | ✅ install.py 会自动检查并修复 |

**名字不重要。** 你叫它 `claude`、`claude-ds`、`claude-opus` 都行——关键是不带 `--bare`。模型是在 `~/.claude/settings.json` 里配的，跟启动命令叫什么毫无关系。

**The command name doesn't matter.** Whether it's `claude`, `claude-ds`, `claude-opus`, whatever — as long as there's no `--bare`. The model is configured in `settings.json`, not in the startup command name.

### 三步搞定 / 3 Steps

```bash
# 1. 克隆 / Clone
git clone https://github.com/sylvanlisayhi-cyber/SkillRouter.git
cd SkillRouter

# 2. 装依赖 / Install deps
pip install -r requirements.txt

# 3. 一键安装 / One-click install
python install.py
```

**重启 Claude Code，打 `--skill-status` 验证。看到回复 → 搞定。**  
**Restart Claude Code, type `--skill-status`. See a response? Done.**

> 🔧 如果 `--skill-status` 没反应，试 `/skillstatus`。某些 CC 版本会拦截 `--` 开头的命令。
> If `--skill-status` doesn't work, try `/skillstatus`. Some CC versions intercept `--` commands.

---

## 🎮 使用 / Usage

### 日常：什么都不做 / Daily: Do Nothing

正常聊天就行。当你的需求命中某个技能，AI 自动按技能规范执行。

Just chat. When your request matches a skill, the AI follows its guidelines automatically.

### 魔法指令 / Magic Commands

直接在聊天框里打。如果 `--xxx` 没反应，用 `/xxx`（前面加斜杠）：

| 指令 / Command | 备选 / Fallback | 干嘛的 / What |
|---|---|---|
| `--skill-status` | `/skillstatus` | 查看状态 / View status |
| `--skill-list` | `/skilllist` | 列出所有技能 / List all skills |
| `--skill-on` | `/skillon` | 开启自动加载 / Enable |
| `--skill-off` | `/skilloff` | 关闭自动加载 / Disable |
| `--skill-debug` | `/skilldebug` | 完整诊断 / Full diagnostics |

> 用 `/skillstatus` 等 CC 自定义命令永远有效，不受 CC 版本影响。  
> `/skillstatus` etc. always work, unaffected by CC version.

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
<summary><b>Q: 装完没反应？打什么都无效？</b></summary>
<b>三步排查：</b><br>
1. 试 <code>/skillstatus</code>（有些 CC 版本拦截 <code>--</code> 开头的命令）<br>
2. 如果 <code>/skillstatus</code> 也不行 → 你在 <code>--bare</code> 模式，重启不要带 <code>--bare</code><br>
3. 如果还不行 → 重新跑一次 <code>python install.py</code>，它会自动扫描修复<br>
<em>1. Try /skillstatus. 2. Restart without --bare. 3. Re-run install.py for auto-fix.</em>
</details>

<details>
<summary><b>Q: 我换了 DeepSeek 模型，启动命令还是 claude 吗？</b></summary>
<b>启动命令叫什么无所谓。</b><br>
模型是在 <code>~/.claude/settings.json</code> 里配置的，跟命令名字没关系。<br>
叫 <code>claude</code>、<code>claude-ds</code>、<code>claude-opus</code> 都行——只要别带 <code>--bare</code>。<br>
<em>The command name doesn't matter. Model is in settings.json. Just don't use --bare.</em>
</details>

<details>
<summary><b>Q: 会拖慢 Claude Code 吗？</b></summary>
关键词匹配 < 0.1ms，LLM 路由 ~500ms，语义匹配 ~50ms。几乎无感。首次加载模型需要 1-2 秒（之后走缓存）。<br>
<em>Keyword < 0.1ms, LLM ~500ms, semantic ~50ms. Barely noticeable.</em>
</details>

<details>
<summary><b>Q: 怎么知道技能到底加载了没？</b></summary>
AI 回复开头会显示 <code>>> ⚡ 技能已加载: xxx</code>。看不到这行就是没加载。<br>
<em>The AI's reply will start with <code>>> ⚡ Skill loaded: xxx</code>.</em>
</details>

<details>
<summary><b>Q: 没有 API Key 怎么办？</b></summary>
没关系。关键词匹配永远可用。装 <code>sentence-transformers</code> 后，本地双语 BGE 模型也永远可用。纯离线都能跑。<br>
<em>No problem. Keyword matching always works. Install sentence-transformers for offline local semantic matching.</em>
</details>

<details>
<summary><b>Q: 能关掉吗？怎么关？</b></summary>
打 <code>--skill-off</code> 或 <code>/skilloff</code>。想聊理论、问概念的时候关掉就行。打 <code>--skill-on</code> 重新开。<br>
<em>Type --skill-off or /skilloff to disable. --skill-on to re-enable.</em>
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
