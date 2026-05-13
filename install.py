#!/usr/bin/env python3
"""SkillRouter Installer — One command setup for automatic skill routing in Claude Code.

What it does:
  1. Scans your ~/.claude/skills/ directory
  2. Generates skills.json (registry of all skills)
  3. Builds bilingual vector index (optional, if sentence-transformers is installed)
  4. Writes Claude Code hook configuration to settings.json

Requirements:
  - Python 3.10+
  - numpy (pip install numpy)
  - sentence-transformers (optional: pip install sentence-transformers for local semantic mode)

Usage:
  git clone https://github.com/sylvanlisayhi-cyber/SkillRouter.git
  cd SkillRouter
  pip install numpy
  python install.py
  # Restart Claude Code — Done!
"""
import json, sys, subprocess
from pathlib import Path

if sys.version_info < (3, 10):
    print(f'[x] Python 3.10+ required. Your version: {sys.version}')
    sys.exit(1)

SETTINGS     = Path.home() / '.claude' / 'settings.json'
HOOK_SCRIPT  = Path(__file__).parent / 'hooks' / 'recommend.py'
BUILD_SCRIPT = Path(__file__).parent / 'build_vector_index.py'

SKILLS_ROOTS = [
    Path('/mnt/skills/public'),
    Path.home() / '.claude' / 'skills',
    Path(__file__).parent / 'skills',
]

SKILL_DB = {
    'frontend-design':          ('React/Vue组件开发规范 — TypeScript、Tailwind CSS、响应式布局、无障碍设计', 'frontend react vue angular component html css tailwind web jsx tsx next.js nuxt svelte 前端 按钮 组件 界面 页面 表单 布局 ui 样式 响应式 导航栏 弹窗 modal 表格 列表'.split()),
    'docx':                     ('Word文档生成与编辑，.docx文件创建、格式化、模板处理', 'word docx document report doc 文档 报告'.split()),
    'pdf':                      ('PDF文件生成、读取、解析与内容提取', 'pdf generate read 生成 读取'.split()),
    'pptx':                     ('PowerPoint演示文稿创建，幻灯片布局设计与内容填充', 'ppt pptx slides presentation 演示 幻灯片 课件'.split()),
    'xlsx':                     ('Excel电子表格处理，数据导入导出、公式计算与图表', 'excel xlsx spreadsheet csv xls 表格 电子表格 数据导出'.split()),
    'python-dev':               ('Python后端开发规范 — FastAPI/Django/Flask、pytest、pip', 'python pip script pytest django flask fastapi import'.split()),
    'database-design':          ('数据库设计与SQL优化 — MySQL/PostgreSQL/MongoDB/Redis', 'database sql mysql postgresql mongodb redis orm query index 数据库 查询 索引 表'.split()),
    'docker-container':         ('Docker容器化部署 — Dockerfile编写、K8s编排', 'docker container dockerfile k8s kubernetes deploy 部署 容器'.split()),
    'debugging':                ('代码调试与故障排查 — 错误堆栈分析、性能瓶颈定位', 'debug bug error crash stack fix 调试 错误 bug 修复 报错 崩溃 异常 堆栈'.split()),
    'testing':                  ('自动化测试规范 — 单元测试、集成测试、E2E、覆盖率', 'test jest pytest e2e coverage mock 测试 单元测试 集成测试'.split()),
    'git-workflow':             ('Git工作流规范 — 分支管理、提交信息、PR审查', 'git commit branch merge rebase pr push clone 分支 提交'.split()),
    'api-design':               ('RESTful/GraphQL API设计规范 — OpenAPI、端点命名、版本管理', 'api rest graphql endpoint swagger openapi restful 接口'.split()),
    'performance-optimization': ('性能优化指南 — 慢查询分析、缓存策略、CDN与资源压缩', 'performance optimize slow latency profile benchmark cache 性能 优化 加速 缓存'.split()),
    'security-audit':           ('安全审计规范 — XSS/CSRF防护、JWT认证、SQL注入防御', 'security xss csrf ssl auth jwt vulnerability 安全 加密 认证'.split()),
    'refactoring':              ('代码重构最佳实践 — Clean Code、设计模式、代码异味消除', 'refactor clean code quality 重构 代码质量 设计模式'.split()),
    'cli-tool':                 ('CLI命令行工具开发规范 — argparse、终端交互设计', 'cli terminal bash shell argparse 命令行 终端 脚本'.split()),
    'data-analysis':            ('数据分析工作流 — Pandas/NumPy、Matplotlib可视化、统计建模', 'pandas numpy csv analysis visualization matplotlib 数据分析 数据可视化 统计 图表'.split()),
}

def check_numpy():
    try:
        import numpy  # noqa
        return True
    except ImportError:
        return False

def check_sentence_transformers():
    try:
        import sentence_transformers  # noqa
        return True
    except ImportError:
        return False

def detect_skills_root():
    for p in SKILLS_ROOTS:
        if p.is_dir():
            return p
    return None

def scan_skills(root):
    entries = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / 'SKILL.md').exists():
            continue
        name = d.name
        if name in SKILL_DB:
            desc, kw = SKILL_DB[name]
        else:
            desc = f'{name} skill'
            kw = name.replace('-', ' ').split()
        entries.append({'name': name, 'description': desc, 'keywords': kw})
    return entries

