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

### 第 0 步：前提条件 / Prerequisites

装 SkillRouter 之前，这三样东西得有。没装过的跟着教程走，5 分钟搞定。

You need these three things before SkillRouter. Follow the guides below, 5 minutes tops.

---

#### 🐍 Python 3.10+

怎么知道你装没装？打开终端，打：

How to check: open a terminal and type:

```bash
python --version
# or / 或者
python3 --version
```

看到 `Python 3.10.x` / `3.11.x` / `3.12.x` / `3.13.x` → 有了，跳过。  
See a 3.10+ version? Skip to the next section.

没装？按你的系统来：

**Windows：**
1. 去 https://www.python.org/downloads/ 点那个黄色大按钮下载
2. 运行安装程序，⚠️ **勾上 "Add Python to PATH"**（这步很多人忘）
3. 装完重新打开终端，打 `python --version` 验证

**macOS：**
```bash
# 方式 1：官网下载（和 Windows 一样）
# 方式 2：Homebrew（推荐）
brew install python@3.12
```

**Linux：**
```bash
# Ubuntu / Debian
sudo apt update && sudo apt install python3 python3-pip -y

# Fedora
sudo dnf install python3 python3-pip -y

# Arch
sudo pacman -S python python-pip
```

---

#### 💻 Claude Code 终端版

> ⚠️ SkillRouter 只支持 **Claude Code 终端版**（命令行工具）。  
> Web 版（claude.ai）和 VS Code/JetBrains 插件版没有 hook 系统，装了也没用。  
> SkillRouter only works with the **Claude Code CLI** (terminal). Not the web app or IDE extensions.

怎么装 Claude Code 终端版：

**方式 1：npm 全局安装（推荐，所有系统通用）**
```bash
npm install -g @anthropic-ai/claude-code
```
（没有 npm？先去 https://nodejs.org 装 Node.js，LTS 版本就行）

**方式 2：直接下载（Windows）**
去 https://claude.ai/download 下载 `.exe` 安装程序。

装完在终端打 `claude`，看到 Claude Code 的界面 → 装好了。

> 💡 如果想换成 DeepSeek 模型：把 API key 设到环境变量 `ANTHROPIC_API_KEY`，然后在 CC 里打 `/model deepseek-v4-pro`。不需要改启动命令，不需要 `claude-ds`。

---

#### 🔑 AI API Key

SkillRouter 的三层路由里，第二层（LLM 路由）需要一个 API Key。**你的 CC 在用哪个模型，就给它哪个模型的 Key。**

| 你用的模型 | 需要什么 Key | 去哪拿 |
|---|---|---|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com → API Keys |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com → API Keys |

**怎么设环境变量：**

**Windows（PowerShell）：**
```powershell
[Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-xxxxx', 'User')
# 或 DeepSeek：
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-xxxxx', 'User')
```
设完**重启终端**生效。

**macOS / Linux：**
```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-xxxxx' >> ~/.zshrc
source ~/.zshrc
```

> ❓ 没有 API Key？没关系。关键词匹配（第一层）永远可用。装了 `sentence-transformers` 的话，本地语义（第三层）也永远可用。纯离线都能跑。
> No API key? Keyword matching (layer 1) always works. Install sentence-transformers for offline semantic matching (layer 3).

---

### 第 1 步：克隆项目 / Clone

```bash
git clone https://github.com/sylvanlisayhi-cyber/SkillRouter.git
cd SkillRouter
```

### 第 2 步：装依赖 / Install Dependencies

```bash
pip install -r requirements.txt
```
（numpy 必装；sentence-transformers 可选，装了能离线语义匹配）

### 第 3 步：一键安装 / Run Installer

```bash
python install.py
```

自动干五件事：
1. 🔍 扫描你有没有 `--bare`，有就自动修
2. 📂 扫描 `~/.claude/skills/` 目录
3. 📋 生成 18 个技能的注册表（skills.json）
4. 🧠 构建中英文双语向量索引
5. ⚙️ 写入 Claude Code hook 配置

