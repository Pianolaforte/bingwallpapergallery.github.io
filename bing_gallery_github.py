#!/usr/bin/env python3
"""
Bing Gallery Generator - GitHub Actions Edition
Based on bing_gen_v5.8.6.py

Adapted for GitHub Actions:
  1. All paths are relative to the script location (BASE_DIR).
  2. Reads bing_gallery_v5.3_backup.html from the same directory; if missing,
     generates a minimal inline HTML template with the same CSS/JS structure
     (header, gallery grid, detail view, market filters, language labels,
     dark mode, search).
  3. Cache lives in .bing_cache.json in the same directory.
  4. browser_descriptions.json is loaded from the same directory if present
     (optional - silently skipped if not found).
  5. Output is index.html (for GitHub Pages) in the same directory.
  6. A validation/proofreading step runs after generation and exits with
     code 1 if quality thresholds are not met.
  7. All existing logic is preserved: language isolation, all market fetching,
     cn.bing.com API, sanitize_text, detect_language, etc.
  8. --supplement flag: also fetches cn.bing.com content and merges it with
     the existing (cached) data.
"""

import json
import urllib.request
import urllib.parse
import time
import re
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

VERSION = "5.8.6-github"

# ---------------------------------------------------------------------------
# Base directory = location of this script (GitHub Actions friendly)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MARKETS = [
    {"code": "en-US", "name": "US",  "flag": "us"},
    {"code": "en-GB", "name": "UK",  "flag": "gb"},
    {"code": "en-CA", "name": "CA",  "flag": "ca"},
    {"code": "de-DE", "name": "DE",  "flag": "de"},
    {"code": "fr-FR", "name": "FR",  "flag": "fr"},
    {"code": "it-IT", "name": "IT",  "flag": "it"},
    {"code": "es-ES", "name": "ES",  "flag": "es"},
    {"code": "pt-BR", "name": "BR",  "flag": "br"},
    {"code": "ja-JP", "name": "JP",  "flag": "jp"},
    {"code": "zh-CN", "name": "CN",  "flag": "cn"},
    {"code": "en-IN", "name": "IN",  "flag": "in"},
]

ENGLISH_MARKETS = ["en-US", "en-GB", "en-CA", "en-IN"]
LOCAL_PRIORITY = ["ja-JP", "zh-CN", "fr-FR", "de-DE", "es-ES", "it-IT", "pt-BR"]

LANG_NAMES = {
    "de": "Deutsch", "fr": "Français", "it": "Italiano",
    "es": "Español", "pt": "Português", "ja": "日本語",
    "zh": "中文", "en": "English"
}

BING_ARCHIVE_API = "https://global.bing.com/HPImageArchive.aspx"
BING_MODEL_API = "https://global.bing.com/hp/api/model"
BING_CN_MODEL_API = "https://cn.bing.com/hp/api/model"

# ---------------------------------------------------------------------------
# All paths relative to BASE_DIR (no hardcoded /workspace paths)
# ---------------------------------------------------------------------------
OUTPUT_PATH = os.path.join(BASE_DIR, "index.html")
CACHE_PATH = os.path.join(BASE_DIR, ".bing_cache.json")
BROWSER_DESCS_PATH = os.path.join(BASE_DIR, "browser_descriptions.json")
PEAPIX_PATH = os.path.join(BASE_DIR, "peapix_supplements.json")
ENGLISH_SUPPLEMENTS_PATH = os.path.join(BASE_DIR, "english_supplements.json")
TEMPLATE_PATH = os.path.join(BASE_DIR, "bing_gallery_v5.3_backup.html")

MAX_CACHE_DAYS = 90

# ---------------------------------------------------------------------------
# Validation thresholds
# ---------------------------------------------------------------------------
MIN_WALLPAPER_COUNT = 28
MAX_EMPTY_DESC_PCT = 10           # empty desc <= 10% of total
MAX_TRUNCATED_DESC_PCT = 10       # truncated desc <= 10% of total
MIN_HTML_SIZE_KB = 50
MAX_NONEN_MISSING_DESC_LANG_PCT = 25  # non-English missing descLang <= 25%


