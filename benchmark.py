#!/usr/bin/env python3
"""AutoSkillsCC Benchmark — systematic accuracy test with 27 cases."""
import json, sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hooks'))

# Must be set BEFORE importing recommend (HF env vars)
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
os.environ.setdefault('TRANSFORMERS_VERBOSITY', 'error')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Silence noisy import warnings
import warnings, logging
warnings.filterwarnings('ignore')
for m in ('sentence_transformers', 'transformers', 'tokenizers', 'tqdm', 'huggingface_hub'):
    logging.getLogger(m).setLevel(logging.ERROR)

# We need .enabled to exist for scoring functions
from pathlib import Path
enabled_file = Path(__file__).parent / '.enabled'
if not enabled_file.exists():
    enabled_file.touch()

from recommend import get_ensemble_scores, mmr_select, load_index, detect_lang

# ═══ Test Cases ═════════════════════════════════════════════════════════════
# Format: (prompt, expected_skills, category)
# expected_skills is the set of skills we want in top results
# None or empty means "should not match anything strongly"

CASES = [
    # ── Clear single-domain (Chinese) ──
    ("帮我写一个带搜索的表格组件",  ["frontend-design"], "single-cn"),
    ("这个SQL查询太慢了帮我优化",    ["performance-optimization", "database-design"], "single-cn"),
    ("帮我写个Dockerfile部署服务",   ["docker-container"], "single-cn"),
    ("这个函数一直报错帮我看看",     ["debugging"], "single-cn"),
    ("帮我生成一个PPT演示文稿",      ["pptx"], "single-cn"),
    ("帮我写个Python脚本处理数据",   ["python-dev"], "single-cn"),
    ("生成一份Word文档报告",         ["docx"], "single-cn"),
    ("帮我写一个Excel表格",          ["xlsx"], "single-cn"),
    ("这个接口怎么设计",             ["api-design"], "single-cn"),
    ("代码要重构一下",               ["refactoring"], "single-cn"),

    # ── Clear single-domain (English) ──
    ("help me refactor this messy function",     ["refactoring"], "single-en"),
    ("design a REST API for user management",    ["api-design"], "single-en"),
    ("how should I set up git branches",         ["git-workflow"], "single-en"),
    ("analyze this dataset and create charts",   ["data-analysis"], "single-en"),
    ("this code has a security vulnerability",   ["security-audit"], "single-en"),
    ("set up docker compose for my app",          ["docker-container"], "single-en"),
    ("write unit tests for this module",          ["testing"], "single-en"),

    # ── Multi-domain (Chinese) ──
    ("写一个React组件并写单元测试",          ["frontend-design", "testing"], "multi-cn"),
    ("优化这个API接口的查询性能",             ["api-design", "performance-optimization", "database-design"], "multi-cn"),
    ("把这个Python项目用Docker打包部署",      ["python-dev", "docker-container"], "multi-cn"),
    ("分析Excel数据然后生成图表报告",        ["xlsx", "data-analysis"], "multi-cn"),

    # ── Tricky / Ambiguous ──
    ("帮我修一下",                 ["debugging"], "tricky"),
    ("代码太乱了整整",             ["refactoring"], "tricky"),
    ("这个页面好卡",               ["performance-optimization"], "tricky"),
    ("跑得太慢了",                 ["performance-optimization"], "tricky"),
    ("数据怎么导出来",             ["xlsx"], "tricky"),
    ("帮我查个东西",               [], "tricky-no-match"),  # too vague, should skip
    ("有没有安全漏洞",             ["security-audit"], "tricky"),

    # ── Mixed / Edge ──
    ("这个component的渲染有bug",          ["frontend-design", "debugging"], "mixed"),
    ("API endpoint返回500帮我排查",       ["api-design", "debugging"], "mixed"),
    ("docker里的数据库挂了",               ["docker-container", "database-design"], "mixed"),
]

# ═══ Run Benchmark ═══════════════════════════════════════════════════════════

def color(c, s):
    codes = {'R': '\033[31m', 'G': '\033[32m', 'Y': '\033[33m',
             'C': '\033[36m', 'D': '\033[90m', 'X': '\033[0m'}
    return codes.get(c, '') + s + codes['X']

