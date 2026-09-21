import os, re, json, sys, argparse
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

def find_workspace_root() -> Path:
    """智能嗅探工作区根目录（优先检测 cwd，再从当前文件向上回溯寻找 raw/ 与 wiki/）"""
    try:
        cwd = Path.cwd().resolve()
        if (cwd / "raw").is_dir() and (cwd / "wiki").is_dir():
            return cwd
    except Exception:
        pass

    cur = Path(__file__).resolve().parent
    for p in [cur, *cur.parents]:
        if (p / "raw").is_dir() and (p / "wiki").is_dir():
            return p

    if cur.name == "scripts":
        if len(cur.parents) >= 3 and cur.parent.parent.name == "skills":
            return cur.parent.parent.parent.parent
        return cur.parent

    return Path.cwd().resolve()


ROOT_DIR = find_workspace_root()
WIKI_DIR = ROOT_DIR / "wiki"
GLOSSARY_FILE = ROOT_DIR / "glossary.md"
SCRATCH_DIR = ROOT_DIR / ".scratch"
RADAR_CACHE_FILE = SCRATCH_DIR / "ghost_radar_cache.json"

SOURCE_TYPES = {"paper", "standard", "guideline", "book", "report", "general", "transcript", "table", "tutorial"}
NON_CONCEPT_EXT = re.compile(r"\.(pdf|png|jpe?g|gif|webp|svg|bmp|mp4|mp3|wav|zip|7z|tar|gz|canvas|csv|xlsx?|docx?|pptx?)$", re.I)

# 多义消歧白名单（严禁粗暴剥离括号的强特异性词，保护法定/学术特异性）
DISAMBIGUATION_PROTECTED = {
    "设计确认", "设计验证", "载体", "敏感度", "转化", "稳健性", "鲁棒性", "极化"
}

stopword_excludes = {
    "index", "log", "glossary", "agents", "readme", "raw_manifest",
    "wikilink", "markdown", "tag", "tags", "frontmatter", "yaml", "dataview", "backlink", "backlinks",
    "显著性", "置信区间", "样本量", "问卷调查", "对照组", "多因素回归", "p值", "标准差",
    "离心机", "移液枪", "室温", "生理盐水", "试管", "ep管", "培养皿", "吸头", "耗材",
    "撒哈拉以南非洲", "成年人", "儿童", "城市", "乡村"
}


def extract_base_key(tname: str) -> tuple[str, bool]:
    """提取中文基底与是否剥离标识，保护多义词与短词"""
    for p in DISAMBIGUATION_PROTECTED:
        if tname.startswith(p):
            return tname, False
    m = re.search(r"^(.+?)\s*[\(（]([A-Za-z0-9\-_/\s\.,+]+)[\)）]$", tname)
    if m:
        base = m.group(1).strip()
        if len(base) >= 2:
            return base, True
    return tname, False


def parse_glossary_terms() -> dict:
    """解析 glossary.md受控词表字典，用于推荐标准命名与同义对齐（不阻断幽灵雷达）"""
    glossary_terms = {}
    if not GLOSSARY_FILE.exists():
        return glossary_terms
    try:
        gtext = GLOSSARY_FILE.read_text(encoding="utf-8")
        for line in gtext.splitlines():
            line_s = line.strip()
            if line_s.startswith("|") and not line_s.startswith("| :") and "英文缩写" not in line_s:
                parts = [p.strip() for p in line_s.split("|")]
                if len(parts) >= 4:
                    en_term = parts[1]
                    zh_term = parts[2]
                    wikilink = parts[3]
                    lm = re.search(r"\[\[(.*?)\]\]", wikilink)
                    canonical_name = lm.group(1).split("|")[0].split("#")[0].strip() if lm else zh_term
                    zh_base = re.sub(r"[\(（].*?[\)）]", "", zh_term).strip().lower()
                    glossary_terms[zh_base] = {
                        "canonical_name": canonical_name,
                        "canonical_link": wikilink,
                        "en": en_term,
                        "zh": zh_term
                    }
    except Exception as e:
        print(f"[Warning] glossary.md 解析失败: {e}", file=sys.stderr)
    return glossary_terms