def fetch_json(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  Failed: {url}: {e}")
                return None


def fetch_market_images(market_code, n=7, idx=0):
    params = {
        "format": "js", "n": n, "idx": idx, "mkt": market_code,
        "pid": "hp", "FORM": "BEHPTB", "ql": "6",
    }
    url = f"{BING_ARCHIVE_API}?{urllib.parse.urlencode(params)}"
    data = fetch_json(url)
    return data.get("images", []) if data else []


def fetch_model_desc(market_code, base_url=None):
    base = base_url or BING_MODEL_API
    url = f"{base}?mkt={market_code}"
    data = fetch_json(url)
    if not data:
        return {}
    result = {}
    all_items = data.get("MediaContents", []) + data.get("PreloadMediaContents", [])
    for item in all_items:
        name = item.get("Name", "")
        if not name:
            continue
        ic = item.get("ImageContent", {})
        desc = ic.get("Description", "").strip()
        title = ic.get("Title", "").strip()
        headline = ic.get("Headline", "").strip()
        if desc and len(desc) < 200 and title:
            supplement = headline + ". " + title if headline and headline != title else title
            if supplement not in desc:
                desc = supplement + ". " + desc
        result[name] = {
            "desc": desc, "title": title, "headline": headline,
            "quickFact": ic.get("QuickFact", {}).get("MainText", "").strip(),
            "copyright": ic.get("Copyright", "").strip(),
            "date": item.get("Ssd", ""),
        }
    return result


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            cutoff = (datetime.now() - timedelta(days=MAX_CACHE_DAYS)).strftime("%Y%m%d")
            pruned = {k: v for k, v in cache.items() if k >= cutoff}
            return pruned
        except Exception as e:
            print(f"  Cache: failed to load ({e}), starting fresh")
    return {}


def save_cache(image_entries):
    cache = {}
    for name, entry in image_entries.items():
        cache[name] = {
            "name": entry["name"], "urlbase": entry["urlbase"],
            "date": entry["date"], "dateFormatted": entry["dateFormatted"],
            "markets": entry["markets"], "titles": entry["titles"],
            "copyrights": entry["copyrights"], "descs": entry["descs"],
            "quickFacts": entry["quickFacts"], "captions": entry["captions"],
            "copyrightlinks": entry["copyrightlinks"], "urlbases": entry["urlbases"],
        }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def merge_cache(image_entries, cache):
    merged_count = 0
    for name, cached in cache.items():
        # Skip corrupted/old format cache entries
        if not isinstance(cached, dict) or "name" not in cached or "urlbase" not in cached:
            continue
        if name not in image_entries:
            try:
                image_entries[name] = {
                    "name": cached["name"], "urlbase": cached["urlbase"],
                    "date": cached.get("date", ""), "dateFormatted": cached.get("dateFormatted", ""),
                    "markets": cached.get("markets", []),
                    "titles": cached.get("titles", {}),
                    "copyrights": cached.get("copyrights", {}),
                    "descs": cached.get("descs", {}),
                    "quickFacts": cached.get("quickFacts", {}),
                    "captions": cached.get("captions", {}),
                    "copyrightlinks": cached.get("copyrightlinks", {}),
                    "urlbases": cached.get("urlbases", {}),
                }
                merged_count += 1
            except Exception as e:
                print(f"  Cache: skipping corrupted entry '{name}': {e}")
                continue
        else:
            entry = image_entries[name]
            for key in ["descs", "quickFacts", "titles", "copyrights"]:
                for mk, val in cached.get(key, {}).items():
                    if mk not in entry[key] and val:
                        entry[key][mk] = val
                        merged_count += 1
    return merged_count


def fetch_all_markets():
    all_data = {}
    for market in MARKETS:
        code = market["code"]
        print(f"  {code}...", end=" ")
        images = []
        for idx in [0, 7]:
            batch = fetch_market_images(code, n=7, idx=idx)
            images.extend(batch)
            time.sleep(0.3)
        all_data[code] = images
        print(f"{len(images)} images")
    return all_data


def fetch_all_descriptions(include_cn=False):
    """Fetch model descriptions from all markets.

    When include_cn is True (supplement mode) the cn.bing.com model API is
    also queried and stored under the 'zh-CN-cn' key so its Chinese content
    can be merged into the existing data.
    """
    all_descs = {}
    for market in MARKETS:
        code = market["code"]
        print(f"  {code}...", end=" ")
        descs = fetch_model_desc(code)
        all_descs[code] = descs
        print(f"{len(descs)} descs")
        time.sleep(0.5)
    if include_cn:
        print("  zh-CN (cn.bing.com)...", end=" ")
        cn_descs = fetch_model_desc("zh-CN", base_url=BING_CN_MODEL_API)
        all_descs["zh-CN-cn"] = cn_descs
        print(f"{len(cn_descs)} descs")
    else:
        print("  Skipping cn.bing.com (use --supplement to enable)")
    return all_descs


def detect_language(text):
    """检测文本的主要语言"""
    if not text:
        return "unknown"
    # 检查字符范围
    sample = text[:200]
    # 日文：平假名/片假名
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', sample):
        return "ja"
    # 中文
    if re.search(r'[\u4E00-\u9FFF]', sample):
        return "zh"
    # 意大利语特征
    it_chars = sum(1 for c in sample if c in "àèéìòùÀÈÉÌÒÙ")
    if it_chars > 3:
        return "it"
    # 葡萄牙语特征
    pt_chars = sum(1 for c in sample if c in "ãõçÃÕÇ")
    if pt_chars > 2:
        return "pt"
    # 德语特征
    de_chars = sum(1 for c in sample if c in "äöüßÄÖÜ")
    if de_chars > 2:
        return "de"
    # 法语特征
    fr_chars = sum(1 for c in sample if c in "àâçéèêëîïôùûüÿæœÀÂÇÉÈÊËÎÏÔÙÛÜŸÆŒ")
    if fr_chars > 3:
        return "fr"
    # 西班牙语特征
    es_chars = sum(1 for c in sample if c in "áéíóúñ¿¡ÁÉÍÓÚÑ")
    if es_chars > 2:
        return "es"
    # 默认英文
    if re.match(r'^[A-Za-z]', sample):
        return "en"
    return "unknown"


def load_browser_descriptions():
    """加载浏览器提取的增强描述 (optional - skipped if file absent)"""
    if os.path.exists(BROWSER_DESCS_PATH):
        try:
            with open(BROWSER_DESCS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  Browser descs: failed to load ({e})")
    else:
        print(f"  Browser descs: {os.path.basename(BROWSER_DESCS_PATH)} not found, skipping")
    return {}


def load_peapix_supplements():
    """Load peapix.com supplements (optional)."""
    if os.path.exists(PEAPIX_PATH):
        try:
            with open(PEAPIX_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  Peapix supplements: failed to load ({e})")
    else:
        print(f"  Peapix supplements: {os.path.basename(PEAPIX_PATH)} not found, skipping")
    return {}


def apply_peapix_supplements(unique_images):
    """Apply peapix descriptions to supplement missing/truncated content."""
    supplements = load_peapix_supplements()
    if not supplements:
        print("  No peapix supplements found, skipping")
        return unique_images

    # Skip entries with known peapix data errors
    skip = {"DragonBoatFestivalY26"}

    updated = 0
    for img in unique_images:
        name = img.get("name", "")
        if name in skip:
            continue
        if name not in supplements:
            continue

        new_desc = supplements[name].get("desc", "").strip()
        if not new_desc:
            continue

        old_desc = img.get("desc", "")
        if len(new_desc) > len(old_desc):
            lang = detect_language(new_desc)
            img["desc"] = new_desc

            # Correct descLang for non-English exclusives
            if not img.get("has_english", False) and lang != "en" and lang != "unknown":
                img["desc_lang"] = lang
                # Also update localDesc/localLangName for consistency
                img["localDesc"] = new_desc
                img["localLangName"] = LANG_NAMES.get(lang, lang.upper())

            updated += 1
            print(f"  Peapix: updated {name} ({len(old_desc)} -> {len(new_desc)} chars, lang={lang})")

    if updated:
        print(f"  Peapix supplements applied: {updated} descriptions")
    else:
        print(f"  Peapix supplements: no updates needed")

    return unique_images


def load_english_supplements():
    """Load curated English supplements (high-quality complete descriptions)."""
    if os.path.exists(ENGLISH_SUPPLEMENTS_PATH):
        try:
            with open(ENGLISH_SUPPLEMENTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  English supplements: failed to load ({e})")
    else:
        print(f"  English supplements: {os.path.basename(ENGLISH_SUPPLEMENTS_PATH)} not found, skipping")
    return {}


def apply_english_supplements(unique_images):
    """Apply curated complete English descriptions for wallpapers with truncated text."""
    supplements = load_english_supplements()
    if not supplements:
        print("  No English supplements found, skipping")
        return unique_images

    updated = 0
    for img in unique_images:
        name = img.get("name", "")
        if name not in supplements:
            continue

        new_desc = supplements[name].strip()
        if not new_desc:
            continue

        old_desc = img.get("desc", "")
        if len(new_desc) > len(old_desc):
            img["desc"] = new_desc
            # Ensure English wallpapers are correctly marked
            if img.get("has_english", True):
                img["desc_lang"] = "en"
            updated += 1
            print(f"  English supplement: updated {name} ({len(old_desc)} -> {len(new_desc)} chars)")

    if updated:
        print(f"  English supplements applied: {updated} descriptions")
    else:
        print(f"  English supplements: no updates needed")

    return unique_images


def apply_browser_enhancements(unique_images):
    """应用浏览器增强描述到图片数据"""
    browser_descs = load_browser_descriptions()
    if not browser_descs:
        print("  No browser enhancements found, skipping")
        return unique_images

    enhanced = 0
    for img in unique_images:
        name = img.get("name", "")
        if name not in browser_descs:
            continue

        new_desc = browser_descs[name]
        lang = detect_language(new_desc)

        if lang == "en" and img.get("has_english", False):
            # 英文壁纸的英文增强描述
            if len(new_desc) > len(img.get("desc", "")):
                img["desc"] = new_desc
                enhanced += 1
        elif lang == "en" and not img.get("has_english", False):
            # 非英文壁纸但有英文增强描述 -> 放入desc
            if len(new_desc) > len(img.get("desc", "")):
                img["desc"] = new_desc
                enhanced += 1
        elif lang != "en" and lang != "unknown":
            # 非英文增强描述 -> 放入localDesc
            lang_name = LANG_NAMES.get(lang, lang.upper())
            if len(new_desc) > len(img.get("localDesc", "")):
                img["localDesc"] = new_desc
                img["localLangName"] = lang_name
                enhanced += 1

    if enhanced:
        print(f"  Browser enhancements applied: {enhanced} descriptions updated")
    else:
        print(f"  Browser enhancements: no updates needed")

    return unique_images


def extract_image_name(urlbase):
    match = re.search(r'OHR\.([A-Za-z0-9]+)', urlbase)
    return match.group(1) if match else ""


def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%B %d, %Y")
    except:
        return date_str


def build_image_data(all_data, all_descs, cache=None):
    image_entries = {}

    # Phase 1: 从HPImageArchive.aspx收集基础信息
    for market_code, images in all_data.items():
        for img in images:
            urlbase = img.get("urlbase", "")
            name = extract_image_name(urlbase)
            if not name:
                continue
            if name not in image_entries:
                image_entries[name] = {
                    "name": name, "urlbase": urlbase,
                    "date": img.get("startdate", ""),
                    "dateFormatted": format_date(img.get("startdate", "")),
                    "markets": [], "titles": {}, "copyrights": {},
                    "descs": {}, "quickFacts": {}, "captions": {},
                    "copyrightlinks": {}, "urlbases": {},
                }
            entry = image_entries[name]
            market_info = next((m for m in MARKETS if m["code"] == market_code), None)
            if not market_info:
                continue
            if not any(m["code"] == market_code for m in entry["markets"]):
                entry["markets"].append({"code": market_info["code"], "name": market_info["name"], "flag": market_info["flag"]})

            raw_title = img.get("title", "").strip()
            if not raw_title:
                raw_title = img.get("bsTitle", "").strip()
            raw_caption = img.get("caption", "").strip()
            if raw_title and raw_title.lower() not in ("info", ""):
                full_title = raw_title
                if raw_caption and raw_caption != raw_title:
                    full_title = raw_title + ". " + raw_caption
                entry["titles"][market_code] = full_title
                entry["captions"][market_code] = raw_caption

            copyright_text = img.get("copyright", "").strip()
            if copyright_text:
                entry["copyrights"][market_code] = copyright_text
            cl = img.get("copyrightlink", "").strip()
            if cl:
                # Ensure absolute URL for GitHub Pages compatibility
                if cl.startswith("/"):
                    cl = "https://www.bing.com" + cl
                entry["copyrightlinks"][market_code] = cl
            desc = img.get("desc", "").strip()
            if desc:
                entry["descs"][market_code] = desc
            entry["urlbases"][market_code] = urlbase

    # Phase 1.5: 合并缓存数据 (existing data)
    if cache:
        merged = merge_cache(image_entries, cache)
        if merged:
            print(f"  Cache merged: {merged} supplements from previous runs")

    # Phase 2: 从每个市场的model API补充描述和Did You Know
    print("\n  Applying descriptions from all markets...")
    for market_code, market_descs in all_descs.items():
        if market_code == "zh-CN-cn":
            continue
        for img_name, desc_data in market_descs.items():
            if img_name not in image_entries:
                continue
            entry = image_entries[img_name]
            desc = desc_data.get("desc", "").strip()
            if desc:
                entry["descs"][market_code] = desc
            qf = desc_data.get("quickFact", "").strip()
            if qf:
                entry["quickFacts"][market_code] = qf
            if market_code not in entry["titles"]:
                nt = desc_data.get("title", "").strip()
                nh = desc_data.get("headline", "").strip()
                if nt and nh and nt != nh:
                    entry["titles"][market_code] = nh + ". " + nt
                elif nh:
                    entry["titles"][market_code] = nh
                elif nt:
                    entry["titles"][market_code] = nt
            nc = desc_data.get("copyright", "").strip()
            if market_code not in entry["copyrights"] and nc:
                entry["copyrights"][market_code] = nc

    # Phase 3: 从cn.bing.com获取中文内容 (supplement mode)
    cn_descs = all_descs.get("zh-CN-cn", {})
    for img_name, desc_data in cn_descs.items():
        if img_name not in image_entries:
            continue
        entry = image_entries[img_name]
        desc = desc_data.get("desc", "").strip()
        if desc:
            entry["descs"]["zh-CN"] = desc
        qf = desc_data.get("quickFact", "").strip()
        if qf:
            entry["quickFacts"]["zh-CN"] = qf

    # Phase 4: 构建最终图片列表
    unique_images = []
    for name, entry in image_entries.items():
        has_english = any(mc in entry["titles"] for mc in ENGLISH_MARKETS)

        title = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["titles"]:
                    title = entry["titles"][mc]
                    break
        else:
            for mc in LOCAL_PRIORITY:
                if mc in entry["titles"]:
                    title = entry["titles"][mc]
                    break

        copyright_text = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["copyrights"]:
                    copyright_text = entry["copyrights"][mc]
                    break
        else:
            for mc in LOCAL_PRIORITY:
                if mc in entry["copyrights"]:
                    copyright_text = entry["copyrights"][mc]
                    break

        # 获取英文描述 - 只从英文市场获取，不混入其他语言
        en_desc = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["descs"] and entry["descs"][mc]:
                    en_desc = entry["descs"][mc]
                    break
        else:
            for mc in LOCAL_PRIORITY:
                if mc in entry["descs"] and entry["descs"][mc]:
                    en_desc = entry["descs"][mc]
                    break

        # 获取英文Did You Know - 只从英文市场获取
        en_qf = ""
        for mc in ENGLISH_MARKETS:
            if mc in entry["quickFacts"] and entry["quickFacts"][mc]:
                en_qf = entry["quickFacts"][mc]
                break

        # 获取中文描述和Did You Know - 只从cn.bing.com获取
        zh_desc = entry["descs"].get("zh-CN", "")
        zh_qf = entry["quickFacts"].get("zh-CN", "")

        # 本地语言内容（非英语独占）
        desc_lang = ""
        local_desc = ""
        local_lang_name = ""
        if not has_english:
            # 优先从非中文本地市场获取
            for mc in LOCAL_PRIORITY:
                if mc in entry["descs"] and mc != "zh-CN":
                    local_desc = entry["descs"][mc]
                    desc_lang = mc.split("-")[0]
                    local_lang_name = LANG_NAMES.get(desc_lang, desc_lang.upper())
                    break
            # 如果没有找到非中文描述，检查 zh-CN
            if not desc_lang and "zh-CN" in entry["descs"] and entry["descs"]["zh-CN"]:
                desc_lang = "zh"
                local_lang_name = "中文"

        source_market = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["urlbases"]:
                    source_market = mc
                    break
        if not source_market:
            for mc in LOCAL_PRIORITY:
                if mc in entry["urlbases"]:
                    source_market = mc
                    break

        img_urlbase = entry["urlbases"].get(source_market, entry["urlbases"].get("en-US", ""))
        img_id = img_urlbase.replace("/th?id=", "") if img_urlbase else ""
        if not img_id or img_id == "OHR." or "_" not in img_id:
            continue

        copyrightlink = ""
        if has_english:
            for mc in ENGLISH_MARKETS:
                if mc in entry["copyrightlinks"]:
                    copyrightlink = entry["copyrightlinks"][mc]
                    break
        if not copyrightlink:
            for mc in LOCAL_PRIORITY:
                if mc in entry["copyrightlinks"]:
                    copyrightlink = entry["copyrightlinks"][mc]
                    break

        # Ensure absolute URL for GitHub Pages compatibility
        if copyrightlink and copyrightlink.startswith("/"):
            copyrightlink = "https://www.bing.com" + copyrightlink

        if not title:
            title = name

        unique_images.append({
            "name": name, "urlbase": img_urlbase,
            "date": entry["date"], "dateFormatted": entry["dateFormatted"],
            "markets": entry["markets"], "has_english": has_english,
            "title": title, "copyright": copyright_text,
            "copyrightlink": copyrightlink, "sourceMarket": source_market,
            "desc": en_desc,
            "descZh": zh_desc,
            "localDesc": local_desc if not has_english and local_desc != en_desc else "",
            "localLangName": local_lang_name,
            "desc_lang": desc_lang,
            "quickFact": en_qf,
            "quickFactZh": zh_qf,
            "thumb": f"https://www.bing.com/th?id={img_id}_1920x1080.jpg",
            "uhd": f"https://www.bing.com/th?id={img_id}_UHD.jpg",
            "h1200": f"https://www.bing.com/th?id={img_id}_1920x1200.jpg",
            "h1080": f"https://www.bing.com/th?id={img_id}_1920x1080.jpg",
        })

    unique_images.sort(key=lambda x: x["date"], reverse=True)

    with_desc = sum(1 for img in unique_images if img["desc"])
    with_zh = sum(1 for img in unique_images if img["descZh"])
    with_qf = sum(1 for img in unique_images if img["quickFact"])
    with_zh_qf = sum(1 for img in unique_images if img["quickFactZh"])

    print(f"\n  Stats (after API):")
    print(f"    Total: {len(unique_images)} images")
    print(f"    EN desc: {with_desc}")
    print(f"    ZH desc: {with_zh}")
    print(f"    EN QuickFact: {with_qf}")
    print(f"    ZH QuickFact: {with_zh_qf}")

    return unique_images, image_entries


def sanitize_text(text):
    """清理文本中的控制字符，防止破坏JavaScript JSON解析"""
    if not text:
        return text
    # 将真实换行符/制表符/回车替换为转义序列
    text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    # 移除其他控制字符（除 \n \r \t 外）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text


def build_image_json(images):
    result = []
    for img in images:
        # 清理所有文本字段中的控制字符
        clean_img = {}
        for key, val in img.items():
            if isinstance(val, str):
                clean_img[key] = sanitize_text(val)
            elif isinstance(val, list):
                clean_img[key] = val  # markets 列表不需要清理
            else:
                clean_img[key] = val
        result.append({
            "name": clean_img["name"], "date": clean_img["date"],
            "dateFormatted": clean_img["dateFormatted"],
            "markets": clean_img["markets"], "hasEnglish": clean_img["has_english"],
            "title": clean_img["title"], "copyright": clean_img["copyright"],
            "copyrightlink": clean_img["copyrightlink"], "sourceMarket": clean_img["sourceMarket"],
            "desc": clean_img["desc"], "descZh": clean_img["descZh"],
            "localDesc": clean_img["localDesc"], "localLangName": clean_img.get("localLangName", ""),
            "descLang": clean_img.get("desc_lang", ""),
            "quickFact": clean_img["quickFact"], "quickFactZh": clean_img["quickFactZh"],
            "thumb": clean_img["thumb"], "uhd": clean_img["uhd"],
            "h1200": clean_img["h1200"], "h1080": clean_img["h1080"],
        })
    return json.dumps(result, indent=2, ensure_ascii=False)


def get_minimal_html_template():
    """Generate a minimal, self-contained HTML template inline.

    Mirrors the CSS/JS structure of bing_gallery_v5.3_backup.html:
    header, gallery grid (card view), stream view, detail view, market
    filter tabs, language labels, dark mode toggle and search box.
    """
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bing Gallery v5.8.6</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/css/flag-icons.min.css">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }
.header { background: #1a2744; color: white; padding: 0 24px; height: 56px; display: flex; align-items: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
.logo { font-size: 20px; font-weight: 700; color: white; cursor: pointer; flex-shrink: 0; text-decoration: none; }
.logo-text { font-size: 20px; font-weight: 700; color: white; letter-spacing: 0.5px; }
.logo:hover .logo-text { color: #4caf50; }
.header-right { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.view-toggle { display: flex; gap: 2px; background: rgba(255,255,255,0.1); border-radius: 8px; padding: 3px; }
.view-btn { width: 34px; height: 34px; border: none; background: none; color: rgba(255,255,255,0.6); border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; font-size: 16px; }
.view-btn:hover { background: rgba(255,255,255,0.15); color: white; }
.view-btn.active { background: rgba(76,175,80,0.8); color: white; }
.search-box { padding: 7px 16px; border: 2px solid transparent; border-radius: 20px; font-size: 14px; width: 220px; outline: none; transition: border-color 0.2s; background: rgba(255,255,255,0.9); }
.search-box:focus { border-color: #4caf50; }
.search-box::placeholder { color: #999; }
.tabs-container { background: white; border-bottom: 1px solid #e0e0e0; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; }
.tabs-container::-webkit-scrollbar { height: 0; }
.tabs { display: flex; padding: 0 16px; }
.tab-btn { padding: 10px 16px; border: none; background: none; cursor: pointer; font-size: 14px; color: #666; border-bottom: 3px solid transparent; transition: all 0.2s; white-space: nowrap; }
.tab-btn:hover { color: #1a2744; background: rgba(26,39,68,0.05); }
.tab-btn.active { color: #1a2744; border-bottom-color: #4caf50; font-weight: 600; }
.update-time { text-align: center; padding: 8px 16px; font-size: 12px; color: #999; background: #fafafa; border-bottom: 1px solid #eee; }
.main { max-width: 1200px; margin: 0 auto; padding: 16px; }
.stream-item { display: flex; gap: 16px; padding: 16px; background: white; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: box-shadow 0.2s; cursor: pointer; }
.stream-item:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.stream-thumb { flex-shrink: 0; width: 200px; height: 112px; border-radius: 6px; overflow: hidden; }
.stream-thumb img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
.stream-item:hover .stream-thumb img { transform: scale(1.05); }
.stream-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.stream-date { font-size: 12px; color: #999; }
.stream-title { font-size: 16px; font-weight: 600; color: #1a2744; line-height: 1.4; cursor: pointer; }
.stream-desc { font-size: 13px; color: #666; line-height: 1.5; }
.stream-copyright { font-size: 11px; color: #aaa; }
.stream-downloads { display: flex; gap: 8px; margin-top: 4px; }
.stream-markets { font-size: 16px; }
.dl-btn { padding: 4px 10px; border-radius: 4px; font-size: 12px; text-decoration: none; color: white; }
.uhd-btn { background: #4caf50; }
.h1200-btn { background: #2196f3; }
.h1080-btn { background: #ff9800; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); cursor: pointer; transition: box-shadow 0.2s; }
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.card-image { width: 100%; height: 160px; overflow: hidden; }
.card-image img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
.card:hover .card-image img { transform: scale(1.05); }
.card-body { padding: 12px; }
.card-title { font-size: 14px; font-weight: 600; color: #1a2744; margin-bottom: 4px; cursor: pointer; }
.card-desc { font-size: 12px; color: #666; line-height: 1.4; margin-bottom: 4px; }
.card-date { font-size: 11px; color: #999; }
.card-copyright { font-size: 11px; color: #aaa; }
.card-downloads { display: flex; gap: 6px; margin-top: 6px; }
.card-markets { font-size: 14px; margin-top: 4px; }
.view-container { min-height: 60vh; }
.view-hidden { display: none; }
.no-results { text-align: center; padding: 60px; color: #999; font-size: 16px; }
.detail-container { max-width: 900px; margin: 0 auto; padding: 16px; }
.detail-back { display: inline-flex; align-items: center; color: #1a2744; cursor: pointer; font-size: 14px; margin-bottom: 16px; text-decoration: none; }
.detail-image-wrap { width: 100%; border-radius: 8px; overflow: hidden; margin-bottom: 16px; }
.detail-image-wrap img { width: 100%; display: block; }
.detail-info { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.detail-title { font-size: 22px; font-weight: 700; color: #1a2744; margin-bottom: 4px; }
.detail-date { font-size: 13px; color: #999; margin-bottom: 4px; }
.detail-copyright { font-size: 12px; color: #aaa; margin-bottom: 16px; }
.desc-section { padding: 16px 0; border-bottom: 1px solid #f0f0f0; }
.desc-section:last-of-type { border-bottom: none; }
.lang-label { display: inline-block; font-size: 11px; padding: 4px 12px; border-radius: 12px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
.lang-en { color: #1565c0; background: #e3f2fd; border: 1px solid #bbdefb; }
.lang-zh { color: #c62828; background: #ffebee; border: 1px solid #ffcdd2; }
.lang-local { color: #2e7d32; background: #e8f5e9; border: 1px solid #c8e6c9; }
.desc-text { font-size: 15px; color: #444; line-height: 1.8; }
.desc-text-zh { font-size: 15px; color: #444; line-height: 1.8; }
.quick-fact-box { margin-top: 12px; padding: 12px; background: #fffde7; border-radius: 6px; border-left: 3px solid #ffc107; }
.quick-fact-label { font-size: 12px; font-weight: 600; color: #f57f17; }
.quick-fact-text { font-size: 14px; color: #555; line-height: 1.6; margin-top: 6px; }
.detail-downloads { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
.detail-dl-btn { padding: 8px 16px; border-radius: 6px; font-size: 13px; text-decoration: none; color: white; }
.search-btn { background: #1a2744; }
.detail-markets-section { margin-top: 16px; }
.detail-markets-label { font-size: 12px; color: #999; margin-bottom: 6px; }
.detail-markets-list { display: flex; gap: 8px; flex-wrap: wrap; }
.detail-market-tag { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; padding: 4px 10px; background: #f0f0f0; border-radius: 12px; }
.local-desc-box { padding: 16px; background: #f1f8e9; border-radius: 8px; margin-bottom: 12px; }
/* Dark mode */
body.dark-mode { background: #1a1a2e; color: #e0e0e0; }
body.dark-mode .tabs-container { background: #16213e; border-bottom-color: #333; }
body.dark-mode .tab-btn { color: #aaa; }
body.dark-mode .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.05); }
body.dark-mode .tab-btn.active { color: #4caf50; }
body.dark-mode .update-time { background: #16213e; color: #666; border-bottom-color: #333; }
body.dark-mode .stream-item { background: #16213e; }
body.dark-mode .stream-title { color: #e0e0e0; }
body.dark-mode .card { background: #16213e; }
body.dark-mode .card-title { color: #e0e0e0; }
body.dark-mode .detail-info { background: #16213e; }
body.dark-mode .detail-title { color: #e0e0e0; }
body.dark-mode .desc-text, body.dark-mode .desc-text-zh { color: #ccc; }
body.dark-mode .desc-section { border-bottom-color: #333; }
body.dark-mode .detail-market-tag { background: #0f3460; }
body.dark-mode .search-box { background: rgba(255,255,255,0.15); color: #fff; }
body.dark-mode .search-box::placeholder { color: #888; }
body.dark-mode .local-desc-box { background: #1b3a1b; }
@media (max-width: 768px) { .stream-thumb { width: 140px; height: 78px; } .search-box { width: 140px; } }
@media (max-width: 480px) { .stream-item { flex-direction: column; } .stream-thumb { width: 100%; height: 180px; } .search-box { width: 120px; } .view-btn { width: 30px; height: 30px; font-size: 14px; } }
</style>
</head>
<body>
<div class="header">
    <a class="logo" onclick="app.navigate('#/')"><span class="logo-text">Bing Gallery</span></a>
    <div class="header-right">
        <div class="view-toggle" id="viewToggle">
            <button class="view-btn active" id="streamBtn" title="Stream view">&#9776;</button>
            <button class="view-btn" id="cardBtn" title="Card view">&#9638;</button>
        </div>
        <button class="view-btn" id="darkBtn" title="Toggle dark mode" style="background:rgba(255,255,255,0.1)">&#9681;</button>
        <input type="text" class="search-box" placeholder="Search wallpapers..." id="searchBox" />
    </div>
</div>
<div class="tabs-container" id="tabsContainer"><div class="tabs" id="tabsBar"></div></div>
<div class="update-time">Last updated: 2026-01-01 00:00:00 UTC | v5.8.6</div>
<div class="main view-container" id="streamView"><div id="streamList"></div></div>
<div class="main view-container view-hidden" id="cardView"><div class="card-grid" id="cardGrid"></div></div>
<div class="view-container view-hidden" id="detailView"><div class="detail-container" id="detailContent"></div></div>
<script>
var ALL_IMAGES = [];
var ALL_MARKETS = [];
var app = { currentView: 'stream', currentMarket: 'all', searchQuery: '', currentImageName: null };
function escapeHtml(s) { if (!s) return ''; return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function getFilteredImages() {
    var q = app.searchQuery.toLowerCase();
    return ALL_IMAGES.filter(function(img) {
        if (app.currentMarket !== 'all') {
            var f = false;
            for (var i = 0; i < img.markets.length; i++) { if (img.markets[i].code === app.currentMarket) { f = true; break; } }
            if (!f) return false;
        }
        if (q) {
            var t = (img.title + ' ' + img.copyright + ' ' + img.desc + ' ' + img.descZh + ' ' + img.dateFormatted).toLowerCase();
            if (t.indexOf(q) === -1) return false;
        }
        return true;
    });
}
function buildMarketFlags(markets) { return markets.map(function(m) { return '<span class="fi fi-' + m.flag + '" title="' + m.name + '"></span>'; }).join(' '); }
function buildMarketTagsHtml(markets) { return markets.map(function(m) { return '<span class="detail-market-tag"><span class="fi fi-' + m.flag + '" title="' + m.name + '"></span> ' + m.name + '</span>'; }).join(''); }
function renderTabs() {
    var h = '<button class="tab-btn' + (app.currentMarket === 'all' ? ' active' : '') + '" data-market="all">All</button>';
    ALL_MARKETS.forEach(function(m) { h += '<button class="tab-btn' + (app.currentMarket === m.code ? ' active' : '') + '" data-market="' + m.code + '"><span class="fi fi-' + m.flag + '"></span> ' + m.name + '</button>'; });
    document.getElementById('tabsBar').innerHTML = h;
    document.querySelectorAll('.tab-btn').forEach(function(t) { t.addEventListener('click', function() { app.currentMarket = this.getAttribute('data-market'); renderTabs(); renderCurrentView(); }); });
}
function renderStreamView() {
    var imgs = getFilteredImages(), c = document.getElementById('streamList');
    if (!imgs.length) { c.innerHTML = '<div class="no-results">No wallpapers found.</div>'; return; }
    var h = '';
    imgs.forEach(function(img) {
        var dp = img.desc ? '<div class="stream-desc">' + escapeHtml(img.desc.substring(0, 150)) + '</div>' : '';
        h += '<div class="stream-item" data-name="' + img.name + '"><div class="stream-thumb" onclick="app.navigate(`#/image/' + img.name + '`)"><img src="' + img.thumb + '" alt="' + escapeHtml(img.title) + '" loading="lazy" /></div><div class="stream-info"><div class="stream-date">' + img.dateFormatted + '</div><div class="stream-title" onclick="app.navigate(`#/image/' + img.name + '`)">' + escapeHtml(img.title) + '</div>' + dp + '<div class="stream-copyright">' + escapeHtml(img.copyright) + '</div><div class="stream-downloads"><a href="' + img.uhd + '" class="dl-btn uhd-btn" target="_blank" onclick="event.stopPropagation()">UHD</a><a href="' + img.h1200 + '" class="dl-btn h1200-btn" target="_blank" onclick="event.stopPropagation()">1920x1200</a></div><div class="stream-markets">' + buildMarketFlags(img.markets) + '</div></div></div>';
    });
    c.innerHTML = h;
}
function renderCardView() {
    var imgs = getFilteredImages(), c = document.getElementById('cardGrid');
    if (!imgs.length) { c.innerHTML = '<div class="no-results">No wallpapers found.</div>'; return; }
    var h = '';
    imgs.forEach(function(img) {
        var dp = img.desc ? '<div class="card-desc">' + escapeHtml(img.desc.substring(0, 120)) + '</div>' : '';
        h += '<div class="card" data-name="' + img.name + '"><div class="card-image" onclick="app.navigate(`#/image/' + img.name + '`)"><img src="' + img.thumb + '" alt="' + escapeHtml(img.title) + '" loading="lazy" /></div><div class="card-body"><div class="card-title" onclick="app.navigate(`#/image/' + img.name + '`)">' + escapeHtml(img.title) + '</div>' + dp + '<div class="card-date">' + img.dateFormatted + '</div><div class="card-copyright">' + escapeHtml(img.copyright) + '</div><div class="card-downloads"><a href="' + img.uhd + '" class="dl-btn uhd-btn" target="_blank" onclick="event.stopPropagation()">UHD</a><a href="' + img.h1200 + '" class="dl-btn h1200-btn" target="_blank" onclick="event.stopPropagation()">1920x1200</a></div><div class="card-markets">' + buildMarketFlags(img.markets) + '</div></div></div>';
    });
    c.innerHTML = h;
}
function renderDetailView(imageName) {
    var img = null;
    for (var i = 0; i < ALL_IMAGES.length; i++) { if (ALL_IMAGES[i].name === imageName) { img = ALL_IMAGES[i]; break; } }
    if (!img) { document.getElementById('detailContent').innerHTML = '<div class="no-results">Image not found.</div>'; return; }
    var bingBtn = img.copyrightlink ? '<a href="' + escapeHtml(img.copyrightlink) + '" class="detail-dl-btn search-btn" target="_blank">&#128269; Search on Bing</a>' : '';
    var contentHtml = '';
    if (img.localDesc && img.localLangName) { contentHtml += '<div class="local-desc-box"><div class="lang-label lang-local">' + img.localLangName + '</div><br><div class="desc-text">' + escapeHtml(img.localDesc) + '</div></div>'; }
    if (img.desc) { contentHtml += '<div class="desc-section"><div class="lang-label lang-en">English</div><br><div class="desc-text">' + escapeHtml(img.desc) + '</div>'; if (img.quickFact) { contentHtml += '<div class="quick-fact-box"><div class="quick-fact-label">&#128161; Did You Know</div><br><div class="quick-fact-text">' + escapeHtml(img.quickFact) + '</div></div>'; } contentHtml += '</div>'; }
    if (img.descZh) { contentHtml += '<div class="desc-section"><div class="lang-label lang-zh">&#20013;&#25991;</div><br><div class="desc-text-zh">' + escapeHtml(img.descZh) + '</div>'; if (img.quickFactZh) { contentHtml += '<div class="quick-fact-box"><div class="quick-fact-label">&#128161; &#20320;&#30693;&#36947;&#21527;&#65311;</div><br><div class="quick-fact-text">' + escapeHtml(img.quickFactZh) + '</div></div>'; } contentHtml += '</div>'; }
    var html = '<a class="detail-back" onclick="app.navigate(`#/`)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;flex-shrink:0"><path d="M15 18l-6-6 6-6"/></svg>Return to Gallery</a><div class="detail-image-wrap"><img src="' + img.h1080 + '" alt="' + escapeHtml(img.title) + '" /></div><div class="detail-info"><div class="detail-title">' + escapeHtml(img.title) + '</div><div class="detail-date">' + img.dateFormatted + '</div><div class="detail-copyright">' + escapeHtml(img.copyright) + '</div>' + contentHtml + '<div class="detail-downloads"><a href="' + img.uhd + '" class="detail-dl-btn uhd-btn" target="_blank">UHD</a><a href="' + img.h1200 + '" class="detail-dl-btn h1200-btn" target="_blank">1920x1200</a><a href="' + img.h1080 + '" class="detail-dl-btn h1080-btn" target="_blank">1920x1080</a>' + bingBtn + '</div><div class="detail-markets-section"><div class="detail-markets-label">Appears in:</div><div class="detail-markets-list">' + buildMarketTagsHtml(img.markets) + '</div></div></div>';
    document.getElementById('detailContent').innerHTML = html;
}
function showView(v) {
    document.getElementById('streamView').classList.toggle('view-hidden', v !== 'stream');
    document.getElementById('cardView').classList.toggle('view-hidden', v !== 'card');
    document.getElementById('detailView').classList.toggle('view-hidden', v !== 'detail');
    document.getElementById('tabsContainer').style.display = v === 'detail' ? 'none' : '';
    document.querySelector('.update-time').style.display = v === 'detail' ? 'none' : '';
    document.getElementById('viewToggle').style.display = v === 'detail' ? 'none' : '';
    app.currentView = v;
}
function renderCurrentView() {
    if (app.currentView === 'stream') renderStreamView();
    else if (app.currentView === 'card') renderCardView();
    else renderDetailView(app.currentImageName);
}
app.navigate = function(p) { window.location.hash = p; };
function handleRoute() {
    var h = window.location.hash || '#/';
    if (h.indexOf('#/image/') === 0) { app.currentImageName = h.replace('#/image/', ''); showView('detail'); renderDetailView(app.currentImageName); window.scrollTo(0, 0); }
    else { app.currentImageName = null; showView(app.currentView === 'detail' ? 'stream' : app.currentView); renderCurrentView(); }
}
(function init() {
    renderTabs();
    document.getElementById('streamBtn').addEventListener('click', function() { app.currentView = 'stream'; this.classList.add('active'); document.getElementById('cardBtn').classList.remove('active'); showView('stream'); renderStreamView(); });
    document.getElementById('cardBtn').addEventListener('click', function() { app.currentView = 'card'; this.classList.add('active'); document.getElementById('streamBtn').classList.remove('active'); showView('card'); renderCardView(); });
    document.getElementById('searchBox').addEventListener('input', function() { app.searchQuery = this.value; if (app.searchQuery) { app.currentMarket = 'all'; renderTabs(); } renderCurrentView(); });
    document.getElementById('darkBtn').addEventListener('click', function() { document.body.classList.toggle('dark-mode'); try { localStorage.setItem('bing-dark', document.body.classList.contains('dark-mode') ? '1' : '0'); } catch(e) {} });
    try { if (localStorage.getItem('bing-dark') === '1') document.body.classList.add('dark-mode'); } catch(e) {}
    window.addEventListener('hashchange', handleRoute);
    handleRoute(); renderStreamView(); renderCardView();
})();
</script>
</body>
</html>
'''


def generate_html(images):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    images_json = build_image_json(images)
    markets_json = json.dumps(MARKETS, indent=2, ensure_ascii=False)

    # 优先使用内嵌模板（确保样式一致性），不再回退到简化模板
    try:
        from bing_template import build_html
        html = build_html(images_json, markets_json, now)
        html = html.replace('<title>Bing Gallery</title>',
                           f'<title>Bing Gallery v{VERSION}</title>')
        html = html.replace(f'Last updated: {now}',
                           f'Last updated: {now} | v{VERSION}')
        print("  Using embedded template (bing_template.py)")
        return html
    except ImportError:
        pass

    # 回退：尝试读取外部模板文件
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template = f.read()
        print(f"  Using external template: {os.path.basename(TEMPLATE_PATH)}")
    else:
        print(f"  WARNING: bing_template.py not found and external template missing!"
              f" Using minimal fallback template (styles will differ).")
        template = get_minimal_html_template()

    html = re.sub(r'var ALL_IMAGES = \[.*?\];',
                  f'var ALL_IMAGES = {images_json};', template, flags=re.DOTALL)
    html = re.sub(r'var ALL_MARKETS = \[.*?\];',
                  f'var ALL_MARKETS = {markets_json};', html, flags=re.DOTALL)
    html = re.sub(r'<title>Bing Gallery v[\d.]+</title>',
                  f'<title>Bing Gallery v{VERSION}</title>', html)
    html = re.sub(r'Last updated: .*? \| v[\d.]+',
                  f'Last updated: {now} | v{VERSION}', html)
    return html


def validate_output(images, html_path):
    """Proofread / validate the generated gallery.

    Checks:
      - Wallpaper count >= 28
      - Empty desc count <= 2
      - Truncated desc (<200 chars) count <= 3
      - HTML file size > 50KB
      - Non-English wallpapers have descLang set (missing <= 2)
    Returns True if all checks pass, False otherwise.
    """
    print("\n" + "=" * 60)
    print("VALIDATION / PROOFREADING")
    print("=" * 60)

    checks = []

    # 1. Wallpaper count
    total = len(images)
    ok = total >= MIN_WALLPAPER_COUNT
    checks.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] Wallpaper count: {total} "
          f"(>= {MIN_WALLPAPER_COUNT})")

    # 2. Empty desc count (percentage-based)
    empty_desc = sum(1 for img in images if not img.get("desc", ""))
    max_empty = max(2, int(total * MAX_EMPTY_DESC_PCT / 100))
    ok = empty_desc <= max_empty
    checks.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] Empty desc count: {empty_desc} "
          f"(<= {max_empty})")

    # 3. Truncated desc count (< 200 chars, non-empty, percentage-based)
    truncated = sum(
        1 for img in images
        if img.get("desc", "") and len(img["desc"]) < 200
    )
    max_trunc = max(3, int(total * MAX_TRUNCATED_DESC_PCT / 100))
    ok = truncated <= max_trunc
    checks.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] Truncated desc (<200 chars) count: "
          f"{truncated} (<= {max_trunc})")

    # 4. HTML file size > 50KB
    html_size_kb = 0.0
    if os.path.exists(html_path):
        html_size_kb = os.path.getsize(html_path) / 1024
    ok = html_size_kb > MIN_HTML_SIZE_KB
    checks.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] HTML file size: {html_size_kb:.1f} KB "
          f"(> {MIN_HTML_SIZE_KB} KB)")

    # 5. Non-English wallpapers have descLang set (percentage-based)
    non_en = [img for img in images if not img.get("has_english", False)]
    non_en_missing = sum(1 for img in non_en if not img.get("desc_lang", ""))
    max_missing = max(2, int(len(non_en) * MAX_NONEN_MISSING_DESC_LANG_PCT / 100)) if non_en else 0
    ok = non_en_missing <= max_missing
    checks.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] Non-English wallpapers missing "
          f"descLang: {non_en_missing}/{len(non_en)} "
          f"(<= {max_missing})")

    print("-" * 60)
    all_pass = all(checks)
    if all_pass:
        print("  RESULT: ALL CHECKS PASSED")
    else:
        failed = sum(1 for c in checks if not c)
        print(f"  RESULT: {failed} CHECK(S) FAILED")
    print("=" * 60)
    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description="Bing Gallery Generator (GitHub Actions Edition)")
    parser.add_argument(
        '--supplement', action='store_true',
        help='Supplement mode: also fetch cn.bing.com content and merge '
             'with existing (cached) data')
    args = parser.parse_args()

    print("=" * 60)
    print(f"Bing Gallery Generator v{VERSION}")
    print("GitHub Actions Edition")
    if args.supplement:
        print("Mode: SUPPLEMENT (cn.bing.com enabled)")
    else:
        print("Mode: STANDARD (cn.bing.com skipped)")
    print(f"Base dir: {BASE_DIR}")
    print(f"Output:   {OUTPUT_PATH}")
    print("=" * 60)

    print("\n[1/7] Loading cache...")
    cache = load_cache()
    print(f"  Cache: {len(cache)} entries loaded ({os.path.basename(CACHE_PATH)})")

    print("\n[2/7] Fetching 14-day history from all markets...")
    all_data = fetch_all_markets()
    print(f"  Total: {sum(len(v) for v in all_data.values())} images")

    print("\n[3/7] Fetching descriptions from ALL markets...")
    all_descs = fetch_all_descriptions(include_cn=args.supplement)

    print("\n[4/7] Building image data...")
    unique_images, image_entries = build_image_data(all_data, all_descs, cache=cache)

    save_cache(image_entries)
    print(f"\n  Cache saved: {len(image_entries)} entries")

    print("\n[5/7] Applying browser enhancements (optional)...")
    unique_images = apply_browser_enhancements(unique_images)

    print("\n[5.5/7] Applying peapix supplements...")
    unique_images = apply_peapix_supplements(unique_images)

    print("\n[5.7/7] Applying curated English supplements...")
    unique_images = apply_english_supplements(unique_images)

    print("\n[6/7] Generating HTML...")
    html = generate_html(unique_images)
    if html:
        os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n  Done! {OUTPUT_PATH} "
              f"({os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB)")

        # Create dated archive copy (incremental: don't overwrite existing archives)
        today_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
        archive_path = os.path.join(BASE_DIR, f"bing_gallery_{today_str}.html")
        if not os.path.exists(archive_path):
            with open(archive_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Archived: {archive_path} "
                  f"({os.path.getsize(archive_path) / 1024:.1f} KB)")
        else:
            # Update existing archive with latest content (incremental supplement)
            with open(archive_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Updated archive: {archive_path} "
                  f"({os.path.getsize(archive_path) / 1024:.1f} KB)")
    else:
        print("ERROR: Failed to generate HTML")
        sys.exit(1)

    print("\n--- Final Summary ---")
    print(f"Total images: {len(unique_images)}")
    print(f"With EN desc: {sum(1 for img in unique_images if img['desc'])}")
    print(f"With ZH desc: {sum(1 for img in unique_images if img['descZh'])}")
    print(f"With local desc: {sum(1 for img in unique_images if img.get('localDesc', ''))}")
    print(f"With EN QuickFact: {sum(1 for img in unique_images if img['quickFact'])}")
    print(f"With ZH QuickFact: {sum(1 for img in unique_images if img['quickFactZh'])}")

    print("\n[7/7] Validating output...")
    ok = validate_output(unique_images, OUTPUT_PATH)
    if not ok:
        print("\nERROR: Validation failed. Exiting with code 1.")
        sys.exit(1)
    print("\nValidation passed. Gallery generation complete.")


if __name__ == "__main__":
    main()