def run():
    print("=" * 70)
    print("  AutoSkillsCC Benchmark — 27 test cases")
    print("=" * 70)

    index = load_index()
    if not index:
        print("[x] skills.json not found")
        return

    print(f"\n[*] {len(index)} skills loaded\n")

    total = len(CASES)
    top1_hits = 0
    top3_hits = 0
    top5_hits = 0
    mmr_hits = 0
    no_match_correct = 0
    no_match_cases = 0

    results = []
    t0 = time.time()

    for i, (prompt, expected, cat) in enumerate(CASES):
        ensemble, has_vecs = get_ensemble_scores(prompt, index)
        if ensemble is None:
            results.append((prompt, expected, cat, [], [], "N/A"))
            continue

        import numpy as np
        n = len(ensemble)
        top_k = min(10, n)
        sorted_idx = np.argsort(ensemble)[::-1][:top_k]
        top_skills = [(index[int(j)], float(ensemble[int(j)])) for j in sorted_idx]

        top1_name = top_skills[0][0]['name']
        top3_names = [e['name'] for e, _ in top_skills[:3]]
        top5_names = [e['name'] for e, _ in top_skills[:5]]

        mmr_idx = mmr_select(ensemble, index, has_vecs, k=3)
        mmr_names = [index[j]['name'] for j in mmr_idx]

        # Scoring
        expected_set = set(expected) if expected else set()
        top1_ok = not expected_set or top1_name in expected_set
        top3_ok = expected_set.issubset(set(top3_names)) or top1_ok
        top5_ok = expected_set.issubset(set(top5_names)) or top3_ok
        mmr_ok = bool(expected_set & set(mmr_names)) if expected_set else True

        if expected_set:
            if top1_ok:
                top1_hits += 1
            if top3_ok:
                top3_hits += 1
            if top5_ok:
                top5_hits += 1
            if mmr_ok:
                mmr_hits += 1
        else:
            no_match_cases += 1
            # "should not match" → best_score should be low
            best_s = top_skills[0][1] if top_skills else 0
            if best_s < 0.15:
                no_match_correct += 1

        # Print per-case
        icon = color('G', '✅') if (not expected_set or top3_ok) else color('R', '❌')
        exp_str = ', '.join(expected) if expected else '(none)'
        lang = detect_lang(prompt)
        print(f'{icon} [{cat}][{lang}] {prompt[:45]:<45} → expect [{exp_str:<35}] '
              f'got top3={top3_names}')

        results.append((prompt, expected, cat, top_skills[:5], mmr_names, lang))

    elapsed = time.time() - t0

    # ── Summary ──
    cases_with_expect = total - no_match_cases
    print()
    print("=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"  Test cases:            {total}")
    print(f"  Time:                  {elapsed:.1f}s ({elapsed/total*1000:.0f}ms avg)")
    print(f"  Vector available:      {'Yes' if has_vecs else 'No'}")
    print()
    print(f"  ── Accuracy (cases with expected skills: {cases_with_expect}) ──")
    print(f"  Top-1 命中:           {top1_hits}/{cases_with_expect}  ({top1_hits/max(cases_with_expect,1)*100:.1f}%)")
    print(f"  Top-3 涵盖:           {top3_hits}/{cases_with_expect}  ({top3_hits/max(cases_with_expect,1)*100:.1f}%)")
    print(f"  Top-5 涵盖:           {top5_hits}/{cases_with_expect}  ({top5_hits/max(cases_with_expect,1)*100:.1f}%)")
    print(f"  MMR Top3 ≥1命中:      {mmr_hits}/{cases_with_expect}  ({mmr_hits/max(cases_with_expect,1)*100:.1f}%)")
    if no_match_cases > 0:
        print(f"  无匹配正确跳过:        {no_match_correct}/{no_match_cases}")
    print(f"  {'─'*40}")

    # ── Failures detail ──
    failures = [(p, e, c, t, m, l) for p, e, c, t, m, l in results
                if e and not set(e).issubset({s['name'] for s, _ in t[:3]})]
    if failures:
        print(f"\n  Failed cases ({len(failures)}):")
        for prompt, expected, cat, top, mmr, lang in failures:
            top_str = ', '.join(f'{e["name"]}({s:.3f})' for e, s in top[:5])
            print(f'  ❌ [{cat}][{lang}] "{prompt[:50]}"')
            print(f'     expected: {expected}')
            print(f'     got top5: {top_str}')
            print(f'     MMR: {mmr}')
    else:
        print(f"\n  🎉 All cases pass Top-3!")
    print()

if __name__ == '__main__':
    run()
