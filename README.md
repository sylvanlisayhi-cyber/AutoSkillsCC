# AutoSkillsCC 🛜

<p align="center">
  <b>你打字，它猜你要什么技能。自动的。零操作。</b>
  <br>
  <i>Type normally. It figures out which skill you need. Automatically. Zero effort.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Claude%20Code-Hook-green?logo=claude" alt="Claude Code Hook">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/%E5%8F%8C%E8%AF%AD-Bilingual-purple" alt="Bilingual">
</p>

---

## 🤔 干嘛的？ / What does this do?

你用 Claude Code 写代码。你有技能文件（`SKILL.md`）。但你不想每次都说"请按前端规范回答"——烦死了。

**AutoSkillsCC 替你干这件事。** 你正常打字，它后台自动分析你的意图，找到最合适的技能，无声注入。你甚至不知道它干活了——直到你看到 AI 回复得特别专业。

You have skill files (`SKILL.md`) for Claude Code. You don't want to manually tell Claude "please follow the frontend guidelines" every single time.

**AutoSkillsCC does it for you. Silently.** You type. It watches. It matches. You get professional results. You do nothing.

---

## 🎬 效果 / See It In Action

### 日常使用（零操作）

```
你:   帮我写一个带搜索的表格组件
      ↓ （后台自动匹配 frontend-design + testing 技能，你什么都没做）
AI:   >> ⚡ 技能已加载: frontend-design, testing <<
      [输出含 TypeScript 类型、Tailwind CSS、单元测试的工业级代码]
```

### 魔法指令（打字就行）

```
你:   --skill-on
AI:   >> 🟢 技能自动加载：已开启 <<

你:   --skill-status
AI:   >> 🟢 技能状态：已开启 | 已注册 18 个技能 <<

你:   --skill-off
AI:   >> 🔴 技能自动加载：已关闭 <<

你:   --skill-list
AI:   >> 📋 已注册技能 (18) <<
```

| 指令 | 作用 |
|---|---|
| `--skill-status` | 查看状态 |
| `--skill-list` | 列出所有技能 |
| `--skill-on` | 开启自动加载 |
| `--skill-off` | 关闭自动加载 |
| `--skill-debug` | 完整诊断 |

---

## 📦 安装 / Install

### 第 0 步：准备工作（3 样东西）/ Prerequisites

装 AutoSkillsCC 之前，这三样东西得有。没装过跟着教程走，5 分钟搞定。

You need these three things. Follow the guides below, 5 minutes tops.

---

#### 🐍 Python 3.10+

打开终端，输入： / Open a terminal and type:

```bash
python --version
# 或 / or
python3 --version
```

看到 `Python 3.10.x` / `3.11.x` / `3.12.x` / `3.13.x` → 有了，跳过。  
没装？去 https://www.python.org/downloads/ 点黄色按钮下载。⚠️ **勾上 "Add Python to PATH"**（很多人忘记这步）。

If you see `Python 3.10.x` or higher, skip. Otherwise download from the link above.

---

#### 💻 Claude Code 终端版

> ⚠️ AutoSkillsCC 只支持 **Claude Code CLI**（命令行工具）。Web 版、VS Code / JetBrains 插件版没有 Hook 系统，装了也没用。

装 Claude Code CLI：

```bash
npm install -g @anthropic-ai/claude-code
```

（没有 npm？去 https://nodejs.org 装 Node.js LTS 版本）

装完在终端打 `claude`，看到 Claude Code 界面 → 装好了。

---

#### 🔑 AI API Key（可选 / Optional）

AutoSkillsCC 的关键词匹配和本地语义模型永远可用——**纯离线都能跑。**  
API Key 只是让 LLM 精选层更准（可选，约 500ms 额外延迟）。

| 你用的模型 | 需要什么 Key | 去哪拿 |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com |

设置环境变量（Windows PowerShell）：

```powershell
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-你的key', 'User')
# 设完重启终端
```

macOS / Linux：

```bash
echo 'export DEEPSEEK_API_KEY=sk-你的key' >> ~/.zshrc
source ~/.zshrc
```

> 没有 API Key？完全没关系。关键词匹配（Layer 1）永远可用。装了 `sentence-transformers` 的话，本地语义（Layer 3）也永远可用。纯离线都能跑。

---

### 第 1 步：克隆项目 / Clone

```bash
git clone https://github.com/sylvanlisayhi-cyber/AutoSkillsCC.git
cd AutoSkillsCC
```

### 第 2 步：装依赖 / Install Dependencies

