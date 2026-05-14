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

## 它能干嘛？

你用 Claude Code 写代码的时候，可能建了一些 `SKILL.md` 文件来规范 AI 的行为（比如前端规范、测试规范）。问题是每次都得手动告诉 CC "请按 XX 规范回答"，很烦。

这个工具帮你自动干这件事。你在聊天框正常打字，它后台分析你想干嘛，匹配到合适的技能就自动注入到上下文里。你什么都不用做，AI 回复直接按规范来。

### 实际效果

```
你:   帮我写一个带搜索的表格组件
      ↓ 后台自动匹配 frontend-design + testing
AI:   >> ⚡ 技能已加载: frontend-design, testing <<
      [按前端规范和测试规范输出的代码]
```

### 开关控制

直接在聊天框输入以下命令：

```
--skill-on        开启
--skill-off       关闭
--skill-status    看状态
--skill-list      列出所有技能
--skill-debug     诊断信息
```

回复示例：

```
>> 🟢 技能状态：已开启 | 已注册 18 个技能 <<
```

---

## 安装

### 前提

需要 Python 3.10 或更高版本，以及 Claude Code CLI（终端版，Web 版和 IDE 插件版不支持）。

```bash
python --version        # 确认版本 ≥ 3.10
npm install -g @anthropic-ai/claude-code   # 如果还没装 CC
```

### 安装步骤

```bash
git clone https://github.com/sylvanlisayhi-cyber/AutoSkillsCC.git
cd AutoSkillsCC
pip install -r requirements.txt
python install.py
```

`install.py` 会自动做以下事情：
- 扫描你的 CC 启动脚本，如果有 `--bare` 就自动去掉（bare 模式会禁用 hook）
- 扫描 `~/.claude/skills/` 目录，注册你已有的技能
- 生成 `skills.json`（技能注册表）
- 构建中英文向量索引（如果装了 sentence-transformers）
- 写入 CC 的 hook 配置到 `~/.claude/settings.json`

装完**重启 Claude Code**，输入 `--skill-status` 验证。如果没反应，99% 是 `--bare` 模式没去掉，再跑一次 `python install.py`。

### API Key（可选）

不配 API Key 也能用。关键词匹配和本地语义模型永远生效——纯离线跑。

如果配了 API Key，LLM 精选层会更准（多 500ms 延迟）：

| 你在用的模型 | 环境变量 | Key 获取地址 |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com |

设置方式（Windows PowerShell）：

```powershell
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-xxx', 'User')
# 设完重启终端
```

macOS / Linux：

```bash
echo 'export DEEPSEEK_API_KEY=sk-xxx' >> ~/.zshrc
source ~/.zshrc
```

工具会自动检测你配了哪个 Key，用哪个 Provider。

---

## 技能放哪里？

技能就是一个目录 + 一个 `SKILL.md` 文件，全放在 `~/.claude/skills/` 下。

```
~/.claude/skills/              # macOS / Linux
C:\Users\你\.claude\skills\    # Windows

├── frontend-design/
│   └── SKILL.md       ← 文件名固定，内容随便写
├── testing/
│   └── SKILL.md
└── 你自己建的/
    └── SKILL.md
```

两条规则：目录名 = 技能名，文件名叫 `SKILL.md`。没了。

### 系统自带的技能

就算目录是空的，系统内置了 18 个技能的关键词，能匹配常见需求：

frontend-design, docx, pdf, pptx, xlsx, python-dev, database-design, docker-container, debugging, testing, git-workflow, api-design, performance-optimization, security-audit, refactoring, cli-tool, data-analysis, ok-person

这些内置技能靠关键词匹配，不需要 `SKILL.md` 文件也能触发。如果你自己建了同名目录并写了 `SKILL.md`，内容会被读取注入。

### 添加你自己的技能

```bash
# 1. 建目录写文件
mkdir -p ~/.claude/skills/my-skill
nano ~/.claude/skills/my-skill/SKILL.md

# 2. 在 skills.json 里注册
# 加一条：{
#   "name": "my-skill",
#   "description": "一句话描述",
#   "keywords": ["关键词1", "keyword2"]
# }

# 3. 重建索引
python build_vector_index.py
```

不需要重启 CC。

---

## 怎么工作的

三层路由，一层没命中就落到下一层：

```
你的消息
    ↓
Layer 1: 关键词匹配（< 0.1ms）
    BM25 算法，纯 Python，零额外依赖，缓存到磁盘
    ↓ 无匹配？
Layer 2: LLM API 路由（~500ms）
    自动检测你的 API Key，用对应模型做精选
    ↓ 无 Key 或无匹配？
Layer 3: 本地语义模型（~50ms）
    BGE 双语模型（中/英各一个），首次加载 1-2s，之后全缓存
    ↓
Ensemble 融合（BM25 × 0.3 + 向量 × 0.7）
    ↓
MMR 多样性选择（λ=0.6，避免选出来全是相似技能）
    ↓
LLM 精选（从 TOP 5 里挑 1~3 个最合适的）
    ↓
读取对应 SKILL.md → 注入到上下文 → AI 按规范回复
```

Provider 检测顺序：`ANTHROPIC_API_KEY → OPENAI_API_KEY → DEEPSEEK_API_KEY → MOONSHOT_API_KEY`。都没有就用本地模型。

---

## 项目文件

```
AutoSkillsCC/
├── hooks/
│   ├── recommend.py       # 主 hook，每次发消息时执行
│   └── cmd.py             # 轻量命令 hook（保留，未注册）
├── build_vector_index.py  # 向量索引编译（加新技能后跑）
├── install.py             # 一键安装
├── benchmark.py           # 27 个测试用例的准确率评测
├── skills.json            # 技能注册表
├── skills_vectors_en.npy  # 英文向量
├── skills_vectors_zh.npy  # 中文向量
└── requirements.txt       # numpy + sentence-transformers
```

---

## FAQ

**装完没反应？**
99% 是 CC 启动命令里带了 `--bare`。`python install.py` 会自动扫描并修复，然后重启 CC。

**会拖慢回复吗？**
不会。关键词 <1ms，语义 ~50ms，LLM ~500ms。体感无延迟。

**怎么知道技能加载了？**
AI 回复第一行显示 `>> ⚡ 技能已加载: xxx`，没看到就是没加载。

**没有 API Key 能用吗？**
能。关键词匹配永远可用。装了 `sentence-transformers`，本地语义也永远可用。纯离线。

**怎么关？**
输入 `--skill-off`，聊理论/概念的时候关掉。`--skill-on` 重新开。

---

## License

MIT
