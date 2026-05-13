# SkillRouter

<p align="center">
  <b>🔀 智能语义路由 — 让 Claude Code 自动加载正确的技能，每次都对。</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python">
  <img src="https://img.shields.io/badge/Claude%20Code-hook-green" alt="Claude Code Hook">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

## 🤔 这是什么？

用 Claude Code 写代码时，你有一堆技能规范（`SKILL.md`），但你不想每次手动告诉 Claude "这次请按前端规范回答"。

**SkillRouter** 是一个 Claude Code Hook：你正常打字，它后台自动分析你的意图，找到最合适的技能规范，无声注入到上下文。Claude 直接按规范执行——你零操作。

### 真实效果

```
你:   帮我写一个带搜索的表格组件
      ↓ （后台自动匹配 frontend-design 技能）
AI:   > 🪄 技能已加载: frontend-design
      [然后输出含 TypeScript 类型、Tailwind 样式、loading/error 状态的工业级代码]
```

---

## 📦 安装（2 步）

### 第 1 步：把项目放到本地

```bash
git clone https://github.com/sylvanlisayhi-cyber/SkillRouter.git
cd SkillRouter
```

### 第 2 步：运行安装脚本

```bash
python install.py
```

它会自动：
- 扫描你的技能目录
- 生成技能注册表（`skills.json`）
- 编译语义向量索引
- 写入 Claude Code 的 hook 配置

**重启 Claude Code 就生效。**

---

## 📁 项目结构

```
SkillRouter/
├── hooks/
│   └── recommend.py          ← 核心 hook，每次回车执行
├── build_vector_index.py     ← 离线向量编译器（新增技能后运行）
├── skills.json               ← 技能注册表（name、description、keywords）
├── skills_vectors.npy        ← 预计算的 384 维语义向量
├── install.py                ← 一键安装脚本
├── .gitignore
└── README.md
```

---

## 🎮 使用方式

### 日常使用

**什么都不用做。** 正常聊天，当你的需求命中某个技能时，AI 回复的第一行会显示：

```
> 🪄 技能已加载: frontend-design
```

### 魔法指令

在聊天框直接输入：

| 指令 | 作用 |
|------|------|
| `--skill-status` | 查看当前状态（开/关，已注册技能数） |
| `--skill-list` | 列出所有已注册的技能 |
| `--skill-off` | 关闭自动加载（聊理论时不想被干预） |
| `--skill-on` | 重新开启 |

---

## 🔧 添加新技能

1. 在 `~/.claude/skills/` 下新建目录，放入 `SKILL.md`
2. 编辑 `skills.json`，添加条目：

```json
{
  "name": "my-skill",
  "description": "一句话描述这个技能的用途",
  "keywords": ["关键词1", "关键词2", "keyword3"]
}
```

3. 运行 `python build_vector_index.py`
4. 完成，无需重启

---

## 🧠 工作原理

```
你的消息
    ↓
[1] 魔法指令拦截 → --skill-* 直接处理
    ↓
[2] 状态检查 → .enabled 不存在就跳过
    ↓
[3] 意图过滤 → "是什么/为什么" 等理论提问跳过
    ↓
[4] 语义向量匹配 → paraphrase-multilingual-MiniLM-L12-v2（已集成，中文准确）
    ↓ (低于阈值或模型不可用)
[5] 关键词兜底 → skills.json 的 keywords 字段
    ↓
[6] 读取 SKILL.md → 注入到 Claude 上下文
    ↓
[7] Claude 按技能规范执行，回复第一行显示 🪄 已加载
```

### 语义 + 关键词双层匹配

- **语义层**：用 sentence-transformers 把你的输入和技能描述都转成 384 维向量，算余弦相似度。阈值 0.40。
- **关键词层**：语义没命中时，用 `skills.json` 里的 `keywords` 做纯文本匹配。

**模型说明**：当前使用 `paraphrase-multilingual-MiniLM-L12-v2`（多语言，~470MB），中文语义匹配准确。如需切换回纯英文轻量模型，把两个文件里的模型名改回 `all-MiniLM-L6-v2`（80MB）。

---

## ❓ FAQ

**Q: 它会让 Claude 变慢吗？**
A: 首次触发加载模型需要 1-2 秒（后续走缓存）。完全值得。

**Q: 怎么知道技能到底加载了没？**
A: AI 回复第一行会显示 `> 🪄 技能已加载: xxx`。看不到这行就是没加载。

**Q: 支持哪些系统？**
A: Windows / macOS / Linux，Python 3.10+。

**Q: 技能怎么管理？**
A: 纯粹的文件系统。`~/.claude/skills/技能名/SKILL.md`。你建目录、写 markdown、注册到 `skills.json` 就行。

---

## 📄 License

MIT