```bash
pip install -r requirements.txt
```

（`numpy` 必装；`sentence-transformers` 可选，装了能离线语义匹配）

### 第 3 步：一键安装 / Run Installer

```bash
python install.py
```

自动干五件事：
1. 🔍 扫描你有没有 `--bare`，有就自动修
2. 📂 扫描 `~/.claude/skills/` 目录，找到你的技能
3. 📋 生成技能注册表（`skills.json`）
4. 🧠 构建中英文双语向量索引
5. ⚙️ 写入 Claude Code Hook 配置

### 第 4 步：重启验证 / Restart & Verify

**重启 Claude Code（关掉重开），然后打：**

```
--skill-status
```

看到这个 → 搞定 🎉

```
>> 🟢 技能状态：已开启 | 已注册 18 个技能 <<
```

> ❌ 没反应？你在 `--bare` 模式。再跑一次 `python install.py` 让它自动修，然后重启 CC。

---

## 📂 技能放哪里？（重点！）/ Where to Put Skills

**这是最重要的部分。技能就是 markdown 文件，放在一个固定目录就行。**

This is the most important part. Skills are just markdown files in a specific folder.

### 目录结构 / Folder Structure

```
C:\Users\你的用户名\.claude\skills\    ← Windows
  或
~/.claude/skills/                      ← macOS / Linux

├── frontend-design/        ← 技能名 = 目录名
│   └── SKILL.md           ← 技能内容（怎么写都行）
│
├── testing/
│   └── SKILL.md
│
├── my-awesome-skill/       ← 你自己建的也放这
│   └── SKILL.md
│
└── ...
```

### 规则只有两条 / Only Two Rules

| | |
|---|---|
| 1️⃣ 每个技能 = 一个**目录** | 目录名就是技能名（`frontend-design`、`testing`……） |
| 2️⃣ 目录里放一个 **SKILL.md** | 文件名必须是 `SKILL.md`，内容随便写 |

### 示例：创建一个技能 / Example

```bash
# 1. 建目录
mkdir -p ~/.claude/skills/my-cool-skill

# 2. 写 SKILL.md（用任意编辑器）
nano ~/.claude/skills/my-cool-skill/SKILL.md
```

SKILL.md 内容示例：

```markdown
# My Cool Skill

When the user asks for Python code:
- Always add type hints
- Use f-strings for formatting
- Include docstrings for all functions
```

### 内置技能（开箱即用）/ Built-in Skills

没建技能目录也能用。AutoSkillsCC 内置了 18 个预定义技能：

| 技能 | 描述 |
|---|---|
| `frontend-design` | React/Vue 组件开发、Tailwind CSS、响应式布局 |
| `docx` | Word 文档生成与编辑 |
| `pdf` | PDF 生成、读取、解析 |
| `pptx` | PPT 演示文稿创建 |
| `xlsx` | Excel 表格处理 |
| `python-dev` | Python 后端开发、FastAPI/Django/Flask |
| `database-design` | 数据库设计、SQL 优化、MySQL/PostgreSQL |
| `docker-container` | Docker 容器化、K8s 编排 |
| `debugging` | 代码调试、错误堆栈分析 |
| `testing` | 自动化测试、单元测试、E2E |
| `git-workflow` | Git 工作流、分支管理、PR 审查 |
| `api-design` | RESTful/GraphQL API 设计 |
| `performance-optimization` | 性能优化、缓存策略 |
| `security-audit` | 安全审计、XSS/CSRF/JWT |
| `refactoring` | 代码重构、Clean Code |
| `cli-tool` | CLI 命令行工具开发 |
| `data-analysis` | 数据分析、Pandas/NumPy/Matplotlib |
| `ok-person` | ok 人 |

---

## 🔧 添加新技能 / Add a New Skill

```bash
# 1. 创建技能目录
mkdir -p ~/.claude/skills/my-awesome-skill
nano ~/.claude/skills/my-awesome-skill/SKILL.md
# 写下你的规范 / Write your guidelines

# 2. 编辑 skills.json，加条目
# {
#   "name": "my-awesome-skill",
#   "description": "当用户要做X时，按Y规范执行",
#   "keywords": ["关键词1", "keyword2"]
# }

# 3. 重建向量索引
python build_vector_index.py

# 完成！无需重启 / Done! No restart needed.
```

---

## 🧠 工作原理 / How It Works