def scan_knowledge_graph(threshold: int = 2) -> list[dict]:
    # 1. 收集物理已建页集合 (vault_pages: 仅限 wiki/*.md 真实卡片与其别名)
    vault_pages = set()
    vault_pages_lower = set()

    for f in WIKI_DIR.glob("*.md"):
        stem = f.stem
        vault_pages.add(stem)
        vault_pages_lower.add(stem.lower())
        try:
            content = f.read_text(encoding="utf-8")
            m = re.search(r"^---\s*\n([\s\S]*?)\n---", content)
            if m:
                yaml = m.group(1)
                alias_br = re.search(r"^aliases?:\s*\[(.*?)\]", yaml, re.M)
                if alias_br:
                    for p in alias_br.group(1).split(","):
                        clean = p.strip().strip("'\"")
                        if clean:
                            vault_pages.add(clean)
                            vault_pages_lower.add(clean.lower())
                alias_lines = re.search(r"^aliases?:\s*\r?\n((?:\s*-\s*.*(?:\r?\n|$))+)", yaml, re.M)
                if alias_lines:
                    for l in alias_lines.group(1).splitlines():
                        clean = re.sub(r"^\s*-\s*", "", l).strip().strip("'\"")
                        if clean:
                            vault_pages.add(clean)
                            vault_pages_lower.add(clean.lower())
        except Exception:
            pass

    glossary_terms = parse_glossary_terms()

    # 2. 遍历提取原始幽灵链接
    raw_ghosts = {}
    for f in WIKI_DIR.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if "insights" in str(f) and re.search(r"status:\s*draft", content, re.I):
            continue

        is_source = False
        is_concept = False
        evidence_level = "L6"
        m = re.search(r"^---\s*\n([\s\S]*?)\n---", content)
        if m:
            yaml = m.group(1)
            tm = re.search(r"^type:\s*(\w+)", yaml, re.M)
            ptype = tm.group(1).lower() if tm else ""
            em = re.search(r"^evidence_level:\s*(\w+)", yaml, re.M)
            if em:
                evidence_level = em.group(1)
            has_s = "source_file:" in yaml
            if has_s or ptype in SOURCE_TYPES:
                is_source = True
            elif ptype in {"topic", "concept", "entity", "tool"}:
                is_concept = True

        is_high_auth = evidence_level in {"L1_standard", "L2_causal_synthesis", "L3_empirical_peer_reviewed"}

        seen = set()
        for raw in re.findall(r"\[\[(.*?)\]\]", content):
            target = raw.split("|")[0].split("#")[0].strip()
            if not target or target.startswith("raw/") or NON_CONCEPT_EXT.search(target):
                continue
            tname = Path(target.replace(".md", "")).name.strip()
            if not tname: continue
            tlower = tname.lower()

            if tname not in vault_pages and tlower not in vault_pages_lower and tlower not in stopword_excludes:
                if tlower not in seen:
                    seen.add(tlower)
                    if tname not in raw_ghosts:
                        raw_ghosts[tname] = {"sources": set(), "contexts": set(), "high_auth_sources": 0}
                    if is_source:
                        raw_ghosts[tname]["sources"].add(f.stem)
                        if is_high_auth:
                            raw_ghosts[tname]["high_auth_sources"] += 1
                    elif is_concept:
                        raw_ghosts[tname]["contexts"].add(f.stem)

    # 3. 中文基底安全聚类
    clusters = {}
    for tname, data in raw_ghosts.items():
        base, stripped = extract_base_key(tname)
        base_lower = base.lower()

        if base_lower not in clusters:
            clusters[base_lower] = {
                "base_name": base,
                "canonical_name": tname,
                "variants": set(),
                "sources": set(),
                "contexts": set(),
                "high_auth_sources": 0,
                "in_glossary": False
            }

        c = clusters[base_lower]
        c["variants"].add(tname)
        c["sources"].update(data["sources"])
        c["contexts"].update(data["contexts"])
        c["high_auth_sources"] += data["high_auth_sources"]

        if base_lower in glossary_terms:
            c["canonical_name"] = glossary_terms[base_lower]["canonical_name"]
            c["in_glossary"] = True
        else:
            if len(tname) > len(c["canonical_name"]):
                c["canonical_name"] = tname

    # 4. 复合权重与准入门禁判定（零实证一票否决）
    candidates = []
    for base_lower, c in clusters.items():
        S = len(c["sources"])
        C = len(c["contexts"])

        if S == 0:
            continue

        passed = False
        if S >= threshold:
            passed = True
        elif S >= 1 and C >= 2 and c["high_auth_sources"] >= 1:
            passed = True

        score = round(S * 1.0 + min(C * 0.4, 1.2), 2)

        if passed:
            candidates.append({
                "name": c["canonical_name"],
                "base": c["base_name"],
                "score": score,
                "sources_count": S,
                "contexts_count": C,
                "sources": sorted(list(c["sources"])),
                "contexts": sorted(list(c["contexts"])),
                "variants": sorted(list(c["variants"])),
                "in_glossary": c["in_glossary"]
            })

    candidates.sort(key=lambda x: (x["score"], x["sources_count"]), reverse=True)
    return candidates


def main():
    parser = argparse.ArgumentParser(description="扫描知识库待孵化概念与实体 (V5.2 实体基底归一与物化视图版)")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON 数据")
    parser.add_argument("--threshold", type=int, default=2, help="独立文献出处频次阈值 (默认 >= 2)")
    parser.add_argument("--no-cache", action="store_true", help="不更新物化视图缓存文件")
    args = parser.parse_args()

    result = scan_knowledge_graph(threshold=args.threshold)

    # 写入物化视图缓存，供 index.md 极速读取，杜绝 Obsidian 主线程卡顿
    if not args.no_cache:
        try:
            SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
            temp_cache = RADAR_CACHE_FILE.with_suffix(".tmp")
            temp_cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_cache.replace(RADAR_CACHE_FILE)
        except Exception as e:
            print(f"[Warning] 物化视图写入失败: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n=============================================================")
        print(f"⏳ 待孵化概念与实体雷达扫描结果 (复合认知门禁 >= {args.threshold})")
        print("=============================================================")
        if not result:
            print("✨ 当前知识图谱致密自洽，暂无达到认知门禁阈值的待孵化词条！")
        else:
            print(f"共发现 {len(result)} 个达到认知门禁阈值的候选概念：\n")
            for idx, item in enumerate(result, 1):
                gloss_tag = " [已在受控词表]" if item["in_glossary"] else ""
                print(f"{idx}. [[{item['name']}]] (综合得分: {item['score']} | 文献出处: {item['sources_count']} | 上下文主题: {item['contexts_count']}){gloss_tag}")
                if len(item["variants"]) > 1:
                    print(f"   已聚合变体: {', '.join(item['variants'])}")
                if item["contexts"]:
                    print(f"   关联已有主题 (Contexts): {', '.join(item['contexts'])}")
                print(f"   出处文献 (Sources): {', '.join(item['sources'])}")
            print("\n💡 提示: 已更新物化视图缓存 (.scratch/ghost_radar_cache.json)，驾驶舱将秒级渲染。")
        print("=============================================================\n")


if __name__ == "__main__":
    main()
