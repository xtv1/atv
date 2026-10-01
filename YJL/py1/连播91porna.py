# coding=utf-8
"""91porna TVBox 爬虫

分类从首页导航现取，筛选从导航子项 / 列表页筛选条现取。
type_id 由分类路径 base64 生成（不含 "/"，可逆），见 _tid / _path。
播放地址从 embed 页现取，数字 video_key 跳过详情页。
"""
import base64
import hashlib
import html as _html
import json
import os
import re
import sys
import time
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except Exception:
    AES = None

    def unpad(data, block_size):
        return data

sys.path.append('..')
from base.spider import Spider as BaseSpider

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_UESC_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _cjk(text):
    return len(_CJK_RE.findall(text or ""))


def _fix_text(text):
    """修标题乱码：\\uXXXX 转义 + HTML 实体 + UTF-8 被按单字节解码的错位。"""
    if text is None:
        return ""
    s = str(text)
    if "\\u" in s:
        try:
            s = _UESC_RE.sub(lambda m: chr(int(m.group(1), 16)), s)
        except Exception:
            pass
    s = _html.unescape(s)
    if "\ufffd" in s or not _cjk(s):
        for enc in ("latin-1", "cp1252"):
            try:
                cand = s.encode(enc, "ignore").decode("utf-8", "ignore")
            except Exception:
                continue
            if _cjk(cand) > _cjk(s):
                s = cand
                break
    return s

# 启动用的入口域名（镜像会变，运行时会从 canonical / og:url 自动校准）。
# 这里只放站点入口，不放播放域名；播放地址全部从页面现取。
_ENTRY_HOSTS = [
    "https://prime.yhneuiqk.cc",
    "https://2033.yhneuiqk.cc",
    "https://91porna.com",
]
_ENTRY_GATES = ["https://91porna85.com", "https://91porna84.com", "https://91porna83.com"]

# 列表卡片容器：模板站常见的几种结构，命中哪个用哪个（不是分类 ID）
_CARD_SELECTORS = (
    "div.video-item",
    "article.video-card",
    "article.post-item",
    "li.ms-d-works-grid__item",
    "ul.ms-grid > li",
    "ul.grid > li",
)

# 内容详情链接的结构特征（不是分类 ID、不是域名）
_CONTENT_RE = re.compile(
    r"/comic/index/(?:detail|avdetail)\b"
    r"|/melonshort/(?:video|detail)/[\w-]+"
    r"|/moviesets(?:/[^/?#]+)*"
    r"|/heiliao-chigua/[\w-]+"
    r"|/novels/[^/?#/]+$",
    re.I,
)