### 第 4 步：重启验证 / Restart & Verify

**重启 Claude Code（关掉重开），然后在对话框里打：**

```
--skill-status
```

看到这个 → 搞定 🎉

```
>> 🟢 技能状态：已开启 | 已注册 18 个技能 <<
```

> ❌ 没反应？你在 `--bare` 模式。再跑一次 `python install.py` 让它自动修，然后重启 CC。  
> No response? You're in --bare mode. Re-run `python install.py` to auto-fix, then restart.

---

## 🎮 使用 / Usage

### 日常：什么都不做 / Daily: Do Nothing

正常聊天就行。当你的需求命中某个技能，AI 自动按技能规范执行。

Just chat. When your request matches a skill, the AI follows its guidelines automatically.

### 魔法指令 / Magic Commands

直接打在聊天框里就行：

| 指令 / Command | 干嘛的 / What |
|---|---|
| `--skill-status` | 查看状态 / View status |
| `--skill-list` | 列出所有技能 / List all skills |
| `--skill-on` | 开启自动加载 / Enable |
| `--skill-off` | 关闭自动加载 / Disable |
| `--skill-debug` | 完整诊断 / Full diagnostics |

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

## 📂 技能放哪里？/ Where Do My Skills Live?

**所有技能都放在一个地方：**

```
~/.claude/skills/
├── frontend-design/
│   └── SKILL.md       ← 就是它！一个目录，一个 SKILL.md
├── ok-person/
│   └── SKILL.md
├── my-awesome-skill/   ← 你自己建的也放这
│   └── SKILL.md
└── ...
```

**规则很简单：**每个技能 = 一个子目录 + 一个 `SKILL.md` 文件。目录名就是技能名。

Windows 上 `~` 是 `C:\Users\你的用户名`，macOS/Linux 上就是 `/home/你的用户名` 或 `/Users/你的用户名`。

SkillRouter 装好后自动扫描这个目录。你放进去的技能会自动注册到 `skills.json`。

---

## 🔧 添加新技能 / Add a New Skill

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
<summary><b>Q: 装完没反应？打 --skill-status 什么都没发生？</b></summary>
<b>99% 是 --bare 模式。</b><br>
你启动 CC 的命令里带了 <code>--bare</code>。重新跑 <code>python install.py</code>，它会自动扫描并修复。<br>
或者自己检查：启动脚本里有没有 <code>--bare</code>？有就删，重启就行。<br>
<em>99% it's --bare. Re-run install.py for auto-fix, or check your startup scripts manually.</em>
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
打 <code>--skill-off</code>。想聊理论、问概念的时候关掉就行。打 <code>--skill-on</code> 重新开。<br>
<em>Type --skill-off to disable, --skill-on to re-enable.</em>
</details>

<details>
<summary><b>Q: 支持哪些系统？</b></summary>
Windows / macOS / Linux，Python 3.10+。
</details>

---

## 🧪 测试状态 / Tested On

| 平台 | 状态 | 备注 |
|---|---|---|
| Windows 11 + Python 3.12 + CC 2.x | ✅ 实测通过 | 开发者日常使用环境 |
| macOS + Python 3.10+ + CC 2.x | 🟡 代码逻辑支持，未实测 | 欢迎反馈 |
| Linux + Python 3.10+ + CC 2.x | 🟡 代码逻辑支持，未实测 | 欢迎反馈 |

> 项目全部使用 Python 标准库 + `Path.home()` 等跨平台 API，路径、编码均做了兼容处理。macOS / Linux 理论上直接能用，但诚实说——没跑过。
>
> Pure Python stdlib + cross-platform APIs. macOS/Linux should work out of the box, but honestly — not yet tested on them.

**遇到问题？** 来提 Issue，附上你的 OS + Python 版本 + CC 版本：  
https://github.com/sylvanlisayhi-cyber/SkillRouter/issues

---

## 📄 License

MIT — 随便用，随便改，随便发。

---

<p align="center">
  <sub>Made with ❤️ · 用 Claude Code 写 Claude Code 的插件</sub>
</p>
