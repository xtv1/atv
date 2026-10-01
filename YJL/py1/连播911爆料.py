# -*- coding: utf-8 -*-
# 回家邮箱 911blcgw@gmail.com，https://telegram.me/cgblw911
import sys
import re
import json
import html
import time
import socket
import threading
import requests
import urllib3
from urllib.parse import urljoin, quote, unquote, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from lxml import etree
except ImportError:
    etree = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def __init__(self, *args, **kwargs):
            self.t4_api = kwargs.get("t4_api", "")
        def getName(self): return "Spider"
        def init(self, extend=""): pass
        def homeContent(self, filter=False): return {'class': [], 'filters': {}}
        def homeVideoContent(self): return {'list': []}
        def categoryContent(self, tid, pg, filter=False, extend=None): return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 0}
        def detailContent(self, ids): return {'list': []}
        def playerContent(self, flag, id, vipFlags=None): return {'parse': 0, 'url': '', 'header': {}}
        def searchContent(self, key, quick=False, pg="1"): return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 0}
        def localProxy(self, param): return [200, "text/plain", b""]
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def getProxyUrl(self, flag=False): return getattr(self, "t4_api", "")
        def destroy(self): pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_PIN_MAP = {}
_PIN_INSTALLED = [False]
_POISON_IP_PREFIX = ('31.13.94.', '31.13.95.', '75.126.', '157.240.')
_PIN_CACHE_TTL = 1800
_PIN_TIME = {}


def _install_pin():
    if _PIN_INSTALLED[0]:
        return
    _PIN_INSTALLED[0] = True
    _orig = socket.getaddrinfo

    def _pinned(host, port, *args, **kwargs):
        _ips = _PIN_MAP.get(host)
        if _ips:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port)) for ip in _ips]
        return _orig(host, port, *args, **kwargs)

    socket.getaddrinfo = _pinned


def _ip_alive(ip, port=443, timeout=1.0):
    try:
        c = socket.create_connection((ip, port), timeout=timeout)
        c.close()
        return True
    except Exception:
        return False


def _doh_resolve(hostname):
    picked = []
    for _u in (
        'https://cloudflare-dns.com/dns-query',
        'https://dns.google/resolve',
        'https://doh.pub/dns-query',
        'https://dns.alidns.com/resolve',
    ):
        try:
            _r = requests.get(_u, params={'name': hostname, 'type': 'A'},
                              headers={'accept': 'application/dns-json'}, timeout=2, verify=False)
            for _a in _r.json().get('Answer', []):
                _d = _a.get('data') if _a.get('type') == 1 else ''
                if _d and not _d.startswith('0.') and not _d.startswith(_POISON_IP_PREFIX):
                    picked.append(_d)
            if picked:
                break
        except Exception:
            continue
    if len(picked) > 1:
        picked = [ip for ip in picked[:3] if _ip_alive(ip)] + picked[3:]
    return picked


def _doh_pin_domain(hostname):
    try:
        if not hostname:
            return
        _install_pin()
        now = time.time()
        if hostname in _PIN_MAP and now - _PIN_TIME.get(hostname, 0) < _PIN_CACHE_TTL:
            return
        picked = _doh_resolve(hostname)
        if picked:
            _PIN_MAP[hostname] = picked
            _PIN_TIME[hostname] = now
    except Exception:
        pass


def _pin_url_host(url):
    try:
        _m = re.match(r'https?://([^/:]+)', url or '')
        if _m:
            _doh_pin_domain(_m.group(1))
    except Exception:
        pass

CACHE_STORE = {}
CACHE_LOCK = threading.Lock()

def get_cache(key):
    with CACHE_LOCK:
        if key in CACHE_STORE:
            val, expire_time = CACHE_STORE[key]
            if time.time() < expire_time:
                return val
            del CACHE_STORE[key]
    return None

def set_cache(key, val, ttl=180):
    with CACHE_LOCK:
        if len(CACHE_STORE) > 500:
            now = time.time()
            expired = [k for k, v in CACHE_STORE.items() if now >= v[1]]
            for k in expired:
                del CACHE_STORE[k]
            if len(CACHE_STORE) > 500:
                CACHE_STORE.clear()
        CACHE_STORE[key] = (val, time.time() + ttl)

def _page(pg):
    try:
        v = int(str(pg or "").strip())
        return v if v > 0 else 1
    except Exception:
        return 1

