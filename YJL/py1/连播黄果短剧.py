#!/usr/bin/python
# coding=utf-8
#huangguoaiai@gmail.com
#永久中转页huangguoai.ai
import re, json, requests, base64, socket, time
from urllib.parse import quote, unquote
from base.spider import Spider
try:
    from Crypto.Cipher import AES
    from base64 import b64encode
except Exception:
    AES = None
    b64encode = None

_doh_cache = {}
_doh_last = {}
_doh_resolving = False
_orig_getaddrinfo = socket.getaddrinfo
_fallback_ips = {}
_doh_ttl = 300


def _doh_lookup(host):
    global _doh_resolving
    now = time.time()
    if host in _doh_cache and now - _doh_last.get(host, 0) < _doh_ttl:
        return _doh_cache[host]
    if _doh_resolving:
        return _fallback_ips.get(host, "")
    ip = ""
    _doh_resolving = True
    try:
        for srv in ("https://doh.pub/dns-query", "https://dns.alidns.com/resolve", "https://dns.google/resolve", "https://cloudflare-dns.com/dns-query"):
            try:
                r = requests.get(srv, params={"name": host, "type": "A"},
                                 headers={"Accept": "application/dns-json"}, timeout=3, verify=False)
                if r.status_code == 200:
                    for ans in r.json().get("Answer", []):
                        d = ans.get("data", "")
                        if ans.get("type") == 1 and re.match(r"^\d+\.\d+\.\d+\.\d+$", d):
                            ip = d
                            break
                if ip:
                    break
            except Exception:
                continue
    finally:
        _doh_resolving = False
    if not ip:
        ip = _fallback_ips.get(host, "")
    _doh_cache[host] = ip
    _doh_last[host] = now
    return ip


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if isinstance(host, str) and not _doh_resolving:
        ip = _doh_lookup(host)
        if ip:
            return _orig_getaddrinfo(ip, port, family, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.name = "黄果短剧"
        self.host = "https://huangguoai.com"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": self.host,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self._cats = None
        self._cat_filters = {}
        self.key = bytes(int(c) for c in "102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48".split("_"))
        self.iv = bytes(int(c) for c in "57_55_98_54_48_51_57_52_97_98_99_50_102_98_101_49".split("_"))
        self.fallback_ips = {}
        self.page_cache = {}
        self.page_index = {}
        self.page_keys = []
        self._src_cache = {}
        _fallback_ips.update(self.fallback_ips)
        socket.getaddrinfo = _patched_getaddrinfo
        self._pin_host(self.host)

    def getName(self):
        return self.name

    def init(self, extend=""):
        self._ensure_host()

    def _cache_get(self, key):
        try:
            v = self.getCache(key)
            if isinstance(v, bytes):
                v = v.decode("utf-8", "ignore")
            if isinstance(v, str) and v:
                return json.loads(v)
            if isinstance(v, dict):
                return v
        except Exception:
            pass
        return None

    def _cache_set(self, key, val):
        try:
            self.setCache(key, json.dumps(val, ensure_ascii=False))
        except Exception:
            pass

    def _ensure_host(self):
        if getattr(self, "_host_ready", False):
            return
        cached = self._cache_get("hg_host") or {}
        host = str(cached.get("host") or "").rstrip("/")
        if host.startswith("http"):
            self.host = host
            self.header["Referer"] = self.host
            self._pin_host(self.host)
        html = self.getHtml("https://huangguoai.ai/")
        if html:
            m = re.search(r'data-url="(https://[^"]+)"', html)
            if m:
                self.host = m.group(1).rstrip("/")
                self.header["Referer"] = self.host
                self._pin_host(self.host)
                self._cache_set("hg_host", {"host": self.host})
        self._host_ready = True

    def getHtml(self, url):
        for attempt in range(3):
            for kw in ({"verify": False}, {}):
                try:
                    r = requests.get(url, headers=self.header, timeout=15, **kw)
                    if r.status_code == 200:
                        return r.text
                except (TypeError, ValueError):
                    continue
                except Exception:
                    pass
        return ""

    def getJson(self, path):
        self._ensure_host()
        url = path if str(path).startswith("http") else self.host + path
        headers = dict(self.header)
        headers["Accept"] = "application/json, */*"
        for attempt in range(3):
            try:
                r = requests.get(url, headers=headers, timeout=15, verify=False)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass
        return None

    def _api(self, path):
        data = self.getJson(path)
        if not isinstance(data, dict):
            return None
        return data.get("data")

    def _apply_page(self, result, pgd, page, n=0):
        if pgd:
            result["page"] = pgd.get("page") or page
            result["pagecount"] = pgd.get("pages") or 1
            result["total"] = pgd.get("total") or 0
            result["limit"] = pgd.get("size") or (n or 20)
        else:
            result["page"] = page
            result["pagecount"] = 1
            result["limit"] = n or 20
            result["total"] = n

    def _parse_menus(self, data):
        cats, filters = [], {}
        for it in (data.get("category") or []):
            code = str(it.get("cat_code") or "").strip()
            name = str(it.get("name") or "").strip()
            if not code or not name or code == "long":
                continue
            kind = "chigua" if code == "community" else "video"
            tid = "chigua" if kind == "chigua" else code
            cats.append({"type_id": tid, "type_name": name, "kind": kind, "api": code})
            if kind == "chigua":
                parent = str(it.get("url") or "/chigua/").strip() or "/chigua/"
                vals = [{"n": "全部", "v": parent}]
                for c in (it.get("children") or []):
                    cn = str(c.get("name") or "").strip()
                    cu = str(c.get("url") or "").strip()
                    if cn and cu:
                        vals.append({"n": cn, "v": cu})
                filters[tid] = [{"key": "sub", "name": "子分类", "value": vals}]
            else:
                filters[tid] = [{"key": "sub", "name": "子分类", "value": [
                    {"n": "最新更新", "v": "latest"},
                    {"n": "当前热播", "v": "hot"},
                    {"n": "独家原创", "v": "original"},
                    {"n": "随机推荐", "v": "random"},
                ]}]
        return cats, filters

    def _apply_extras(self, cats, filters):
        extras = [
            ("topic", "专题", "topic", None),
            ("rank", "排行榜", "rank", [
                {"n": "热播榜", "v": "hot"},
                {"n": "潜力榜", "v": "potential"},
                {"n": "推荐榜", "v": "recommend"},
            ]),
            ("author", "黄果官方", "author", [
                {"n": "黄果官方", "v": "156291"},
                {"n": "黄果AI大师", "v": "156305"},
            ]),
        ]
        have = {c["type_id"] for c in cats} | {c["type_name"] for c in cats}
        for tid, name, kind, tabs in extras:
            if tid in have or name in have:
                continue
            cats.append({"type_id": tid, "type_name": name, "kind": kind, "api": tid})
            if tabs:
                filters[tid] = [{"key": "sub", "name": "子分类", "value": tabs}]
        return cats, filters

    def _load_cats(self):
        if self._cats:
            return self._cats
        data = self._api("/api/site/menus") or {}
        cats, filters = self._parse_menus(data)
        if cats:
            self._cache_set("hg_cats", {"cats": cats, "filters": filters})
        else:
            cached = self._cache_get("hg_cats") or {}
            cats = list(cached.get("cats") or [])
            filters = dict(cached.get("filters") or {})
        ready = bool(cats)
        cats, filters = self._apply_extras(cats, filters)
        self._cat_filters = filters
        if ready:
            self._cats = cats
        return cats

    def fix_url(self, url):
        if not url:
            return ""
        url = url.replace("\\u0026", "&").replace("&amp;", "&")
        if url.startswith("/proxy?") or url.startswith("/local/") or url.startswith("http://127.0.0.1"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def _pin_host(self, url):
        try:
            m = re.search(r'https?://([^/?#]+)', url)
            if m:
                _doh_lookup(m.group(1))
        except Exception:
            pass

    def proc_pic(self, pic):
        if not pic:
            return ""
        pic = self.fix_url(pic)
        if "127.0.0.1" in pic or "local://" in pic or pic.startswith("data:"):
            return pic
        try:
            b = self.getProxyUrl()
            if "?" not in b:
                b += "?do=py"
            return b + "&url=" + quote(pic)
        except Exception:
            return "http://127.0.0.1:9978/proxy?do=py&url=" + quote(pic)

    def extract_cards(self, html, link_prefix="detail"):
        result = []
        seen = set()
        matches = list(re.finditer(r'data-track-id="(\d+)"', html))
        for i, m in enumerate(matches):
            try:
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else min(start + 3000, len(html))
                chunk = html[start:end]
                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                link = re.search(r'href="(/%s/%s/)"' % (link_prefix, re.escape(vod_id)), chunk)
                if not link:
                    link = re.search(r'href="(/%s/%s)"' % (link_prefix, re.escape(vod_id)), chunk)
                if not link:
                    continue
                seen.add(vod_id)
                title = re.search(r'data-track-title="([^"]*)"', chunk)
                vod_name = title.group(1) if title else ""
                if not vod_name:
                    t = re.search(r'alt="([^"]*)"', chunk)
                    vod_name = t.group(1) if t else ""
                if not vod_name:
                    h = re.search(r'<h2[^>]*>.*?<a[^>]*>([^<]+)</a>', chunk, re.S)
                    vod_name = h.group(1).strip() if h else ""
                pic = re.search(r'data-src="(https?://[^"]*)"', chunk)
                if not pic:
                    pic = re.search(r'<img[^>]*data-src="([^"]+)"', chunk)
                vod_pic = self.proc_pic(pic.group(1) if pic else "")
                ep = re.search(r'hg-drama-card__episode[^>]*>([^<]*)', chunk)
                vod_remarks = ep.group(1).strip() if ep else ""
                if not vod_remarks:
                    score = re.search(r'hg-drama-card__score[^>]*>([^<]*)', chunk)
                    vod_remarks = score.group(1).strip() if score else ""
                if vod_name and vod_id:
                    result.append({
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": vod_remarks
                    })
            except Exception:
                continue
        return result

    def parse_rank_list(self, items):
        result = []
        for it in items or []:
            try:
                vid = str(it.get("video_id") or it.get("id") or "")
                name = (it.get("title") or "").strip()
                if not vid or not name:
                    continue
                remark = str(it.get("metric_value") or it.get("score") or "")
                result.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": self.proc_pic(it.get("cover") or ""),
                    "vod_remarks": remark
                })
            except Exception:
                continue
        return result

    def parse_topic_list(self, items):
        result = []
        for it in items or []:
            try:
                slug = str(it.get("slug") or "").strip()
                name = (it.get("title") or "").strip()
                if not slug or not name:
                    continue
                cnt = it.get("video_count") or 0
                result.append({
                    "vod_id": "/topics/%s/" % slug,
                    "vod_name": name,
                    "vod_pic": self.proc_pic(it.get("cover") or ""),
                    "vod_remarks": ("%d部" % cnt) if cnt else ""
                })
            except Exception:
                continue
        return result

    def extract_posts(self, html):
        result = []
        seen = set()
        for m in re.finditer(r'<a class="hg-post-card"[^>]*href="(/archives/(\d+)/)"', html):
            pid = m.group(2)
            if pid in seen:
                continue
            seen.add(pid)
            chunk = html[m.start():m.start() + 1800]
            title = re.search(r"<h3>([^<]*)</h3>", chunk)
            vod_name = title.group(1).strip() if title else ""
            if not vod_name:
                alt = re.search(r'alt="([^"]*)"', chunk)
                vod_name = alt.group(1).strip() if alt else ""
            pic = re.search(r'data-src="(https?://[^"]*)"', chunk)
            vod_pic = self.proc_pic(pic.group(1) if pic else "")
            cat = re.search(r'hg-post-card__cat[^>]*>([^<]*)', chunk)
            vod_remarks = cat.group(1).strip() if cat else ""
            if vod_name:
                result.append({
                    "vod_id": m.group(1),
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_remarks": vod_remarks
                })
        return result

    def _chigua_url(self, tab, page):
        base = tab if str(tab).startswith("/") else "/chigua/"
        base = base.rstrip("/") or "/chigua"
        if page <= 1:
            return base + "/"
        if base == "/chigua":
            return "/chigua/page/%d/" % page
        return "%s/%d/" % (base, page)

    def parse_api_list(self, items):
        result = []
        for it in items:
            try:
                vid = str(it.get("id") or "")
                if not vid:
                    continue
                name = (it.get("title") or "").strip()
                if not name:
                    continue
                score = it.get("score") or 0
                remark = ""
                if it.get("is_finished"):
                    remark = "全%d集" % (it.get("total_episodes") or 0)
                else:
                    ec = it.get("episode_count") or 0
                    if ec:
                        remark = "更新至%d集" % ec
                if score:
                    remark = ("%s %.1f分" % (remark, score)).strip()
                if it.get("is_original"):
                    remark = ("黄果原创 " + remark).strip()
                result.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": self.proc_pic(it.get("cover") or ""),
                    "vod_remarks": remark
                })
            except Exception:
                continue
        return result

    def _t(self, s):
        return str(s or "").replace("$", " ").replace("#", " ").strip()

    def _cache_page(self, key, items):
        videos = [it for it in (items or []) if isinstance(it, dict) and it.get("vod_id")]
        if not videos:
            return
        self.page_cache[key] = videos
        if key in self.page_keys:
            self.page_keys.remove(key)
        self.page_keys.append(key)
        while len(self.page_keys) > 30:
            old = self.page_keys.pop(0)
            for it in self.page_cache.pop(old, []):
                vid = str(it.get("vod_id") or "")
                if self.page_index.get(vid) == old:
                    self.page_index.pop(vid, None)
        for it in videos:
            self.page_index[str(it["vod_id"])] = key

    def _src_from_vod(self, vod):
        froms = [x for x in str((vod or {}).get("vod_play_from") or "").split("$$$") if x] or ["黄果短剧"]
        groups = str((vod or {}).get("vod_play_url") or "").split("$$$")
        src = []
        for i, name in enumerate(froms):
            eps = []
            for p in str(groups[i] if i < len(groups) else (groups[0] if groups else "")).split("#"):
                if not p:
                    continue
                n, u = p.split("$", 1) if "$" in p else ("播放", p)
                eps.append((self._t(n), u))
            if eps:
                src.append((name, eps))
        return src

    def _load_src(self, vid):
        vid = str(vid)
        if vid in self._src_cache:
            return self._src_cache[vid]
        src = self._src_from_vod(self._video_vod(vid) or {})
        if src:
            self._src_cache[vid] = src
        return src

    def _after_items(self, vid):
        key = self.page_index.get(str(vid))
        items = [x for x in (self.page_cache.get(key) or []) if x.get("vod_id")]
        ids = [str(x.get("vod_id")) for x in items]
        if str(vid) not in ids:
            return []
        return items[ids.index(str(vid)) + 1:]

    def _load_after(self, vid, n=10):
        for it in self._after_items(vid)[:n]:
            oid = str(it.get("vod_id") or "")
            if not oid or oid in self._src_cache:
                continue
            try:
                self._load_src(oid)
            except Exception:
                pass

    def _build_page_play(self, vid, film, play_from, play_url):
        vid, film = str(vid), self._t(film) or str(vid)
        froms = [x for x in str(play_from or "").split("$$$") if x] or ["黄果短剧"]
        groups = str(play_url or "").split("$$$")
        tails, seen = [], {vid}
        for it in self._after_items(vid):
            oid = str(it.get("vod_id") or "")
            if not oid or oid in seen:
                continue
            seen.add(oid)
            name = self._t(it.get("vod_name")) or oid
            src = self._src_cache.get(oid) or []
            eps = src[0][1] if src and src[0][1] else []
            if len(eps) > 1:
                for en, u in eps:
                    tails.append("%s$%s" % (self._t("%s %s" % (name, en)), u))
            elif eps and eps[0][1] and not str(eps[0][1]).startswith("nid:"):
                tails.append("%s$%s" % (name, eps[0][1]))
            else:
                tails.append("%s$nid:%s" % (name, quote(oid, safe="")))
        tail = ("#" + "#".join(tails)) if tails else ""
        out = []
        for i, _n in enumerate(froms):
            raw = str(groups[i] if i < len(groups) else (groups[0] if groups else "") or "").strip()
            if not raw:
                first = film + "$"
            elif "$" in raw:
                first = raw
            else:
                first = "%s$%s" % (film, raw)
            out.append(first + tail)
        return "$$$".join(froms), "$$$".join(out)

    def _nid_url(self, vid, flag):
        try:
            src = self._load_src(str(vid))
            picked = []
            for name, eps in src:
                if str(name) == str(flag) and eps:
                    picked = eps
                    break
            if not picked and src:
                picked = src[0][1]
            if not picked:
                return ""
            return picked[0][1]
        except Exception:
            return ""

    def homeContent(self, filter):
        result = {"class": [], "filters": {}}
        for cat in self._load_cats():
            result["class"].append({"type_id": cat["type_id"], "type_name": cat["type_name"]})
        result["filters"] = dict(self._cat_filters)
        result["list"] = self.homeVideoContent().get("list", [])
        return result

    def homeVideoContent(self):
        result = {"list": []}
        d = self._api("/api/videos?page=1") or {}
        result["list"] = self.parse_api_list(d.get("items") or [])[:20]
        self._cache_page(("home",), result["list"])
        return result

    def get_tab(self, filter, extend):
        for d in (filter, extend):
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except Exception:
                    d = None
            if isinstance(d, dict):
                if d.get("sub"):
                    return str(d.get("sub"))
                inner = d.get("filter")
                if isinstance(inner, dict) and inner.get("sub"):
                    return str(inner.get("sub"))
        return ""

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        page = int(pg) if pg else 1
        if tid and str(tid).startswith("folder_topic_"):
            return self.topicFolderList(tid, page)
        cat = next((c for c in self._load_cats() if c["type_id"] == tid or c["type_name"] == tid), None)
        if not cat:
            return result
        kind = cat.get("kind", "")
        tab = self.get_tab(filter, extend)
        if kind == "topic":
            d = self._api("/api/topics?page=%d" % page) or {}
            for t in self.parse_topic_list(d.get("items") or []):
                fid = "folder_topic_" + base64.urlsafe_b64encode(t["vod_id"].encode("utf-8")).decode("utf-8")
                result["list"].append({
                    "vod_id": fid,
                    "vod_name": t["vod_name"],
                    "vod_pic": t["vod_pic"],
                    "vod_remarks": t["vod_remarks"] or "进入专辑",
                    "vod_tag": "folder"
                })
            self._apply_page(result, d.get("pagination") or {}, page, len(result["list"]))
        elif kind == "rank":
            key = tab if tab in ("hot", "potential", "recommend") else "hot"
            d = self._api("/api/ranks/%s" % key) or {}
            result["list"] = self.parse_rank_list(d.get("items") or [])
            n = len(result["list"])
            result["page"] = 1
            result["pagecount"] = 1
            result["limit"] = n or 20
            result["total"] = n
        elif kind == "chigua":
            html = self.getHtml(self.host + self._chigua_url(tab, page))
            if not html:
                return result
            result["list"] = self.extract_posts(html)
            page_m = re.search(r"第\s*(\d+)/(\d+)\s*页", html)
            total_m = re.search(r"共\s*(\d+)\s*条", html)
            result["page"] = int(page_m.group(1)) if page_m else page
            result["pagecount"] = int(page_m.group(2)) if page_m else 1
            result["total"] = int(total_m.group(1)) if total_m else len(result["list"])
            result["limit"] = len(result["list"]) if result["list"] else 20
        elif kind == "author":
            aid = tab if str(tab).isdigit() else "156291"
            d = self._api("/api/videos/user/%s?page=%d" % (aid, page)) or {}
            result["list"] = self.parse_api_list(d.get("items") or [])
            self._apply_page(result, d.get("pagination") or {}, page, len(result["list"]))
        else:
            qmap = {"latest": "sort=latest", "hot": "", "original": "is_original=1", "random": "sort=random&size=20"}
            q = qmap.get(tab, "sort=latest")
            url = "/api/videos/category/%s?page=%d" % (cat.get("api") or cat["type_id"], page)
            if q:
                url += "&" + q
            d = self._api(url) or {}
            result["list"] = self.parse_api_list(d.get("items") or [])
            self._apply_page(result, d.get("pagination") or {}, page, len(result["list"]))
        self._cache_page(("cate", str(tid), str(page), str(extend)), result.get("list"))
        return result

    def _video_vod(self, vid):
        m = re.search(r'(\d+)', str(vid or ""))
        if not m:
            return None
        vid = m.group(1)
        html = self.getHtml("%s/detail/%s/" % (self.host, vid))
        if not html:
            return None
        vod = {"vod_id": vid}
        title = re.search(r'<title>([^|<]*)', html)
        if title:
            vod["vod_name"] = re.sub(r'\s*-\s*(短剧视频在线观看|黄果短剧|短剧).*$', '', title.group(1).strip()).strip() or vid
        else:
            vod["vod_name"] = vid
        pic = re.search(r'(?:data-src|src)="(https?://pic[^"]*)"', html)
        if pic:
            vod["vod_pic"] = self.proc_pic(pic.group(1))
        else:
            vod["vod_pic"] = ""
        eps = re.findall(r'<a[^>]*href="(/video/%s(?:/ep-\d+)?/)"[^>]*data-ep-id="(\d+)"[^>]*>(.*?)</a>' % re.escape(vid), html, re.S)
        if eps:
            ep_map = {}
            for href, eid, name in eps:
                ep_map[int(eid)] = (href, re.sub(r'<[^>]+>', '', name).strip())
            play_urls = []
            for eid in sorted(ep_map.keys()):
                href, name = ep_map[eid]
                label = name if name else "第%02d集" % eid
                play_urls.append("%s$%s" % (label, self.fix_url(href)))
            vod["vod_play_from"] = "黄果短剧"
            vod["vod_play_url"] = "#".join(play_urls)
        else:
            data = None
            dm = re.search(r'<script id="videoInitialData" type="application/json">(.*?)</script>', html, re.S)
            if dm:
                try:
                    data = json.loads(dm.group(1).replace("\\u0026", "&"))
                except Exception:
                    data = None
            if data and data.get("epPlaySrcs"):
                vod["vod_pic"] = self.proc_pic(data.get("coverSrc")) or vod["vod_pic"]
                eps = data.get("epPlaySrcs") or {}
                play_urls = []
                for ep_id in sorted(eps.keys(), key=lambda x: int(x)):
                    play_urls.append("第%02d集$%s" % (int(ep_id), self.proxy_play(eps[ep_id])))
                vod["vod_play_from"] = "黄果短剧"
                vod["vod_play_url"] = "#".join(play_urls)
            else:
                vod["vod_play_from"] = "黄果短剧"
                vod["vod_play_url"] = "第01集$/video/%s/" % vid
        return vod

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) else ids
        if isinstance(vid, str) and vid.startswith("nid:"):
            vid = unquote(vid[4:])
        if isinstance(vid, str) and vid.startswith("folder_topic_"):
            return self.topicFolderDetail(vid)
        if isinstance(vid, str) and (vid.startswith("/topics/") or vid.startswith("/archives/")):
            if vid.startswith("/topics/"):
                return self.topicDetail(vid)
            return self.postDetail(vid)
        vod = self._video_vod(vid)
        if not vod:
            return result
        oid = str(vod.get("vod_id") or vid)
        src = self._src_from_vod(vod)
        if src:
            self._src_cache[oid] = src
        self._load_after(oid)
        vod["vod_play_from"], vod["vod_play_url"] = self._build_page_play(
            oid, vod.get("vod_name") or "", vod.get("vod_play_from"), vod.get("vod_play_url"))
        result["list"] = [vod]
        return result

    def topicFolderList(self, tid, page):
        result = {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        try:
            path = base64.urlsafe_b64decode(tid[len("folder_topic_"):].encode("utf-8")).decode("utf-8")
        except Exception:
            return result
        slug = str(path).strip("/").split("/")[-1]
        d = self._api("/api/topics/%s?page=%d" % (slug, page)) or {}
        videos = d.get("videos") if isinstance(d.get("videos"), dict) else {}
        result["list"] = self.parse_api_list(videos.get("items") or [])
        self._apply_page(result, videos.get("pagination") or {}, page, len(result["list"]))
        return result

    def topicFolderDetail(self, tid):
        result = {"list": []}
        try:
            path = base64.urlsafe_b64decode(tid[len("folder_topic_"):].encode("utf-8")).decode("utf-8")
        except Exception:
            return result
        html = self.getHtml(self.fix_url(path))
        if not html:
            return result
        cards = self.extract_cards(re.sub(r'<template[\s\S]*?</template>', '', html))
        seen = set()
        unique = []
        for c in cards:
            if c["vod_id"] not in seen:
                seen.add(c["vod_id"])
                unique.append(c)
        if not unique:
            return result
        title = re.search(r'<title>([^<]*)', html)
        name = title.group(1).strip() if title else "专辑"
        name = re.sub(r'\s*[·\-]\s*黄果短剧.*$', '', name).strip() or "专辑"
        vod = {
            "vod_id": tid,
            "vod_name": name,
            "vod_pic": unique[0]["vod_pic"],
            "vod_remarks": "专辑目录",
            "vod_content": "目录入口，点击播放进入视频列表",
            "vod_play_from": "目录",
            "vod_play_url": "打开$" + tid
        }
        result["list"] = [vod]
        return result

    def topicDetail(self, vid):
        result = {"list": []}
        html = self.getHtml(self.fix_url(vid))
        if not html:
            return result
        cards = self.extract_cards(re.sub(r'<template[\s\S]*?</template>', '', html))
        seen = set()
        unique = []
        for c in cards:
            if c["vod_id"] not in seen:
                seen.add(c["vod_id"])
                unique.append(c)
        result["list"] = unique
        return result

    def postDetail(self, vid):
        result = {"list": []}
        html = self.getHtml(self.fix_url(vid))
        if not html:
            return result
        vod = {"vod_id": vid}
        title = re.search(r'<h1[^>]*>([^<]*)', html)
        if title:
            vod["vod_name"] = title.group(1).strip()
        else:
            t = re.search(r'<title>([^<]*)', html)
            vod["vod_name"] = t.group(1).strip() if t else vid
        pic = re.search(r'data-src="(https?://pic[^\"]*)"', html)
        if pic:
            vod["vod_pic"] = self.proc_pic(pic.group(1))
        else:
            vod["vod_pic"] = ""
        players = re.findall(r'class="post-video-player"[^>]*data-src="([^"]*)"', html)
        if players:
            play_urls = []
            for idx, src in enumerate(players, 1):
                play_urls.append("第%02d集$%s" % (idx, self.proxy_play(src.replace("\\u0026", "&"))))
            vod["vod_play_from"] = "黄果短剧"
            vod["vod_play_url"] = "#".join(play_urls)
        else:
            m3u8s = re.findall(r'(https?://[^\s"<>\\]*\.m3u8[^\s"<>\\]*)', html)
            if m3u8s:
                seen = []
                for u in m3u8s:
                    u = u.replace("\\u0026", "&")
                    if u not in seen:
                        seen.append(u)
                vod["vod_play_from"] = "黄果短剧"
                vod["vod_play_url"] = "#".join("第%02d集$%s" % (i + 1, self.proxy_play(u)) for i, u in enumerate(seen))
            else:
                vod["vod_play_from"] = "黄果短剧"
                vod["vod_play_url"] = "第01集$" + vid
        result["list"] = [vod]
        return result

    def searchContent(self, key, quick, pg):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        page = int(pg) if pg else 1
        url = "%s/search/?keyword=%s" % (self.host, quote(key))
        if page > 1:
            url += "&page=%d" % page
        html = self.getHtml(url)
        if not html:
            return result
        result["list"] = self.extract_cards(re.sub(r'<template[\s\S]*?</template>', '', html))
        total = re.search(r'data-track-search-total="(\d+)"', html)
        if total:
            result["total"] = int(total.group(1))
        result["page"] = page
        self._cache_page(("search", str(key), str(page)), result.get("list"))
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        if isinstance(id, str) and id.startswith("nid:"):
            id = self._nid_url(unquote(id[4:]), flag)
        if isinstance(id, str) and id.startswith("folder_topic_"):
            return {"parse": 1, "url": id, "header": {}}
        play_url = self.fix_url(id) if id else ""
        if play_url.startswith("/proxy?") or play_url.startswith("/local/") or play_url.startswith("http://127.0.0.1"):
            result["url"] = play_url
            result["header"] = json.dumps({"User-Agent": self.header["User-Agent"], "Referer": self.host})
            return result
        if 'm3u8' in play_url or '.mp4' in play_url:
            result["url"] = self.proxy_play(play_url)
            result["header"] = json.dumps({"User-Agent": self.header["User-Agent"], "Referer": self.host})
            return result
        if re.fullmatch(r'\d+', play_url):
            d = self.detailContent([play_url])
            if d["list"]:
                first = d["list"][0].get("vod_play_url", "").split("#")[0]
                if "$" in first:
                    play_url = self.fix_url(first.split("$", 1)[1])
        if play_url.startswith("/proxy?") or play_url.startswith("/local/") or play_url.startswith("http://127.0.0.1"):
            result["url"] = play_url
            result["header"] = json.dumps({"User-Agent": self.header["User-Agent"], "Referer": self.host})
            return result
        html = self.getHtml(play_url)
        if not html:
            return result
        m3u8 = ""
        m = re.search(r'"videoSrc"\s*:\s*"([^"]*)"', html)
        if m:
            m3u8 = m.group(1).replace("\\u0026", "&")
        if not m3u8:
            m = re.search(r'<video[^>]*>\s*<source[^>]*src="([^"]*)"', html)
            if m:
                m3u8 = m.group(1)
        if not m3u8:
            m = re.search(r'(https?://[^\s"<>\\]*\.m3u8[^\s"<>\\]*)', html)
            if m:
                m3u8 = m.group(1).replace("\\u0026", "&")
        result["url"] = self.proxy_m3u8_url(m3u8) if m3u8 else ""
        result["header"] = json.dumps({"User-Agent": self.header["User-Agent"], "Referer": self.host})
        return result

    def proxy_m3u8_url(self, url):
        return self._proxy_base("m3u8", url)

    def proxy_ts_url(self, url):
        return self._proxy_base("ts", url)

    def proxy_key_url(self, url):
        return self._proxy_base("key", url)

    def _proxy_base(self, typ, url):
        b = self.getProxyUrl()
        if "?" not in b:
            b += "?do=py"
        return b + "&type=" + typ + "&url=" + quote(url)

    def proxy_play(self, url):
        url = self.fix_url(url)
        if url.startswith("/proxy?") or url.startswith("/local/") or url.startswith("http://127.0.0.1"):
            return url
        if "m3u8" in url.lower():
            return self.proxy_m3u8_url(url)
        return url

    def _proxy_m3u8(self, url):
        try:
            r = requests.get(url, headers=self.header, timeout=20, verify=False)
            if r.status_code != 200:
                return [502, "text/plain", "err:%d" % r.status_code]
            text = r.text
            host_base = re.match(r'https?://[^/]+', url)
            host_base = host_base.group(0) if host_base else ""
            path_dir = url[:url.rfind("/") + 1] if "/" in url else ""
            lines = []
            for line in text.split("\n"):
                s = line.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    if 'URI="' in s:
                        mm = re.search(r'URI="([^"]*)"', s)
                        if mm:
                            u = mm.group(1)
                            if u.startswith("//"):
                                u = "https:" + u
                            elif u.startswith("/"):
                                u = host_base + u
                            elif not re.match(r'https?://', u):
                                u = path_dir + u
                            s = s[:mm.start(1)] + self.proxy_key_url(u) + s[mm.end(1):]
                    lines.append(s)
                    continue
                if re.match(r'https?://', s):
                    turl = s
                elif s.startswith("//"):
                    turl = "https:" + s
                elif s.startswith("/"):
                    turl = host_base + s
                else:
                    turl = path_dir + s
                lines.append(self.proxy_ts_url(turl))
            return [200, "application/vnd.apple.mpegurl", "\n".join(lines).encode("utf-8")]
        except Exception:
            return [502, "text/plain", "err"]

    def _proxy_ts(self, url):
        try:
            r = requests.get(url, headers=self.header, timeout=20, verify=False)
            if r.status_code != 200:
                return [502, "text/plain", "err:%d" % r.status_code]
            return [200, "video/mp2t", r.content]
        except Exception:
            return [502, "text/plain", "err"]

    def _proxy_key(self, url):
        try:
            r = requests.get(url, headers=self.header, timeout=20, verify=False)
            if r.status_code != 200:
                return [502, "text/plain", "err:%d" % r.status_code]
            return [200, "application/octet-stream", r.content]
        except Exception:
            return [502, "text/plain", "err"]

    def _proxy_pic(self, url):
        try:
            r = requests.get(url, headers=self.header, timeout=15, verify=False)
            ct = r.content
            if ct[:3] == b"\xff\xd8\xff":
                return [200, "image/jpeg", ct]
            if ct[:8] == b"\x89PNG\r\n\x1a\n":
                return [200, "image/png", ct]
            if ct[:4] == b"RIFF" and ct[8:12] == b"WEBP":
                return [200, "image/webp", ct]
            if ct[:3] == b"GIF":
                return [200, "image/gif", ct]
            if AES and len(ct) % 16 == 0:
                dec = AES.new(self.key, AES.MODE_CBC, self.iv).decrypt(ct)
                if dec[:3] == b"\xff\xd8\xff":
                    return [200, "image/jpeg", dec]
                if dec[:8] == b"\x89PNG\r\n\x1a\n":
                    return [200, "image/png", dec]
                if dec[:4] == b"RIFF" and dec[8:12] == b"WEBP":
                    return [200, "image/webp", dec]
                if dec[:3] == b"GIF":
                    return [200, "image/gif", dec]
                return [200, "image/jpeg", dec]
            return [200, "image/jpeg", ct]
        except Exception:
            return [404, "text/plain", "err"]

    def localProxy(self, param):
        if not param:
            return [404, "text/plain", "nf"]
        typ = param.get("type") or ""
        url = param.get("url") or param.get("pic") or ""
        if not url:
            return [404, "text/plain", "nf"]
        url = unquote(url)
        if typ == "m3u8":
            return self._proxy_m3u8(url)
        if typ == "ts":
            return self._proxy_ts(url)
        if typ == "key":
            return self._proxy_key(url)
        return self._proxy_pic(url)