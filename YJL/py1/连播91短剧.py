# -*- coding: utf-8 -*-
# 91成人短剧 https://91crdj.com，91crdj89@gmail.com，https://t.me/hubiaorenshipin/4202

import re
import json
import time
import zlib

try:
    from base.spider import Spider as BaseSpider
except Exception:
    try:
        from base.spider import BaseSpider
    except Exception:
        class BaseSpider(object):
            pass

try:
    from urllib.request import Request, build_opener, HTTPSHandler
    from urllib.parse import quote, unquote, urljoin, parse_qsl, urlparse
except Exception:
    from urllib2 import Request, build_opener, HTTPSHandler
    from urllib import quote, unquote
    from urlparse import urljoin, parse_qsl, urlparse

try:
    import ssl as _ssl
except Exception:
    _ssl = None

try:
    import threading as _threading
    _LOCK = _threading.Lock()
except Exception:
    _LOCK = None

IMG_KEY = "".join(chr(int(x)) for x in
                  "102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48".split("_"))
IMG_IV = "".join(chr(int(x)) for x in
                 "57_55_98_54_48_51_57_52_97_98_99_50_102_98_101_49".split("_"))
IMG_PROXY = 1
PROXY_BASE = "http://127.0.0.1:9978"
_PIC_CACHE = {}
_PIC_CACHE_MAX = 80

NAME = "91成人短剧"
HOST = "https://91crdj.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
TIMEOUT = 8
RETRY = 1
MIN_GAP = 0.2

_CUR_HOST = HOST
_CACHE = {}
_ITEM_POOL = {}
_TTL_LIST = 300
_TTL_DETAIL = 1800
_TTL_PLAY = 120
_OPENER = None
_LAST_REQ = [0.0]

DEFAULT_CLASSES = [
    {"type_id": "duanju", "type_name": "成人短剧"},
    {"type_id": "manju", "type_name": "成人漫剧"},
    {"type_id": "zhenrenju", "type_name": "真人剧"},
    {"type_id": "shipin", "type_name": "成人视频"},
    {"type_id": "manhua", "type_name": "成人漫画"},
    {"type_id": "xiaoshuo", "type_name": "成人小说"},
    {"type_id": "paihang", "type_name": "热播榜"},
    {"type_id": "biaoqian", "type_name": "标签榜"},
]
_TYPE_NAME = dict((c["type_id"], c["type_name"]) for c in DEFAULT_CLASSES)
_VALID = dict((c["type_id"], 1) for c in DEFAULT_CLASSES)
_TAG = {"manhua": "image", "xiaoshuo": "text"}

FILTERS = {
    "biaoqian": [
        {"key": "order", "name": "排序", "value": [
            {"n": "最新", "v": "new"},
            {"n": "最热", "v": "hot"}]},
        {"key": "videoTag", "name": "分类", "value": [
            {"n": "全部", "v": "biaoqian"},
            {"n": "AI短剧", "v": "aiduanju"},
            {"n": "AI视频", "v": "aishipin"},
            {"n": "高颜值", "v": "gaoyanzhi"},
            {"n": "剧情", "v": "juqing"},
            {"n": "女神", "v": "nvshen"},
            {"n": "巨乳", "v": "juru"},
            {"n": "AI漫剧", "v": "aimanju"}]},
        {"key": "videoTag", "name": "分类", "value": [
            {"n": "口交", "v": "koujiao"},
            {"n": "后入", "v": "houru"},
            {"n": "美乳", "v": "meiru"},
            {"n": "诱惑", "v": "youhuo"},
            {"n": "反差", "v": "fancha"},
            {"n": "91短剧", "v": "91duanju"},
            {"n": "都市短剧", "v": "doushiduanju"},
            {"n": "调教", "v": "diaojiao"}]},
        {"key": "videoTag", "name": "分类", "value": [
            {"n": "古装", "v": "guzhuang"},
            {"n": "中出", "v": "zhongchu"},
            {"n": "模特", "v": "mote"},
            {"n": "美腿", "v": "meitui"},
            {"n": "性感", "v": "xinggan"},
            {"n": "AI魔改", "v": "aimogai"}]},
    ],
}

_BAD_PIC = ("data:", "base64,", "load.gif", "loading.gif", "placeholder",
            "default.png", "nopic", "no-pic", "spacer.gif", "blank.gif")
_PIC_ATTRS = ("data-original", "data-src", "data-echo", "data-lazy-src",
              "data-url", "data-thumb")