class Spider(BaseSpider):
    AES_KEY = b"f5d965df75336270"
    AES_IV = b"97b60394abc2fbe1"

    _IMG_ATTRS = ("z-image-loader-url", "data-xkrkllgl", "data-original", "data-src",
                  "data-lazy-src", "data-cover", "data-thumb", "data-echo", "data-bg", "src")
    _BAD_PIC_MARKS = ("placeholder", "loading", "blank", "1px", "default", "ads")

    AD_KEYWORDS = {
        "app", "911爆料app", "下载app", "官方推荐", "加入911", "章鱼导航", "欲洛降临",
        "七夕活动", "911暑期活动", "回家的路", "投稿方式", "常见问题", "广告商务",
        "所有标签", "关于我们", "官方tg群", "官方推特", "ai换脸脱衣", "广告", "商务合作"
    }

    CATEGORY_GROUPS = [
        ("18+精选", [("mrds", "每日大赛"), ("hjsq", "海角社区"), ("aidj", "AI短剧"),
                     ("crfys", "午夜剧场"), ("dmhv", "动漫天堂"), ("sgpjs", "水果派解说")]),
        ("吃瓜爆料", [("rmgb", "独家爆料"), ("rlph", "黑料排行"), ("ssdbl", "热点吃瓜"),
                     ("xyss", "校园吃瓜")]),
        ("名人黑料", [("bgzq", "反差爆料"), ("whbl", "网红黑料"), ("mxhl", "明星吃瓜")]),
        ("猎奇社区", [("blqw", "猎奇吃瓜"), ("tksm", "偷窥泄密"), ("zksr", "SM专区"),
                     ("ntll", "男男女女")]),
        ("尤物品鉴", [("thjx", "探花经典"), ("fljq", "福利视频"), ("crlz", "网黄专辑"),
                     ("slec", "影视床戏"), ("kpzj", "看片专辑")]),
    ]

    DOMAIN_POOL = [
        "https://d10cq29fdobmmg.cloudfront.net",
        "https://catch.belwfufv.cc",
        "https://911bla.com",
        "https://911bl16.com",
        "https://911bl.com",
        "https://carry.cyepzjnb.com",
        "https://admire.cyepzjnb.com"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t4_api = kwargs.get("t4_api", "")
        self.host = self.DOMAIN_POOL[0]
        self.ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        self.headers = {
            "User-Agent": self.ua,
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=25, pool_maxsize=50, max_retries=Retry(total=1, backoff_factor=0.1))
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(self.headers)
        self.ext = ""
        self._last_detail_url = ""
        self._img_cache = {}
        self._img_lock = threading.Lock()
        self._group_subs = {gname: subs for gname, subs in self.CATEGORY_GROUPS}
        self.categories = self._build_categories()
        self.page_cache = {}
        self.page_index = {}
        self.page_keys = []

    def _build_categories(self):
        cats = [{"type_id": "category/jrgb", "type_name": "今日大瓜"}]
        for gname, _ in self.CATEGORY_GROUPS:
            cats.append({"type_id": gname, "type_name": gname})
        return cats

    def getName(self):
        return "911爆料网"

    def _select_fastest_host(self):
        cache_key = "fastest_911_host"
        cached = get_cache(cache_key)
        if cached:
            return cached

        probe_path = "/category/jrgb/"
        results = {}
        threads = []

        def test_host(u):
            try:
                _pin_url_host(u)
                st = time.time()
                r = requests.get(u + probe_path, headers=self.headers, timeout=3, allow_redirects=True, verify=False)
                cost = (time.time() - st) * 1000
                if r.status_code != 200:
                    results[u] = None
                    return
                if not self._looks_like_content(r.text):
                    results[u] = None
                    return
                cards = self._extract_cards(r.text)
                results[u] = (cost, len(cards)) if len(cards) >= 5 else None
            except Exception:
                results[u] = None

        for u in self.DOMAIN_POOL:
            t = threading.Thread(target=test_host, args=(u,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=3.5)

        valid = {k: v for k, v in results.items() if v}
        best = min(valid.items(), key=lambda x: x[1][0])[0] if valid else self.DOMAIN_POOL[0]
        set_cache(cache_key, best, ttl=900)
        return best

    def setExtendInfo(self, extend):
        self.ext = extend or ""
        if isinstance(extend, str) and extend.startswith("http"):
            self.host = extend.rstrip("/")
        elif isinstance(extend, dict) and extend.get("host"):
            self.host = str(extend["host"]).rstrip("/")
        else:
            self.host = self._select_fastest_host()

        self.headers["Referer"] = self.host + "/"
        self.session.headers.update(self.headers)
        _pin_url_host(self.host)
        return None

    def init(self, extend=""):
        raw = getattr(self, "ext", "") or extend or ""
        self.setExtendInfo(raw)
        return None

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(?:m3u8|mp4|flv|m4a)(?:$|[?#])', str(url or ''), re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if hasattr(self, "session") and self.session:
            try:
                self.session.close()
            except Exception:
                pass

    def _fix_url(self, url):
        if not url:
            return ""
        url = str(url).strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin(self.host, url)

    @staticmethod
    def _clean_url(u):
        return str(u or "").replace(r"\/", "/").replace("\\", "").strip()

    def _proxy_base(self):
        try:
            f = getattr(self, "getProxyUrl", None)
            url = f() if callable(f) else ""
            if url:
                return url
        except Exception:
            pass
        return getattr(self, "t4_api", "")

    def _wrap_media_proxy(self, url):
        try:
            if not url:
                return url
            if not re.search(r'\.(?:m3u8|mp4)(?:$|[?#])', str(url), re.I):
                return url
            b = self._proxy_base()
            if not b:
                return url
            _pin_url_host(url)
            sep = "&" if "?" in b else "?"
            return b + sep + "type=m3u8&url=" + quote(url, safe="")
        except Exception:
            return url

    def _fix_pic(self, pic):
        if not pic:
            return ""
        pic_url = self._fix_url(pic)
        base = self._proxy_base()
        if base and pic_url.startswith("http"):
            sep = "&" if "?" in base else "?"
            return f"{base}{sep}type=img&url={quote(pic_url, safe='')}"
        if "@Referer=" not in pic_url and pic_url.startswith("http"):
            pic_url += f"@Referer={self.host}/&User-Agent={self.ua}"
        return pic_url

    @staticmethod
    def _looks_like_content(html_text):
        if not html_text or len(html_text) < 500:
            return False
        return bool(re.search(r"/(?:archives|article|post|detail)/\d+", html_text, re.I))

    def _ensure_session(self):
        if not hasattr(self, "session") or not self.session:
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        return self.session

    def _req_headers(self):
        return {
            "Referer": self.host + "/",
            "User-Agent": self.ua
        }

    def _fetch(self, url, retry_backup=True):
        self._ensure_session()

        _pin_url_host(url)
        candidates = [url]
        if retry_backup:
            for b_host in self.DOMAIN_POOL:
                parsed = urlparse(url)
                if parsed.netloc and parsed.netloc != urlparse(b_host).netloc:
                    candidates.append(url.replace(f"{parsed.scheme}://{parsed.netloc}", b_host))

        for target_url in candidates:
            try:
                r = self.session.get(target_url, headers=self.headers, timeout=(2.5, 5), verify=False)
                if r.status_code == 200:
                    r.encoding = "utf-8"
                    if self._looks_like_content(r.text):
                        return r.text
            except Exception:
                continue
        return ""

    def _decrypt_image_bytes(self, data):
        if not data:
            return b""
        if AES:
            try:
                cipher = AES.new(self.AES_KEY, AES.MODE_CBC, self.AES_IV)
                raw = cipher.decrypt(data)
                pad = raw[-1] if raw else 0
                if 0 < pad <= 16 and raw.endswith(bytes([pad]) * pad):
                    return raw[:-pad]
                return raw
            except Exception:
                pass
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV), backend=default_backend())
            decryptor = cipher.decryptor()
            raw = decryptor.update(data) + decryptor.finalize()
            pad = raw[-1] if raw else 0
            if 0 < pad <= 16 and raw.endswith(bytes([pad]) * pad):
                return raw[:-pad]
            return raw
        except Exception:
            pass
        return data

    def _mime_from_bytes(self, data):
        if data.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return "gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "webp"
        return "jpeg"

    @staticmethod
    def _good_pic_val(val):
        v = str(val).strip()
        return bool(v) and not v.startswith("data:image") and not any(x in v.lower() for x in Spider._BAD_PIC_MARKS)

    def _extract_pic_from_node(self, node, raw_str=""):
        if not raw_str and node is not None:
            raw_str = str(node)

        script_match = re.search(r"loadBannerDirect\(['\"]([^'\"]+)['\"]", raw_str)
        if script_match:
            return script_match.group(1).strip()

        if hasattr(node, "xpath") and etree:
            meta_imgs = node.xpath('.//meta[@itemprop="image" or @itemprop="thumbnailUrl"]/@content')
            if meta_imgs and meta_imgs[0].strip():
                return meta_imgs[0].strip()
        elif hasattr(node, "select_one"):
            meta_img = node.select_one('meta[itemprop="image"], meta[itemprop="thumbnailUrl"]')
            if meta_img and meta_img.get("content"):
                return meta_img.get("content").strip()

        if hasattr(node, "xpath") and etree:
            for attr in self._IMG_ATTRS:
                vals = node.xpath(f'.//img/@{attr}')
                if vals and self._good_pic_val(vals[0]):
                    return str(vals[0]).strip()
        elif hasattr(node, "select_one"):
            img = node.select_one("img")
            if img:
                for attr in self._IMG_ATTRS:
                    val = img.get(attr, "")
                    if self._good_pic_val(val):
                        return val

        bg_match = re.search(r'background-image\s*:\s*url\([\'"]?([^\'")]+)[\'"]?\)', raw_str, re.I)
        if bg_match and self._good_pic_val(bg_match.group(1)):
            return bg_match.group(1).strip()

        return ""

    def _is_valid_item(self, title, href, pic, raw_node=""):
        if not title or not href:
            return False
        clean_title = title.strip().lower()
        if clean_title in self.AD_KEYWORDS:
            return False
        if len(clean_title) <= 3 and clean_title in ["app", "vip", "gg", "ad", "ads"]:
            return False
        if raw_node and any(x in raw_node for x in ['rel="sponsored"', 'data-event="ad_click"', 'class="ad', 'class="advert', 'class="sticky-ad']):
            return False
        if not re.search(r"/(?:archives|article|post|detail)/\d+", href) and not re.search(r"/\d+\.html", href):
            return False
        if not pic or not str(pic).strip():
            return False
        return True

    def _make_card(self, href, title, remark, pic):
        return {
            "vod_id": self._fix_url(href),
            "vod_name": title[:100],
            "vod_pic": self._fix_pic(pic),
            "vod_remarks": remark
        }

    def _extract_cards(self, html_text):
        videos = []
        if not html_text:
            return videos

        if etree:
            try:
                parser = etree.HTMLParser(recover=True, encoding="utf-8")
                tree = etree.HTML(html_text.encode("utf-8", errors="ignore"), parser=parser)
                if tree is not None:
                    items = tree.xpath('//div[@id="index" or @id="archive"]//article[.//a[contains(@href,"/archives/")]] | //ul[contains(@class,"row")]/li[.//a] | //article[.//a]')
                    for item in items:
                        try:
                            hrefs = item.xpath('.//a[contains(@href,"/archives/") or contains(@href,"/article/")]/@href') or item.xpath('.//a/@href')
                            href = str(hrefs[0]).strip() if hrefs else ""
                            titles = item.xpath('.//h2[contains(@class,"headline")]//text() | .//h2//text() | .//h3//text() | .//*[contains(@class,"post-card-bottom-text")]//text()')
                            title = "".join(titles).strip()
                            remarks = item.xpath('.//span[@itemprop="datePublished"]//text() | .//span[contains(@class,"small")]//text() | .//time//text() | .//span[contains(@class,"text-muted")]//text()')
                            remark = "".join(remarks).strip()
                            raw_str = etree.tostring(item, encoding="utf-8").decode("utf-8", errors="ignore")
                            pic = self._extract_pic_from_node(item, raw_str)

                            if not self._is_valid_item(title, href, pic, raw_str):
                                continue

                            videos.append(self._make_card(href, title, remark, pic))
                        except Exception:
                            continue
            except Exception:
                pass

        if not videos and BeautifulSoup:
            doc = BeautifulSoup(html_text, "html.parser")
            containers = doc.select("div#index article, div#archive article, ul.row li, div.article-item, article, .post-item, .video-item, div[class*='item']")
            for item in containers:
                try:
                    title_elem = item.select_one("h2.headline, .headline, h2 a, h3 a, a[title], .post-card-bottom-text, .title, h2, h3")
                    title = title_elem.get("title") or title_elem.get_text(strip=True) if title_elem else ""
                    a_elem = item.select_one("a[href*='/archives/'], a[href*='/article/'], a[href*='/post/'], a")
                    href = a_elem.get("href", "") if a_elem else ""
                    remark_elem = item.select_one("span[itemprop='datePublished'], span.small, time, .date, .time, span.text-muted, .item-meta")
                    remark = remark_elem.get_text(strip=True) if remark_elem else ""
                    pic = self._extract_pic_from_node(item, str(item))

                    if not self._is_valid_item(title, href, pic, str(item)):
                        continue

                    videos.append(self._make_card(href, title, remark, pic))
                except Exception:
                    continue

        return videos

    def _t(self, s):
        return str(s or "").replace("$", " ").replace("#", " ").strip()

    def _list_filt(self, extend):
        if isinstance(extend, dict):
            return json.dumps(extend, sort_keys=True, ensure_ascii=False)
        return str(extend or "")

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

    def _split_eps(self, raw):
        eps = []
        for p in str(raw or "").split("#"):
            if not p:
                continue
            n, u = p.split("$", 1) if "$" in p else ("", p)
            eps.append((self._t(n), u))
        return eps

    def _playlist_items(self, vid, limit=20):
        vid = str(vid)
        key = self.page_index.get(vid)
        items = list(self.page_cache.get(key, [])) if key else []
        idx = next((i for i, it in enumerate(items) if str(it.get("vod_id")) == vid), -1)
        if idx < 0:
            return []
        out, seen = [], set()

        def _take(rows):
            for it in rows:
                oid = str(it.get("vod_id") or "")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                out.append(it)
                if len(out) >= limit:
                    return True
            return False

        if _take(items[idx:]) or not isinstance(key, tuple) or len(key) < 4:
            return out
        kind, tid, filt, pg = key[0], key[1], key[2], key[3]
        try:
            n = int(str(pg) or "1")
        except Exception:
            return out
        for _ in range(4):
            n += 1
            before = len(out)
            try:
                if kind == "search":
                    r = self.searchContent(tid, False, str(n))
                else:
                    extend = json.loads(filt) if filt and str(filt).startswith("{") else None
                    r = self.categoryContent(tid, str(n), False, extend)
                nxt = (r or {}).get("list") or []
            except Exception:
                nxt = []
            if not nxt or _take(nxt) or len(out) == before:
                break
        return out

    def _build_page_play(self, vid, film, play_from, play_url):
        vid = str(vid)
        film = self._t(film) or vid
        froms = [x for x in str(play_from or "").split("$$$") if x]
        items = self._playlist_items(vid)
        if not froms or not items:
            return play_from, play_url
        groups = str(play_url or "").split("$$$")
        outs = []
        for i, _n in enumerate(froms):
            raw = groups[i] if i < len(groups) else (groups[0] if groups else "")
            eps = self._split_eps(raw)
            parts = []
            for it in items:
                oid = str(it.get("vod_id") or "")
                if not oid:
                    continue
                name = film if oid == vid else (self._t(it.get("vod_name")) or oid)
                if oid == vid and len(eps) > 1:
                    for j, (_en, u) in enumerate(eps):
                        parts.append("%s$%s" % (self._t("%s %02d" % (name, j + 1)), u or ("nid:%s" % quote(oid, safe=""))))
                elif oid == vid and eps and eps[0][1]:
                    parts.append("%s$%s" % (name, eps[0][1]))
                else:
                    parts.append("%s$nid:%s" % (name, quote(oid, safe="")))
            if parts:
                outs.append("#".join(parts))
        if not outs:
            return play_from, play_url
        return "$$$".join(froms[:len(outs)]), "$$$".join(outs)

    def _load_src(self, vid):
        vod = self._load_detail_vod(vid) or {}
        froms = [x for x in str(vod.get("vod_play_from") or "").split("$$$") if x]
        groups = str(vod.get("vod_play_url") or "").split("$$$")
        src = []
        for i, name in enumerate(froms):
            raw = groups[i] if i < len(groups) else (groups[0] if groups else "")
            src.append((name, self._split_eps(raw)))
        return src

    def homeContent(self, filter=False):
        filters = {}
        for gname, subs in self.CATEGORY_GROUPS:
            filters[gname] = [{
                "key": "sub",
                "name": "子分类",
                "value": [{"n": "全部", "v": ""}] + [{"n": name, "v": sid} for sid, name in subs]
            }]
        return {
            "class": self.categories,
            "filters": filters
        }

    def homeVideoContent(self):
        return self.categoryContent("category/jrgb", "1")

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = _page(pg)
        raw = str(tid or "category/jrgb").strip("/")
        group_name, sub_id = self._split_tid(raw)
        page_key = ("cate", str(tid or ""), self._list_filt(extend), str(page))

        if group_name:
            sel = (extend or {}).get("sub") or ""
            if sel in dict(self._group_subs.get(group_name, [])):
                sub_id, group_name = sel, None
            else:
                cache_key = f"cate_group_{group_name}"
                cached = get_cache(cache_key)
                if cached:
                    self._cache_page(page_key, (cached or {}).get("list"))
                    return cached
                videos = self._fetch_group(group_name)
                res = {"list": videos, "page": page, "pagecount": page,
                       "limit": len(videos) if videos else 20, "total": len(videos)}
                if videos:
                    set_cache(cache_key, res, ttl=180)
                self._cache_page(page_key, res.get("list"))
                return res

        cache_key = f"cate_{sub_id}_{page}"
        cached = get_cache(cache_key)
        if cached:
            self._cache_page(page_key, (cached or {}).get("list"))
            return cached

        url = f"{self.host}/category/{sub_id}/{page}/" if page > 1 else f"{self.host}/category/{sub_id}/"
        html_text = self._fetch(url)
        videos = self._extract_cards(html_text)

        res = {
            "list": videos,
            "page": page,
            "pagecount": page + 1 if len(videos) >= 10 else page,
            "limit": len(videos) if videos else 20,
            "total": 9999
        }
        if videos:
            set_cache(cache_key, res, ttl=180)
        self._cache_page(page_key, res.get("list"))
        return res

    def _split_tid(self, raw):
        parts = raw.split("/") if raw else []
        if len(parts) >= 2:
            return None, parts[-1]
        if raw in self._group_subs:
            return raw, None
        return None, raw or "jrgb"

    def _fetch_group(self, group_name):
        videos, seen = [], set()
        for sub_id, _ in self._group_subs.get(group_name, []):
            html_text = self._fetch(f"{self.host}/category/{sub_id}/")
            for v in self._extract_cards(html_text):
                if v["vod_id"] not in seen:
                    seen.add(v["vod_id"])
                    videos.append(v)
        return videos

    def _extract_video_urls(self, html_text):
        play_urls = []
        seen_urls = set()

        if BeautifulSoup:
            doc = BeautifulSoup(html_text, "html.parser")
            for d in doc.select(".dplayer[data-config], div[data-config]"):
                raw_conf = html.unescape(d.get("data-config") or "")
                url = ""
                try:
                    cfg = json.loads(raw_conf)
                    video_cfg = cfg.get("video") or {}
                    url = video_cfg.get("url") or ""
                except Exception:
                    m = re.search(r'"video"\s*:\s*\{.*?\"url\"\s*:\s*"([^"]+)"', raw_conf)
                    if m: url = m.group(1)
                if url:
                    clean_u = self._fix_url(self._clean_url(url))
                    if clean_u and clean_u not in seen_urls:
                        seen_urls.add(clean_u)
                        play_urls.append(clean_u)

            for v in doc.select("video[src], source[src]"):
                u = (v.get("src") or "").strip()
                if u and not u.endswith((".jpg", ".png", ".gif")):
                    clean_u = self._fix_url(u)
                    if clean_u not in seen_urls:
                        seen_urls.add(clean_u)
                        play_urls.append(clean_u)

            for ifr in doc.select("iframe[src]"):
                u = (ifr.get("src") or "").strip()
                pm = re.search(r"[?&]url=([^&]+)", u)
                if pm:
                    clean_u = self._fix_url(unquote(pm.group(1)).strip())
                    if clean_u and clean_u not in seen_urls:
                        seen_urls.add(clean_u)
                        play_urls.append(clean_u)
                elif any(x in u.lower() for x in ["player", "play", "m3u8", "dp", "video"]):
                    clean_u = self._fix_url(u)
                    if clean_u not in seen_urls:
                        seen_urls.add(clean_u)
                        play_urls.append(clean_u)

        for m in re.finditer(r'video\s*:\s*\{[^\}]*?url\s*:\s*["\']([^"\']+)["\']', html_text, re.I | re.S):
            raw_u = self._clean_url(m.group(1))
            if raw_u and not raw_u.endswith((".jpg", ".png", ".gif", ".css", ".js")):
                clean_u = self._fix_url(raw_u)
                if clean_u not in seen_urls:
                    seen_urls.add(clean_u)
                    play_urls.append(clean_u)

        if not play_urls:
            for direct_m in re.finditer(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html_text, re.I):
                clean_u = self._clean_url(direct_m.group(1))
                if clean_u not in seen_urls:
                    seen_urls.add(clean_u)
                    play_urls.append(clean_u)

        return play_urls

    def _load_detail_vod(self, did):
        url = self._fix_url(did)
        cache_key = f"detail_{url}"
        cached = get_cache(cache_key)
        if cached:
            lst = (cached or {}).get("list") or []
            vod = dict(lst[0]) if lst and isinstance(lst[0], dict) else {}
            return vod or None

        html_text = self._fetch(url)
        if not html_text:
            return None
        self._last_detail_url = url

        title = ""
        t_match = re.search(r'<h1[^>]*class=["\'][^"\']*(?:title|headline)[^"\']*["\'][^>]*>(.+?)</h1>', html_text, re.I | re.S)
        if t_match:
            title = re.sub(r'<[^>]+>', '', t_match.group(1)).strip()
        if not title:
            t_match = re.search(r'<h1[^>]*>(.+?)</h1>', html_text, re.I | re.S)
            if t_match:
                title = re.sub(r'<[^>]+>', '', t_match.group(1)).strip()
        if not title:
            t_match = re.search(r'<title>(.+?)</title>', html_text, re.I | re.S)
            if t_match:
                title = t_match.group(1).split("-")[0].split("_")[0].strip()

        pic = ""
        og_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.I)
        if not og_match:
            og_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html_text, re.I)
        if og_match:
            pic = og_match.group(1).strip()
        if not pic:
            p_match = re.search(r'<(?:div|article|section)[^>]*class=["\'][^"\']*(?:content|post|entry)[^"\']*["\'][^>]*>.*?<img[^>]+(?:z-image-loader-url|data-xkrkllgl|data-original|data-src|src)=["\']([^"\']+)["\']', html_text, re.I | re.S)
            if p_match:
                pic = p_match.group(1).strip()

        desc = ""
        desc_match = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.I)
        if not desc_match:
            desc_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:og:description|description)["\']', html_text, re.I)
        if desc_match:
            desc = desc_match.group(1).strip()

        date_str = ""
        d_match = re.search(r'(?:datePublished|pubdate|time)[^>]*>([0-9\-\s:]+)<', html_text, re.I)
        if d_match:
            date_str = d_match.group(1).strip()

        play_urls = self._extract_video_urls(html_text)

        episodes = []
        for idx, p_url in enumerate(play_urls, 1):
            ep_title = f"视频{idx}" if len(play_urls) > 1 else "在线播放"
            episodes.append(f"{ep_title}${self._wrap_media_proxy(p_url)}")

        play_url_str = "#".join(episodes) if episodes else f"在线播放${url}"

        vod = {
            "vod_id": did,
            "vod_name": title or "911爆料",
            "vod_pic": self._fix_pic(pic),
            "vod_remarks": date_str,
            "vod_content": desc,
            "vod_play_from": "$$$".join(["911爆料", "备用解析"]),
            "vod_play_url": "$$$".join([play_url_str, play_url_str])
        }
        set_cache(cache_key, {"list": [dict(vod)]}, ttl=300)
        return vod

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        did = ids[0] if isinstance(ids, list) else ids
        vod = self._load_detail_vod(did)
        if not vod:
            return {"list": []}
        vod = dict(vod)
        vod["vod_play_from"], vod["vod_play_url"] = self._build_page_play(
            vod.get("vod_id") or did, vod.get("vod_name") or "",
            vod.get("vod_play_from"), vod.get("vod_play_url"))
        return {"list": [vod]}

    def searchContent(self, key, quick=False, pg="1"):
        page = _page(pg)
        encoded_key = quote(str(key or '').strip())
        url = f"{self.host}/search/{encoded_key}/{page}/" if page > 1 else f"{self.host}/search/{encoded_key}/"
        html_text = self._fetch(url)
        videos = self._extract_cards(html_text)
        res = {
            "list": videos,
            "page": page,
            "pagecount": page + 1 if len(videos) >= 10 else page,
            "limit": len(videos) if videos else 20,
            "total": 9999
        }
        self._cache_page(("search", str(key or ""), "", str(page)), res.get("list"))
        return res

    def playerContent(self, flag, id, vipFlags=None):
        play_id = str(id or "").strip()
        if play_id.startswith("nid:"):
            vid = unquote(play_id[4:])
            src = self._load_src(vid)
            picked = next((eps for name, eps in src if str(name) == str(flag) and eps), None)
            if not picked and src:
                picked = src[0][1]
            real = picked[0][1] if picked else ""
            play_id = real if real and not str(real).startswith("nid:") else ""
        if "$" in play_id and not play_id.startswith("http"):
            play_id = play_id.split("$")[-1].strip()
        play_id = self._clean_url(play_id)
        proxy = play_id.startswith("http") and (
            "/proxy?" in play_id or "/local/" in play_id
            or "type=m3u8" in play_id or "type=ts" in play_id
        )
        if play_id and not proxy:
            play_id = self._clean_url(unquote(play_id))
            proxy = play_id.startswith("http") and (
                "/proxy?" in play_id or "/local/" in play_id
                or "type=m3u8" in play_id or "type=ts" in play_id
            )
        passthrough = bool(play_id) and (proxy or self.isVideoFormat(play_id))
        return {
            "parse": 0 if passthrough else 1,
            "playUrl": "",
            "url": play_id,
            "header": {
                "User-Agent": self.ua,
                "Referer": self.host + "/"
            }
        }

    def _refresh_auth_url(self, old_url):
        try:
            if not self._last_detail_url:
                return ""
            html_text = self._fetch(self._last_detail_url)
            if not html_text:
                return ""
            parts = urlparse(old_url).path.rsplit("/", 1)
            vhash = parts[1].split(".")[0] if len(parts) >= 2 else ""
            for m in re.finditer(r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*', html_text):
                u = m.group(0).replace("\\", "").strip()
                if vhash and vhash not in u:
                    continue
                return u
        except Exception:
            return ""
        return ""

    def _media_proxy(self, pt, url):
        try:
            _pin_url_host(url)
            host = urlparse(url).hostname
            req_headers = self._req_headers()
            r = None
            for _try in range(3):
                try:
                    if _try == 0:
                        r = self.session.get(url, headers=req_headers, timeout=(2.5, 8), verify=False, allow_redirects=True)
                    else:
                        if host and _PIN_MAP.get(host) and len(_PIN_MAP[host]) > 1:
                            _PIN_MAP[host].append(_PIN_MAP[host].pop(0))
                        r = requests.get(url, headers=req_headers, timeout=(2.5, 8), verify=False, allow_redirects=True)
                    if r.status_code == 200:
                        break
                except Exception:
                    r = None
                if _try < 2:
                    time.sleep(0.3)
            if r is None or r.status_code != 200:
                new_url = self._refresh_auth_url(url)
                if new_url and new_url != url:
                    try:
                        r = requests.get(new_url, headers=req_headers, timeout=(2.5, 8), verify=False, allow_redirects=True)
                    except Exception:
                        r = None
            if r is None or r.status_code != 200:
                return [404, "text/plain", "not found"]
            if pt == "m3u8":
                body = r.text
                b = self._proxy_base()
                if b:
                    sep = "&" if "?" in b else "?"
                    body = re.sub(r'(URI=")([^"]+)(")',
                                  lambda mm: mm.group(1) + b + sep + "type=key&url=" + quote(mm.group(2), safe="") + mm.group(3),
                                  body)
                    lines = []
                    for line in body.splitlines():
                        s = line.strip()
                        if s.startswith("http://") or s.startswith("https://"):
                            line = b + sep + "type=ts&url=" + quote(s, safe="")
                        lines.append(line)
                    body = "\n".join(lines)
                return [200, "application/vnd.apple.mpegurl;charset=UTF-8", body.encode("utf-8")]
            if pt == "key":
                return [200, "application/octet-stream", r.content]
            return [200, "video/mp2t", r.content]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]

    def localProxy(self, param):
        self._ensure_session()

        url = param.get("url") or param.get("img") or ""
        if isinstance(url, list):
            url = url[0] if url else ""
        if not url:
            return [400, "text/plain", b""]

        url = unquote(url).strip()
        _pin_url_host(url)
        _pt = param.get("type") or ""
        if _pt in ("m3u8", "ts", "key"):
            return self._media_proxy(_pt, url)
        if "loadBannerDirect" in url:
            m = re.search(r"loadBannerDirect\(['\"]([^'\"]+)['\"]", url)
            if m:
                url = m.group(1).strip()

        with self._img_lock:
            if url in self._img_cache:
                mime, c_data = self._img_cache[url]
                return [200, "image/" + mime, c_data]

        try:
            req_headers = self._req_headers()
            r = self.session.get(url, headers=req_headers, timeout=(2.5, 6), verify=False, allow_redirects=True)
            content = r.content

            is_encrypted = any(x in url for x in ["/xiao/", "/upload_01/xiao/", "/upload/upload/xiao/"])
            is_valid_magic = (content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG") or content.startswith(b"GIF") or content[:4] == b"RIFF")
            
            if is_encrypted or not is_valid_magic:
                try:
                    dec = self._decrypt_image_bytes(content)
                    if dec and (dec.startswith(b"\xff\xd8\xff") or dec.startswith(b"\x89PNG") or dec.startswith(b"GIF") or dec[:4] == b"RIFF"):
                        content = dec
                except Exception:
                    pass

            mime = self._mime_from_bytes(content)

            with self._img_lock:
                if len(self._img_cache) > 200:
                    self._img_cache.clear()
                self._img_cache[url] = (mime, content)

            return [200, "image/" + mime, content]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8")]