# 封面可能落在的懒加载属性（黑料吃瓜把封面挂在 div[data-src]，没有 img 标签）
_IMG_ATTRS = (
    "data-src", "data-original", "data-lazy-src", "data-echo",
    "data-bg", "data-cover", "data-image", "data-img", "data-url", "src",
)
_LAZY_ATTRS = tuple(a for a in _IMG_ATTRS if a != "src")
_LAZY_SEL = ",".join("[" + a + "]" for a in _LAZY_ATTRS)
_BG_RE = re.compile(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", re.I)

_PACK_HEAD = "eval(function(p,a,c,k,e,"
_PACK = re.compile(
    r"eval\(function\(p,a,c,k,e,(?:d|r)\)\{[\s\S]+?\}\('\s*([\s\S]*?)\s*',\s*(\d+),\s*(\d+),\s*'([\s\S]*?)'\.split\('\|'\)\s*,\s*0\s*,\s*\{\}\)\)"
)
_VIDEO_RE = re.compile(r'https?://[^"\'\s\\<>]+?\.(?:m3u8|mp4)(?:\?[^"\'\s\\<>]*)?', re.I)
_DUR_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_SEARCH_RE = re.compile(r"search", re.I)
# 「91品牌」= 友情链接目录页，不属于内容分类
_LINKS_RE = re.compile(r"/comic/index/links", re.I)
_FOOTER_PATH_RE = re.compile(r"/comic/index/(?:links|hotsearch)|/novels/(?:new|hot|rank|all)?$", re.I)
# 页脚文案，不能进筛选、不能进列表
_SKIP_FILTER = {
    "使用条款", "使用协议", "隐私政策", "常见问题", "联络我们",
    "申请移除", "热门搜索", "91小说", "dmca", "2257", "DMCA",
}
# /novels/{slug} 里属于分类入口而非作品的 slug
_NOVEL_RESERVED = {"new", "hot", "rank", "all"}
_IMG_CACHE = {}


def _soup(html):
    return BeautifulSoup(html or "", "html.parser")


def _unpack(text):
    if not text or _PACK_HEAD not in text:
        return text or ""
    i = text.find(_PACK_HEAD)
    m = _PACK.search(text[i:i + 24000])
    if not m:
        m = _PACK.search(text[i:])
    if not m:
        return text or ""
    p, a, c, k = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split("|")
    digits = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def _base(n):
        if n == 0:
            return "0"
        out = ""
        while n:
            n, r = divmod(n, a)
            out = digits[r] + out
        return out

    for i in range(c - 1, -1, -1):
        key = _base(i)
        val = k[i] if i < len(k) and k[i] else key
        p = re.sub(r"\b" + re.escape(key) + r"\b", val, p)
    return p


class Spider(BaseSpider):
    def init(self, extend=""):
        cfg = {}
        if isinstance(extend, str) and extend.strip().startswith("{"):
            try:
                cfg = json.loads(extend)
            except Exception:
                cfg = {}
        elif isinstance(extend, dict):
            cfg = extend
        self.proxies = cfg.get("proxies") or {}
        self.slug = "91porna"
        self._cache = {}
        self._page = []
        self._refreshed_at = 0
        self.host = (cfg.get("host") or _ENTRY_HOSTS[0]).rstrip("/")
        self.headers = {
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        if self.proxies:
            self.session.proxies.update(self.proxies)
        self._proxy = None

    def getName(self):
        return "91porna"

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return any(x in u for x in (".m3u8", ".mp4", ".ts"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        _IMG_CACHE.clear()
        try:
            self.session.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ 基础网络

    def _abs(self, path):
        if not path:
            return self.host + "/"
        p = str(path)
        if p.startswith("//"):
            return urlparse(self.host).scheme + ":" + p
        if p.startswith("http"):
            return p
        return urljoin(self.host + "/", p.lstrip("/"))

    def _paged(self, url, pg):
        pg = int(pg or 1)
        p = urlparse(url)
        path = p.path.rstrip("/") or "/"
        if re.search(r"/melonshort(?:/cat/[\w-]+)?$", path):
            if pg > 1:
                path = path + "/" + str(pg)
            return urlunparse(p._replace(path=path, query=""))
        qs = parse_qs(p.query)
        if pg > 1:
            qs["page"] = [str(pg)]
        else:
            qs.pop("page", None)
        return urlunparse(p._replace(query=urlencode(qs, doseq=True)))

    def _swap(self, url):
        p = urlparse(url)
        h = urlparse(self.host)
        return urlunparse(p._replace(scheme=h.scheme, netloc=h.netloc))

    def _probe(self, host):
        """探活：首页能解析出内容卡片即视为可用。"""
        try:
            r = self.session.get(host.rstrip("/") + "/", timeout=8)
            if r.status_code != 200:
                return False
            t = r.text or ""
            return ("video-item" in t) or ("video-card" in t) or ("post-item" in t) or bool(_CONTENT_RE.search(t))
        except Exception:
            return False

    def _rehost(self):
        for h in _ENTRY_HOSTS:
            if h != self.host and self._probe(h):
                self._use(h)
                return h
        for e in _ENTRY_GATES:
            try:
                r = self.session.get(e.rstrip("/") + "/", timeout=8)
            except Exception:
                continue
            cands = []
            for m in re.finditer(r'https?://([a-z0-9.-]+\.[a-z]{2,})', r.text or "", re.I):
                h = "https://" + m.group(1).lower()
                if h not in cands and h != self.host:
                    cands.append(h)
            for h in cands[:12]:
                if self._probe(h):
                    self._use(h)
                    return h
        return None

    def _use(self, host):
        self.host = host.rstrip("/")
        self.headers["Referer"] = self.host + "/"
        try:
            self.session.headers["Referer"] = self.host + "/"
        except Exception:
            pass

    def _learn(self, text):
        """从页面 canonical / og:url 校准当前可用域名，只改 host，不再二次探活。"""
        for pat in (
            r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](https?://[^"\']+)',
            r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\'](https?://[^"\']+)',
        ):
            m = re.search(pat, text or "", re.I)
            if not m:
                continue
            p = urlparse(m.group(1))
            if p.netloc and p.netloc != urlparse(self.host).netloc:
                if "yhneuiqk" in urlparse(self.host).netloc and "91porna.com" in p.netloc:
                    return
                self._use("%s://%s" % (p.scheme or "https", p.netloc))
            return

    def _text_of(self, r):
        raw = r.content or b""
        charset = (r.encoding or "").strip()
        if not charset or charset.lower() in ("iso-8859-1", "latin-1", "ascii"):
            m = re.search(rb'charset=["\']?\s*([\w-]+)', raw[:2048], re.I)
            charset = m.group(1).decode("ascii", "ignore") if m else "utf-8"
        try:
            return raw.decode(charset, "replace")
        except Exception:
            return raw.decode("utf-8", "replace")

    def _get(self, url, ref=None, min_len=1500, rehost=True):
        if not url:
            return None
        hdrs = dict(self.headers)
        if ref:
            hdrs["Referer"] = ref
        cur = url
        tries = 3 if rehost else 1
        for i in range(tries):
            try:
                r = self.session.get(cur, headers=hdrs, timeout=8)
                if r.status_code == 200:
                    text = self._text_of(r)
                    if len(text or "") >= min_len:
                        return text
            except Exception:
                pass
            if not rehost:
                break
            nxt = self._rehost()
            if not nxt:
                break
            cur = self._swap(cur)
        return None

    # ------------------------------------------------------------------ type_id 编解码

    def _tid(self, path):
        """分类路径 -> 短码（不含 "/"，可逆）。"""
        if not path:
            return ""
        return "t" + base64.urlsafe_b64encode(str(path).encode("utf-8")).decode("ascii").rstrip("=")

    def _path(self, tid):
        if not tid:
            return ""
        tid = str(tid)
        if tid.startswith("t"):
            s = tid[1:]
            s += "=" * (-len(s) % 4)
            try:
                return base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8")
            except Exception:
                return ""
        return tid

    def _norm(self, path):
        """归一化路径用于比较（去掉 page 参数）。"""
        if not path:
            return ""
        if not str(path).startswith("http"):
            path = self._abs(path)
        u = urlparse(str(path))
        q = parse_qs(u.query)
        q.pop("page", None)
        flat = {k: v[0] for k, v in sorted(q.items())}
        return u.path + ("?" + urlencode(flat) if flat else "")

    def _in_chrome(self, el):
        p = el
        while p is not None and getattr(p, "name", None) not in (None, "body", "[document]"):
            cls = " ".join(p.get("class") or []) if hasattr(p, "get") else ""
            ident = (p.get("id") or "") if hasattr(p, "get") else ""
            if getattr(p, "name", None) == "footer" or "app-footer" in cls or ident == "app-footer":
                return True
            p = getattr(p, "parent", None)
        return False

    def _ok_filter(self, name, path):
        n = (name or "").strip()
        if not n or n in _SKIP_FILTER:
            return False
        href = path or ""
        p = self._path_of(href) if href else ""
        if _LINKS_RE.search(href) or _FOOTER_PATH_RE.search(href) or _FOOTER_PATH_RE.search(p):
            return False
        return True

    def _is_hl_list(self, path):
        p = unquote(self._path_of(path) or "")
        if re.search(r"/heiliao-chigua/\d+", p):
            return False
        return ("黑料吃瓜" in p) or ("heiliao-chigua" in p)

    # ------------------------------------------------------------------ 缓存

    def _cache_paths(self):
        out = [os.path.join("/sdcard/tvbox", "spider_%s.json" % self.slug)]
        try:
            out.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "spider_%s.json" % self.slug))
        except Exception:
            pass
        return out

    def _cache_key(self):
        return "spider_%s" % self.slug

    def _load(self):
        if self._cache:
            return self._cache
        blob = None
        try:
            blob = self.getCache(self._cache_key())
        except Exception:
            blob = None
        if isinstance(blob, dict):
            self._cache = blob
            return self._cache
        if not blob:
            for p in self._cache_paths():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        blob = f.read()
                    if blob:
                        break
                except Exception:
                    continue
        if blob:
            try:
                self._cache = json.loads(blob) if isinstance(blob, str) else {}
            except Exception:
                self._cache = {}
        return self._cache

    def _save(self):
        self._cache["host"] = self.host
        self._cache["saved"] = int(time.time())
        blob = json.dumps(self._cache, ensure_ascii=False)
        try:
            self.setCache(self._cache_key(), blob)
        except Exception:
            pass
        for p in self._cache_paths():
            try:
                d = os.path.dirname(p)
                if d and not os.path.isdir(d):
                    os.makedirs(d)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(blob)
            except Exception:
                continue

    # ------------------------------------------------------------------ 形态判定

    def _refresh(self, cache):
        html = self._get(self._abs("/"))
        if not html:
            return False
        self._learn(html)
        cats = self._parse_nav(html)
        if not cats:
            return False
        cache["nav"] = cats
        cache["classes"] = self._build_classes(cats)
        learned = cache.get("filters") or {}
        nf = self._build_filters(cats)
        for k, v in learned.items():
            nf.setdefault(k, v)
        cache["filters"] = nf
        cache["list"] = self._items(_soup(html))
        return True

    def _parse_nav(self, html):
        soup = _soup(html)
        cats = []
        nodes = soup.select("li.video-nav-dropdown")
        if not nodes:
            nodes = soup.select("header nav li, .video-menu-item")
        for li in nodes:
            a = li.select_one(":scope > a[href]") or li.select_one("a[href]")
            if not a or not a.get("href"):
                continue
            name = a.get_text(" ", strip=True)
            if not name:
                continue
            if _LINKS_RE.search(a.get("href") or ""):
                continue
            subs = []
            for s in li.select(".video-sub-menu a[href]"):
                sp, sn = s.get("href"), s.get_text(" ", strip=True)
                if sp and sn and self._ok_filter(sn, sp):
                    subs.append({"name": sn, "path": sp, "key": s.get("data-navigation_key") or ""})
            cats.append({"name": name, "path": a.get("href"), "key": a.get("data-navigation_key") or "", "subs": subs})
        for a in soup.select('a[href*="?"]'):
            href = a.get("href") or ""
            if not _SEARCH_RE.search(urlparse(href).path or ""):
                continue
            q = parse_qs(urlparse(href).query)
            if len(q) == 1:
                self._cache["search"] = {"path": urlparse(href).path, "param": list(q.keys())[0]}
                break
        return cats

    # ------------------------------------------------------------------ 分类 / 筛选构建

    def _build_classes(self, cats):
        out, seen = [], set()
        for c in cats:
            if not c.get("path") or _LINKS_RE.search(c["path"]):
                continue
            tid = self._tid(c["path"])
            if tid in seen:
                continue
            seen.add(tid)
            out.append({"type_name": c["name"], "type_id": tid})
        return out

    def _rows_for(self, opts, default_path):
        vals, seen = [], set()
        if default_path:
            vals.append({"n": "全部", "v": self._tid(default_path)})
            seen.add(self._norm(default_path))
        for o in opts:
            p = o.get("path")
            n = o.get("name") or ""
            if not p or self._norm(p) in seen:
                continue
            if not self._ok_filter(n, p):
                continue
            seen.add(self._norm(p))
            vals.append({"n": n or p, "v": self._tid(p)})
        if not vals:
            return []
        key = "videoTag"
        keys = {o.get("key") or "" for o in opts}
        if len(keys) == 1 and list(keys)[0]:
            key = list(keys)[0]
        rows = []
        for i in range(0, len(vals), 8):
            rows.append({"key": key, "name": "分类", "value": vals[i:i + 8]})
        return rows

    def _build_filters(self, cats):
        out = {}
        for c in cats:
            if not c.get("subs"):
                continue
            rows = self._rows_for(c["subs"], c["path"])
            if rows:
                out[self._tid(c["path"])] = rows
        return out

    def _refresh_filters(self, tid, path, soup, cats):
        """进入列表页时，顺手把该分类的筛选条落盘（导航子项 + 页面 tab）。"""
        main_path, nav_subs = path, []
        for c in cats:
            if self._norm(c["path"]) == self._norm(path) or any(
                self._norm(s["path"]) == self._norm(path) for s in c.get("subs") or []
            ):
                main_path, nav_subs = c["path"], c.get("subs") or []
                break
        tab_opts = []
        for box in soup.select("ul.dx-line-tabs, .dx-tabs, nav[class*=cate], [class*=filter]"):
            if self._in_chrome(box):
                continue
            for a in box.select("a[href]"):
                p, n = a.get("href"), a.get_text(" ", strip=True)
                if p and n and self._ok_filter(n, p):
                    tab_opts.append({"name": n, "path": p, "key": ""})
        rows = self._rows_for(nav_subs + tab_opts, main_path)
        if rows:
            self._cache.setdefault("filters", {})[tid] = rows

    # ------------------------------------------------------------------ 列表解析

    def _first_video(self, text):
        """取页面里的视频直链。同一地址常同时以裸链和带 auth_key 的完整链出现，
        裸链会被 403，所以优先返回带 auth_key / 带参数的完整地址。"""
        t = (text or "").replace("\\/", "/")
        cands = []
        for m in _VIDEO_RE.finditer(t):
            u = m.group(0).split("\\")[0].rstrip("\"'").replace("&amp;", "&")
            if u and u not in cands:
                cands.append(u)
        for m in re.finditer(r'data-url=["\'](https?://[^"\']+)["\']', t, re.I):
            u = m.group(1).replace("&amp;", "&")
            if u.startswith("{{"):
                continue
            if any(x in u for x in (".m3u8", ".mp4", "yd-hls", "/videos")) and u not in cands:
                cands.append(u)
        if not cands:
            return ""
        for u in cands:
            if "auth_key" in u:
                return u
        for u in cands:
            if "?" in u:
                return u
        return cands[0]

    def _looks_content(self, url):
        u = url or ""
        if not _CONTENT_RE.search(u):
            return False
        p = self._path_of(u)
        if p in ("/novels", "/novels/new", "/novels/hot", "/novels/rank", "/novels/all"):
            return False
        parts = [x for x in p.split("/") if x]
        if parts and parts[0] == "novels" and parts[-1] in _NOVEL_RESERVED:
            return False
        if "/comic/index/links" in p:
            return False
        return True

    def _pick_img(self, card):
        """封面兜底：img 懒加载属性 / srcset / video poster / 任意元素懒加载属性 / 内联 background-image。"""
        for tag in card.select("img, source, video"):
            for attr in _IMG_ATTRS:
                v = tag.get(attr)
                if v:
                    return v
            ss = tag.get("srcset") or tag.get("data-srcset") or ""
            if ss:
                first = ss.split(",")[0].strip().split(" ")[0]
                if first:
                    return first
        for tag in card.select(_LAZY_SEL):
            for attr in _LAZY_ATTRS:
                v = tag.get(attr)
                if v:
                    return v
        for el in card.select("[style]"):
            m = _BG_RE.search(el.get("style") or "")
            if m:
                return m.group(1)
        return ""

    def _card_fields(self, card):
        a = None
        if card.name == "a" and self._looks_content(self._abs(card.get("href"))):
            a = card
        if not a:
            for cand in card.select("a[href]"):
                if self._looks_content(self._abs(cand.get("href"))):
                    a = cand
                    break
        if not a:
            p = getattr(card, "parent", None)
            while p is not None and getattr(p, "name", None) not in (None, "body", "[document]"):
                if p.name == "a" and self._looks_content(self._abs(p.get("href"))):
                    a = p
                    break
                p = getattr(p, "parent", None)
        if not a:
            return None
        if card.select_one(".post-ad-poster"):
            return None
        vod_id = self._abs(a.get("href"))
        img = card.select_one("img")
        title = (a.get("title") or "").strip()
        if not title and img:
            title = (img.get("alt") or img.get("title") or "").strip()
        if not title:
            n = card.select_one(".ms-card__title, .title, [class*=title], h1, h2, h3, [class*=line-clamp]")
            title = n.get_text(" ", strip=True) if n else ""
        if not title:
            t = card.select_one("[title], [aria-label], [data-title]")
            if t:
                title = (t.get("title") or t.get("aria-label") or t.get("data-title") or "").strip()
        if not title or len(title) < 2:
            title = a.get_text(" ", strip=True)[:60]
        title = _fix_text(re.sub(r"\s+", " ", title).strip())
        if len(title) < 2:
            return None
        if title in _SKIP_FILTER:
            return None
        pic = self._pick_img(card)
        if "poster_loading" in pic:
            pic = ""
        remarks = ""
        m = _DUR_RE.search(card.get_text(" ", strip=True))
        if m:
            remarks = m.group(0)
        else:
            meta = card.select_one(".ms-card__meta")
            if meta:
                remarks = meta.get_text(" ", strip=True)
        out = {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": self._img(pic),
            "vod_remarks": _fix_text(remarks),
            "style": {"type": "rect", "ratio": 1.33},
        }
        if self._is_folder(vod_id):
            out["vod_tag"] = "folder"
        elif self._is_novel(vod_id):
            out["vod_tag"] = "text"
        return out

    def _items(self, soup):
        best = []
        for sel in _CARD_SELECTORS:
            try:
                cards = soup.select(sel)
            except Exception:
                continue
            out, seen = [], set()
            for card in cards:
                if self._in_chrome(card):
                    continue
                f = self._card_fields(card)
                if not f or f["vod_id"] in seen:
                    continue
                seen.add(f["vod_id"])
                out.append(f)
            if len(out) > len(best):
                best = out
        return best

    def _pagecount(self, soup, cur, html="", nitems=0):
        mx = 0
        for v in re.findall(r'[?&]page=(\d+)', html or ""):
            mx = max(mx, int(v))
        rel = soup.select_one('link[rel="next"], a[rel="next"]')
        if rel:
            href = rel.get("href") or ""
            q = parse_qs(urlparse(href).query)
            for v in q.get("page", []):
                if str(v).isdigit():
                    mx = max(mx, int(v))
            mx = max(mx, cur + 1)
        if nitems >= 8:
            mx = max(mx, cur + 1)
        if mx:
            return max(mx, cur)
        return 9999 if cur == 1 else cur

    # ------------------------------------------------------------------ 类型识别 / folder 协议 / 连播

    def _path_of(self, url):
        return urlparse(self._abs(url)).path.rstrip("/") or "/"

    def _is_set_index(self, url):
        p = self._path_of(url)
        if p == "/moviesets":
            return True
        parts = [x for x in p.split("/") if x]
        return len(parts) == 2 and parts[0] == "moviesets" and parts[1] in ("rank", "category", "people", "brand")

    def _is_set_leaf(self, url):
        p = self._path_of(url)
        parts = [x for x in p.split("/") if x]
        return bool(parts) and parts[0] == "moviesets" and not self._is_set_index(url)

    def _is_folder(self, url):
        return self._is_set_index(url) or self._is_set_leaf(url)

    def _is_novel(self, url):
        p = self._path_of(url)
        if not p.startswith("/novels/"):
            return False
        parts = [x for x in p.split("/") if x]
        return len(parts) == 2 and parts[1] not in _NOVEL_RESERVED

    def _clean(self, text):
        return _fix_text(re.sub(r"[$#]", " ", str(text or "")).strip())

    def _page_title(self, html, fallback=""):
        title = ""
        if html:
            m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.I)
            if not m:
                m = re.search(r'<title>([^<]+)', html, re.I)
            if m:
                title = _html.unescape(m.group(1))
        title = re.sub(r"\s*[-|·]\s*91porn.*$", "", title, flags=re.I).strip()
        title = re.sub(r"\s*[-–]\s*在线观看\s*$", "", title).strip()
        if not title and fallback and not str(fallback).startswith("http"):
            title = fallback
        return self._clean(title)

    def _remember(self, items):
        """整页写入缓存，供连播拼选集使用。"""
        self._page = list(items or [])
        try:
            self._cache["page_items"] = self._page
            self._save()
        except Exception:
            pass

    def _page_items(self):
        return list(self._page) or list(self._cache.get("page_items") or [])

    def _with_playlist(self, vid, title, lines):
        """点中的放第一，同页其余接在后面；线路名原样保留。"""
        extra, seen = [], {vid}
        for it in self._page_items():
            iid = it.get("vod_id")
            if not iid or iid in seen:
                continue
            if self._is_folder(iid) or self._is_novel(iid):
                continue
            seen.add(iid)
            extra.append(it)
            if len(extra) >= 20:
                break
        out = []
        for name, eps in lines:
            segs = []
            for i, (_en, eu) in enumerate(eps):
                tag = self._clean(title)
                if len(eps) > 1:
                    tag = "%s %02d" % (tag, i + 1)
                segs.append("%s$%s" % (tag, eu))
            for it in extra:
                segs.append("%s$nid:%s" % (self._clean(it.get("vod_name")), quote(it.get("vod_id") or "", safe="")))
            out.append((name, "#".join(segs)))
        return out

    def _play_novel(self, token):
        """novel_<slug>_1 -> 小说正文"""
        parts = str(token).split("_")
        slug = parts[1] if len(parts) > 1 else ""
        html = self._get(self._abs("/novels/" + slug))
        soup = _soup(html or "")
        art = soup.select_one("article")
        paras = [p.get_text(" ", strip=True) for p in art.select("p")] if art else []
        content = "\n".join([p for p in paras if p])
        title = self._page_title(html, slug)
        return {
            "parse": 0,
            "url": "novel://" + json.dumps({"title": title, "content": content}, ensure_ascii=False),
            "header": "",
        }

    # ------------------------------------------------------------------ 入口接口

    def homeContent(self, filter):
        cache = self._load()
        now = time.time()
        if not (self._refreshed_at and now - self._refreshed_at < 300):
            try:
                self._refresh(cache)
            except Exception:
                pass
            self._refreshed_at = now
            self._save()
        self._page = cache.get("list") or []
        return {
            "class": cache.get("classes") or [],
            "filters": cache.get("filters") or {},
            "list": self._page,
        }

    def homeVideoContent(self):
        cache = self._load()
        if not cache.get("list"):
            html = self._get(self._abs("/"))
            if html:
                cache["list"] = self._items(_soup(html))
                self._save()
        self._page = cache.get("list") or []
        return {"list": self._page}

    def _extend_path(self, extend):
        if not isinstance(extend, dict):
            return ""
        for v in extend.values():
            if not isinstance(v, str) or not v:
                continue
            p = self._path(v)
            if p.startswith("/") or p.startswith("http"):
                return p
            if v.startswith("/") or v.startswith("http"):
                return v
        return ""

    def _resolve(self, tid, extend):
        path = self._path(tid)
        if self._is_set_leaf(path) or re.search(r"/heiliao-chigua/\d+", path or ""):
            return path
        ext = self._extend_path(extend)
        return ext or path

    def _list_url(self, path, pg):
        if not path:
            path = "/"
        if path.startswith("http"):
            return self._paged(path, pg)
        return self._paged(self._abs(path), pg)

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        path = self._resolve(tid, extend)
        stride = 2 if self._is_hl_list(path) else 1
        start = (pg - 1) * stride + 1
        items, seen = [], set()
        last_html, last_soup, last_site, last_n = "", None, start, 0
        for i in range(stride):
            site_pg = start + i
            html = self._get(self._list_url(path, site_pg))
            if not html:
                break
            soup = _soup(html)
            last_html, last_soup, last_site = html, soup, site_pg
            if i == 0:
                try:
                    self._refresh_filters(tid, path, soup, self._cache.get("nav") or [])
                    self._save()
                except Exception:
                    pass
            chunk = self._items(soup)
            last_n = len(chunk)
            for it in chunk:
                vid = it.get("vod_id")
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                items.append(it)
        if not items and not last_html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}
        self._remember(items)
        site_pc = self._pagecount(last_soup or _soup(""), last_site, last_html, last_n)
        if stride > 1:
            pc = max(pg, (site_pc + stride - 1) // stride)
            if site_pc > last_site:
                pc = max(pc, pg + 1)
        else:
            pc = site_pc
        return {"list": items, "page": pg, "pagecount": pc, "limit": len(items), "total": 999999}

    def _search_ep(self):
        ep = self._cache.get("search")
        if ep and ep.get("path") and ep.get("param"):
            return ep
        html = self._get(self._abs("/"))
        if html:
            self._parse_nav(html)
            self._save()
        return self._cache.get("search") or {}

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg):
        pg = int(pg or 1)
        ep = self._search_ep()
        if not ep.get("path") or not ep.get("param"):
            return {"list": [], "page": pg, "pagecount": 1}
        url = self._abs(ep["path"]) + "?" + urlencode({ep["param"]: key}, quote_via=quote)
        html = self._get(self._paged(url, pg))
        if not html:
            return {"list": [], "page": pg, "pagecount": 1}
        soup = _soup(html)
        items = self._items(soup)
        self._remember(items)
        return {"list": items, "page": pg, "pagecount": self._pagecount(soup, pg, html, len(items))}

    # ------------------------------------------------------------------ 详情 / 播放

    def _og(self, html):
        out = {}
        if not html:
            return out
        for m in re.finditer(
            r'<meta[^>]+property=["\'](og:[^"\']+)["\'][^>]+content=["\']([^"\']*)',
            html, re.I,
        ):
            out.setdefault(m.group(1).lower(), m.group(2))
        return out

    def _video_from(self, text):
        return self._first_video(_unpack(text)) or self._first_video(text)

    def _play_js(self, page_url, js_name, img, uu, ref):
        if not js_name.startswith("/"):
            js_name = "/" + js_name
        js_url = "%s?img=%s&u=%s&h=&t=%d" % (
            urljoin(page_url, js_name), img, quote(uu, safe=""), int(time.time() / 2100))
        return self._get(js_url, ref=ref, min_len=50, rehost=False)

    def _embed_href(self, url, html=""):
        m = re.search(r"[?&]video_key=(\d+)", url or "")
        if m:
            return self._abs("/comic/index/embed?id=" + m.group(1))
        m = re.search(r"/melonshort/video/([\w-]+)", url or "")
        if m:
            return self._abs("/melonshort/embed/" + m.group(1))
        text = html or ""
        m = re.search(r'content=["\']([^"\']+(?:/comic/index/embed\?id=|/melonshort/embed/)[^"\']+)', text)
        if m:
            return m.group(1)
        m = re.search(r'(/comic/index/embed\?id=[^"\'\s&<>]+)', text)
        if m:
            return self._abs(m.group(1))
        m = re.search(r'(/melonshort/embed/[\w-]+)', text)
        if m:
            return self._abs(m.group(1))
        m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', text, re.I)
        if m:
            return urljoin(url or self.host, m.group(1))
        return ""

    def _embed_play(self, embed_url, ref):
        html = self._get(embed_url, ref=ref, rehost=False)
        if not html:
            return "", ""
        title = self._page_title(html, "")
        u = self._first_video(html)
        if u:
            return u, title
        packed = _unpack(html)
        img = re.search(r'embed_play\.js\?img=([^"&\\\s]+)', packed)
        uu = re.search(r'encodeURIComponent\(["\']([^"\']+)["\']\)', packed)
        if not (img and uu):
            return self._first_video(packed), title
        js = self._play_js(embed_url, "/index/embed_play.js", img.group(1), uu.group(1), embed_url)
        return (self._video_from(js) if js else ""), title

    def _js_play(self, page_url, text):
        packed = _unpack(text) if text else ""
        src = packed or text or ""
        if "_play.js" not in src:
            return ""
        m = re.search(r'([\w./-]*_play\.js)\?img=([^"\'&\\\s]*)', src)
        uu = re.search(r'encodeURIComponent\(["\']([^"\']+)["\']\)', src)
        if not (m and uu):
            return self._first_video(src)
        js = self._play_js(page_url, m.group(1), m.group(2), uu.group(1), page_url)
        return self._video_from(js) if js else ""

    def _play_from(self, url, html=None):
        """数字 video_key / 短视频走 embed；吃瓜从 packed 的 melon_detail_play.js 现取。"""
        if html:
            u = self._first_video(html)
            if u:
                return u, self._page_title(html, "")
        embed = self._embed_href(url, html or "")
        if embed:
            return self._embed_play(embed, url)
        if html is None:
            html = self._get(url, rehost=False) or ""
            return self._play_from(url, html)
        v = self._js_play(url, html)
        return v, self._page_title(html or "", "")

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        url = self._abs(vid)

        if self._is_folder(url):
            html = self._get(url)
            items = self._items(_soup(html or ""))
            out, seen = [], set()
            for it in items:
                iid = it.get("vod_id") or ""
                if not iid or iid in seen:
                    continue
                seen.add(iid)
                child = {
                    "vod_id": iid,
                    "vod_name": it.get("vod_name") or "",
                    "vod_pic": it.get("vod_pic") or "",
                    "vod_remarks": it.get("vod_remarks") or "",
                }
                if self._is_folder(iid):
                    child["vod_tag"] = "folder"
                elif self._is_novel(iid):
                    child["vod_tag"] = "text"
                out.append(child)
            if out:
                return {"list": out}

        cached = None
        key = urlparse(url).query
        for it in self._page_items():
            iid = it.get("vod_id") or ""
            if iid == vid or (key and key in iid):
                cached = it
                break
        title = (cached or {}).get("vod_name") or ""
        pic = (cached or {}).get("vod_pic") or ""
        desc = ""
        html = None
        digit_key = bool(re.search(r"[?&]video_key=\d+", url))
        short = bool(re.search(r"/melonshort/video/", url or ""))
        hl = "/heiliao-chigua/" in self._path_of(url)
        if self._is_novel(url) or hl or not (digit_key or short):
            html = self._get(url)
            if not html:
                return {"list": []}
            title = title or self._page_title(html, "")
            og = self._og(html)
            pic = pic or og.get("og:image") or ""
            desc = og.get("og:description") or ""
        content = desc or title

        if self._is_novel(url):
            slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
            return {"list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic if str(pic).startswith("http") else self._img(pic),
                "vod_content": content,
                "vod_remarks": "小说",
                "vod_play_from": "小说",
                "vod_play_url": "正文$novel_%s_1" % slug,
            }]}

        play, etitle = self._play_from(url, html)
        title = title or etitle or self._page_title(html or "", "")
        lines = [("播放", [("正片", play or url)])]
        if play:
            lines = self._with_playlist(vid, title, lines)
        return {"list": [{
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic if str(pic).startswith("http") else self._img(pic),
            "vod_content": content,
            "vod_remarks": "m3u8" if play else "",
            "vod_play_from": "$$$".join(n for n, _ in lines),
            "vod_play_url": "$$$".join(u for _, u in lines),
        }]}

    def playerContent(self, flag, id, vipFlags):
        s = str(id or "")
        if s.startswith("nid:"):
            s = unquote(s[4:])
        if s.startswith("novel://"):
            return {"parse": 0, "url": s, "header": ""}
        if s.startswith("novel_"):
            return self._play_novel(s)
        url = s
        if url and not url.startswith("data:") and not self.isVideoFormat(url):
            play, _ = self._play_from(self._abs(url))
            url = play or url
        headers = dict(self.headers)
        headers["Referer"] = self.host + "/"
        return {"parse": 0, "jx": 0, "url": url, "header": headers}

    # ------------------------------------------------------------------ 图片代理

    def localProxy(self, param):
        param = param if isinstance(param, dict) else {}
        t = param.get("type")
        if t == "cache":
            return [200, "image/jpeg", _IMG_CACHE.get(param.get("key"), b"")]
        if t == "img":
            url = param.get("url")
            real = self.d64(url) if url and not str(url).startswith("http") else url
            real = str(real or "")
            if real.startswith("//"):
                real = urlparse(self.host).scheme + ":" + real
            hdrs = dict(self.headers)
            try:
                p = urlparse(real)
                if p.scheme and p.netloc:
                    hdrs["Referer"] = "%s://%s/" % (p.scheme, p.netloc)
            except Exception:
                pass
            try:
                raw = self.session.get(real, headers=hdrs, timeout=10).content
            except Exception:
                raw = b""
            return [200, "image/jpeg", self.aesimg(raw)]
        return [404, "text/plain", b""]

    def _pbase(self):
        if self._proxy is not None:
            return self._proxy
        base = ""
        try:
            u = self.getProxyUrl()
            if u:
                base = u if str(u).endswith(("?", "&")) else str(u) + "&"
        except Exception:
            pass
        self._proxy = base
        return base

    def e64(self, text):
        return base64.b64encode(str(text).encode()).decode()

    def d64(self, text):
        return base64.b64decode(str(text).encode()).decode()

    def aesimg(self, data):
        if AES is None or not data or len(data) < 16:
            return data
        for key, iv in ((b"f5d965df75336270", b"97b60394abc2fbe1"), (b"75336270f5d965df", b"abc2fbe197b60394")):
            try:
                dec = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(data), 16)
                if dec.startswith((b"\xff\xd8", b"\x89PNG", b"GIF8")):
                    return dec
            except Exception:
                pass
        return data

    def _img(self, url):
        url = _html.unescape((url or "").strip().strip("'\" "))
        if not url:
            return ""
        if url.startswith("//"):
            url = urlparse(self.host).scheme + ":" + url
        base = self._pbase()
        if url.startswith("data:"):
            try:
                _, b64s = url.split(",", 1)
                raw = base64.b64decode(b64s)
                raw = raw if raw.startswith((b"\xff\xd8", b"\x89PNG", b"GIF8")) else self.aesimg(raw)
                key = hashlib.md5(raw).hexdigest()
                _IMG_CACHE[key] = raw
                return (base + "type=cache&key=" + key) if base else url
            except Exception:
                return ""
        if not url.startswith("http"):
            url = urljoin(self.host + "/", url.lstrip("/"))
        if base:
            return base + "url=" + self.e64(url) + "&type=img"
        return url
