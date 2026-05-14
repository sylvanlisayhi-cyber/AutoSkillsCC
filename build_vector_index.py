#!/usr/bin/env python3
"""AutoSkillsCC Bilingual vector compiler — English + Chinese embeddings for skill routing."""
import json, sys
from pathlib import Path

DIR_PATH    = Path(__file__).parent
SKILLS_JSON = DIR_PATH / 'skills.json'
VECTOR_DB_EN = DIR_PATH / 'skills_vectors_en.npy'
VECTOR_DB_ZH = DIR_PATH / 'skills_vectors_zh.npy'

C = {'R': '\033[31m', 'G': '\033[32m', 'Y': '\033[33m', 'C': '\033[36m', 'X': '\033[0m'}

def check_deps():
    missing = []
    try:
        import numpy  # noqa
    except ImportError:
        missing.append('numpy')
    try:
        import sentence_transformers  # noqa
    except ImportError:
        missing.append('sentence-transformers')
    if missing:
        print(C['R'] + f'[x] Missing: {", ".join(missing)}' + C['X'])
        print(C['Y'] + f'    pip install {" ".join(missing)}' + C['X'])
        print(C['Y'] + f'    In China: pip install {" ".join(missing)} -i https://mirrors.aliyun.com/pypi/simple/' + C['X'])
        sys.exit(1)

def main():
    check_deps()

    import numpy as np
    from sentence_transformers import SentenceTransformer

    print(C['C'] + '=' * 50 + C['X'])
    print(C['C'] + '  Bilingual Vector Index Compiler v3' + C['X'])
    print(C['C'] + '=' * 50 + C['X'])

    if not SKILLS_JSON.exists():
        print(C['R'] + f'[x] skills.json not found: {SKILLS_JSON}' + C['X'])
        print(C['Y'] + '    Run install.py first' + C['X'])
        sys.exit(1)

    with open(SKILLS_JSON, 'r', encoding='utf-8') as f:
        skills = json.load(f)

    if not skills:
        print(C['Y'] + '[!] skills.json empty, nothing to compile' + C['X'])
        sys.exit(0)

    texts = []
    print(f'{len(skills)} skills:')
    for s in skills:
        name = s.get('name', 'unknown')
        desc = s.get('description', '')
        kws  = ' '.join(s.get('keywords', []))
        texts.append(f'Skill: {name}. Description: {desc}. Keywords: {kws}.')
        print(f'  -> {name} ({len(kws.split())} keywords)')

    # English vectors
    print(C['C'] + '\n[1/4] Loading EN model (BAAI/bge-small-en-v1.5 ~33MB)...' + C['X'])
    print(C['Y'] + '      First run downloads from HuggingFace.' + C['X'])
    model_en = SentenceTransformer('BAAI/bge-small-en-v1.5')
    print(C['G'] + '      EN model loaded' + C['X'])

    print(C['C'] + f'[2/4] Encoding {len(skills)} skills (EN)...' + C['X'])
    emb_en = model_en.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    np.save(VECTOR_DB_EN, emb_en)
    size_kb = VECTOR_DB_EN.stat().st_size // 1024
    print(C['G'] + f'      Saved: {VECTOR_DB_EN.name}  shape={emb_en.shape}  {size_kb}KB' + C['X'])

    # Chinese vectors
    print(C['C'] + '\n[3/4] Loading ZH model (BAAI/bge-small-zh-v1.5 ~33MB)...' + C['X'])
    model_zh = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    print(C['G'] + '      ZH model loaded' + C['X'])

    print(C['C'] + f'[4/4] Encoding {len(skills)} skills (ZH)...' + C['X'])
    emb_zh = model_zh.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    np.save(VECTOR_DB_ZH, emb_zh)
    size_kb = VECTOR_DB_ZH.stat().st_size // 1024
    print(C['G'] + f'      Saved: {VECTOR_DB_ZH.name}  shape={emb_zh.shape}  {size_kb}KB' + C['X'])

    # Precompute skill-skill similarity matrices for fast MMR
    print(C['C'] + '\n[5/5] Precomputing similarity matrices...' + C['X'])
    sim_en = emb_en @ emb_en.T
    sim_zh = emb_zh @ emb_zh.T
    cache_dir = DIR_PATH / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / 'skill_sim_en.npy', sim_en)
    np.save(cache_dir / 'skill_sim_zh.npy', sim_zh)
    print(C['G'] + f'      Saved: skill_sim_en.npy  shape={sim_en.shape}' + C['X'])
    print(C['G'] + f'      Saved: skill_sim_zh.npy  shape={sim_zh.shape}' + C['X'])

    # Clean legacy single-index file
    legacy = DIR_PATH / 'skills_vectors.npy'
    if legacy.exists():
        legacy.unlink()
        print(C['Y'] + '      Removed legacy: skills_vectors.npy' + C['X'])

    print(C['G'] + '\n[v] Done! Bilingual vector index + similarity matrices ready.' + C['X'])
    print(C['Y'] + '    Re-run this script whenever you add/modify skills.' + C['X'])


if __name__ == '__main__':
    main()
