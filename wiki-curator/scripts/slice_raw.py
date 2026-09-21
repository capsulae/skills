#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/slice_raw.py - 利刃的第二大脑·超长文档只读虚拟切片与拓扑探针
Version: 1.0 (无头只读分治版)

核心设计与第一性原理原则：
1. 原始资料绝对只读：严格以只读模式透视 raw/ 文档，杜绝任何磁盘写入与原件破坏。
2. 毫秒级目录拓扑投影 (TOC Tree)：利用 PyMuPDF (fitz) 毫秒级解析长文档层级大纲。
3. 全局认知锚点广播 (Global Context Anchor)：抽离全书符号定义、前言与核心假说，供子章节精读时注入。
4. 物理页码可溯源投影 (Traceable Slices)：切片输出内嵌真实物理页码标记 (<!-- Page X -->)，保障维基证据溯源。
5. 自适应双轨门禁 (Adaptive Dual-Track)：自动判定文档是否触达超长门槛 (>= 50 页或 >= 40k Tokens)。
"""

import sys
import json
import argparse
from pathlib import Path

# 强制终端输出为 UTF-8，消除 Windows 控制台 GBK 乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import fitz  # PyMuPDF
except ImportError:
    print("[Error] 缺少 fitz (PyMuPDF) 依赖，请先运行: pip install pymupdf", file=sys.stderr)
    sys.exit(1)

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
RAW_DIR = ROOT_DIR / "raw"

# 第一性原理 Token 动态准入常量 (Gemini 原生多模态 560 Tokens/页)
PDF_PAGE_TOKENS = 560
AGENTS_MD_TOKENS = 10000
SYSTEM_PROMPT_TOKENS = 4000
BASE_OVERHEAD_TOKENS = AGENTS_MD_TOKENS + SYSTEM_PROMPT_TOKENS  # 基础前置总开销基线: 14,000 Tokens
MASSIVE_TOTAL_TOKEN_THRESHOLD = 33600  # 端到端总会话超过 33,600 Tokens 触发超长切片 (对应 >= 35页)
MASSIVE_PAGE_THRESHOLD = (MASSIVE_TOTAL_TOKEN_THRESHOLD - BASE_OVERHEAD_TOKENS) // PDF_PAGE_TOKENS  # 35 页 (>=35页触发)


def resolve_file(file_path_str: str) -> Path:
    """安全解析路径，严格校验必须位于 raw/ 内且真实存在"""
    p = Path(file_path_str)
    if not p.is_absolute():
        p = ROOT_DIR / p
    
    # 物理存在校验
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path_str}")
    
    # 路径安全约束：必须在项目目录内
    try:
        p.resolve().relative_to(ROOT_DIR.resolve())
    except ValueError:
        raise PermissionError(f"禁止访问项目根目录外的文件: {file_path_str}")
    
    return p


def inspect_document(doc_path: Path) -> dict:
    """毫秒级解析文档拓扑、目录大纲与基于 Token 动态准入的切片划分建议"""
    doc = fitz.open(doc_path)
    total_pages = len(doc)
    file_size = doc_path.stat().st_size
    
    raw_toc = doc.get_toc() # [[lvl, title, page, ...], ...]
    
    # 基于第一性原理计算端到端总消耗 Tokens
    multimodal_doc_tokens = total_pages * PDF_PAGE_TOKENS
    total_est_context_tokens = multimodal_doc_tokens + BASE_OVERHEAD_TOKENS
    is_massive = total_est_context_tokens >= MASSIVE_TOTAL_TOKEN_THRESHOLD
    
    # 快速抽样前 3 页检测是否为纯扫描图像
    sample_pages = min(3, total_pages)
    has_text = any(bool(doc[p].get_text("text").strip()) for p in range(sample_pages))
    
    toc_tree = []
    suggested_slices = []
    
    if raw_toc:
        for i, item in enumerate(raw_toc):
            lvl, title, start_p = item[0], item[1].strip(), item[2]
            # 计算该节点的结束页
            end_p = total_pages
            for next_item in raw_toc[i+1:]:
                if next_item[0] <= lvl: # 同级或更高级别出现，则当前节结束
                    end_p = max(start_p, next_item[2] - 1)
                    break
            
            toc_tree.append({
                "level": lvl,
                "title": title,
                "start_page": start_p,
                "end_page": end_p
            })
            
            # 对一级标题（Level 1）推荐切片方案
            if lvl == 1:
                suggested_slices.append({
                    "title": title,
                    "pages": f"{start_p}-{end_p}",
                    "page_count": end_p - start_p + 1
                })
    else:
        # 无内置书签时，按每 30 页自动生成平铺切片规划
        step = 30
        for s in range(1, total_pages + 1, step):
            e = min(s + step - 1, total_pages)
            suggested_slices.append({
                "title": f"Part_{s:03d}_{e:03d}",
                "pages": f"{s}-{e}",
                "page_count": e - s + 1
            })

    # 快速统计全文文本量与 Token 预估
    total_chars = 0
    total_words = 0
    if has_text:
        for p in range(total_pages):
            page_text = doc[p].get_text("text")
            total_chars += len(page_text)
            total_words += len(page_text.split())
    # 学术文献中英文混合 Token 启发式预估：
    # 英文学术词汇/化学式按 1 word ≈ 1.33 tokens；或按纯字符 4 chars ≈ 1 token 互为边界区间
    est_tokens_word_based = int(total_words * 1.33)
    est_tokens_char_based = int(total_chars / 4) if total_chars else 0
    est_tokens_range = f"{est_tokens_word_based:,} ~ {est_tokens_char_based:,}" if est_tokens_char_based > est_tokens_word_based else f"{est_tokens_word_based:,}"

    # 尝试提取元数据
    meta = doc.metadata or {}
    rel_path = str(doc_path.relative_to(ROOT_DIR)).replace("\\", "/")
    
    result = {
        "file": rel_path,
        "total_pages": total_pages,
        "size_bytes": file_size,
        "is_massive": is_massive,
        "has_embedded_text": has_text,
        "total_chars": total_chars,
        "total_words": total_words,
        "estimated_tokens_range": est_tokens_range,
        "multimodal_doc_tokens": multimodal_doc_tokens,
        "base_overhead_tokens": BASE_OVERHEAD_TOKENS,
        "total_estimated_context_tokens": total_est_context_tokens,
        "title_metadata": meta.get("title") or doc_path.stem,
        "author_metadata": meta.get("author") or "",
        "toc_count": len(toc_tree),
        "toc": toc_tree[:50],  # 截断展示前 50 条防膨胀
        "suggested_slices": suggested_slices
    }
    doc.close()
    return result


def extract_anchor(doc_path: Path, max_pages: int = 5) -> str:
    """提取全局认知锚点（前言、符号定义表、前若干页核心框架）"""
    doc = fitz.open(doc_path)
    total_pages = len(doc)
    pages_to_extract = min(max_pages, total_pages)
    
    anchor_lines = [
        f"<!-- GLOBAL COGNITIVE ANCHOR: {doc_path.name} (Pages 1-{pages_to_extract}) -->",
        f"# 全局认知锚点 (Global Cognitive Anchor) - {doc_path.stem}\n"
    ]
    
    for p_num in range(pages_to_extract):
        page = doc[p_num]
        text = page.get_text("text").strip()
        if text:
            anchor_lines.append(f"\n<!-- Page {p_num + 1} -->\n{text}")
            
    doc.close()
    return "\n".join(anchor_lines)


def radar_scan(doc_path: Path, mode: str = "normative") -> dict:
    """Pass 1: 全景命题雷达扫描，客观检测全书量化指标、规范裁决词与表格分布，生成命题热力图
    
    支持三态认识论自适应权重 (Adaptive Tri-Modal Weighting):
    - normative (模式 A: 法定标准/临床指南): 重点检测推荐、禁忌、截断值、统计量与表格
    - heuristic (模式 B: 实务架构/经管方法论): 重点检测模式、权衡、指标、架构坏味道、延迟/吞吐与代码块
    - descriptive (模式 C: 客观自然机理/反应方程): 重点检测化学反应式、动力学方程、催化机理、常数与定量单位
    """
    doc = fitz.open(doc_path)
    total_pages = len(doc)
    
    import re
    # 模式 A: 法定规程与临床标准模式
    if mode == "heuristic":
        QUANT_RE = re.compile(r"\b(\d+(\.\d+)?\s*(ms|s|sec|rps|qps|tps|kb|mb|gb|tb|%|usd|\$|元|次/秒|毫秒)\b|p9[0-9]|sla|slo|mtbf|mttr)", re.IGNORECASE)
        DOMAIN_RE = re.compile(r"\b(pattern|anti-pattern|trade-off|heuristic|guideline|refactor|smell|coupling|cohesion|invariant|principle)\b|架构|设计模式|权衡|坏味道|高内聚|低耦合|最佳实践|原则", re.IGNORECASE)
        quant_weight, domain_weight = 2, 4
    elif mode == "descriptive":
        QUANT_RE = re.compile(r"\b(\d+(\.\d+)?\s*(mol/L|mmol/L|μmol/L|nmol/L|mM|μM|nM|°C|K|nm|Da|kDa|pH|g/mol)\b|ka|kd|km|vmax|t1/2|半衰期|常数)", re.IGNORECASE)
        DOMAIN_RE = re.compile(r"\b(equation|formula|kinetics|catalysis|reaction|synthesis|mechanism|theorem|lemma|corollary|proof)\b|方程|反应式|动力学|催化|机制|合成|机理|定理|引理|推论", re.IGNORECASE)
        quant_weight, domain_weight = 3, 3
    else:  # 默认 normative
        QUANT_RE = re.compile(r"\b(\d+(\.\d+)?\s*(mg|g|kg|μg|mcg|mmol/L|mg/dL|mmHg|%|weeks?|ml|IU)\b|OR\s*[:=]|RR\s*[:=]|95%\s*CI|p\s*[<=])", re.IGNORECASE)
        DOMAIN_RE = re.compile(r"\b(recommend(ed|ation)?|not recommended|context-specific|contraindicated|mandatory|standard|cut-off|threshold|must)\b|推荐|不推荐|禁忌|标准|截断值|阈值", re.IGNORECASE)
        quant_weight, domain_weight = 2, 3

    # 纯引用与致谢排除模式
    BIBLIO_RE = re.compile(r"\b(references|bibliography|contributors|acknowledgements|declarations? of interest)\b|参考文献|致谢|利益声明", re.IGNORECASE)
    
    page_stats = []
    high_density_pages = []
    zero_density_pages = []
    table_pages = []
    total_chars = 0
    
    for p_num in range(total_pages):
        page = doc[p_num]
        txt = page.get_text("text", sort=True).strip()
        p_real = p_num + 1
        total_chars += len(txt)
        
        # 表格探测
        try:
            tabs = page.find_tables()
            tab_count = len(tabs.tables) if tabs else 0
        except Exception:
            tab_count = 0
            
        if tab_count > 0:
            table_pages.append(p_real)
            
        quant_matches = len(QUANT_RE.findall(txt))
        domain_matches = len(DOMAIN_RE.findall(txt))
        is_biblio = bool(BIBLIO_RE.search(txt[:300])) # 头部出现参考文献或致谢
        
        score = quant_matches * quant_weight + domain_matches * domain_weight + tab_count * 5
        
        if is_biblio and score < 5:
            zero_density_pages.append(p_real)
        elif score >= 5 or tab_count > 0:
            high_density_pages.append({
                "page": p_real,
                "score": score,
                "tables": tab_count,
                "quant_hits": quant_matches,
                "domain_hits": domain_matches,
                "preview": txt[:120].replace("\n", " ")
            })
            
        page_stats.append({
            "page": p_real,
            "text_len": len(txt),
            "score": score,
            "has_table": tab_count > 0
        })
        
    doc.close()
    
    avg_chars_per_page = (total_chars / total_pages) if total_pages > 0 else 0
    is_scanned_pdf = (avg_chars_per_page < 30) and (total_pages > 0)
    
    return {
        "file": str(doc_path.name),
        "total_pages": total_pages,
        "mode": mode,
        "is_scanned_image_pdf": is_scanned_pdf,
        "avg_chars_per_page": round(avg_chars_per_page, 1),
        "high_density_pages_count": len(high_density_pages),
        "table_pages_count": len(table_pages),
        "table_pages": table_pages,
        "all_high_density_pages": [h["page"] for h in high_density_pages],
        "all_high_density_items": high_density_pages,
        "high_density_summary": high_density_pages[:20],
        "confirmed_low_entropy_pages_count": len(zero_density_pages)
    }


def table_to_markdown(tab_extract) -> str:
    """将 fitz 提取的二维表格矩阵序列化为标准 Markdown 表格"""
    if not tab_extract or len(tab_extract) < 2:
        return ""
    
    # 清洗单元格换行与空值
    cleaned = []
    max_cols = max(len(r) for r in tab_extract)
    for row in tab_extract:
        r_clean = []
        for cell in row:
            if cell is None:
                r_clean.append("")
            else:
                c_str = str(cell).replace("\n", " ").replace("|", "\\|").strip()
                r_clean.append(c_str)
        # 补齐列数
        while len(r_clean) < max_cols:
            r_clean.append("")
        cleaned.append(r_clean)
        
    headers = cleaned[0]
    sep = ["---"] * max_cols
    rows = cleaned[1:]
    
    md_lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |"
    ]
    for r in rows:
        md_lines.append("| " + " | ".join(r) + " |")
        
    return "\n".join(md_lines)


def extract_slice(doc_path: Path, page_range_str: str, overlap: int = 0) -> str:
    """高保真提取指定页码区间的纯文本与结构化表格，支持版面重排与滑动重叠防截断"""
    doc = fitz.open(doc_path)
    total_pages = len(doc)
    
    # 解析页码范围
    if "-" in page_range_str:
        parts = page_range_str.split("-")
        start_p = int(parts[0].strip())
        end_p = int(parts[1].strip())
    else:
        start_p = int(page_range_str.strip())
        end_p = start_p
        
    # 应用滑动重叠窗口 (Sliding Overlap Window)
    if overlap > 0:
        actual_start_p = max(1, start_p - overlap)
        actual_end_p = min(total_pages, end_p + overlap)
    else:
        actual_start_p = max(1, start_p)
        actual_end_p = min(total_pages, end_p)
        
    actual_start_p = min(actual_start_p, total_pages)
    actual_end_p = max(actual_start_p, min(actual_end_p, total_pages))
    
    slice_lines = [
        f"<!-- VIRTUAL SLICE: {doc_path.name} | Pages {start_p}-{end_p} (With Overlap Padding: {actual_start_p}-{actual_end_p}) / Total {total_pages} -->\n"
    ]
    
    extracted_any_text = False
    for p_num in range(actual_start_p - 1, actual_end_p):
        p_real = p_num + 1
        page = doc[p_num]
        
        # 1. 尝试版面感知提取二维表格
        table_md_blocks = []
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                for t in tabs.tables:
                    t_mat = t.extract()
                    t_md = table_to_markdown(t_mat)
                    if t_md:
                        table_md_blocks.append(t_md)
        except Exception:
            pass
            
        # 2. 获取按阅读顺序排版的文本流 (sort=True 消除双栏交错)
        text = page.get_text("text", sort=True).strip()
        
        if text or table_md_blocks:
            extracted_any_text = True
            slice_lines.append(f"\n<!-- Page {p_real} -->")
            if table_md_blocks:
                slice_lines.append(f"> [!NOTE] 检测到物理页面的二维结构化表格 (Preserved Markdown Table):")
                slice_lines.extend(table_md_blocks)
                slice_lines.append("\n**正文流 (Text Flow):**")
            if text:
                slice_lines.append(text)
        else:
            slice_lines.append(f"\n<!-- Page {p_real} (无内嵌文本层，可能为纯扫描图像) -->")
            
    if not extracted_any_text:
        slice_lines.append("\n> [!WARNING]\n> 本切片区间未检测到内嵌文本层，该文档可能为纯图片扫描件 (Scanned Image PDF)。")
        
    doc.close()
    return "\n".join(slice_lines)


def plan_subagents(doc_path: Path, mode: str = "normative", max_cluster_pages: int = 15) -> dict:
    """根据全景雷达热力图聚类高熵区间，生成 Subagent 并行派发任务契约
    
    工程加固特性 (Hardened Invariants):
    1. 零截断保证：彻底消除 [:30] 截断漏洞，全量消费 all_high_density_pages，杜绝静默知识丢弃。
    2. 上下文注意力上限防范 (Anti-Monster-Cluster)：严格限制单切片最长物理页跨度 <= max_cluster_pages (默认 15 页)。
    3. 目录边界感知 (TOC Boundary Snapping)：若文档含 Level 1 大纲，优先在章节点截断聚类，严禁跨章混杂。
    4. 扫描件硬熔断：对无文本层扫描件直接返回 FAILED 预警，杜绝空转。
    5. 篇内历史范式免疫接种 (Historical Inoculation)：契约显式注入前言历史淘汰理论（如 FANC 2002）防混淆警示。
    """
    radar = radar_scan(doc_path, mode=mode)
    if radar.get("is_scanned_image_pdf"):
        return {
            "file": str(doc_path.name),
            "status": "FAILED",
            "error": f"纯扫描图片 PDF 检测警告：全书平均每页内嵌文本仅 {radar.get('avg_chars_per_page', 0)} 字符。必须先经 OCR 识别后再执行双轨摄取。",
            "total_subagents_needed": 0,
            "tasks": []
        }
        
    high_pages = sorted(radar.get("all_high_density_pages") or [h["page"] for h in radar.get("high_density_summary", [])])
    
    # 提取目录一级大纲章节起始页
    doc = fitz.open(doc_path)
    chapter_starts = set()
    try:
        toc = doc.get_toc()
        if toc:
            for item in toc:
                if item[0] == 1 and item[2] > 0:
                    chapter_starts.add(item[2])
    except Exception:
        pass
    doc.close()
    
    clusters = []
    if high_pages:
        cur_cluster = [high_pages[0]]
        for p in high_pages[1:]:
            gap = p - cur_cluster[-1]
            span = p - cur_cluster[0] + 1
            crosses_chapter = any(cur_cluster[-1] < cs <= p for cs in chapter_starts)
            
            # 距离 <= 3 且 跨度 <= max_cluster_pages 且 未跨越一级大纲章节边界
            if gap <= 3 and span <= max_cluster_pages and not crosses_chapter:
                cur_cluster.append(p)
            else:
                clusters.append(cur_cluster)
                cur_cluster = [p]
        if cur_cluster:
            clusters.append(cur_cluster)
            
    tasks = []
    for idx, cl in enumerate(clusters, 1):
        start_p, end_p = cl[0], cl[-1]
        tasks.append({
            "task_id": f"subagent_slice_{idx}",
            "pages": f"{start_p}-{end_p}",
            "page_count": end_p - start_p + 1,
            "overlap": 2,
            "role": f"切片{idx}专业提取员 (Pages {start_p}-{end_p})",
            "target_draft": f".scratch/shadow_drafts/part_{idx}_{start_p}_{end_p}.md",
            "contract": {
                "preserve_tables": True,
                "preserve_exact_numbers": True,
                "preserve_footnotes": True,
                "max_tokens_output": 1200,
                "global_anchor_mandate": "必须严格继承前言全局锚点中确立的宏观范式跃迁与核心实体词汇。",
                "historical_inoculation": "篇内历史防范警示：若本切片属于早期背景综述，涉及的历史废弃理论（如 2002 年 FANC 4 次产检旧模型）必须严格打上 historical 标签，绝对严禁作为现行标准提取！",
                "pass_by_reference": "微观参数在 Master Hub 中完整记录并建立物理页码锚点（[[#Page X]]），供下游知识主题按需引用，杜绝全库概念卡片肥胖症。"
            }
        })
        
    return {
        "file": str(doc_path.name),
        "status": "SUCCESS",
        "total_high_density_pages": len(high_pages),
        "total_subagents_needed": len(tasks),
        "tasks": tasks
    }


def audit_wiki(wiki_path: Path, profile: str = "auto") -> dict:
    """零丢失覆盖度自动核验探针：检查 Wiki 页面中的推荐编号连续性、表格与生化参数
    
    防御对抗特性 (Adversarial Defenses):
    1. 注释清洗 (Anti-Goodhart Gaming): 提取前强制剔除所有 <!-- ... --> HTML 隐藏注释，杜绝挂羊头作弊。
    2. 全学科通用规范探针 (Multi-Domain Generalization): 兼容临床指南编号 ([A-E].X.Y)、IETF RFC、软件标准条目与数学定理。
    3. 穿透物理页码核验 (Page-Anchor Density): 验证是否携带 [[...#Page X]] 物理页码溯源锚点。
    4. 结构化 Markdown 表格保真度核验。
    """
    target_p = wiki_path if wiki_path.is_absolute() else (ROOT_DIR / wiki_path)
    if not target_p.exists():
        raise FileNotFoundError(f"Wiki 文件不存在: {target_p}")
        
    with open(target_p, "r", encoding="utf-8") as f:
        raw_content = f.read()
        
    import re
    # 1. 关键对抗防御：剔除所有 HTML 注释与 UTF-8 BOM，防止隐藏 payload 骗取审计高分 (Goodhart's Law Bypass)
    content = re.sub(r"<!--.*?-->", "", raw_content.lstrip("\ufeff"), flags=re.DOTALL)
    
    # 统计 Markdown 表格 (包含表头分隔行 :--- 判定)
    TABLE_RE = re.compile(r"\|(?:\s*:?-+:?\s*\|)+")
    tables_found = len(TABLE_RE.findall(content))
    
    # 统计微观量化指标与单位
    QUANT_RE = re.compile(r"\b\d+(\.\d+)?\s*(mg|g|kg|μg|mcg|mmol/L|mg/dL|mmHg|%|weeks?|days?|IU|ms|rps|qps|KB|MB|GB|mol/L|mM)\b", re.I)
    quant_hits = len(QUANT_RE.findall(content))
    
    # 统计穿透溯源物理页码锚点 (如 [[WHO_...#... (pp. 13-14)]] 或 Page 42)
    PAGE_ANCHOR_RE = re.compile(r"\[\[.*?#(?:Page\s*\d+|第\w+章|pp?\.?\s*\d+(?:[-–]\d+)?).*?\]\]")
    page_anchors = len(PAGE_ANCHOR_RE.findall(content))
    
    # 判断是否适配 WHO ANC 专属临床基准
    is_who_anc = (profile == "who_anc") or (profile == "auto" and ("ANC" in target_p.name or "Antenatal" in target_p.name or "孕产妇" in target_p.name))
    
    score = 0.0
    rec_matches = []
    hard_points_detail = {}
    
    if is_who_anc:
        # WHO ANC 专属高精度审计
        REC_ID_RE = re.compile(r"\b([A-E]\.\d+(\.\d+)?)\b")
        rec_matches = sorted(list(set(m.group(1) for m in REC_ID_RE.finditer(content))))
        
        has_iron_conv = ("七水硫酸亚铁" in content or "ferrous sulfate" in content) and "60" in content
        has_gdm_cutoffs = ("5.1" in content and "10.0" in content) or ("92" in content and "180" in content)
        has_hiv_retest = ("复检" in content or "retest" in content.lower()) and "HIV" in content
        has_post_term_41 = "41" in content and ("返院" in content or "post-term" in content or "delivery" in content)
        has_annex4 = ("Need to know" in content or "Need to do" in content) or ("附录 4" in content or "Annex 4" in content)
        
        hard_points_detail = {
            "iron_salt_equivalence": has_iron_conv,
            "gdm_diagnostic_cutoffs": has_gdm_cutoffs,
            "hiv_mandatory_retest": has_hiv_retest,
            "post_term_41_week_return": has_post_term_41,
            "annex4_implementation_matrix": has_annex4
        }
        
        # 推荐项覆盖度 (满分 40)
        rec_score = min(40.0, len(rec_matches) * (40.0 / 49.0)) if rec_matches else 0.0
        score += rec_score
        
        # 表格保真度 (满分 20)
        tab_score = 20.0 if tables_found >= 2 else (10.0 if tables_found == 1 else 0.0)
        score += tab_score
        
        # 核心量化参数覆盖 (满分 20)
        quant_score = min(20.0, quant_hits * 0.5)
        score += quant_score
        
        # 五大关键断言硬指标 (满分 20)
        hard_points = sum(hard_points_detail.values())
        hard_score = min(20.0, hard_points * 4.0)
        score += hard_score
    else:
        # 通用跨学科规范与著作审计 (Generic Epistemic Audit)
        GENERIC_SPEC_RE = re.compile(r"\b([A-Z]\.\d+(\.\d+)?|RFC\s*\d+|Section\s*\d+(\.\d+)*|条款\s*\d+(\.\d+)*|定理\s*\d+|Rule\s*\d+|Rec(?:ommendation)?\s*\d+(\.\d+)?)\b", re.I)
        rec_matches = sorted(list(set(m.group(1) for m in GENERIC_SPEC_RE.finditer(content))))
        
        # 条目覆盖度 (满分 30)
        spec_score = min(30.0, len(rec_matches) * 3.0)
        score += spec_score
        
        # 表格保真度 (满分 25)
        tab_score = min(25.0, tables_found * 10.0)
        score += tab_score
        
        # 量化指标密度 (满分 25)
        quant_score = min(25.0, quant_hits * 1.0)
        score += quant_score
        
        # 物理页码溯源密度 (满分 20)
        anchor_score = min(20.0, page_anchors * 4.0)
        score += anchor_score
        
        hard_points_detail = {
            "has_yaml_frontmatter": content.startswith("---"),
            "has_traceable_anchors": page_anchors >= 3,
            "has_structured_tables": tables_found >= 1,
            "has_quantitative_grounding": quant_hits >= 5
        }
    
    fidelity_grade = "AAA (零丢失黄金级)" if score >= 90 else ("AA (高保真级)" if score >= 75 else ("A (良好)" if score >= 60 else "B (存在丢项警告)"))
    
    return {
        "wiki_file": target_p.name,
        "profile_applied": "who_anc" if is_who_anc else "generic_epistemic",
        "fidelity_grade": fidelity_grade,
        "total_fidelity_score": round(score, 1),
        "specification_ids_count": len(rec_matches),
        "specification_ids": rec_matches[:20],
        "tables_preserved_count": tables_found,
        "quantitative_hits_count": quant_hits,
        "page_anchors_count": page_anchors,
        "critical_anchors_verified": hard_points_detail
    }


def main():
    parser = argparse.ArgumentParser(description="超长文档只读虚拟切片与拓扑探针 (V2.2 零丢失对抗加固版)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. inspect 命令
    inspect_parser = subparsers.add_parser("inspect", help="解析文档目录大纲与切片规划")
    inspect_parser.add_argument("--file", required=True, help="目标文件路径 (如 raw/book.pdf)")
    inspect_parser.add_argument("--json", action="store_true", help="强制纯 JSON 格式输出")

    # 2. radar 命令 (全新零丢失全景雷达)
    radar_parser = subparsers.add_parser("radar", help="全景命题热力雷达扫描 (Pass 1)")
    radar_parser.add_argument("--file", required=True, help="目标文件路径")
    radar_parser.add_argument("--mode", choices=["normative", "heuristic", "descriptive"], default="normative", help="认识论自适应权重模式 (默认 normative)")
    radar_parser.add_argument("--json", action="store_true", help="强制纯 JSON 格式输出")

    # 3. extract-anchor 命令
    anchor_parser = subparsers.add_parser("extract-anchor", help="提取全书前言与全局认知锚点")
    anchor_parser.add_argument("--file", required=True, help="目标文件路径")
    anchor_parser.add_argument("--max-pages", type=int, default=5, help="提取前多少页作为全局锚点 (默认 5)")
    anchor_parser.add_argument("--out", help="保存到临时文件路径 (默认输出到 stdout)")

    # 4. extract-slice 命令 (增强重叠与表格)
    slice_parser = subparsers.add_parser("extract-slice", help="高保真提取指定页码区间的纯文本与表格")
    slice_parser.add_argument("--file", required=True, help="目标文件路径")
    slice_parser.add_argument("--pages", required=True, help="页码区间 (如 10-35 或 42)")
    slice_parser.add_argument("--overlap", type=int, default=0, help="滑动重叠窗口页数 (默认 0，推荐 2~5 页)")
    slice_parser.add_argument("--out", help="保存到临时文件路径 (默认输出到 stdout)")

    # 5. audit 命令 (全新零丢失覆盖度自动核验探针)
    audit_parser = subparsers.add_parser("audit", help="自动核验 Wiki 页面的推荐覆盖度、表格保真度与量化参数")
    audit_parser.add_argument("--wiki", required=True, help="待核验 Wiki 文件路径 (如 wiki/页面.md)")
    audit_parser.add_argument("--profile", default="auto", choices=["auto", "who_anc", "generic"], help="审计画像 (默认 auto)")
    audit_parser.add_argument("--json", action="store_true", help="强制纯 JSON 格式输出")

    # 6. plan-subagents 命令 (根据雷达热力图聚类并生成 Subagent 派发规划)
    plan_parser = subparsers.add_parser("plan-subagents", help="根据雷达热力图聚类高密区间并生成 Subagent 派发规划")
    plan_parser.add_argument("--file", required=True, help="目标文件路径")
    plan_parser.add_argument("--mode", choices=["normative", "heuristic", "descriptive"], default="normative", help="认识论自适应权重模式 (默认 normative)")
    plan_parser.add_argument("--max-cluster", type=int, default=15, help="单切片最大物理页跨度 (默认 15)")
    plan_parser.add_argument("--json", action="store_true", help="强制纯 JSON 格式输出")

    args = parser.parse_args()

    if args.command == "audit":
        res = audit_wiki(Path(args.wiki), profile=getattr(args, "profile", "auto"))
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"==================================================")
            print(f"🔍 零丢失保真度审计报告: {res['wiki_file']} (画像: {res['profile_applied']})")
            print(f"🏆 综合保真等级: {res['fidelity_grade']} (得分: {res['total_fidelity_score']}/100)")
            print(f"📋 规范条目编号命中: {res['specification_ids_count']} 项 -> {res['specification_ids'][:10]}...")
            print(f"📊 二维表格保真度: {res['tables_preserved_count']} 个表格")
            print(f"🔢 微观量化参数命中: {res['quantitative_hits_count']} 处")
            print(f"🔗 穿透物理页码锚点: {res['page_anchors_count']} 处")
            print(f"---------------- 关键断言核验 -------------------")
            for k, v in res["critical_anchors_verified"].items():
                print(f"  • {k}: {'✅ 已验证' if v else '❌ 缺失'}")
            print(f"==================================================")
        return

    doc_path = resolve_file(args.file)

    if args.command == "inspect":
        info = inspect_document(doc_path)
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print(f"==================================================")
            print(f"📄 文件: {info['file']}")
            print(f"📊 物理维度: {info['total_pages']} 页 | 体积: {info['size_bytes'] / 1024 / 1024:.2f} MB | 文本量: {info['total_chars']:,} 字符 / {info['total_words']:,} 词")
            print(f"🧠 多模态 Token 测算 (Gemini @ 560/页): 文档 {info['multimodal_doc_tokens']:,} + 前置底数 {info['base_overhead_tokens']:,} (AGENTS.md 8.1k + 系统提示词 3.9k) = 预估总上下文 {info['total_estimated_context_tokens']:,} Tokens")
            print(f"🚨 大文件分治阈值: {'【触发大文件双轨分治 (总开销 >= 40k)】' if info['is_massive'] else '【单篇常规摄取轨道 (总开销 < 40k)】'}")
            print(f"📑 目录节点总数: {info['toc_count']} 个")
            print(f"---------------- 推荐切片规划 -------------------")
            for s in info["suggested_slices"][:15]:
                print(f"  • [{s['pages']} 页] (共 {s['page_count']} 页) {s['title']}")
            if len(info["suggested_slices"]) > 15:
                print(f"  ... 另有 {len(info["suggested_slices"]) - 15} 个分节")
            print(f"==================================================")

    elif args.command == "radar":
        res = radar_scan(doc_path, mode=getattr(args, "mode", "normative"))
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"==================================================")
            print(f"🎯 全景命题热力雷达 (Radar Heatmap): {res['file']} (模式: {res['mode']})")
            print(f"📊 总页数: {res['total_pages']} 页 | 扫描件预警: {'⚠️ 纯图片扫描件(无文本)' if res['is_scanned_image_pdf'] else '✅ 正常文本层'}")
            print(f"🌟 高密命题页面: {res['high_density_pages_count']} 页")
            print(f"📐 包含结构化表格页面: {res['table_pages_count']} 页 -> {res['table_pages'][:15]}...")
            print(f"💤 证实为参考文献/致谢低熵区: {res['confirmed_low_entropy_pages_count']} 页")
            print(f"---------------- 热力高密页面抽样 -------------------")
            for h in res["high_density_summary"][:10]:
                print(f"  • Page {h['page']:03d} (Score: {h['score']:02d}, Tabs: {h['tables']}, Quant: {h['quant_hits']}) | {h['preview'][:60]}...")
            print(f"==================================================")

    elif args.command == "extract-anchor":
        content = extract_anchor(doc_path, max_pages=args.max_pages)
        if args.out:
            out_p = Path(args.out)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[Success] 全局锚点已写入: {args.out}")
        else:
            print(content)

    elif args.command == "extract-slice":
        content = extract_slice(doc_path, page_range_str=args.pages, overlap=getattr(args, "overlap", 0))
        if args.out:
            out_p = Path(args.out)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[Success] 切片已写入: {args.out}")
        else:
            print(content)

    elif args.command == "plan-subagents":
        res = plan_subagents(doc_path, mode=getattr(args, "mode", "normative"), max_cluster_pages=getattr(args, "max_cluster", 15))
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"==================================================")
            print(f"🤖 Subagent 并行派发规划: {res['file']}")
            if res.get("status") == "FAILED":
                print(f"🚨 规划熔断: {res.get('error')}")
            else:
                print(f"👥 高密总页数: {res.get('total_high_density_pages', 0)} 页 | 需要 Subagents 总数: {res['total_subagents_needed']} 个")
                print(f"---------------- 派发任务清单 -------------------")
                for t in res["tasks"]:
                    print(f"  • [{t['task_id']}] {t['role']} (Pages: {t['pages']}, 跨度: {t['page_count']}页) -> {t['target_draft']}")
            print(f"==================================================")


if __name__ == "__main__":
    main()
