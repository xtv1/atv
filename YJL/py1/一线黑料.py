# coding: utf-8
# ============================================================
# 一线黑料 爬虫源  (TVBox / FongMi)
# 主域名   : https://danbady4042982.buzz
# 备用域名 : https://ad.addizhi.top/app/app.html

import json
import os
import re
import math
import time
import posixpath
from urllib.parse import quote, urljoin, unquote, urlparse

from base.spider import Spider as BaseSpider

try:
    from concurrent.futures import ThreadPoolExecutor
except ImportError:
    ThreadPoolExecutor = None


class Spider(BaseSpider):

    # ---- 由 m3u8_analyzer 取证结论决定 ----
    # True  = 存在广告目录，走 localProxy 五层清洗
    # False = 无广告特征，直接返回直链
    NEED_CLEAN = True
    AD_ANCHOR = "/20260911/pmWBKnV6/1500kb/hls/"
    AD_DIRS = ["/20260731/UTxI1Mxv/9567kb/hls/"]

    # 子分类筛选每行最多选项数,超过拆行(同 key 多行)
    FILTER_CHUNK = 8
    # 子分类筛选 key(TVBox 同 key 多行筛选)
    FILTER_KEY = "videoTag"

    def __init__(self):
        self.extend = ""
        self.hosts = [
            "https://danbady4042982.buzz",
            "https://danbady3674328.xyz",
        ]
        self.host = self.hosts[0]
        self._host_ok = False

        # 分类/筛选全部动态获取,新进程首次调用强制拉取,同进程走内存缓存
        self._classes = None
        self._filters = None
        self._loaded = False

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; 22127RK46C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + "/",
        }

    def getName(self):
        return "一线黑料"

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        u = str(url or "")
        if u.startswith(("novel://", "pics://", "text://", "txt://")):
            return False
        return ".m3u8" in u or u.endswith(".mp4")

    def manualVideoCheck(self):
        return False

    def init(self, extend=""):
        # init 零网络;域名探测懒加载放 _pick_host
        self.extend = extend or ""
        self._loaded = False

    def destroy(self):
        self._host_ok = False
        self._loaded = False

    # ==================== 基础请求 ====================

    def _pick_host(self):
        """懒加载域名探测。缓存的上次可用 host 排到最前优先探测。"""
        if self._host_ok:
            return
        for h in self.hosts:
            try:
                r = self.fetch(h + "/", headers={"User-Agent": self.headers["User-Agent"]}, timeout=8)
                if r and getattr(r, "status_code", 0) == 200:
                    self.host = h
                    self.headers["Referer"] = h + "/"
                    break
            except Exception:
                continue
        self._host_ok = True

    def _abs(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        return urljoin(self.host + "/", url.lstrip("/"))

    def _get(self, url, timeout=15):
        self._pick_host()
        try:
            r = self.fetch(url, headers=self.headers, timeout=timeout)
            if not r or getattr(r, "status_code", 0) != 200:
                return ""
            return getattr(r, "text", "") or ""
        except Exception:
            return ""

    @staticmethod
    def _norm_ids(ids):
        if ids is None:
            return ""
        if isinstance(ids, (list, tuple)):
            if not ids:
                return ""
            ids = ids[0]
        if isinstance(ids, bytes):
            ids = ids.decode("utf-8", errors="ignore")
        return str(ids).strip()

    def _parse_extend(self, extend):
        if not extend:
            return {}
        if isinstance(extend, dict):
            return extend
        if isinstance(extend, str):
            try:
                return json.loads(extend)
            except Exception:
                pass
            out = {}
            for part in extend.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    out[k.strip()] = v.strip()
            return out
        return {}

    # ==================== 分类/筛选动态获取 ====================

    def _ensure_data(self):
        """首页只保证有分类:先读 sdcard 缓存,没有再拉一次导航,不扫 17 个分类页。"""
        if self._loaded:
            return
        self._load_cache()
        if not self._classes:
            self._fetch_nav_only()
        self._loaded = True

    @staticmethod
    def _tid_code(kind, num):
        k = {"video": "v", "image": "i", "novel": "n"}.get(str(kind).lower(), "v")
        return "%s%s" % (k, num)

    @staticmethod
    def _tid_path(tid):
        """v913 / i961 / n962 -> video/type/913 ; 兼容旧路径 tid。"""
        tid = str(tid or "").strip().strip("/")
        m = re.match(r"^([vin])(\d+)$", tid)
        if m:
            return {"v": "video", "i": "image", "n": "novel"}[m.group(1)] + "/type/" + m.group(2)
        return tid

    def _fetch_nav_only(self):
        """只拉首页导航得分类,一次请求,立刻可展示。"""
        self._pick_host()
        home = self._get(self.host + "/", timeout=8)
        if not home:
            return False
        classes = self._parse_nav(home)
        if not classes:
            return False
        self._classes = classes
        if not self._filters:
            self._filters = {}
        self._save_cache()
        return True

    _NAV_RE = re.compile(
        r'href=["\']?/(video|image|novel)/type/(\d+)\.html["\'][^>]*>\s*([^<]{1,30}?)\s*<',
        re.I,
    )

    def _parse_nav(self, home_html):
        """首页导航 -> class 列表 [{type_id, type_name, type_extend}]。按 tid 去重保序。"""
        classes = []
        seen = set()
        for kind, tid, name in self._NAV_RE.findall(home_html or ""):
            name = self._clean(name)
            type_id = self._tid_code(kind, tid)
            if not name or type_id in seen:
                continue
            seen.add(type_id)
            classes.append({
                "type_id": type_id,
                "type_name": name,
                "type_extend": {},
            })
        return classes

    def _parse_mycate(self, html):
        """从分类页 HTML 抽 mycate 子分类 [{n:名称, v:子tid}]。"""
        m = re.search(r'<nav class="mycate">(.*?)</nav>', html or "", re.S | re.I)
        if not m:
            return []
        subs = []
        seen = set()
        for href, name in re.findall(r'href=["\']([^"\']+)["\'][^>]*>([^<]+)', m.group(1)):
            name = self._clean(name)
            mm = re.match(r"^/(video|image|novel)/type/(\d+)\.html$", (href or "").strip())
            if not mm or not name or name == "所有分类":
                continue
            sub_tid = self._tid_code(mm.group(1), mm.group(2))
            if sub_tid in seen:
                continue
            seen.add(sub_tid)
            subs.append({"n": name, "v": sub_tid})
        return subs

    def _ingest_mycate(self, tid, html):
        """进分类时顺手写入该分类筛选,落盘到 sdcard,下次打开源直接有。"""
        tid = str(tid or "").strip()
        subs = self._parse_mycate(html)
        if not tid or not subs:
            return
        if self._filters is None:
            self._filters = {}
        rows = self._build_filter_rows(tid, subs)
        old = self._filters.get(tid)
        if old == rows:
            return
        self._filters[tid] = rows
        if self._classes:
            for c in self._classes:
                if c.get("type_id") == tid:
                    c["type_extend"] = {"extend": "#".join("%s=%s" % (s["v"], s["n"]) for s in subs)}
                    break
        self._save_cache()

    def _build_filter_rows(self, tid, subs):
        """同 key 多行筛选:超过 FILTER_CHUNK 个拆多组,每组独立一行,
        各组同 key,后续行不加「全部」,避免单行过长看不到后面。"""
        rows = []
        head = [{"n": "全部", "v": tid}] + subs[: self.FILTER_CHUNK]
        rows.append({"key": self.FILTER_KEY, "name": "分类", "value": head})
        rest = subs[self.FILTER_CHUNK:]
        while rest:
            rows.append({"key": self.FILTER_KEY, "name": "分类", "value": rest[: self.FILTER_CHUNK]})
            rest = rest[self.FILTER_CHUNK:]
        return rows

    def _first_tid(self, kind):
        self._ensure_data()
        prefix = {"video": "v", "image": "i", "novel": "n"}.get(kind, "v")
        for c in (self._classes or []):
            tid = str(c.get("type_id", ""))
            if tid.startswith(prefix) and tid[1:].isdigit():
                return tid
        return ""

    # ==================== 本地缓存兜底 ====================

    def _cache_paths(self):
        name = "spider_yixianheiliao.json"
        paths = []
        try:
            paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), name))
        except Exception:
            pass
        for d in ("/sdcard/tvbox", "/storage/emulated/0/tvbox", "/sdcard", "/storage/emulated/0"):
            paths.append(os.path.join(d, name))
        paths.append("/tmp/" + name)
        return paths

    def _save_cache(self):
        data = {
            "host": self.host,
            "saved": int(time.time()),
            "classes": self._classes,
            "filters": self._filters or {},
        }
        raw = json.dumps(data, ensure_ascii=False)
        try:
            if hasattr(self, "setCache"):
                self.setCache("yxhl_nav", raw)
        except Exception:
            pass
        for p in self._cache_paths():
            try:
                d = os.path.dirname(p)
                if d and not os.path.isdir(d):
                    os.makedirs(d)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(raw)
            except Exception:
                continue

    def _apply_cache(self, data):
        classes = data.get("classes")
        if not classes:
            return False
        self._classes = classes
        self._filters = data.get("filters") or {}
        host = str(data.get("host") or "")
        if host and host in self.hosts:
            self.hosts.remove(host)
            self.hosts.insert(0, host)
            self.host = host
        return True

    def _load_cache(self):
        """优先读 TVBox getCache(重启仍在),再读 sdcard 文件。"""
        try:
            if hasattr(self, "getCache"):
                raw = self.getCache("yxhl_nav")
                if raw:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(data, dict) and self._apply_cache(data):
                        return True
        except Exception:
            pass
        for p in self._cache_paths():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if self._apply_cache(data):
                return True
        return False

    # ==================== 首页 ====================

    def homeContent(self, filter):
        self._ensure_data()
        return {
            "class": self._classes or [],
            "filters": self._filters or {},
            "list": [],
        }

    def getHomeContent(self, filter):
        return self.homeContent(filter)

    def homeVideoContent(self):
        tid = self._first_tid("video")
        if not tid:
            return {"list": []}
        r = self.categoryContent(tid, "1", False, {})
        return {"list": r.get("list", [])}

    # ==================== 列表 ====================

    # 列表卡片: li[id^=content] > a[href][title] > img[src] ; span=日期
    _CARD_RE = re.compile(
        r"<li[^>]*id=[\"']?content\d+[\"']?[^>]*>.*?<a[^>]*href=[\"']([^\"']+)[\"'][^>]*title=[\"']([^\"']*)[\"'][^>]*>.*?<img[^>]*?(?:data-src|data-original|src)=[\"']([^\"']+)[\"']",
        re.S | re.I,
    )
    # 无图卡片(小说): <li ...> <a href='/novel/info/xxx.html' title="...">...</a>
    _CARD_NOTXT_RE = re.compile(
        r"<li[^>]*>\s*<a[^>]*href=[\"']([^\"']*(?:novel|video|image)/info/[^\"']+)[\"'][^>]*title=[\"']([^\"']*)[\"']",
        re.S | re.I,
    )

    def _card(self, vid, title, pic=""):
        item = {
            "vod_id": vid,
            "vod_name": self._clean(title),
            "vod_pic": self._abs(pic) if pic else "",
            "vod_remarks": "",
        }
        if "/image/" in vid:
            item["vod_tag"] = "image"
        elif "/novel/" in vid:
            item["vod_tag"] = "text"
        return item

    def _parse_cards(self, html):
        items = []
        seen = set()
        for m in self._CARD_RE.finditer(html or ""):
            href, title, pic = m.group(1), m.group(2), m.group(3)
            vid = self._abs(href)
            if not vid or vid in seen:
                continue
            seen.add(vid)
            items.append(self._card(vid, title, pic))
        for m in self._CARD_NOTXT_RE.finditer(html or ""):
            href, title = m.group(1), m.group(2)
            vid = self._abs(href)
            if not vid or vid in seen:
                continue
            seen.add(vid)
            items.append(self._card(vid, title, ""))
        return items

    @staticmethod
    def _clean(t):
        t = re.sub(r"<[^>]+>", "", t or "")
        t = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
        t = t.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
        return t.strip()

    def categoryContent(self, tid, pg, filter, extend):
        self._pick_host()
        page = str(pg or "1")
        tid = str(tid or "").strip().strip("/")
        class_tid = tid
        ext = self._parse_extend(extend)
        sel = str(ext.get(self.FILTER_KEY, "") or "").strip().strip("/")
        if sel:
            tid = sel
        path = self._tid_path(tid)
        if page == "1":
            url = "%s/%s.html" % (self.host, path)
        else:
            url = "%s/%s/%s.html" % (self.host, path, page)
        html = self._get(url)
        self._ingest_mycate(class_tid, html)
        items = self._parse_cards(html)
        # 总页数：页面文本 "当前x/y页"
        pagecount = 9999
        m = re.search(r"当前\s*\d+\s*/\s*(\d+)\s*页", html or "")
        if m:
            try:
                pagecount = int(m.group(1))
            except Exception:
                pagecount = 9999
        return {
            "list": items,
            "page": int(page),
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
        }

    # ==================== 搜索 ====================

    def searchContent(self, key, quick, pg="1"):
        self._pick_host()
        kw = quote(str(key or "").strip(), safe="")
        page = str(pg or "1")
        urls = [
            "%s/video/search/%s.html" % (self.host, kw),
            "%s/image/search/%s.html" % (self.host, kw),
            "%s/novel/search/%s.html" % (self.host, kw),
        ]
        if page != "1":
            urls = [u.replace(".html", "/%s.html" % page) for u in urls]

        results = []
        if ThreadPoolExecutor:
            with ThreadPoolExecutor(max_workers=3) as ex:
                for lst in ex.map(self._search_one, urls):
                    results += lst
        else:
            for u in urls:
                results += self._search_one(u)

        seen, out = set(), []
        for it in results:
            if it["vod_id"] not in seen:
                seen.add(it["vod_id"])
                out.append(it)
        return {"list": out, "page": int(page)}

    def _search_one(self, url):
        try:
            html = self._get(url)
            return self._parse_cards(html)
        except Exception:
            return []

    # ==================== 详情(按 URL 分流,三条路线独立) ====================

    def detailContent(self, ids):
        raw = self._norm_ids(ids)
        if not raw:
            return {"list": []}
        try:
            detail_url = raw if raw.startswith("http") else self._abs(raw)
            html = self._get(detail_url)
            if "/novel/" in detail_url:
                return self._detail_novel(detail_url, html)
            if "/image/" in detail_url:
                return self._detail_image(detail_url, html)
            return self._detail_video(detail_url, html)
        except Exception as e:
            self.log({"detail": "exception", "error": type(e).__name__})
            return self._skeleton(raw)

    def _page_title(self, html):
        m = re.search(r"<title>(.*?)</title>", html or "", re.S | re.I)
        return self._clean(m.group(1)) if m else ""

    def _page_pic(self, html):
        # 优先 data-img（真实图），src 常为占位 gif
        m = re.search(r'class=["\']detail-img["\'][^>]*?(?:data-img|data-src)=["\']([^"\']+)["\']', html or "", re.S | re.I)
        if m and m.group(1).strip():
            return self._abs(m.group(1))
        m = re.search(r'class=["\']detail-img["\'][^>]*?src=["\']([^"\']+)["\']', html or "", re.S | re.I)
        if m and m.group(1).strip() and not m.group(1).endswith(".gif"):
            return self._abs(m.group(1))
        m = re.search(r'<img[^>]*?(?:data-img|data-src|src)=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']', html or "", re.S | re.I)
        return self._abs(m.group(1)) if m else ""

    def _detail_base(self, html, fallback):
        title = self._page_title(html).split("｜")[0].strip()
        title = re.sub(r"\s*[-－]\s*一线黑料.*$", "", title).strip() or fallback
        return title, self._page_pic(html)

    @staticmethod
    def _play_id(detail_url, kind):
        """从 /{kind}/info/{id}.html 或 /{kind}/play/{id}.html 抽作品数字 id。"""
        m = re.search(r"/(?:%s)/(?:info|play)/(\d+)" % kind, detail_url or "")
        return m.group(1) if m else "0"

    def _play_page(self, kind, vid, chap=1):
        base = "%s/%s/play/%s" % (self.host, kind, vid)
        if kind == "image" and chap and int(chap) > 1:
            return "%s/number-%d.html" % (base, int(chap))
        return base + ".html"

    def _detail_video(self, detail_url, html):
        title, pic = self._detail_base(html, "视频")
        vid = self._play_id(detail_url, "video")
        return {"list": [{
            "vod_id": detail_url,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": "",
            "vod_content": title,
            "vod_play_from": "一线黑料",
            "vod_play_url": "正片$video_%s_1" % vid,
        }]}

    def _detail_image(self, detail_url, html):
        title, pic = self._detail_base(html, "图集")
        vid = self._play_id(detail_url, "image")
        chapters = self._image_chapters(vid)
        play = "#".join("%s$img_%s_%d" % (name, vid, n) for name, n in chapters) or ("第1章$img_%s_1" % vid)
        return {"list": [{
            "vod_id": detail_url,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": "",
            "vod_content": title,
            "type_name": "漫画",
            "vod_play_from": "漫画",
            "vod_tag": "image",
            "vod_play_url": play,
        }]}

    def _image_chapters(self, vid):
        """抓首章拿总章数,按章拆条:第1章..第N章。"""
        try:
            html = self._get(self._play_page("image", vid, 1))
        except Exception:
            html = ""
        nums = re.findall(r"/number-(\d+)\.html", html or "")
        total = min(max([int(n) for n in nums], default=1), 200)
        return [("第%d章" % i, i) for i in range(1, total + 1)]

    def _detail_novel(self, detail_url, html):
        title, pic = self._detail_base(html, "小说")
        vid = self._play_id(detail_url, "novel")
        return {"list": [{
            "vod_id": detail_url,
            "vod_name": title,
            "vod_pic": pic,
            "vod_remarks": "",
            "vod_content": title,
            "type_name": "小说",
            "vod_play_from": "小说",
            "vod_tag": "text",
            "vod_play_url": "正文$novel_%s_1" % vid,
        }]}

    def _skeleton(self, vid, title="", pic=""):
        if "/novel/" in vid:
            pid = "novel_%s_1" % self._play_id(vid, "novel")
        elif "/image/" in vid:
            pid = "img_%s_1" % self._play_id(vid, "image")
        else:
            pid = "video_%s_1" % self._play_id(vid, "video")
        return {"list": [{
            "vod_id": vid, "vod_name": title or "未知标题", "vod_pic": pic or "",
            "vod_remarks": "", "vod_content": "",
            "vod_play_from": "播放", "vod_play_url": "播放$" + pid,
        }]}

    # ==================== 播放(按前缀分发) ====================

    def playerContent(self, flag, id, vipFlags):
        s = str(id or "").strip()
        if s.startswith(("novel://", "pics://")):
            return {"parse": 0, "url": s, "header": ""}
        m = re.match(r"^(img|novel|video)_(\d+)_(\d+)$", s)
        if not m:
            return {"parse": 0, "url": "", "header": ""}
        kind, vid, chap = m.group(1), m.group(2), int(m.group(3))
        if kind == "img":
            return self._play_image(self._play_page("image", vid, chap))
        if kind == "novel":
            return self._play_novel(self._play_page("novel", vid, chap))
        m3u8 = self._extract_play_url(self._play_page("video", vid, chap))
        if m3u8:
            return self._wrap_m3u8(m3u8)
        return {"parse": 0, "url": "", "header": {}, "msg": "未取到播放地址"}

    # 播放器模板与线路配置(从播放器页面动态读取,站点加减线路自动跟随)
    _PLAYER_IFRAME_RE = re.compile(r"/static/html/player\d+\.html\?id=([^\"'&]+)")
    _LINE_Q_RE = re.compile(r"\{\s*name\s*:\s*['\"][^'\"]*['\"]\s*,\s*q\s*:\s*['\"]([^'\"]*)['\"]\s*\}")

    def _extract_play_url(self, play_page_url):
        """播放页 iframe -> /aa/{token} 动态解析 m3u8(带时效签名,须现取)。"""
        html = self._get(play_page_url)
        if not html:
            return ""
        m = self._PLAYER_IFRAME_RE.search(html)
        if m:
            token = re.sub(r"^https?://", "", m.group(1))
            # 线路 q 列表来自播放器页面 LINES 数组,默认线路 q='' 声明在最前
            qs = self._LINE_Q_RE.findall(html) or [""]
            for q in qs:
                t = self._aa_get("%s/aa/%s%s" % (self.host, token, q))
                if t:
                    return t
        # 兜底:页面裸 m3u8
        m = re.search(r"(https?://[^\s\"'<>]+\.m3u8[^\s\"'<>]*)", html)
        if m:
            return m.group(1).replace("\\/", "/")
        return ""

    def _aa_get(self, url):
        """/aa/{token} 接口:XHR 请求,响应体为纯文本 m3u8 直链。"""
        self._pick_host()
        try:
            h = dict(self.headers)
            h["X-Requested-With"] = "XMLHttpRequest"
            h["Referer"] = self.host + "/static/html/"
            r = self.fetch(url, headers=h, timeout=12)
            if not r or getattr(r, "status_code", 0) != 200:
                return ""
            t = (getattr(r, "text", "") or "").strip().replace("amp;", "")
            if t.startswith("http") and ".m3u8" in t:
                return t
            return ""
        except Exception:
            return ""

    def _wrap_m3u8(self, url):
        ua = self.headers.get("User-Agent", "")
        if self.NEED_CLEAN:
            return {"parse": 0, "url": self._m3u8_proxy_url(url), "header": {"User-Agent": ua}}
        return {"parse": 0, "url": url, "header": {"User-Agent": ua}}

    # ---------- 图集 pics:// (前缀 img_) ----------

    def _play_image(self, play_url):
        imgs = self._collect_images(play_url)
        if not imgs:
            return {"parse": 0, "url": "", "header": {}, "msg": "未提取到图片"}
        payload = "pics://" + "&&".join(imgs)
        return {"parse": 0, "url": payload, "header": ""}

    def _collect_images(self, play_url):
        """单章收集:play_url 已是具体章的播放页。"""
        html = self._get(play_url)
        if not html:
            return []
        return self._extract_images(html)

    _IMG_RE = re.compile(
        r'<img[^>]+(?:data-original|data-src|src)=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']',
        re.I,
    )

    def _extract_images(self, html):
        raw = self._IMG_RE.findall(html or "")
        out = []
        for u in raw:
            if self._is_noise_image(u):
                continue
            # Android 9+ 默认禁明文 HTTP，图片统一升级 HTTPS
            if u.startswith("http://"):
                u = "https://" + u[7:]
            out.append(u)
        if raw and not out:
            # 过滤过度，回退
            return [self._abs(u) for u in raw]
        return out

    _NOISE_KW = ("logo", "icon", "favicon", "banner", "avatar", "loading",
                 "placeholder", "default", "blank", "qrcode", "share", "btn",
                 "arrow", "star")

    def _is_noise_image(self, url):
        low = str(url or "").lower()
        path = low.split("?")[0]
        name = path.rsplit("/", 1)[-1]
        for k in self._NOISE_KW:
            if k in name:
                return True
        if path.endswith((".gif", ".svg", ".ico")):
            return True
        if low.startswith("data:"):
            return True
        return False

    # ---------- 小说 novel:// (前缀 novel_) ----------

    def _play_novel(self, play_url):
        html = self._get(play_url)
        if not html:
            return {"parse": 0, "url": "", "header": {}, "msg": "读取失败"}
        title = self._page_title(html).split("｜")[0].strip() or "正文"
        content = self._extract_novel_text(html)
        chapter = {"title": title, "content": content}
        return {"parse": 0, "url": "novel://" + json.dumps(chapter, ensure_ascii=False), "header": ""}

    def _extract_novel_text(self, html):
        # 只取正文容器 novel-wrap，避免混入导航/标签/页脚
        m = re.search(r'<div[^>]*class=["\'][^"\']*novel-wrap[^"\']*["\'][^>]*>(.*?)</div>\s*(?:</div>|<div|<section|$)', html or "", re.S | re.I)
        body = m.group(1) if m else ""
        if not body or len(body) < 100:
            # 兜底：取 <body> 到「相关推荐」之间
            bm = re.search(r"<body[^>]*>(.*?)(?:相关推荐|友情链接|</body>)", html or "", re.S | re.I)
            body = bm.group(1) if bm else (html or "")
        t = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.S | re.I)
        t = re.sub(r"<style[^>]*>.*?</style>", "", t, flags=re.S | re.I)
        t = re.sub(r"</p>", "\n", t, flags=re.I)
        t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
        t = re.sub(r"<[^>]+>", "", t)
        for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                     ("&quot;", '"'), ("&#160;", " "), ("&#39;", "'")):
            t = t.replace(a, b)
        t = re.sub(r"[ \t\xa0]+", " ", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        bad = ("本站", "最新章节", "请收藏", "手机阅读", "笔趣", "推荐本书",
               "加入书签", "一线黑料", "友情链接", "网站地图", "警告：")
        lines = [l.strip() for l in t.split("\n")]
        lines = [l for l in lines if l and not any(b in l for b in bad)]
        return "\n\n".join(lines)

    def recommendContent(self, ids, pg):
        try:
            tid = self._first_tid("video")
            if not tid:
                return {"list": []}
            return self.categoryContent(tid, str(pg or "1"), False, {})
        except Exception:
            return {"list": []}

    # ==================== m3u8 代理清洗 ====================

    def getProxyUrl(self):
        return "http://127.0.0.1:9978/proxy"

    def _m3u8_proxy_url(self, url):
        if url:
            url = url.replace("\\/", "/")
        return self.getProxyUrl() + "?do=py&url=" + quote(str(url or ""), safe="")

    def localProxy(self, param):
        try:
            if isinstance(param, dict):
                target = param.get("url", "") or param.get("source", "")
            else:
                target = str(param or "")
            if target.startswith("url="):
                target = target[4:]
            elif "url=" in target:
                qs = unquote(target)
                m = re.search(r"[?&]url=([^&]+)", qs)
                if m:
                    target = m.group(1)
            target = unquote(str(target or ""))
            if not target or not re.match(r"^https?://", target, re.I):
                return [400, "text/plain", b"invalid url"]

            r = self.fetch(target, headers={"User-Agent": self.headers["User-Agent"],
                                            "Referer": self.host + "/"}, timeout=20)
            if not r or getattr(r, "status_code", 0) != 200:
                return [502, "text/plain", b"fetch failed"]
            content = getattr(r, "content", b"") or b""
            if not content and getattr(r, "text", ""):
                content = r.text.encode("utf-8", errors="ignore")
            text = content.decode("utf-8", errors="ignore")
            if "#EXTM3U" not in text:
                return [502, "text/plain", b"invalid m3u8"]
            cleaned = self._clean_m3u8(text, target)
            return [200, "application/vnd.apple.mpegurl", cleaned.encode("utf-8")]
        except Exception as e:
            return [500, "text/plain", ("localProxy error: %s" % type(e).__name__).encode("utf-8")]

    def _is_fake_image_stream(self, text):
        IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
        VIDEO_EXT = (".ts", ".m4s", ".mp4", ".aac", ".m4a")
        has_v = has_i = False
        for line in str(text or "").split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split("?")[0].split("#")[0].lower()
            if p.endswith(VIDEO_EXT):
                has_v = True
            elif p.endswith(IMAGE_EXT):
                has_i = True
        return has_i and not has_v

    def _resolve_main_dir(self, lines, source_url, is_image_stream=False):
        base_dir = posixpath.dirname(urlparse(source_url).path)
        if not base_dir.endswith("/"):
            base_dir += "/"
        if is_image_stream:
            counter = {}
            for line in lines:
                if not line or line.startswith("#"):
                    continue
                p = urlparse(urljoin(source_url, line)).path
                d = posixpath.dirname(p)
                if d and d != "/":
                    counter[d + "/"] = counter.get(d + "/", 0) + 1
            if counter:
                return max(counter.items(), key=lambda kv: kv[1])[0]
            return base_dir
        for line in lines:
            if not line.startswith("#EXT-X-KEY") or "URI=" not in line:
                continue
            m = re.search(r'URI="([^"]+)"', line)
            if not m:
                continue
            key_uri = m.group(1)
            kp = urlparse(key_uri if key_uri.startswith("http") else urljoin(source_url, key_uri)).path
            kd = posixpath.dirname(kp)
            if kd and kd != "/":
                return kd + "/"
        return base_dir

    def _clean_m3u8(self, text, source_url):
        lines = [l.strip() for l in str(text or "").replace("\r", "").split("\n") if l.strip()]
        if not lines:
            return "#EXTM3U\n"

        # 第1层：图片流检测（只打标记，不 return）
        is_img = self._is_fake_image_stream(text)

        # 第2层：多码率主表
        if any(l.startswith("#EXT-X-STREAM-INF") for l in lines):
            out = []
            for line in lines:
                if line.startswith("#"):
                    out.append(line)
                else:
                    child = urljoin(source_url, line)
                    out.append(self._m3u8_proxy_url(child) if ".m3u8" in child.lower() else child)
            return "\n".join(out) + "\n"

        # 第3层：锚点
        main_dir = self.AD_ANCHOR if self.AD_ANCHOR else self._resolve_main_dir(lines, source_url, is_img)

        # 第4层：过滤
        segments, removed, kept = self._filter_segments(lines, source_url, main_dir)

        # 第5层：全滤兜底
        if removed > 0 and (kept == 0 or removed > kept):
            self.log({"stage": "clean", "fallback": "no_filter", "removed": removed, "kept": kept})
            out = [self._rewrite_m3u8_tag(l, source_url) for l in lines]
            return "\n".join(out) + "\n"

        if removed:
            self.log({"stage": "clean", "removed": removed, "kept": kept, "anchor": main_dir})

        out = self._dedup_tags(segments, source_url)
        return "\n".join(out) + "\n"

    def _filter_segments(self, lines, source_url, main_dir):
        segments, pending = [], []
        removed = kept = 0
        for line in lines:
            if line.startswith("#EXTINF"):
                pending = [line]
                continue
            if pending and line.startswith("#"):
                pending.append(line)
                continue
            if pending:
                media = urljoin(source_url, line)
                path = urlparse(media).path
                is_ad = any(ad in path for ad in self.AD_DIRS)
                if not is_ad and main_dir and not path.startswith(main_dir):
                    is_ad = True
                if is_ad:
                    removed += 1
                else:
                    segments.extend(pending)
                    segments.append(self._rewrite_m3u8_tag(media, source_url))
                    kept += 1
                pending = []
                continue
            segments.append(self._rewrite_m3u8_tag(line, source_url))
        return segments, removed, kept

    def _dedup_tags(self, segments, source_url):
        NOISE = ("#EXT-X-DISCONTINUITY", "#EXT-X-KEY:METHOD=NONE")
        out = []
        for line in segments:
            line = self._rewrite_m3u8_tag(line, source_url)
            if line in NOISE:
                if not out or out[-1] in NOISE:
                    continue
            out.append(line)
        while len(out) > 1 and out[-1] in NOISE:
            out.pop()
        return out

    def _rewrite_m3u8_tag(self, line, source_url):
        if line.startswith("#EXT-X-KEY") or line.startswith("#EXT-X-MAP"):
            def repl(match):
                uri = match.group(1)
                if uri.startswith(("http://", "https://")):
                    return 'URI="' + uri + '"'
                return 'URI="' + urljoin(source_url, uri) + '"'
            return re.sub(r'URI="([^"]+)"', repl, line)
        if line and not line.startswith("#"):
            if line.startswith(("http://", "https://")):
                return line
            return urljoin(source_url, line)
        return line