def build_vector_index():
    if not BUILD_SCRIPT.exists():
        print('[!] build_vector_index.py not found, skipping')
        return
    if not check_sentence_transformers():
        print('[!] sentence-transformers not installed')
        print('    Local semantic matching unavailable (pip install sentence-transformers to enable)')
        print('    Keyword matching + LLM API routing will still work')
        return

    print('[*] Building bilingual vector index...')
    try:
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            timeout=300,
            capture_output=False,
        )
        if result.returncode == 0:
            print('[v] Vector index ready — local semantic matching enabled')
        else:
            print(f'[!] Vector build failed (exit {result.returncode})')
    except subprocess.TimeoutExpired:
        print('[!] Build timed out — try: HF_ENDPOINT=https://hf-mirror.com python build_vector_index.py')
    except Exception as e:
        print(f'[!] Error: {e}')

def write_settings():
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    try:
        s = json.loads(SETTINGS.read_text(encoding='utf-8'))
    except Exception:
        s = {}

    py = sys.executable.replace('\\', '/')
    hp = str(HOOK_SCRIPT).replace('\\', '/')
    hook_cmd = f'{py} {hp}'

    s.setdefault('hooks', {})
    s['hooks']['UserPromptSubmit'] = [{
        'matcher': '',
        'hooks': [{'type': 'command', 'command': hook_cmd, 'timeout': 30}]
    }]

    # Add CC custom commands for skill control
    s.setdefault('commands', {})
    s['commands']['skillstatus'] = {'description': 'Show SkillRouter status', 'prompt': '--skill-status'}
    s['commands']['skilllist']   = {'description': 'List all registered skills', 'prompt': '--skill-list'}
    s['commands']['skillon']     = {'description': 'Enable auto-loading', 'prompt': '--skill-on'}
    s['commands']['skilloff']    = {'description': 'Disable auto-loading', 'prompt': '--skill-off'}
    s['commands']['skilldebug']  = {'description': 'Diagnostic report', 'prompt': '--skill-debug'}

    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    print('=' * 55)
    print('  SkillRouter Installer — Smart Skill Auto-Loader')
    print('=' * 55)
    print(f'  Python: {sys.executable}')

    if not HOOK_SCRIPT.exists():
        print(f'\n[x] Hook script not found: {HOOK_SCRIPT}')
        print('    Make sure you cloned the full repository.')
        sys.exit(1)

    # Check dependencies
    if not check_numpy():
        print('\n[x] numpy is required. Install it first:')
        print('    pip install numpy')
        sys.exit(1)

    has_st = check_sentence_transformers()

    # Scan skills
    skills_json = Path(__file__).parent / 'skills.json'
    root = detect_skills_root()
    if root:
        print(f'\n[*] Skills directory: {root}')
        entries = scan_skills(root)
        if entries:
            print(f'    Found {len(entries)} skills: {[e["name"] for e in entries]}')
        else:
            print('    No SKILL.md files found — using default registry')
            entries = []
        skills_json.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        print(f'\n[!] No skills directory found')
        print(f'    Create one at ~/.claude/skills/<name>/SKILL.md')
        print(f'    Using existing skills.json')

    # Build vectors (optional)
    build_vector_index()

    # Write settings
    write_settings()
    print(f'\n[v] Hook installed to: {SETTINGS}')

    # Summary
    keyword_ok = 'Yes'
    llm_ok = 'Yes (auto-detect your API key)'
    local_ok = 'Yes (BGE bilingual)' if has_st else 'No — pip install sentence-transformers'

    print(f'\n{"─" * 55}')
    print('  Routing layers available:')
    print(f'  1. Keyword matching:      {keyword_ok}')
    print(f'  2. LLM API routing:        {llm_ok}')
    print(f'  3. Local semantic:         {local_ok}')
    print(f'{"─" * 55}')

    print(f'''
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  READ THIS — or SkillRouter won't work!                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Restart Claude Code. Then type: --skill-status              ║
║                                                              ║
║  ✅ See a response? → You're good.                           ║
║  ❌ No response? → You're in --bare mode.                    ║
║                                                              ║
║  BARE MODE: The #1 reason SkillRouter "doesn't work".        ║
║                                                              ║
║  Fix: Don't run "claude --bare". Just run "claude".          ║
║       Model is in settings.json, not in the command.         ║
║       If you have a custom .cmd/.sh shortcut, open it        ║
║       and delete the "--bare" part.                          ║
║                                                              ║
║  不管你把模型换成什么 (DeepSeek, OpenAI...)，启动命令        ║
║  永远是 "claude"。模型在 settings.json 里配置，跟命令        ║
║  没关系。不需要 claude-ds、claude-opus 之类的东西。          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝''')
    print(f'  Try in CC:')
    print(f'    --skill-status  View router status')
    print(f'    --skill-list    List all {len(entries) if root else "?"} skills')
    print(f'    --skill-debug   Full diagnostic')
    print(f'    --skill-off     Disable')
    print(f'    --skill-on      Re-enable')


if __name__ == '__main__':
    main()
