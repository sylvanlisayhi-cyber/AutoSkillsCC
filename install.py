#!/usr/bin/env python3
"""AutoSkillsCC Installer — One command setup for automatic skill routing in Claude Code.

What it does:
  1. Checks for --bare mode in your startup scripts and auto-fixes it
  2. Scans your ~/.claude/skills/ directory
  3. Generates skills.json (registry of all skills)
  4. Builds bilingual vector index (optional)
  5. Writes Claude Code hook configuration to settings.json

Usage:
  git clone https://github.com/sylvanlisayhi-cyber/AutoSkillsCC.git
  cd AutoSkillsCC
  pip install -r requirements.txt
  python install.py
  # Restart Claude Code — Done!
"""
import json, sys, subprocess, os, re, shutil, io, argparse
from pathlib import Path

if sys.version_info < (3, 10):
    print(f'[x] Python 3.10+ required. Your version: {sys.version}')
    sys.exit(1)

if sys.platform == 'win32':
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

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

# ── Bare mode auto-detection & fix ──────────────────────────────────────────

BARE_PATTERN = re.compile(r'\s--bare(?=\s|$)', re.IGNORECASE)

def _get_npm_bin():
    """Get npm global bin directory."""
    try:
        result = subprocess.run(
            ['npm', 'config', 'get', 'prefix'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            prefix = result.stdout.strip()
            if sys.platform == 'win32':
                return Path(prefix)
            return Path(prefix) / 'bin'
    except Exception:
        pass
    # Fallback defaults
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'npm'
    return Path('/usr/local/bin')

def _scan_files_for_bare(directory, pattern='claude*'):
    """Scan a directory for files matching pattern that contain --bare."""
    hits = []
    if not directory or not directory.is_dir():
        return hits
    for f in sorted(directory.iterdir()):
        if not f.is_file():
            continue
        name = f.name.lower()
        # Match: claude, claude.cmd, claude.ps1, claude-ds, claude-ds.cmd, etc.
        if not name.startswith('claude'):
            continue
        # Skip .ps1 module manifests, only check scripts
        if f.suffix.lower() not in ('', '.cmd', '.bat', '.ps1', '.sh', '.bash', '.zsh'):
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            # Binary file? Skip
            continue
        if BARE_PATTERN.search(content):
            hits.append((f, content))
    return hits

def _scan_shell_configs():
    """Scan common shell config files for --bare in aliases."""
    hits = []
    configs = []
    home = Path.home()
    for rc in ['.bashrc', '.bash_profile', '.bash_aliases', '.zshrc', '.zprofile',
               '.profile', '.config/fish/config.fish', '.aliases']:
        p = home / rc
        if p.is_file():
            configs.append(p)
    # Also check /etc for system-wide configs
    for p in [Path('/etc/bash.bashrc'), Path('/etc/zsh/zshrc')]:
        if p.is_file():
            configs.append(p)

    for f in configs:
        try:
            content = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        # Find lines with claude AND --bare
        for line in content.splitlines():
            if 'claude' in line.lower() and BARE_PATTERN.search(line):
                hits.append((f, line.strip()))
                break  # One hit per file is enough
    return hits

def _scan_desktop_shortcuts():
    """Scan Windows desktop shortcuts for --bare. Returns list of (path, target)."""
    if sys.platform != 'win32':
        return []
    hits = []
    desktop = Path.home() / 'Desktop'
    if not desktop.is_dir():
        # Chinese Windows: 桌面
        desktop_cn = Path.home() / '桌面'
        if desktop_cn.is_dir():
            desktop = desktop_cn
    if not desktop.is_dir():
        return hits

    for f in sorted(desktop.iterdir()):
        if not f.suffix.lower() == '.lnk':
            continue
        if 'claude' not in f.name.lower():
            continue
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(f))
            target = shortcut.TargetPath or ''
            args = shortcut.Arguments or ''
            combined = f'{target} {args}'
            if '--bare' in combined:
                hits.append((f, combined))
        except Exception:
            # win32com may not be available, skip
            pass
    return hits

def _fix_file(filepath, content=None):
    """Remove --bare from file content. Returns new content or None if unchanged."""
    if content is None:
        try:
            content = filepath.read_text(encoding='utf-8', errors='replace')
        except Exception:
            return None
    # Replace ' --bare' (with leading space, optional trailing space)
    new_content = BARE_PATTERN.sub('', content)
    if new_content != content:
        return new_content
    return None

def check_and_fix_bare():
    """Main entry: scan for bare mode and auto-fix."""
    print('\n[*] Checking for --bare mode in your startup scripts...')

    npm_bin = _get_npm_bin()
    print(f'    npm bin dir: {npm_bin}')

    problems = []

    # 1. Scan npm global bin for claude* scripts
    script_hits = _scan_files_for_bare(npm_bin)
    for f, content in script_hits:
        problems.append(('script', f, content))

    # 2. Scan shell configs (Linux/macOS)
    for f, line in _scan_shell_configs():
        problems.append(('shell_config', f, line))

    # 3. Scan desktop shortcuts (Windows)
    for f, target in _scan_desktop_shortcuts():
        problems.append(('shortcut', f, target))

    if not problems:
        print('    [v] No --bare found in your startup scripts — good!')
        return

    # Report findings
    print(f'\n    [!] Found --bare in {len(problems)} location(s):')
    for kind, f, detail in problems:
        if kind == 'script':
            # Find the line containing --bare
            for line in detail.splitlines():
                if '--bare' in line:
                    print(f'        {f}')
                    print(f'        → {line.strip()}')
                    break
        elif kind == 'shell_config':
            print(f'        {f}')
            print(f'        → {detail}')
        else:
            print(f'        {f} (Desktop shortcut)')
            print(f'        → {detail}')

    # Auto-fix
    print()
    fixed_count = 0
    for kind, f, content in problems:
        if kind == 'shortcut':
            print(f'    [!] Skipped shortcut (needs manual fix): {f.name}')
            print(f'        Right-click → Properties → remove "--bare" from Target/Arguments')
            continue
        if kind == 'shell_config':
            print(f'    [!] Skipped shell config (needs manual check): {f}')
            print(f'        Edit the file and remove "--bare" from the claude alias')
            continue

        # Auto-fix scripts (.cmd/.ps1/.sh)
        new_content = _fix_file(f, content)
        if new_content is None:
            continue
        # Backup
        backup = f.with_suffix(f.suffix + '.skillrouter-backup')
        try:
            shutil.copy2(f, backup)
            f.write_text(new_content, encoding='utf-8')
            print(f'    [v] Fixed: {f.name}  (backup: {backup.name})')
            fixed_count += 1
        except Exception as e:
            print(f'    [x] Failed to fix {f.name}: {e}')

    if fixed_count:
        print(f'\n    [v] Auto-fixed {fixed_count} file(s). Originals backed up as *.skillrouter-backup')
    if any(kind in ('shortcut', 'shell_config') for kind, _, _ in problems):
        print(f'    [!] Some items need manual fix — see above.')

    print()

# ── Dependency checks ──────────────────────────────────────────────────────

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

# ── Skill scanning ─────────────────────────────────────────────────────────

def detect_skills_root():
    for p in SKILLS_ROOTS:
        if p.is_dir():
            return p
    return None

def scan_skills(root):
    """Recursively scan for SKILL.md files. Supports both flat and nested layouts:
    skills/name/SKILL.md         → name = directory name
    skills/category/name/SKILL.md → name = leaf directory name
    """
    seen = set()
    entries = []
    for f in sorted(root.rglob('SKILL.md')):
        name = f.parent.name
        if name in seen:
            continue
        seen.add(name)
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
        print('    Local semantic matching unavailable: pip install sentence-transformers')
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

    # Add CC custom commands for --skill-* magic commands
    s.setdefault('commands', {})
    s['commands']['skillstatus'] = {
        'description': 'Show AutoSkillsCC status',
        'prompt': '--skill-status'
    }
    s['commands']['skilllist'] = {
        'description': 'List all registered skills',
        'prompt': '--skill-list'
    }
    s['commands']['skillon'] = {
        'description': 'Enable auto-loading of skills',
        'prompt': '--skill-on'
    }
    s['commands']['skilloff'] = {
        'description': 'Disable auto-loading of skills',
        'prompt': '--skill-off'
    }
    s['commands']['skilldebug'] = {
        'description': 'Show AutoSkillsCC diagnostic info',
        'prompt': '--skill-debug'
    }

    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')

# ═══ Main ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='AutoSkillsCC Installer')
    parser.add_argument('--refresh', action='store_true',
                        help='Refresh skills.json and rebuild vector index only (skip bare check & hook config)')
    args = parser.parse_args()

    print('=' * 55)
    print('  AutoSkillsCC Installer — Smart Skill Auto-Loader')
    print('=' * 55)
    print(f'  Python: {sys.executable}')

    if args.refresh:
        print('\n[*] --refresh mode: updating skills.json and rebuilding vectors...')
        # Clear stale caches
        cache_dir = Path(__file__).parent / 'cache'
        if cache_dir.is_dir():
            import shutil as _shutil
            _shutil.rmtree(cache_dir)
            print('[*] Cleared cache/ directory')
    else:
        if not HOOK_SCRIPT.exists():
            print(f'\n[x] Hook script not found: {HOOK_SCRIPT}')
            print('    Make sure you cloned the full repository.')
            sys.exit(1)

        # ── Step 0: Bare mode check ──
        check_and_fix_bare()

        # ── Step 1: Dependencies ──
        if not check_numpy():
            print('[x] numpy is required. Install it first:')
            print('    pip install -r requirements.txt')
            sys.exit(1)

    has_st = check_sentence_transformers()

    # ── Step 2: Scan skills ──
    skills_json = Path(__file__).parent / 'skills.json'
    root = detect_skills_root()
    entries = []
    if root:
        print(f'[*] Skills directory: {root}')
        scanned = scan_skills(root)
        scanned_names = {e['name'] for e in scanned}
        # Add scanned skills first
        entries = list(scanned)
        # Also include SKILL_DB entries for skills without SKILL.md files yet
        # (so the LLM router knows about all available skills)
        for name, (desc, kw) in SKILL_DB.items():
            if name not in scanned_names:
                entries.append({'name': name, 'description': desc, 'keywords': kw})
        if scanned:
            print(f'    Found {len(scanned)} SKILL.md(s), {len(entries)} skills total')
        else:
            print(f'    No SKILL.md files found — using {len(entries)} pre-defined skills')
    else:
        print(f'[!] No skills directory found')
        print(f'    Create one at ~/.claude/skills/<name>/SKILL.md')
        entries = [{'name': n, 'description': d, 'keywords': k} for n, (d, k) in SKILL_DB.items()]
        print(f'    Using {len(entries)} pre-defined skills')

    skills_json.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')

    # ── Step 3: Build vectors ──
    build_vector_index()

    # ── Step 4: Write hook config ──
    if not args.refresh:
        write_settings()
        print(f'\n[v] Hook installed to: {SETTINGS}')

    # ── Summary ──
    keyword_ok = 'Yes'
    llm_ok = 'Yes (auto-detect your API key)'
    local_ok = 'Yes (BGE bilingual)' if has_st else 'No — pip install sentence-transformers'

    print(f'\n{"─" * 55}')
    print('  Routing layers available:')
    print(f'  1. Keyword matching:      {keyword_ok}')
    print(f'  2. LLM API routing:        {llm_ok}')
    print(f'  3. Local semantic:         {local_ok}')
    print(f'{"─" * 55}')

    n = len(entries) if entries else 18
    if args.refresh:
        print(f'\n✅ Refresh complete — {n} skills registered, vectors rebuilt.')
        print('   No restart needed — changes take effect immediately.')
    else:
        print(f'''
╔══════════════════════════════════════════════════════════════╗
║  ✅  INSTALL COMPLETE                                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Restart Claude Code, then type: --skill-status              ║
║                                                              ║
║  ✅ Response → working!                                      ║
║  ❌ No response → your CC is in --bare mode.                 ║
║     Re-run install.py to auto-fix, or start CC without       ║
║     --bare. Just type "claude" (or whatever you named it).   ║
║                                                              ║
║  启动命令叫什么无所谓 (claude/claude-ds/什么都行)，           ║
║  关键是不要 --bare。模型在 settings.json 里配置。             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝''')
        print(f'  Commands (type in CC dialog):')
        print(f'    --skill-status   View status ({n} skills)')
        print(f'    --skill-list     List all skills')
        print(f'    --skill-debug    Full diagnostic')
        print(f'    --skill-off      Disable auto-loading')
        print(f'    --skill-on       Re-enable auto-loading')


if __name__ == '__main__':
    main()