```
你的消息 / Your message
         ↓
┌─────────────────────────────────┐
│ Layer 1: 关键词匹配     < 0.1ms │  ← 零延迟，首先尝试
│           Keyword Match         │
├─────────────────────────────────┤
│ Layer 2: LLM API 路由   ~500ms  │  ← 自动检测你用的 AI
│           Dynamic AI Detection  │
├─────────────────────────────────┤
│ Layer 3: 本地语义模型   ~50ms   │  ← BGE 双语模型兜底
│           Bilingual BGE Model   │
└─────────────────────────────────┘
         ↓
  Ensemble 融合 (BM25 × 0.3 + Vector × 0.7)
         ↓
  MMR 多样性选择（避免技能扎堆，λ = 0.6）
         ↓
  LLM 精选（从 5 个候选挑 1~3 个）
         ↓
  读取 SKILL.md → 注入上下文 → AI 按规范回复 ✅
```

### 🎯 自动检测你用的 AI

你用什么 AI，AutoSkillsCC 就用什么 AI。不需要配置。

```
ANTHROPIC_API_KEY → OPENAI_API_KEY → DEEPSEEK_API_KEY → MOONSHOT_API_KEY
```

没有 API Key？本地 BGE 双语模型自动顶上。纯离线也能跑。

---

## 📁 项目结构 / Project Structure

```
AutoSkillsCC/
├── hooks/
│   └── recommend.py          ← 核心 hook，每次你打字都跑一次
├── build_vector_index.py     ← 双语向量编译器（加新技能后跑一次）
├── install.py                ← 一键安装脚本
├── skills.json               ← 技能注册表（18 个预设技能）
├── skills_vectors_en.npy     ← 英文向量索引
├── skills_vectors_zh.npy     ← 中文向量索引
└── README.md
```

---

## 🧪 测试 / Testing

```bash
python benchmark.py
```

运行 27 个测试用例，验证路由准确率。

---

## ❓ FAQ

<details>
<summary><b>Q: 装完没反应？打 --skill-status 什么都没发生？</b></summary>
<b>99% 是 --bare 模式。</b><br>
你启动 CC 的命令里带了 <code>--bare</code>。重新跑 <code>python install.py</code>，它会自动扫描并修复。<br>
<em>99% it's --bare. Re-run install.py for auto-fix.</em>
</details>

<details>
<summary><b>Q: 会拖慢 Claude Code 吗？</b></summary>
关键词 < 0.1ms，LLM ~500ms，语义 ~50ms。几乎无感。首次加载模型 1-2 秒（之后走缓存）。<br>
<em>Keyword < 0.1ms, LLM ~500ms, semantic ~50ms. Barely noticeable.</em>
</details>

<details>
<summary><b>Q: 怎么知道技能到底加载了没？</b></summary>
AI 回复第一行会显示 <code>>> ⚡ 技能已加载: xxx</code>。看不到就是没加载。<br>
<em>AI's reply starts with <code>>> ⚡ Skill loaded: xxx</code>.</em>
</details>

<details>
<summary><b>Q: 没有 API Key 怎么办？</b></summary>
没关系。关键词永远可用。装 <code>sentence-transformers</code> 后本地语义也永远可用。纯离线。<br>
<em>No API key needed. Keyword matching always works. Install sentence-transformers for offline semantic matching.</em>
</details>

<details>
<summary><b>Q: 能关掉吗？</b></summary>
打 <code>--skill-off</code>。聊理论的时候关掉。打 <code>--skill-on</code> 重新开。<br>
<em>Type --skill-off to disable, --skill-on to re-enable.</em>
</details>

<details>
<summary><b>Q: 支持哪些系统？</b></summary>
Windows / macOS / Linux，Python 3.10+。
</details>

<details>
<summary><b>Q: 和 autoskills、AutoSkill 是什么关系？</b></summary>
<b>互补，不竞争。</b><br>
<code>autoskills</code>（midudev）= 帮你<b>下载</b>技能文件到本地<br>
<code>AutoSkill</code>（ECNU）= 帮你从对话中<b>自动生成</b>技能<br>
<code>AutoSkillsCC</code>（本项目）= 帮你<b>实时匹配并注入</b>技能到 CC<br>
<em>autoskills downloads skills. AutoSkill generates skills. AutoSkillsCC matches and injects them in real-time for Claude Code.</em>
</details>

---

## 📄 License

MIT — 随便用，随便改，随便发。

---

<p align="center">
  <sub>Made with ❤️ · 用 Claude Code 写 Claude Code 的插件</sub>
  <br>
  <sub>AutoSkillsCC · 打字即匹配，无声注入</sub>
</p>
