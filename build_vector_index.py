#!/usr/bin/env python3
"""技能向量编译器 (离线运行) - 把 skills.json 转化为 Embedding 向量持久化到本地。"""
import json, sys, numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

DIR_PATH = Path(__file__).parent
SKILLS_JSON = DIR_PATH / 'skills.json'
VECTOR_DB   = DIR_PATH / 'skills_vectors.npy'

C = {'R': '\033[31m', 'G': '\033[32m', 'Y': '\033[33m', 'C': '\033[36m', 'X': '\033[0m'}

def main():
    print(C['C'] + '=' * 50 + C['X'])
    print(C['C'] + '  Skill Vector Index Compiler' + C['X'])
    print(C['C'] + '=' * 50 + C['X'])

    if not SKILLS_JSON.exists():
        print(C['R'] + '[x] skills.json not found at: ' + str(SKILLS_JSON) + C['X'])
        sys.exit(1)

    with open(SKILLS_JSON, 'r', encoding='utf-8') as f:
        skills = json.load(f)

    if not skills:
        print(C['Y'] + '[!] skills.json is empty, nothing to compile.' + C['X'])
        sys.exit(0)

    print(C['C'] + '[1/3] Loading embedding model (all-MiniLM-L6-v2)...' + C['X'])
    print(C['Y'] + '      First run will download ~90MB model. Please wait.' + C['X'])
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print(C['G'] + '      Model loaded.' + C['X'])

    print(C['C'] + f'[2/3] Encoding {len(skills)} skills...' + C['X'])

    texts_to_encode = []
    for s in skills:
        name = s.get('name', 'unknown')
        desc = s.get('description', '')
        kws  = ' '.join(s.get('keywords', []))
        rich_text = f'Skill: {name}. Description: {desc}. Keywords: {kws}.'
        texts_to_encode.append(rich_text)
        print(f'      -> {name} ({len(kws.split())} keywords)')

    embeddings = model.encode(texts_to_encode, show_progress_bar=True)
    print(C['G'] + f'      Encoded {len(embeddings)} vectors, dim={embeddings.shape[1]}' + C['X'])

    print(C['C'] + f'[3/3] Saving to {VECTOR_DB.name}...' + C['X'])
    np.save(VECTOR_DB, embeddings)
    print(C['G'] + f'[v] Done! Vector DB saved: {VECTOR_DB}' + C['X'])
    print(C['Y'] + '      Tip: Re-run this script whenever you add/modify skills.' + C['X'])

if __name__ == '__main__':
    main()
