#!/usr/bin/env python3
"""Skill AutoLoader Installer - v2 with semantic vector index support."""
import json, sys, subprocess
from pathlib import Path

SETTINGS    = Path.home() / '.claude' / 'settings.json'
HOOK_SCRIPT = Path(__file__).parent / 'hooks' / 'recommend.py'
BUILD_SCRIPT = Path(__file__).parent / 'build_vector_index.py'

SKILLS_ROOTS = [
    Path('/mnt/skills/public'),
    Path.home() / '.claude' / 'skills',
    Path(__file__).parent / 'skills',
]

# keyword -> (description, keywords)
SKILL_DB = {
    'frontend-design':         ('高质量前端React/Vue组件开发规范，包含TypeScript类型定义、Tailwind CSS样式、响应式布局和无障碍设计', 'frontend react vue angular component html css tailwind web'.split()),
    'docx':                    ('Word文档生成与编辑，.docx文件创建、格式化、模板处理', 'word docx document report doc'.split()),
    'pdf':                     ('PDF文件生成、读取、解析与内容提取', 'pdf generate read'.split()),
    'pptx':                    ('PowerPoint演示文稿创建，幻灯片布局设计与内容填充', 'ppt pptx slides presentation'.split()),
    'xlsx':                    ('Excel电子表格处理，数据导入导出、公式计算与图表', 'excel xlsx spreadsheet csv xls'.split()),
    'python-dev':              ('Python后端开发规范，包含FastAPI/Django/Flask框架、pytest测试与pip依赖管理', 'python pip script pytest django flask fastapi import'.split()),
    'database-design':         ('数据库设计与SQL优化，支持MySQL/PostgreSQL/MongoDB/Redis多种数据库', 'database sql mysql postgresql mongodb redis orm query index'.split()),
    'docker-container':        ('Docker容器化部署，Dockerfile编写、Kubernetes编排与服务管理', 'docker container dockerfile k8s kubernetes deploy'.split()),
    'debugging':               ('代码调试与故障排查，错误堆栈分析、性能瓶颈定位', 'debug bug error crash stack fix'.split()),
    'testing':                 ('自动化测试规范，单元测试、集成测试、E2E测试与覆盖率要求', 'test jest pytest e2e coverage mock'.split()),
    'git-workflow':            ('Git工作流规范，分支管理、提交信息格式、PR审查流程', 'git commit branch merge rebase pr push clone'.split()),
    'api-design':              ('RESTful/GraphQL API设计规范，OpenAPI文档、端点命名与版本管理', 'api rest graphql endpoint swagger openapi restful'.split()),
    'performance-optimization':('性能优化指南，慢查询分析、缓存策略、CDN与资源压缩', 'performance optimize slow latency profile benchmark'.split()),
    'security-audit':          ('安全审计规范，XSS/CSRF防护、JWT认证、SQL注入防御与漏洞扫描', 'security xss csrf ssl auth jwt vulnerability'.split()),
    'refactoring':             ('代码重构最佳实践，Clean Code原则、设计模式应用与代码异味消除', 'refactor clean code quality'.split()),
    'cli-tool':                ('CLI命令行工具开发规范，argparse参数解析、终端交互设计', 'cli terminal bash shell argparse'.split()),
    'data-analysis':           ('数据分析工作流，Pandas/NumPy数据处理、Matplotlib可视化与统计建模', 'pandas numpy csv analysis visualization matplotlib'.split()),
}

def detect_skills_root():
    for p in SKILLS_ROOTS:
        if p.is_dir():
            return p
    return None

def scan_skills(root):
    entries = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        if not (d / 'SKILL.md').exists():
            continue
        name = d.name
        info = SKILL_DB.get(name)
        if info:
            desc, kw = info
        else:
            desc, kw = ('', [name.replace('-', ' ')])
        entries.append({'name': name, 'description': desc, 'keywords': kw})
    return entries

def main():
    print('Skill AutoLoader Install v2 (Semantic Router)')
    print('Python:', sys.executable)
    root = detect_skills_root()
    skills_json = Path(__file__).parent / 'skills.json'
    if root:
        print('Skills dir:', str(root))
        entries = scan_skills(root)
        names = [e['name'] for e in entries]
        print('Found', len(entries), 'skills:', names)
        skills_json.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
        print('skills.json updated')
    else:
        print('No skills dir found, using existing skills.json')

    # Build vector index
    if BUILD_SCRIPT.exists():
        print('Building semantic vector index...')
        try:
            subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=True, timeout=120)
        except Exception as e:
            print('  Warning: vector index build failed:', e)
            print('  (Semantic matching will fall back to keyword matching)')
    else:
        print('Warning: build_vector_index.py not found, skipping vector index')

    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    try:
        s = json.loads(SETTINGS.read_text(encoding='utf-8'))
    except Exception:
        s = {}
    py = sys.executable.replace(chr(92), '/')
    hp = str(HOOK_SCRIPT).replace(chr(92), '/')
    s.setdefault('hooks', {})
    s['hooks']['UserPromptSubmit'] = [{
        'matcher': '',
        'hooks': [{'type': 'command', 'command': py + ' ' + hp, 'timeout': 30}]
    }]
    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Done:', str(SETTINGS))
    print('Restart Claude Code to activate.')

if __name__ == '__main__':
    main()
