#!/usr/bin/env python3
"""Perceptual-hash hero dedup for sanctum-docs. Computes a 64-bit dHash for the
hero image of every .mdx page and clusters images whose Hamming distance is
small (visually near-identical even when the bytes differ). Prints clusters so
we can regenerate the duplicates to unique art.

Usage: phash_dupes.py <repo-root> [threshold]
  threshold = max Hamming distance to call two images 'the same' (default 10)
"""
import glob, os, re, sys
from PIL import Image

def main():
    REPO = sys.argv[1]
    THRESH = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    def dhash(path, size=8):
        img = Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS)
        bits = 0
        idx = 0
        px = img.load()
        for y in range(size):
            for x in range(size):
                bits |= (1 if px[x, y] < px[x + 1, y] else 0) << idx
                idx += 1
        return bits
    
    def ahash(path, size=8):
        img = Image.open(path).convert("L").resize((size, size), Image.LANCZOS)
        px = list(img.getdata())
        avg = sum(px) / len(px)
        bits = 0
        for i, p in enumerate(px):
            bits |= (1 if p >= avg else 0) << i
        return bits
    
    def ham(a, b):
        return bin(a ^ b).count("1")
    
    entries = []  # (page, imgpath, dhash, ahash)
    for f in sorted(glob.glob(os.path.join(REPO, "src/content/docs/**/*.mdx"), recursive=True)):
        with open(f) as fh:
            head = fh.read(4000)
        m = re.search(r'!\[[^\]]*\]\((\.[^)]+\.(?:png|jpg|jpeg|webp))\)', head)
        if not m:
            continue
        imgpath = os.path.normpath(os.path.join(os.path.dirname(f), m.group(1)))
        if not os.path.exists(imgpath):
            continue
        page = f.split("src/content/docs/")[-1]
        try:
            entries.append((page, imgpath, dhash(imgpath), ahash(imgpath)))
        except Exception as e:
            print(f"  skip {page}: {e}")
    
    # cluster by combined similarity (both dhash AND ahash close)
    n = len(entries)
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def union(i, j):
        parent[find(i)] = find(j)
    
    for i in range(n):
        for j in range(i + 1, n):
            dd = ham(entries[i][2], entries[j][2])
            da = ham(entries[i][3], entries[j][3])
            if dd <= THRESH and da <= THRESH:
                union(i, j)
    
    from collections import defaultdict
    clusters = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)
    
    print(f"scanned {n} hero images; threshold Hamming<= {THRESH}")
    dup_clusters = [v for v in clusters.values() if len(v) > 1]
    print(f"VISUAL-DUPLICATE clusters: {len(dup_clusters)}\n")
    for cl in sorted(dup_clusters, key=lambda c: -len(c)):
        print(f"  cluster of {len(cl)}:")
        for i in cl:
            # min pairwise distance to the cluster anchor
            print(f"      {entries[i][0]}   ({os.path.basename(entries[i][1])})")
        print()


if __name__ == "__main__":
    main()