_RE_CARD = re.compile(r'<a class="card"', re.I)
_RE_HREF = re.compile(r'href="([^"]+)"')
_RE_TRACK_NAME = re.compile(r'data-track-item-name="([^"]*)"')
_RE_ALT = re.compile(r'\balt="([^"]*)"')
_RE_TITLE = re.compile(r'\btitle="([^"]*)"')
_RE_PTITLE = re.compile(r'<span class="p-title[^"]*">(.*?)</span>', re.S)
_RE_BADGE = re.compile(r'<span class="badge[^"]*">(.*?)</span>', re.S)
_RE_EPSFLAG = re.compile(r'<span class="eps-flag[^"]*">(.*?)</span>', re.S)
_RE_PIMG = re.compile(r'<img class="p-img"[^>]*>', re.I)
_RE_SRC = re.compile(r'(?<![-\w.])src\s*=\s*"([^"]+)"')
_RE_H1 = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
_RE_EPGRID = re.compile(r'<div class="ep-grid[^"]*">(.*?)</div>', re.S)
_RE_EP_A = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_RE_COMIC_PAGE = re.compile(r'<img class="comic-page[^"]*"[^>]*>', re.I)
_RE_NOVEL_ART = re.compile(r'<article class="novel"[^>]*>(.*?)</article>', re.S | re.I)
_RE_NOVEL_H = re.compile(r'<h2 class="novel-h"[^>]*>(.*?)</h2>', re.S | re.I)
_RE_PLAY_ID = re.compile(r'^(img|novel)_(\d+)_(\d+)$')
_RE_OGIMG = re.compile(r'<meta[^>]*og:image[^>]*content="([^"]+)"', re.I)
_RE_OGDESC = re.compile(r'<meta[^>]*og:description[^>]*content="([^"]*)"', re.I)
_RE_METADESC = re.compile(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', re.I)
_RE_TIME = re.compile(r'<time[^>]*>(\d{4})', re.I)
_RE_PAGE = re.compile(r'/page/(\d+)/')
_RE_PAGES = re.compile(r'data-pages="(\d+)"')
_RE_CURRENT = re.compile(r'"current"\s*:\s*\{[^{}]*"src"\s*:\s*"([^"]+)"')
_RE_ANYM3U8 = re.compile(r'(https?://[^\'"\s<>]+?\.m3u8[^\'"\s<>]*)')


def _txt(s):
    try:
        s = re.sub(r"<[^>]+>", "", s or "")
        s = re.sub(r"\s+", " ", s).strip()
    except Exception:
        s = ""
    return (s.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
             .replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")).strip()


def _q(s):
    try:
        return quote(str(s or ""), safe="")
    except Exception:
        return str(s or "")


def _abs_url(u):
    if not u:
        return ""
    u = str(u).strip()
    if "://" in u:
        return u
    if u.startswith("//"):
        return "https:" + u
    try:
        return urljoin(_CUR_HOST + "/", u.lstrip("/"))
    except Exception:
        return _CUR_HOST + "/" + u.lstrip("/")


def _path_segs(href):
    try:
        p = urlparse(href).path or href
    except Exception:
        p = href
    if not str(p).startswith("/"):
        p = "/" + str(p)
    return [s for s in p.split("/") if s]


def _split_path(href):
    seg = _path_segs(href)
    if len(seg) < 2:
        return "", ""
    return seg[0], "/" + seg[0] + "/" + seg[1] + "/"


def _work_id(path):
    seg = [s for s in str(path or "").split("/") if s]
    if len(seg) < 2:
        return ""
    m = re.match(r"(\d+)", seg[1])
    return m.group(1) if m else ""


def _chap_id(href):
    seg = _path_segs(href)
    if len(seg) >= 3 and seg[-1].isdigit():
        return seg[-1]
    return "1"


def _clean_pic(u):
    if not u:
        return ""
    u = str(u).strip().strip('"').strip("'")
    if not u:
        return ""
    low = u.lower()
    for bad in _BAD_PIC:
        if bad in low:
            return ""
    if "://" not in u and not u.startswith("//"):
        u = _abs_url(u)
    elif u.startswith("//"):
        u = "https:" + u
    return u


def _pick_pic(block):
    if not block:
        return ""
    for attr in _PIC_ATTRS:
        m = re.search(attr + r'\s*=\s*"([^"]+)"', block, re.I)
        if m:
            p = _clean_pic(m.group(1))
            if p:
                return p
    m = _RE_SRC.search(block)
    if m:
        return _clean_pic(m.group(1))
    return ""


def _cache_get(key, ttl):
    item = _CACHE.get(key)
    if item and (time.time() - item[0]) < ttl:
        return item[1]
    return None


def _cache_set(key, value):
    try:
        if len(_CACHE) > 400:
            now = time.time()
            for k in list(_CACHE.keys()):
                if now - _CACHE[k][0] > 3600:
                    del _CACHE[k]
        _CACHE[key] = (time.time(), value)
    except Exception:
        pass


def _pool_put(vid, name, pic, remarks):
    try:
        if len(_ITEM_POOL) > 800:
            _ITEM_POOL.clear()
        _ITEM_POOL[vid] = {"name": name, "pic": pic, "remarks": remarks}
    except Exception:
        pass


_AES_SBOX = [0] * 256
_AES_INV = [0] * 256
_AES_READY = [0]
_AES_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]
_AES_T = [None]


def _aes_mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        b >>= 1
        a <<= 1
        if a & 0x100:
            a ^= 0x11B
    return p & 0xFF


def _aes_gf_inv(a):
    if a == 0:
        return 0
    r, base, e = 1, a, 254
    while e:
        if e & 1:
            r = _aes_mul(r, base)
        base = _aes_mul(base, base)
        e >>= 1
    return r


def _aes_init():
    if _AES_READY[0]:
        return
    for x in range(256):
        inv = _aes_gf_inv(x)
        s = 0
        for i in range(8):
            b = (((inv >> i) & 1) ^ ((inv >> ((i + 4) % 8)) & 1)
                 ^ ((inv >> ((i + 5) % 8)) & 1) ^ ((inv >> ((i + 6) % 8)) & 1)
                 ^ ((inv >> ((i + 7) % 8)) & 1) ^ ((0x63 >> i) & 1))
            s |= b << i
        _AES_SBOX[x] = s
    for i, v in enumerate(_AES_SBOX):
        _AES_INV[v] = i
    _AES_READY[0] = 1


def _aes_expand(key16):
    w = [list(key16[i * 4:i * 4 + 4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [_AES_SBOX[x] for x in t]
            t[0] ^= _AES_RCON[i // 4 - 1]
        w.append([w[i - 4][j] ^ t[j] for j in range(4)])
    return w


def _aes_tables():
    g = dict((m, [_aes_mul(x, m) for x in range(256)]) for m in (9, 11, 13, 14))

    def td(coefs):
        t = [0] * 256
        for x in range(256):
            y = _AES_INV[x]
            t[x] = ((g[coefs[0]][y] << 24) | (g[coefs[1]][y] << 16)
                    | (g[coefs[2]][y] << 8) | g[coefs[3]][y])
        return t
    return (td((0x0E, 0x09, 0x0D, 0x0B)), td((0x0B, 0x0E, 0x09, 0x0D)),
            td((0x0D, 0x0B, 0x0E, 0x09)), td((0x09, 0x0D, 0x0B, 0x0E)))


def _aes_round_keys(key16):
    w = _aes_expand(key16)
    g = dict((m, [_aes_mul(x, m) for x in range(256)]) for m in (9, 11, 13, 14))
    rk = []
    for rd in range(11):
        cols = []
        for c in range(4):
            b = w[rd * 4 + c]
            cols.append((b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3])
        rk.append(cols)
    dw = [rk[0]]
    for rd in range(1, 10):
        cols = []
        for c in range(4):
            a0, a1, a2, a3 = w[rd * 4 + c]
            cols.append(((g[14][a0] ^ g[11][a1] ^ g[13][a2] ^ g[9][a3]) << 24)
                        | ((g[9][a0] ^ g[14][a1] ^ g[11][a2] ^ g[13][a3]) << 16)
                        | ((g[13][a0] ^ g[9][a1] ^ g[14][a2] ^ g[11][a3]) << 8)
                        | (g[11][a0] ^ g[13][a1] ^ g[9][a2] ^ g[14][a3]))
        dw.append(cols)
    dw.append(rk[10])
    return w, dw


def _aes128_cbc_decrypt(data, key16, iv16):
    _aes_init()
    if _AES_T[0] is None:
        _AES_T[0] = _aes_tables()
    TD0, TD1, TD2, TD3 = _AES_T[0]
    w, dwk = _aes_round_keys(key16)
    rk0 = w[0] + w[1] + w[2] + w[3]
    out = bytearray(len(data))
    prev = [iv16[0] << 24 | iv16[1] << 16 | iv16[2] << 8 | iv16[3],
            iv16[4] << 24 | iv16[5] << 16 | iv16[6] << 8 | iv16[7],
            iv16[8] << 24 | iv16[9] << 16 | iv16[10] << 8 | iv16[11],
            iv16[12] << 24 | iv16[13] << 16 | iv16[14] << 8 | iv16[15]]
    n = len(data) // 16
    off = 0
    for _ in range(n):
        s = list(data[off:off + 16])
        st = [0, 0, 0, 0]
        for c in range(4):
            st[c] = ((s[4 * c] << 24) | (s[4 * c + 1] << 16)
                     | (s[4 * c + 2] << 8) | s[4 * c + 3]) ^ dwk[10][c]
        for rd in range(9, 0, -1):
            rk = dwk[rd]
            ns = [0, 0, 0, 0]
            for c in range(4):
                ns[c] = (TD0[(st[c] >> 24) & 0xFF]
                         ^ TD1[(st[(c - 1) % 4] >> 16) & 0xFF]
                         ^ TD2[(st[(c - 2) % 4] >> 8) & 0xFF]
                         ^ TD3[st[(c - 3) % 4] & 0xFF] ^ rk[c])
            st = ns
        res = [0] * 16
        for c in range(4):
            for r in range(4):
                b = (st[(c - r) % 4] >> (24 - 8 * r)) & 0xFF
                res[r + 4 * c] = _AES_INV[b] ^ rk0[r + 4 * c]
        for c in range(4):
            x = (res[4 * c] << 24 | res[4 * c + 1] << 16
                 | res[4 * c + 2] << 8 | res[4 * c + 3]) ^ prev[c]
            out[off + 4 * c] = (x >> 24) & 0xFF
            out[off + 4 * c + 1] = (x >> 16) & 0xFF
            out[off + 4 * c + 2] = (x >> 8) & 0xFF
            out[off + 4 * c + 3] = x & 0xFF
        prev = [s[0] << 24 | s[1] << 16 | s[2] << 8 | s[3],
                s[4] << 24 | s[5] << 16 | s[6] << 8 | s[7],
                s[8] << 24 | s[9] << 16 | s[10] << 8 | s[11],
                s[12] << 24 | s[13] << 16 | s[14] << 8 | s[15]]
        off += 16
    return bytes(out)


def _aes_dec_image(raw):
    if len(raw) < 32 or len(raw) % 16:
        return raw
    try:
        pt = _aes128_cbc_decrypt(raw, IMG_KEY.encode("utf-8"), IMG_IV.encode("utf-8"))
    except Exception:
        return raw
    if pt[:3] == b"\xff\xd8\xff" or pt[:8] == b"\x89PNG\r\n\x1a\n" \
            or (pt[:4] == b"RIFF" and pt[8:12] == b"WEBP"):
        n = pt[-1]
        if 1 <= n <= 16 and len(pt) >= n and pt[-n:] == bytes(bytearray([n] * n)):
            pt = pt[:-n]
        return pt
    return raw


def _pic_proxy_url(u):
    if not u or not IMG_PROXY or "/proxy?" in u:
        return u or ""
    try:
        return PROXY_BASE + "/proxy?do=py&url=" + _q(u)
    except Exception:
        return u


def _get_opener():
    global _OPENER
    if _OPENER is None:
        handlers = []
        if _ssl is not None:
            try:
                handlers.append(HTTPSHandler(context=_ssl._create_unverified_context()))
            except Exception:
                pass
        try:
            _OPENER = build_opener(*handlers)
        except Exception:
            _OPENER = build_opener()
    return _OPENER


def _throttle():
    if _LOCK is None:
        return
    try:
        _LOCK.acquire()
        gap = time.time() - _LAST_REQ[0]
        if 0 < gap < MIN_GAP:
            time.sleep(MIN_GAP - gap)
        _LAST_REQ[0] = time.time()
    except Exception:
        pass
    finally:
        try:
            _LOCK.release()
        except Exception:
            pass


def _decompress(raw):
    try:
        if raw[:2] == b"\x1f\x8b" or (raw and raw[0] == 0x78):
            return zlib.decompress(raw, 47)
    except Exception:
        pass
    return raw


def _decode(raw):
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def _http_raw(url, referer="", retry=RETRY, timeout=TIMEOUT):
    if not url:
        return b""
    headers = {
        "User-Agent": UA,
        "Referer": referer or (_CUR_HOST + "/"),
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
    }
    for attempt in range(retry + 1):
        try:
            _throttle()
            resp = _get_opener().open(Request(url, headers=headers), timeout=timeout)
            return _decompress(resp.read())
        except Exception:
            if attempt >= retry:
                break
            try:
                time.sleep(0.4 * (attempt + 1))
            except Exception:
                pass
    return b""


def _http_get(url, referer="", retry=RETRY, timeout=TIMEOUT):
    raw = _http_raw(url, referer=referer, retry=retry, timeout=timeout)
    return _decode(raw) if raw else ""


def _get_html_cached(url, ckey, ttl, referer=""):
    html = _cache_get(ckey, ttl)
    if html:
        return html
    html = _http_get(url, referer=referer)
    if html:
        _cache_set(ckey, html)
    return html or ""


_SCOPE = {"manhua": "comic", "xiaoshuo": "novel"}


def _u_list(tid, pg=1, tag="", order=""):
    if tag:
        base = _CUR_HOST + "/biaoqian/" + tag + "/"
        return base + ("page/%d/" % pg if pg > 1 else "")
    if order == "hot":
        scope = _SCOPE.get(tid, "category")
        key = "" if scope in ("comic", "novel") else tid
        if tid not in ("paihang", "biaoqian"):
            return "%s/api/list/fragment?scope=%s&key=%s&sort=hot&page=%d" % (
                _CUR_HOST, scope, _q(key), pg)
    if pg <= 1:
        return _CUR_HOST + "/" + tid + "/"
    return _CUR_HOST + "/" + tid + "/page/" + str(int(pg)) + "/"


def _u_search(q, pg=1):
    url = _CUR_HOST + "/search/?q=" + _q(q)
    if pg > 1:
        url += "&page=" + str(int(pg))
    return url


def _parse_cards(html, channel_hint=""):
    vods, seen = [], {}
    if not html:
        return vods
    starts = [m.start() for m in _RE_CARD.finditer(html)]
    total = len(starts)
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < total else len(html)
        block = html[st:end]
        cut = block.find("</a>")
        if cut > 0:
            block = block[:cut]
        hm = _RE_HREF.search(block)
        if not hm:
            continue
        channel, path = _split_path(hm.group(1))
        if not path:
            continue
        if channel not in _VALID and channel_hint:
            channel = channel_hint
        name = ""
        for rx in (_RE_TRACK_NAME, _RE_ALT, _RE_TITLE, _RE_PTITLE):
            m = rx.search(block)
            if m:
                name = _txt(m.group(1))
                if name:
                    break
        if not name:
            continue
        pic = _pick_pic(block)
        remarks = ""
        m = _RE_BADGE.search(block) or _RE_EPSFLAG.search(block)
        if m:
            remarks = _txt(m.group(1))
        vid = channel + "|" + path
        if vid in seen:
            continue
        seen[vid] = 1
        _pool_put(vid, name, pic, remarks)
        item = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": _pic_proxy_url(pic),
            "vod_remarks": remarks,
        }
        tag = _TAG.get(channel)
        if tag:
            item["vod_tag"] = tag
        vods.append(item)
    return vods


def _parse_max_page(html):
    mx = 1
    for m in _RE_PAGE.finditer(html or ""):
        try:
            mx = max(mx, int(m.group(1)))
        except Exception:
            pass
    for m in _RE_PAGES.finditer(html or ""):
        try:
            mx = max(mx, int(m.group(1)))
        except Exception:
            pass
    return mx


def _fallback_episode(channel, path):
    if channel == "manhua":
        name = "第1话"
    elif channel == "xiaoshuo":
        name = "正文"
    else:
        name = "1"
    return [{"ep": 1, "name": name, "chap": "1", "url": _abs_url(path + "1/")}]


def _parse_detail(html, vid, channel="", path=""):
    result = {"vid": vid, "name": "", "pic": "", "channel": channel,
              "path": path, "episodes": [], "content": "", "year": "",
              "type_name": _TYPE_NAME.get(channel, channel)}
    if not html:
        return result
    m = _RE_H1.search(html)
    if m:
        result["name"] = _txt(m.group(1))
    m = _RE_PIMG.search(html)
    if m:
        result["pic"] = _pick_pic(m.group(0))
    if not result["pic"]:
        head = html[:6000]
        idx = head.find("detail-poster")
        result["pic"] = _pick_pic(head[idx:idx + 1200] if idx > 0 else head)
    if not result["pic"]:
        m = _RE_OGIMG.search(html)
        if m:
            result["pic"] = _clean_pic(m.group(1))
    m = _RE_EPGRID.search(html)
    if m:
        for em in _RE_EP_A.finditer(m.group(1)):
            href = em.group(1)
            chap = _chap_id(href)
            try:
                epn = int(chap)
            except Exception:
                epn = 1
            result["episodes"].append({
                "ep": epn,
                "name": _txt(em.group(2)) or chap,
                "chap": chap,
                "url": _abs_url(href),
            })
    if not result["episodes"] and path:
        result["episodes"] = _fallback_episode(channel, path)
    m = _RE_OGDESC.search(html) or _RE_METADESC.search(html)
    if m:
        result["content"] = _txt(m.group(1))
    m = _RE_TIME.search(html)
    if m:
        result["year"] = m.group(1)
    return result


def _parse_play(html):
    if not html:
        return ""
    m = _RE_CURRENT.search(html) or _RE_ANYM3U8.search(html)
    if not m:
        return ""
    return m.group(1).replace("\\/", "/").replace("\\u0026", "&")


def _raw_img_url(tag):
    if not tag:
        return ""
    for attr in _PIC_ATTRS:
        m = re.search(attr + r'\s*=\s*"([^"]+)"', tag, re.I)
        if not m:
            continue
        u = str(m.group(1) or "").strip()
        if not u or u.lower().startswith("data:") or "base64," in u.lower():
            continue
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("http://"):
            u = "https://" + u[7:]
        return u
    return ""


def _parse_comic_pages(html):
    out, seen = [], {}
    for tag in _RE_COMIC_PAGE.findall(html or ""):
        u = _raw_img_url(tag)
        if not u or u in seen:
            continue
        seen[u] = 1
        out.append(_pic_proxy_url(u))
    return out


def _html_to_text(body):
    t = re.sub(r"<script[^>]*>.*?</script>", "", body or "", flags=re.S | re.I)
    t = re.sub(r"<style[^>]*>.*?</style>", "", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</p>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = (t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
           .replace("&#34;", '"').replace("&nbsp;", " ")
           .replace("&lt;", "<").replace("&gt;", ">"))
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _parse_novel_chapter(html):
    m = _RE_NOVEL_ART.search(html or "")
    body = m.group(1) if m else ""
    title = ""
    hm = _RE_NOVEL_H.search(body)
    if hm:
        title = _txt(hm.group(1))
        body = body[hm.end():]
    if not body:
        m = _RE_H1.search(html or "")
        if m:
            title = title or _txt(m.group(1))
        body = html or ""
    return title or "正文", _html_to_text(body)


def _pl_clean(s):
    return str(s or "").replace("$", " ").replace("#", " ").strip()


def _make_vod(did, d, pool, play_from, play_url, tag=""):
    vod = {
        "vod_id": did,
        "vod_name": d.get("name") or did,
        "vod_pic": _pic_proxy_url(d.get("pic") or ""),
        "type_name": d.get("type_name") or "",
        "vod_year": d.get("year") or "",
        "vod_remarks": pool.get("remarks") or "",
        "vod_content": d.get("content") or "",
        "vod_play_from": play_from,
        "vod_play_url": play_url,
    }
    if tag:
        vod["vod_tag"] = tag
    return vod


class Spider(BaseSpider):
    name = NAME
    site_url = HOST
    base_url = HOST
    searchable = 1
    quickSearch = 1
    filterable = 1

    def init(self, extend=""):
        global _CUR_HOST, PROXY_BASE, IMG_PROXY
        ext = (extend or "").strip().strip("/")
        if ext and "." in ext and ext != "py" and "=" not in ext:
            if "://" not in ext:
                ext = "https://" + ext
            _CUR_HOST = ext
            _CACHE.clear()
        for kv in (extend or "").split(","):
            if "=" not in kv:
                continue
            k, v = kv.split("=", 1)
            k, v = k.strip().lower(), v.strip()
            if k == "proxy" and v:
                PROXY_BASE = v.rstrip("/")
            elif k == "imgproxy":
                IMG_PROXY = 1 if v.lower() in ("1", "true", "on", "yes") else 0
            elif k == "host" and v:
                if "://" not in v:
                    v = "https://" + v
                _CUR_HOST = v
                _CACHE.clear()
        self.page_cache = {}
        self.page_index = {}
        self.page_keys = []
        self._src_cache = {}
        return "OK"

    def _ensure_page_cache(self):
        if not hasattr(self, "page_cache"):
            self.page_cache = {}
            self.page_index = {}
            self.page_keys = []
            self._src_cache = {}

    def _cache_page(self, key, items):
        self._ensure_page_cache()
        out = [x for x in (items or []) if isinstance(x, dict) and x.get("vod_id")]
        if not out:
            return
        self.page_cache[key] = out
        if key in self.page_keys:
            self.page_keys.remove(key)
        self.page_keys.append(key)
        for it in out:
            self.page_index[str(it["vod_id"])] = key
        while len(self.page_keys) > 30:
            old = self.page_keys.pop(0)
            self.page_cache.pop(old, None)

    def homeContent(self, filter=False):
        html = _get_html_cached(_u_list("duanju", 1), "home", _TTL_LIST)
        vods = _parse_cards(html, "duanju")
        self._cache_page(("home", "duanju", "", 1), vods)
        return {"class": list(DEFAULT_CLASSES), "filters": FILTERS, "list": vods}

    def homeVideoContent(self):
        html = _get_html_cached(_u_list("duanju", 1), "home", _TTL_LIST)
        vods = _parse_cards(html, "duanju")
        self._cache_page(("homev", "duanju", "", 1), vods)
        return {"list": vods}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        tid = str(tid or "duanju")
        if tid not in _VALID:
            tid = "duanju"
        ext = extend if isinstance(extend, dict) else {}
        tag = str(ext.get("videoTag") or "").strip()
        if not tag or tag == tid:
            tag = ""
        order = str(ext.get("order") or "").strip()
        html = _get_html_cached(_u_list(tid, pg, tag, order),
                                "cat:%s:%s:%s:%d" % (tid, tag, order, pg),
                                _TTL_LIST, referer=_CUR_HOST + "/" + tid + "/")
        vods = _parse_cards(html, tid)
        max_page = _parse_max_page(html)
        if pg > 1 and pg > max_page:
            vods = []
        self._cache_page(("cate", tid, str(extend or ""), pg), vods)
        return {
            "list": vods, "page": pg, "pagecount": max_page,
            "limit": len(vods) or 24, "total": max_page * 24,
            "parse": 0, "jx": 0,
        }

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        empty = {"list": [], "page": pg, "pagecount": 0, "limit": 0, "total": 0, "parse": 0, "jx": 0}
        key = str(key or "").strip()
        if not key:
            return empty
        html = _get_html_cached(_u_search(key, pg), "search:%s:%d" % (key, pg), _TTL_LIST)
        vods = _parse_cards(html)
        max_page = _parse_max_page(html)
        if pg > 1 and pg > max_page:
            vods = []
        self._cache_page(("search", str(key), "", pg), vods)
        return {
            "list": vods, "page": pg, "pagecount": max_page,
            "limit": len(vods), "total": max_page * len(vods),
            "parse": 0, "jx": 0,
        }

    def _page_of(self, vid):
        self._ensure_page_cache()
        key = self.page_index.get(str(vid))
        if key in self.page_cache:
            return list(self.page_cache[key])
        return []

    def _page_follow(self, vid):
        items = self._page_of(vid)
        if not items:
            return []
        idx = -1
        for i, x in enumerate(items):
            if str(x.get("vod_id")) == str(vid):
                idx = i
                break
        if idx < 0:
            return []
        out, seen = [], set()
        for it in items[idx:]:
            iid = str(it.get("vod_id") or "")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            out.append(it)
        return out

    def _split_sources(self, vod):
        fr = str((vod or {}).get("vod_play_from") or "").split("$$$")
        ur = str((vod or {}).get("vod_play_url") or "").split("$$$")
        while len(ur) < len(fr):
            ur.append("")
        sources = []
        for i, name in enumerate(fr):
            parts = []
            for p in (ur[i] or "").split("#"):
                if not p:
                    continue
                if "$" in p:
                    n, u = p.split("$", 1)
                else:
                    n, u = str(i + 1), p
                parts.append((_pl_clean(n), u))
            if parts:
                sources.append((_pl_clean(name) or NAME, parts))
        return sources

    def _load_src(self, iid):
        vod = self._load_detail(iid) or {}
        sources = self._split_sources(vod)
        self._ensure_page_cache()
        if _cache_get("detail:" + str(iid), _TTL_DETAIL) is None:
            return []
        self._src_cache[str(iid)] = sources
        return sources

    def _prefetch_src(self, items, keep_vid, limit=10):
        self._ensure_page_cache()
        unknown = []
        for it in items or []:
            iid = str(it.get("vod_id") or "")
            if not iid or iid == str(keep_vid) or iid in self._src_cache:
                continue
            if it.get("vod_tag") in ("image", "text"):
                continue
            unknown.append(iid)
            if len(unknown) >= limit:
                break
        if not unknown:
            return
        ex = None
        try:
            from concurrent.futures import ThreadPoolExecutor, wait
            ex = ThreadPoolExecutor(max_workers=min(4, len(unknown)))
            futs = [ex.submit(self._load_src, iid) for iid in unknown]
            wait(futs, timeout=8)
        except Exception:
            for iid in unknown[:4]:
                try:
                    self._load_src(iid)
                except Exception:
                    pass
        finally:
            if ex:
                try:
                    ex.shutdown(wait=False)
                except Exception:
                    pass

    def _item_parts(self, it, src_idx, current_sources, current_vid):
        iid = str(it.get("vod_id") or "")
        if not iid:
            return []
        name = _pl_clean(it.get("vod_name") or iid) or iid
        if iid == str(current_vid):
            sources = current_sources
        else:
            sources = self._src_cache.get(iid) or []
        eps = []
        if sources:
            if src_idx < len(sources) and sources[src_idx][1]:
                eps = sources[src_idx][1]
            else:
                eps = sources[0][1]
        if len(eps) > 1:
            out = []
            for i, (en, u) in enumerate(eps):
                label = _pl_clean("%s %s" % (name, en or ("%02d" % (i + 1))))
                out.append("%s$%s" % (label, u))
            return out
        if eps and (iid == str(current_vid) or not str(eps[0][1]).startswith("nid:")):
            return ["%s$%s" % (name, eps[0][1])]
        return ["%s$nid:%s" % (name, _q(iid))]

    def _apply_page_playlist(self, vid, vod, items):
        sources = self._split_sources(vod)
        self._ensure_page_cache()
        self._src_cache[str(vid)] = sources
        if not items:
            return vod
        plist, seen = [], set()
        for it in items:
            iid = str(it.get("vod_id") or "")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            plist.append(it)
        if not plist:
            return vod
        self._prefetch_src(plist, vid, 10)
        if not sources:
            sources = [(NAME, [("播放", "nid:%s" % _q(vid))])]
        play_from, play_urls = [], []
        for i, (sname, _eps) in enumerate(sources):
            parts = []
            for it in plist:
                if str(it.get("vod_id")) != str(vid) and it.get("vod_tag") in ("image", "text"):
                    continue
                parts.extend(self._item_parts(it, i, sources, vid))
            if not parts:
                continue
            play_from.append(sname or NAME)
            play_urls.append("#".join(parts))
        if not play_from:
            return vod
        vod = dict(vod)
        vod["vod_play_from"] = "$$$".join(play_from)
        vod["vod_play_url"] = "$$$".join(play_urls)
        return vod

    def _current_play_url(self, vid, flag=""):
        vod = self._load_detail(vid) or {}
        sources = self._split_sources(vod)
        self._ensure_page_cache()
        self._src_cache[str(vid)] = sources
        if not sources:
            return ""
        picked = None
        for name, eps in sources:
            if str(name) == str(flag) and eps:
                picked = eps
                break
        if not picked:
            picked = sources[0][1]
        return picked[0][1] if picked else ""

    def _load_detail(self, did):
        did = str(did or "").strip()
        if not did:
            return None
        channel, path = "", ""
        if "|" in did:
            channel, path = did.split("|", 1)
        pool = _ITEM_POOL.get(did) or {}
        d = _cache_get("detail:" + did, _TTL_DETAIL)
        if d is None:
            html = _http_get(_abs_url(path), referer=_CUR_HOST + "/" + (channel or "") + "/")
            d = _parse_detail(html, did, channel, path)
            if d and (d.get("name") or d.get("pic")):
                _cache_set("detail:" + did, d)
        if (not d) or (not d.get("name") and not d.get("pic")):
            if not pool:
                return None
            d = {"name": pool.get("name") or "", "pic": pool.get("pic") or "",
                 "channel": channel, "path": path, "content": "", "year": "",
                 "type_name": _TYPE_NAME.get(channel, channel),
                 "episodes": _fallback_episode(channel, path) if path else []}
        if not d.get("pic"):
            d["pic"] = pool.get("pic") or ""
        if not d.get("name"):
            d["name"] = pool.get("name") or did
        if not d.get("episodes") and path:
            d["episodes"] = _fallback_episode(channel, path)
        if not d.get("episodes"):
            return None
        work = _work_id(path)
        if channel == "manhua":
            play = "#".join("%s$img_%s_%s" % (
                _pl_clean(ep.get("name") or ("第%d话" % ep["ep"])),
                work, ep.get("chap") or ep["ep"]) for ep in d["episodes"])
            return _make_vod(did, d, pool, "漫画", play, "image")
        if channel == "xiaoshuo":
            play = "#".join("%s$novel_%s_%s" % (
                _pl_clean(ep.get("name") or "正文"),
                work, ep.get("chap") or ep["ep"]) for ep in d["episodes"])
            return _make_vod(did, d, pool, "小说", play, "text")
        multi = len(d["episodes"]) > 1
        play = "#".join("%s$%s" % (
            ("%02d" % ep["ep"]) if multi else _pl_clean(d.get("name") or did),
            ep["url"]) for ep in d["episodes"])
        return _make_vod(did, d, pool, NAME, play)

    def detailContent(self, ids):
        try:
            did = ids[0] if isinstance(ids, list) else ids
        except Exception:
            did = None
        did = str(did or "").strip()
        vod = self._load_detail(did)
        if not vod:
            return {"list": [], "parse": 0, "jx": 0}
        if vod.get("vod_tag") in ("image", "text"):
            return {"list": [vod], "parse": 0, "jx": 0}
        cached = self._page_follow(did)
        if cached:
            vod = self._apply_page_playlist(did, vod, cached)
        return {"list": [vod], "parse": 0, "jx": 0}

    def playerContent(self, flag="", id="", vipFlags=None):
        try:
            if not id and isinstance(flag, str) and "$" in flag:
                id = flag
        except Exception:
            pass
        url = str(id or "")
        if "$" in url:
            url = url.split("$")[-1]
        if url.startswith("nid:"):
            vid = unquote(str(url[4:]))
            url = self._current_play_url(vid, flag)
            if "$" in url:
                url = url.split("$")[-1]
        if not url:
            return {"parse": 0, "url": "", "header": "", "jx": 0}
        if url.startswith(("novel://", "pics://")):
            return {"parse": 0, "url": url, "header": ""}
        m = _RE_PLAY_ID.match(url)
        if m:
            kind, work, chap = m.group(1), m.group(2), m.group(3)
            if kind == "img":
                return self._play_comic(work, chap)
            return self._play_novel(work, chap, flag)
        header = json.dumps({"User-Agent": UA, "Referer": _CUR_HOST + "/"})
        if ".m3u8" in url or ".mp4" in url:
            return {"parse": 0, "url": url, "jx": 0, "header": header}
        if url.startswith("http"):
            m3u8 = _cache_get("play:" + url, _TTL_PLAY)
            if not m3u8:
                m3u8 = _parse_play(_http_get(url, retry=2))
                if m3u8:
                    _cache_set("play:" + url, m3u8)
            if m3u8:
                return {"parse": 0, "url": m3u8, "jx": 0, "header": header}
        return {"parse": 1, "url": url, "jx": 0}

    def _play_comic(self, work, chap):
        html = _http_get(_CUR_HOST + "/manhua/%s/%s/" % (work, chap),
                         referer=_CUR_HOST + "/manhua/%s/" % work, retry=2)
        imgs = _parse_comic_pages(html)
        if not imgs:
            return {"parse": 0, "url": "", "header": ""}
        return {"parse": 0, "url": "pics://" + "&&".join(imgs), "header": ""}

    def _play_novel(self, work, chap, flag=""):
        html = _http_get(_CUR_HOST + "/xiaoshuo/%s/%s/" % (work, chap),
                         referer=_CUR_HOST + "/xiaoshuo/%s/" % work, retry=2)
        title, text = _parse_novel_chapter(html)
        if not text:
            return {"parse": 0, "url": "", "header": ""}
        payload = json.dumps({"title": str(flag or title or "正文"), "content": text},
                             ensure_ascii=False)
        return {"parse": 0, "url": "novel://" + payload, "header": ""}

    def localProxy(self, param):
        try:
            if isinstance(param, dict):
                d = param
            else:
                s = str(param or "").strip().lstrip("/")
                i = s.find("://")
                if i >= 0:
                    s = s[i + 3:]
                d = dict(parse_qsl(s))
            url = d.get("url") or ""
            try:
                url = unquote(url.strip())
            except Exception:
                pass
            if not url:
                return [500, "text/plain", b"empty url"]
            referer = str(d.get("referer") or (_CUR_HOST + "/"))
            cached = _PIC_CACHE.get(url)
            if cached is None:
                raw = _http_raw(url, referer=referer)
                if not raw:
                    return [502, "text/plain", b"pic fetch error"]
                cached = _aes_dec_image(raw)
                if len(_PIC_CACHE) > _PIC_CACHE_MAX:
                    _PIC_CACHE.clear()
                _PIC_CACHE[url] = cached
            ctype = "image/jpeg"
            low = url.split("?")[0].lower()
            if low.endswith(".png"):
                ctype = "image/png"
            elif low.endswith(".webp"):
                ctype = "image/webp"
            elif low.endswith(".gif"):
                ctype = "image/gif"
            return [200, ctype, cached]
        except Exception as e:
            return [502, "text/plain", ("Proxy Error: %s" % e).encode("utf-8")]

    def isVideoFormat(self, url):
        u = str(url or "")
        if u.startswith(("novel://", "pics://")):
            return 0
        path = u.split("?")[0].lower()
        for ext in (".m3u8", ".mp4", ".flv", ".avi", ".mkv", ".ts", ".mov"):
            if path.endswith(ext):
                return 1
        return 0

    def manualVideoCheck(self):
        return 0

    def getDependence(self):
        return []

    def destroy(self):
        try:
            _CACHE.clear()
        except Exception:
            pass


_sp = None


def _get():
    global _sp
    if _sp is None:
        _sp = Spider()
    return _sp


def init(extend=""):
    return _get().init(extend)


def homeContent(filter=False):
    return _get().homeContent(filter)


def homeVideoContent():
    return _get().homeVideoContent()


def categoryContent(tid, pg, filter=False, extend=None):
    return _get().categoryContent(tid, pg, filter, extend)


def detailContent(ids):
    return _get().detailContent(ids)


def searchContent(key, quick=False, pg="1"):
    return _get().searchContent(key, quick, pg)


def playerContent(flag="", id="", vipFlags=None):
    return _get().playerContent(flag, id, vipFlags)


def localProxy(param):
    return _get().localProxy(param)


def getName():
    return NAME


def isVideoFormat(url):
    return _get().isVideoFormat(url)


def manualVideoCheck():
    return _get().manualVideoCheck()


def destroy():
    return _get().destroy()
