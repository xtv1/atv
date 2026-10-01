#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RouVideo CatVod/TVBox 爬虫源。线路名：飞鱼。
子分类同 key 每 8 值一段；当页连播 20 部；localProxy 返回 [状态码, 类型, 内容]。
"""

import base64
import re
import time
import zlib
import threading
import requests
import urllib3
from concurrent.futures import Future
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup
from base.spider import Spider

try:
    urllib3.disable_warnings()
except Exception:
    pass


_ORDER = {
    "key": "order",
    "name": "排序",
    "value": [
        {"n": "最新发布", "v": "createdAt"},
        {"n": "最多观看", "v": "viewCount"},
        {"n": "最多点赞", "v": "likeCount"},
    ],
}


class Spider(Spider):

    HOSTS = [
        "https://rouvb1.xyz",
        "https://rouva8.xyz",
        "https://rou.video",
        "https://rou-video.zproxy.org",
    ]
    PUB_PAGES = [
        "https://rdz4.xyz/dizhi",
        "https://rdz3.xyz/dizhi",
    ]

    _current_host_idx = 0
    _fetched_pub_page = False
    _pub_cache = ""

    @property
    def HOST(self):
        return self.HOSTS[self._current_host_idx]

    def getName(self):
        return "飞鱼"

    def init(self, extend=""):
        self._check_tamper()

    def isVideoFormat(self, url):
        low = str(url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".ts", "m3u8%7c", "/api/hls/"))

    def manualVideoCheck(self):
        return False

    def actionHeaders(self, host_url=None):
        ref = host_url if host_url else self.HOST
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": f"{ref}/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _fetch_latest_host_from_pub(self):
        if self._pub_cache:
            return self._pub_cache
        if self._fetched_pub_page:
            return ""
        self._fetched_pub_page = True

        for pub in self.PUB_PAGES:
            html = self._download(pub, referer=pub)
            if not html:
                continue
            try:
                soup = BeautifulSoup(html, "html.parser")
                for sec in soup.find_all("section", class_="sec"):
                    h2 = sec.find("h2")
                    if h2 and "肉視頻" in h2.get_text(strip=True):
                        for a in sec.find_all("a"):
                            if "科學地址" in a.get_text(strip=True):
                                href = (a.get("href") or "").strip().rstrip("/")
                                if href.startswith("http"):
                                    self._pub_cache = href
                                    return href
                        span = sec.find("span", class_="url")
                        if span:
                            span_url = span.get_text(strip=True).rstrip("/")
                            if span_url.startswith("http"):
                                self._pub_cache = span_url
                                return span_url
            except Exception:
                pass
        return ""

    _session = None
    _session_lock = threading.Lock()
    _TIMEOUT = (5, 15)
    _HLS_TIMEOUT = (4, 12)

    def _http(self):
        if Spider._session is None:
            with Spider._session_lock:
                if Spider._session is None:
                    sess = requests.Session()
                    adapter = requests.adapters.HTTPAdapter(
                        pool_connections=32, pool_maxsize=64, max_retries=0)
                    sess.mount("https://", adapter)
                    sess.mount("http://", adapter)
                    Spider._session = sess
        return Spider._session

    def _get(self, url, referer=None, timeout=None, allow_redirects=True, tries=2):
        headers = self.actionHeaders(referer or url)
        for _ in range(tries if tries and tries > 0 else 1):
            try:
                r = self._http().get(url, headers=headers,
                                     timeout=timeout or self._TIMEOUT,
                                     verify=False, allow_redirects=allow_redirects)
                if r is not None:
                    return r
            except Exception:
                pass
        return None

    def _download(self, url, referer=None):
        r = self._get(url, referer=referer or url)
        if r is not None and r.status_code == 200 and r.content:
            return r.content.decode("utf-8", "replace")
        try:
            r = self.fetch(url, headers=self.actionHeaders(referer or url))
            if r is not None and getattr(r, "status_code", 0) == 200 and getattr(r, "text", ""):
                return r.text
        except Exception:
            pass
        return ""

    def _download_bytes(self, url, referer=None, timeout=None, tries=1):
        r = self._get(url, referer=referer, timeout=timeout, tries=tries)
        if r is not None and r.status_code == 200 and r.content:
            return r.content
        return b""

    def _fetch_hls(self, url, referer=None):
        r = self._get(url, referer=referer or self.HOST, timeout=self._HLS_TIMEOUT, tries=1)
        if r is not None and r.status_code == 200 and r.content:
            return (getattr(r, "url", "") or url), r.content
        return url, b""

    def _req(self, path):
        for i in range(len(self.HOSTS)):
            idx = (self._current_host_idx + i) % len(self.HOSTS)
            host = self.HOSTS[idx]
            url = f"{host}{path}" if path.startswith("/") else f"{host}/{path}"
            text = self._download(url, referer=host)
            if text:
                self._current_host_idx = idx
                return text

        new_host = self._fetch_latest_host_from_pub()
        if new_host and new_host not in self.HOSTS:
            self.HOSTS.append(new_host)
            self._current_host_idx = len(self.HOSTS) - 1
            url = f"{new_host}{path}" if path.startswith("/") else f"{new_host}/{path}"
            return self._download(url, referer=new_host)

        return ""

    def _check_tamper(self):
        if self.getName() != "飞鱼":
            raise RuntimeError("版权被篡改，无法启动引擎！")

    def _js_str(self, s, i):
        i += 1
        out = []
        n = len(s)
        while i < n:
            c = s[i]
            if c == '"':
                return "".join(out), i + 1
            if c == "\\" and i + 1 < n:
                nxt = s[i + 1]
                if nxt == "u" and i + 5 < n:
                    try:
                        out.append(chr(int(s[i + 2:i + 6], 16)))
                    except Exception:
                        out.append(nxt)
                    i += 6
                    continue
                out.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
                i += 2
                continue
            out.append(c)
            i += 1
        return "".join(out), i

    def _js_val(self, s, i):
        n = len(s)
        while i < n and s[i] in " \t\r\n":
            i += 1
        if i >= n:
            return None, i
        c = s[i]
        if c == "{":
            return self._js_obj(s, i)
        if c == "[":
            return self._js_arr(s, i)
        if c == '"':
            return self._js_str(s, i)
        if s.startswith("null", i) or s.startswith("void 0", i):
            return None, i + (4 if s[i] == "n" else 6)
        if s.startswith("true", i):
            return True, i + 4
        if s.startswith("false", i):
            return False, i + 5
        if s.startswith("!0", i):
            return True, i + 2
        if s.startswith("!1", i):
            return False, i + 2
        m = re.match(r"-?\d+(?:\.\d+)?", s[i:])
        if m:
            t = m.group(0)
            return (float(t) if "." in t else int(t)), i + len(t)
        m = re.match(r"[A-Za-z_$][\w$]*", s[i:])
        if m:
            return None, i + len(m.group(0))
        return None, i + 1

    def _js_obj(self, s, i):
        i += 1
        obj = {}
        n = len(s)
        while i < n:
            while i < n and s[i] in " \t\r\n,":
                i += 1
            if i < n and s[i] == "}":
                return obj, i + 1
            if s[i] == '"':
                k, i = self._js_str(s, i)
            else:
                m = re.match(r"[A-Za-z_$][\w$]*", s[i:])
                if not m:
                    return obj, i + 1
                k = m.group(0)
                i += len(k)
            while i < n and s[i] in " \t\r\n":
                i += 1
            if i >= n or s[i] != ":":
                return obj, i
            i += 1
            start = i
            v, i = self._js_val(s, i)
            if i == start:
                i += 1
            obj[k] = v
        return obj, i

    def _js_arr(self, s, i):
        i += 1
        arr = []
        n = len(s)
        while i < n:
            while i < n and s[i] in " \t\r\n,":
                i += 1
            if i < n and s[i] == "]":
                return arr, i + 1
            start = i
            v, i = self._js_val(s, i)
            if i == start:
                i += 1
            arr.append(v)
        return arr, i

    def _tsr_props(self, html):
        blob = re.sub(
            r"\$R\[\d+\]=",
            "",
            "\n".join(re.findall(r'<script data-tsr-stream-part="">(.*?)</script>', html or "", re.S)),
        )
        if not blob:
            return {}
        props = {}
        m = re.search(r"\bvideos:(\[)", blob)
        if m:
            arr, _ = self._js_val(blob, m.start(1))
            if isinstance(arr, list):
                props["videos"] = [x for x in arr if isinstance(x, dict)]
        for key in ("totalPage", "totalVideoNum"):
            mm = re.search(r"\b%s:(-?\d+)" % key, blob)
            if mm:
                props[key] = int(mm.group(1))
        m = re.search(r"\btaxonomy:(\{)", blob)
        if m:
            obj, _ = self._js_val(blob, m.start(1))
            if isinstance(obj, dict):
                props["taxonomy"] = obj
        m = re.search(r"\bvideo:(\{)", blob)
        if m:
            obj, _ = self._js_val(blob, m.start(1))
            if isinstance(obj, dict) and obj.get("id"):
                props["video"] = obj
        m = re.search(r"\brelatedVideos:(\[)", blob)
        if m:
            arr, _ = self._js_val(blob, m.start(1))
            if isinstance(arr, list):
                props["relatedVideos"] = [x for x in arr if isinstance(x, dict)]
        return props

    def fix_url(self, url):
        url = (url or "").strip()
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.HOST + url
        return url

    def _png_payload(self, raw):
        if not raw or raw[:8] != b"\x89PNG\r\n\x1a\n":
            return b""
        i = 8
        while i + 8 <= len(raw):
            ln = int.from_bytes(raw[i:i + 4], "big")
            typ = raw[i + 4:i + 8]
            if typ == b"roUd":
                return raw[i + 8:i + 8 + ln]
            i += 12 + ln
        return b""

    def _png_unwrap(self, raw):
        payload = self._png_payload(raw)
        if not payload:
            return b""
        for off in range(0, 4):
            try:
                return zlib.decompress(payload[off:])
            except Exception:
                pass
        return payload[1:] if payload[:1] == b"\x00" else payload

    def _decode_pack(self, raw):
        if not raw:
            return b""
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            return self._png_unwrap(raw)
        head = raw.lstrip()[:8]
        if head.startswith(b"#EXTM3U") or head[:1] == b"G":
            return raw
        return self._png_unwrap(raw) or raw

    def _e64(self, s):
        return base64.urlsafe_b64encode(str(s or "").encode("utf-8")).decode("ascii").rstrip("=")

    def _d64(self, s):
        s = str(s or "")
        s = s.replace("-", "+").replace("_", "/")
        s += "=" * (-len(s) % 4)
        return base64.b64decode(s).decode("utf-8", "replace")

    def _proxy(self, payload, ptype=""):
        try:
            base = self.getProxyUrl()
        except Exception:
            base = "http://127.0.0.1:9978/proxy?do=py"
        out = "%s&url=%s" % (base, self._e64(payload))
        if ptype:
            out += "&type=" + ptype
        return out

    def localProxy(self, param):
        self._ensure()
        if isinstance(param, dict):
            raw = param.get("url", "") or param.get("pdid", "") or ""
            ptype = str(param.get("type", "") or "")
        else:
            raw = str(param or "")
            ptype = ""
        q = ""
        try:
            q = self._d64(raw)
        except Exception:
            q = ""
        if not q.startswith(("m3u8|", "seg|", "http://", "https://", "//")):
            q = unquote(raw)
        if q.startswith("m3u8|"):
            ptype, q = "m3u8", q[5:]
        elif q.startswith("seg|"):
            ptype, q = "seg", q[4:]

        if ptype == "seg":
            seg = self._cached(self._seg_cache, ("seg", q), self._SEG_TTL,
                               lambda: self._load_seg(q), self._SEG_MAX)
            if not seg:
                return [502, "text/plain", b"seg fetch failed"]
            return [200, "video/mp2t", seg]

        vid = ""
        m = re.search(r"/api/hls/([^/?#]+)", q)
        if m:
            vid = m.group(1)
        data = self._cached(self._playlist_cache, ("pl", q, vid), self._PL_TTL,
                            lambda: self._build_playlist(q, vid), self._PL_MAX)
        if not data:
            return [502, "text/plain", b"m3u8 fetch failed"]
        return [200, "application/vnd.apple.mpegurl", data]

    _PL_TTL = 180
    _SEG_TTL = 180
    _PL_MAX = 8
    _SEG_MAX = 16
    _PREFETCH_SEGS = 3
    _SEG_TIMEOUT = (3, 10)

    filters_data = {
        "國產AV": [
            _ORDER,
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "全部", "v": "國產AV"},
                        {"n": "糖心Vlog", "v": "糖心Vlog"},
                        {"n": "蜜桃影像傳媒", "v": "蜜桃影像傳媒"},
                        {"n": "香蕉視頻傳媒", "v": "香蕉視頻傳媒"},
                        {"n": "星空無限傳媒", "v": "星空無限傳媒"},
                        {"n": "天美傳媒", "v": "天美傳媒"},
                        {"n": "精東影業", "v": "精東影業"},
                        {"n": "杏吧傳媒", "v": "杏吧傳媒"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "91製片廠", "v": "91製片廠"},
                        {"n": "皇家華人", "v": "皇家華人"},
                        {"n": "起點傳媒", "v": "起點傳媒"},
                        {"n": "大象傳媒", "v": "大象傳媒"},
                        {"n": "果凍傳媒", "v": "果凍傳媒"},
                        {"n": "蘿莉社", "v": "蘿莉社"},
                        {"n": "ED Mosaic", "v": "ED Mosaic"},
                        {"n": "兔子先生", "v": "兔子先生"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "扣扣傳媒", "v": "扣扣傳媒"},
                        {"n": "SA國際傳媒", "v": "SA國際傳媒"},
                        {"n": "愛神傳媒", "v": "愛神傳媒"},
                        {"n": "性視界傳媒", "v": "性視界傳媒"},
                        {"n": "PsychopornTW", "v": "PsychopornTW"},
                        {"n": "拍攝花絮", "v": "拍攝花絮"},
                        {"n": "抖陰", "v": "抖陰"},
                        {"n": "91茄子", "v": "91茄子"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "絕對領域傳媒", "v": "絕對領域傳媒"},
                        {"n": "烏托邦傳媒", "v": "烏托邦傳媒"},
                        {"n": "紅斯燈影像", "v": "紅斯燈影像"},
                        {"n": "草莓視頻", "v": "草莓視頻"},
                        {"n": "渡邊傳媒", "v": "渡邊傳媒"},
                        {"n": "葫蘆影業", "v": "葫蘆影業"},
                        {"n": "樂播傳媒", "v": "樂播傳媒"},
                        {"n": "Pussy Hunter", "v": "Pussy Hunter"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "麻麻傳媒", "v": "麻麻傳媒"},
                        {"n": "三只狼傳媒", "v": "三只狼傳媒"},
                        {"n": "萝莉原创", "v": "萝莉原创"},
                        {"n": "辣椒原創", "v": "辣椒原創"},
                        {"n": "MisAV", "v": "MisAV"},
                        {"n": "SWAG@daisybaby", "v": "SWAG@daisybaby"},
                        {"n": "冠希傳媒", "v": "冠希傳媒"},
                        {"n": "微密圈傳媒", "v": "微密圈傳媒"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "愛妃傳媒", "v": "愛妃傳媒"},
                        {"n": "天美影院", "v": "天美影院"},
                        {"n": "西瓜影視", "v": "西瓜影視"},
                        {"n": "肉肉傳媒", "v": "肉肉傳媒"},
                        {"n": "烏鴉傳媒", "v": "烏鴉傳媒"},
                        {"n": "日出文化", "v": "日出文化"},
                        {"n": "鯨魚傳媒", "v": "鯨魚傳媒"},
                        {"n": "國產AV劇情", "v": "國產AV劇情"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "SWAG@cartiernn", "v": "SWAG@cartiernn"},
                        {"n": "TWAV", "v": "TWAV"},
                        {"n": "Mini傳媒", "v": "Mini傳媒"},
                        {"n": "桃花源", "v": "桃花源"},
                        {"n": "叮叮映畫", "v": "叮叮映畫"},
                        {"n": "蜜桃視頻", "v": "蜜桃視頻"},
                        {"n": "O-STAR", "v": "O-STAR"},
                        {"n": "開心鬼傳媒", "v": "開心鬼傳媒"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "葵心娛樂", "v": "葵心娛樂"},
                        {"n": "愛污傳媒", "v": "愛污傳媒"}
                    ]
                }
        ],
        "麻豆傳媒": [
            _ORDER,
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "全部", "v": "麻豆傳媒"},
                        {"n": "愛豆傳媒", "v": "愛豆傳媒"},
                        {"n": "MD", "v": "MD"},
                        {"n": "MDX", "v": "MDX"},
                        {"n": "麻豆US", "v": "麻豆US"},
                        {"n": "MSD", "v": "MSD"},
                        {"n": "MCY", "v": "MCY"},
                        {"n": "MKY", "v": "MKY"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "MPG", "v": "MPG"},
                        {"n": "FLIXKO", "v": "FLIXKO"},
                        {"n": "貓爪影像", "v": "貓爪影像"},
                        {"n": "國產麻豆AV節目", "v": "國產麻豆AV節目"},
                        {"n": "麻豆女神微愛視頻", "v": "麻豆女神微愛視頻"},
                        {"n": "麻豆番外", "v": "麻豆番外"},
                        {"n": "麻豆三十天特別企劃", "v": "麻豆三十天特別企劃"},
                        {"n": "麻豆導演系列", "v": "麻豆導演系列"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "情趣K歌房", "v": "情趣K歌房"},
                        {"n": "MDWP", "v": "MDWP"},
                        {"n": "突襲女優家", "v": "突襲女優家"},
                        {"n": "麻豆女優", "v": "麻豆女優"},
                        {"n": "麻豆達人秀", "v": "麻豆達人秀"},
                        {"n": "澀會", "v": "澀會"},
                        {"n": "MDS", "v": "MDS"},
                        {"n": "MDSR", "v": "MDSR"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "麻豆女神微愛影片", "v": "麻豆女神微愛影片"},
                        {"n": "MDL", "v": "MDL"},
                        {"n": "MAN", "v": "MAN"},
                        {"n": "MSM", "v": "MSM"},
                        {"n": "MDHT", "v": "MDHT"},
                        {"n": "MDAG", "v": "MDAG"},
                        {"n": "MS", "v": "MS"},
                        {"n": "MSG", "v": "MSG"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "MDJ", "v": "MDJ"},
                        {"n": "MDM", "v": "MDM"},
                        {"n": "MXJ", "v": "MXJ"},
                        {"n": "MDD", "v": "MDD"},
                        {"n": "MLT", "v": "MLT"}
                    ]
                }
        ],
        "探花": [
            _ORDER,
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "全部", "v": "探花"},
                        {"n": "91沈先生", "v": "91沈先生"},
                        {"n": "探花精選400", "v": "探花精選400"},
                        {"n": "小寶尋花", "v": "小寶尋花"},
                        {"n": "91lisa", "v": "91lisa"},
                        {"n": "調教小景甜", "v": "調教小景甜"},
                        {"n": "午夜尋花", "v": "午夜尋花"},
                        {"n": "91鳳鳴鳥唱", "v": "91鳳鳴鳥唱"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "大神精選", "v": "大神精選"},
                        {"n": "AVOVE直播", "v": "AVOVE直播"},
                        {"n": "91貓先生", "v": "91貓先生"},
                        {"n": "千人斬探花", "v": "千人斬探花"},
                        {"n": "全國探花", "v": "全國探花"},
                        {"n": "91Fans", "v": "91Fans"},
                        {"n": "七天探花", "v": "七天探花"},
                        {"n": "9總全國探花", "v": "9總全國探花"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "91大神@LovELolita7", "v": "91大神@LovELolita7"},
                        {"n": "18歲母狗無限高潮", "v": "18歲母狗無限高潮"},
                        {"n": "鴨哥探花", "v": "鴨哥探花"},
                        {"n": "锤子探花", "v": "锤子探花"},
                        {"n": "探花合集", "v": "探花合集"},
                        {"n": "91不見星空", "v": "91不見星空"},
                        {"n": "早期東莞ISO桑拿系列", "v": "早期東莞ISO桑拿系列"},
                        {"n": "91康先生", "v": "91康先生"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "肉オナホ", "v": "肉オナホ"},
                        {"n": "91大神唐伯虎", "v": "91大神唐伯虎"},
                        {"n": "韋小寶", "v": "韋小寶"},
                        {"n": "91風流哥全集", "v": "91風流哥全集"},
                        {"n": "91蜜桃的合集", "v": "91蜜桃的合集"},
                        {"n": "換妻探花", "v": "換妻探花"},
                        {"n": "小陳頭星選", "v": "小陳頭星選"},
                        {"n": "91大神括約肌大叔", "v": "91大神括約肌大叔"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "情侶自拍", "v": "情侶自拍"},
                        {"n": "探花精選", "v": "探花精選"},
                        {"n": "91呆哥", "v": "91呆哥"},
                        {"n": "mmmn753", "v": "mmmn753"},
                        {"n": "楊導撩妹", "v": "楊導撩妹"},
                        {"n": "歌廳探花陳先生", "v": "歌廳探花陳先生"},
                        {"n": "91美女涵菱", "v": "91美女涵菱"},
                        {"n": "太子探花", "v": "太子探花"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "小馬尋花", "v": "小馬尋花"},
                        {"n": "91唐哥", "v": "91唐哥"},
                        {"n": "jimmybiiig", "v": "jimmybiiig"},
                        {"n": "91天堂原創", "v": "91天堂原創"},
                        {"n": "小飛探花", "v": "小飛探花"},
                        {"n": "文軒探花", "v": "文軒探花"},
                        {"n": "王子哥專啪學生妹", "v": "王子哥專啪學生妹"},
                        {"n": "偉哥尋歡", "v": "偉哥尋歡"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "大草莓寶貝", "v": "大草莓寶貝"},
                        {"n": "探花女下海直播", "v": "探花女下海直播"},
                        {"n": "91天堂系列", "v": "91天堂系列"},
                        {"n": "91大神胖Kyo", "v": "91大神胖Kyo"},
                        {"n": "攝影師果哥出品", "v": "攝影師果哥出品"},
                        {"n": "莞式選妃", "v": "莞式選妃"},
                        {"n": "catman", "v": "catman"},
                        {"n": "90w粉", "v": "90w粉"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "探花大神", "v": "探花大神"},
                        {"n": "91原創達人@多乙丶", "v": "91原創達人@多乙丶"},
                        {"n": "91大黃鴨", "v": "91大黃鴨"},
                        {"n": "小東全國尋妹", "v": "小東全國尋妹"},
                        {"n": "91Dr哥", "v": "91Dr哥"},
                        {"n": "大熊探花", "v": "大熊探花"},
                        {"n": "91約妹達人", "v": "91約妹達人"},
                        {"n": "91大神揚風", "v": "91大神揚風"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "91愛絲小仙女思妍", "v": "91愛絲小仙女思妍"},
                        {"n": "探花郎李尋歡", "v": "探花郎李尋歡"},
                        {"n": "91新晉大神sweattt", "v": "91新晉大神sweattt"},
                        {"n": "91新人GD超模（現改名69DD）", "v": "91新人GD超模（現改名69DD）"},
                        {"n": "91大神jinx", "v": "91大神jinx"},
                        {"n": "91sex哥", "v": "91sex哥"},
                        {"n": "175車模", "v": "175車模"},
                        {"n": "東莞探花", "v": "東莞探花"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "嫖嫖sex探花", "v": "嫖嫖sex探花"},
                        {"n": "秀人網模特", "v": "秀人網模特"}
                    ]
                }
        ],
        "AI短劇": [
            _ORDER,
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "全部", "v": "AI短劇"},
                        {"n": "現代", "v": "現代"},
                        {"n": "都市", "v": "都市"},
                        {"n": "大男主", "v": "大男主"},
                        {"n": "奇幻", "v": "奇幻"},
                        {"n": "後宮", "v": "後宮"},
                        {"n": "古風", "v": "古風"},
                        {"n": "校園", "v": "校園"}
                    ]
                }
        ],
        "OnlyFans": [
            _ORDER,
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "全部", "v": "OnlyFans"},
                        {"n": "fansly", "v": "fansly"},
                        {"n": "tangbo_hu", "v": "tangbo_hu"},
                        {"n": "HongKongDoll", "v": "HongKongDoll"},
                        {"n": "BunnyMiffy", "v": "BunnyMiffy"},
                        {"n": "Nana_Taipei", "v": "Nana_Taipei"},
                        {"n": "qiobnxingcai", "v": "qiobnxingcai"},
                        {"n": "suchanghub", "v": "suchanghub"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "ssrpeach", "v": "ssrpeach"},
                        {"n": "nicolove.cc", "v": "nicolove.cc"},
                        {"n": "Miuzxc", "v": "Miuzxc"},
                        {"n": "yui_xin_tw", "v": "yui_xin_tw"},
                        {"n": "kitty2002102", "v": "kitty2002102"},
                        {"n": "kittyxkum", "v": "kittyxkum"},
                        {"n": "juneliu", "v": "juneliu"},
                        {"n": "YuZuKitty", "v": "YuZuKitty"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "jeenzen", "v": "jeenzen"},
                        {"n": "monmon_tw", "v": "monmon_tw"},
                        {"n": "applecptv", "v": "applecptv"},
                        {"n": "Loliiiiipop99", "v": "Loliiiiipop99"},
                        {"n": "andmlove", "v": "andmlove"},
                        {"n": "daintywilder", "v": "daintywilder"},
                        {"n": "ZZZ666", "v": "ZZZ666"},
                        {"n": "aixiaixi", "v": "aixiaixi"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "ChiChibae", "v": "ChiChibae"},
                        {"n": "blazeconjure3", "v": "blazeconjure3"},
                        {"n": "moremore618", "v": "moremore618"},
                        {"n": "bdollairi", "v": "bdollairi"},
                        {"n": "olive_emmm", "v": "olive_emmm"},
                        {"n": "chocoletmilkk", "v": "chocoletmilkk"},
                        {"n": "SLRabbit", "v": "SLRabbit"},
                        {"n": "Xreindeers", "v": "Xreindeers"}
                    ]
                },
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "Carla Grace", "v": "Carla Grace"}
                    ]
                }
        ],
        "日本": [
            _ORDER,
                {
                    "key": "videoTag",
                    "name": "分类",
                    "value": [
                        {"n": "全部", "v": "日本"},
                        {"n": "fc2 ppv", "v": "fc2 ppv"},
                        {"n": "my amateur-z", "v": "my amateur-z"}
                    ]
                }
        ],
        "自拍流出": [_ORDER],
    }

    def _cache_get(self, store, key, ttl):
        item = store.get(key)
        if not item:
            return None
        if time.time() - item[0] > ttl:
            store.pop(key, None)
            return None
        return item[1]

    def _cache_put(self, store, key, val, limit):
        store[key] = (time.time(), val)
        if limit and len(store) > limit:
            for k in sorted(store.keys(), key=lambda x: store[x][0])[:len(store) - limit]:
                store.pop(k, None)

    def _spawn(self, fn):
        fut = Future()

        def run():
            try:
                fut.set_result(fn())
            except BaseException as e:
                fut.set_exception(e)

        threading.Thread(target=run, daemon=True).start()
        return fut

    def _cached(self, store, key, ttl, fn, limit, wait=True):
        val = self._cache_get(store, key, ttl)
        if val is not None:
            return val
        with self._lock:
            fut = self._jobs.get(key)
            if fut is None:
                fut = self._spawn(lambda: self._fill(store, key, fn, limit))
                self._jobs[key] = fut
        if not wait:
            return None
        try:
            return fut.result(timeout=20)
        except Exception:
            return None

    def _fill(self, store, key, fn, limit):
        try:
            val = fn()
            if val is not None:
                self._cache_put(store, key, val, limit)
            return val
        finally:
            with self._lock:
                self._jobs.pop(key, None)

    def _load_seg(self, url):
        return self._decode_pack(
            self._download_bytes(url, referer=self.HOST,
                                  timeout=self._SEG_TIMEOUT, tries=1)) or None

    def _prefetch_seg(self, url):
        self._cached(self._seg_cache, ("seg", url), self._SEG_TTL,
                     lambda: self._load_seg(url), self._SEG_MAX, wait=False)

    def _prefetch_play(self, real_url, vid=""):
        self._cached(self._playlist_cache, ("pl", real_url, vid), self._PL_TTL,
                     lambda: self._build_playlist(real_url, vid), self._PL_MAX, wait=False)

    def _build_playlist(self, real_url, vid=""):
        self._ensure()
        final_url, raw = self._fetch_hls(real_url, referer=self.HOST)
        if not raw:
            return None
        text = self._decode_pack(raw)
        if not text or b"#EXTM3U" not in text[:80]:
            return None
        base = final_url.rsplit("/", 1)[0] + "/"
        out = []
        segs = []
        for line in text.decode("utf-8", "replace").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                seg = s if s.startswith("http") else base + s
                segs.append(seg)
                out.append(self._proxy(seg, "seg"))
            else:
                out.append(line)
        for seg in segs[:self._PREFETCH_SEGS]:
            self._prefetch_seg(seg)
        return "\n".join(out).encode("utf-8")

    def _ensure(self):
        if not hasattr(self, "page_cache"):
            self.page_cache = {}
            self.page_index = {}
            self.page_keys = []
            self.play_cache = {}
            self._playlist_cache = {}
            self._seg_cache = {}
            self._jobs = {}
            self._lock = threading.RLock()
            self._quiet = 0

    def _clean_name(self, s):
        return str(s or "").replace("$", " ").replace("#", " ").strip()

    def _hdr(self):
        return {"User-Agent": self.actionHeaders()["User-Agent"],
                "Referer": f"{self.HOST}/"}

    def _cache_page(self, key, items):
        self._ensure()
        if not items:
            return
        self.page_cache[key] = list(items)
        if key in self.page_keys:
            self.page_keys.remove(key)
        self.page_keys.append(key)
        for it in items:
            iid = str(it.get("vod_id") or "")
            if iid:
                self.page_index[iid] = key
        while len(self.page_keys) > 12:
            old = self.page_keys.pop(0)
            self.page_cache.pop(old, None)
        if getattr(self, "_quiet", 0):
            return
        if key and key[0] in ("cate", "search"):
            self._spawn(lambda: self._peek_next(key))

    def _next_key(self, key):
        try:
            if key[0] == "cate":
                return ("cate", key[1], key[2], key[3] + 1)
            if key[0] == "search":
                return ("search", key[1], key[2] + 1)
        except Exception:
            pass
        return None

    def _fetch_next(self, key):
        try:
            if key[0] == "cate":
                tid, cate_id, page = key[1], key[2], key[3]
                r = self.categoryContent(tid, page + 1, False, {"videoTag": cate_id})
                return ("cate", tid, cate_id, page + 1), (r or {}).get("list") or []
            if key[0] == "search":
                kw, page = key[1], key[2]
                r = self.searchContent(kw, False, page + 1)
                return ("search", kw, page + 1), (r or {}).get("list") or []
        except Exception:
            pass
        return None, []

    def _enter_quiet(self):
        with self._lock:
            self._quiet = getattr(self, "_quiet", 0) + 1

    def _leave_quiet(self):
        with self._lock:
            self._quiet = max(0, getattr(self, "_quiet", 0) - 1)

    def _peek_next(self, key):
        time.sleep(8)
        nk = self._next_key(key)
        if not nk or nk in self.page_cache:
            return
        self._enter_quiet()
        try:
            self._fetch_next(key)
        except Exception:
            pass
        finally:
            self._leave_quiet()

    def _page_follow(self, vid, need=20):
        self._ensure()
        key = self.page_index.get(str(vid))
        if not key or key not in self.page_cache:
            return []
        out, seen = [], set()
        cur, skip_to = key, str(vid)
        for _ in range(4):
            for it in self.page_cache.get(cur) or []:
                iid = str(it.get("vod_id") or "")
                if skip_to:
                    if iid != skip_to:
                        continue
                    skip_to = ""
                if not iid or iid in seen:
                    continue
                seen.add(iid)
                out.append(it)
                if len(out) >= need:
                    return out
            nk = self._next_key(cur)
            if not nk or nk not in self.page_cache:
                break
            cur = nk
        return out

    def homeContent(self, filter):
        if self.getName() != "飞鱼":
            return {}
        classes = [
            {"type_id": "國產AV", "type_name": "國產AV"},
            {"type_id": "麻豆傳媒", "type_name": "麻豆傳媒"},
            {"type_id": "探花", "type_name": "探花"},
            {"type_id": "AI短劇", "type_name": "AI短剧"},
            {"type_id": "OnlyFans", "type_name": "OnlyFans"},
            {"type_id": "日本", "type_name": "日本"},
            {"type_id": "自拍流出", "type_name": "自拍流出"},
            {"type_id": "视频分类", "type_name": "视频分类"},
        ]
        return {"class": classes, "filters": self.filters_data}

    def homeVideoContent(self):
        return self.categoryContent("國產AV", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        if self.getName() != "飞鱼":
            return {"page": 1, "pagecount": 0, "limit": 0, "total": 0, "list": []}
        if tid == "视频分类":
            return self._parse_three_level_categories()

        page = str(pg)
        extend = extend or {}
        order = extend.get("order", "createdAt")
        if tid.startswith("cat_tag:"):
            cate_id = tid.replace("cat_tag:", "").strip()
        else:
            cate_id = str(extend.get("videoTag") or "") or tid
        html = self._req(f"/t/{quote(cate_id)}?order={order}&page={page}")
        result = self._parse_video_list(html, page)
        self._cache_page(("cate", tid, cate_id, int(page) if str(page).isdigit() else 1),
                         result.get("list") or [])
        return result

    def _parse_three_level_categories(self):
        tag_items, seen = [], set()
        taxonomy = self._tsr_props(self._req("/cat")).get("taxonomy") or {}
        for gkey in ("cats", "genre"):
            for item in taxonomy.get(gkey) or []:
                if not isinstance(item, dict):
                    continue
                tag_id = str(item.get("id", "")).strip()
                if not tag_id or tag_id in seen:
                    continue
                seen.add(tag_id)
                tag_items.append({
                    "vod_id": f"cat_tag:{tag_id}",
                    "vod_name": tag_id,
                    "vod_pic": self.fix_url(item.get("coverImageUrl", "")) or f"{self.HOST}/favicon.ico",
                    "vod_remarks": f"{item.get('count', 0)} 个视频",
                    "vod_tag": "folder",
                })
        return {
            "page": 1, "pagecount": 1,
            "limit": len(tag_items), "total": len(tag_items), "list": tag_items,
        }

    def searchContent(self, key, quick, pg="1"):
        if self.getName() != "飞鱼":
            return {"page": 1, "pagecount": 0, "limit": 0, "total": 0, "list": []}

        page = str(pg)
        path = f"/search?q={quote(key)}&t=&sort=&page={page}"
        html = self._req(path)
        result = self._parse_video_list(html, page)
        self._cache_page(("search", key, int(page) if page.isdigit() else 1),
                         result.get("list") or [])
        return result

    def _fmt_remarks(self, item):
        parts = []
        dur = item.get("duration")
        try:
            sec = int(float(dur))
            if sec > 0:
                parts.append(f"{sec // 60}:{sec % 60:02d}")
        except Exception:
            pass
        views = item.get("viewCount")
        if views:
            parts.append(f"{views} 次观看")
        return " | ".join(parts)

    def _parse_video_list(self, html, page="1"):
        if not html:
            return {"page": 1, "pagecount": 0, "limit": 0, "total": 0, "list": []}
        props = self._tsr_props(html)
        videos, seen = [], set()
        for item in props.get("videos") or []:
            it = self._vod_from_item(item)
            if not it or it["vod_id"] in seen:
                continue
            seen.add(it["vod_id"])
            videos.append(it)
        p_num = int(page) if str(page).isdigit() else 1
        try:
            pagecount = int(props.get("totalPage") or 0) or (p_num + 1 if videos else p_num)
        except Exception:
            pagecount = p_num + 1 if videos else p_num
        return {
            "page": p_num,
            "pagecount": pagecount,
            "limit": len(videos) if videos else 20,
            "total": props.get("totalVideoNum") or 999,
            "list": videos,
        }

    def _vod_from_item(self, item):
        if not isinstance(item, dict):
            return None
        vod_id = str(item.get("id") or item.get("vid") or "").strip()
        if not vod_id:
            return None
        return {
            "vod_id": vod_id,
            "vod_name": item.get("name") or item.get("nameZh") or vod_id,
            "vod_pic": self.fix_url(item.get("coverImageUrl", "")),
            "vod_remarks": self._fmt_remarks(item),
        }

    def _cached_item(self, vid):
        self._ensure()
        key = self.page_index.get(str(vid))
        if not key:
            return None
        for it in self.page_cache.get(key) or []:
            if str(it.get("vod_id")) == str(vid):
                return it
        return None

    def _build_parts(self, items, fallback_id, fallback_name):
        parts, seen = [], set()
        for it in items or []:
            iid = str(it.get("vod_id") or "")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            nm = self._clean_name(it.get("vod_name") or iid) or iid
            parts.append("%s$nid:%s" % (nm, quote(iid, safe="")))
        if not parts:
            nm = self._clean_name(fallback_name) or "正片播放"
            parts = ["%s$nid:%s" % (nm, quote(fallback_id, safe=""))]
        return parts

    def detailContent(self, array):
        if self.getName() != "飞鱼":
            return {"list": []}

        vod_id = array[0]
        clean_id = re.sub(r"^https?://[^/]+/v/", "", vod_id).replace("/v/", "").strip()
        self._ensure()
        self._prefetch_play(self.fix_url("/api/hls/%s" % clean_id), clean_id)

        cached = self._cached_item(clean_id)
        follow = self._page_follow(clean_id, 20)
        if cached and follow:
            return {"list": [{
                "vod_id": clean_id,
                "vod_name": cached.get("vod_name") or clean_id,
                "vod_remarks": cached.get("vod_remarks") or "",
                "vod_pic": cached.get("vod_pic") or "",
                "type_name": "飞鱼",
                "vod_content": cached.get("vod_name") or "",
                "vod_play_from": self.getName(),
                "vod_play_url": "#".join(self._build_parts(follow, clean_id, cached.get("vod_name"))),
            }]}

        props = self._tsr_props(self._req("/v/%s" % clean_id))
        video_info = props.get("video") or {}
        if not isinstance(video_info, dict):
            video_info = {}
        it = self._vod_from_item(video_info) or {
            "vod_id": clean_id, "vod_name": clean_id, "vod_pic": "", "vod_remarks": "",
        }
        vod_name = it["vod_name"]
        tags = video_info.get("tagsZh") or video_info.get("tags") or []
        types = []
        for t in tags:
            t = str(t).strip().lstrip("#")
            if t and t not in types:
                types.append(t)
        vod_content = (video_info.get("description") or "").strip() or vod_name
        if types:
            vod_content += "\n标签：" + "、".join(types)

        if len(follow) < 2:
            follow = [it]
            for item in props.get("relatedVideos") or []:
                rel = self._vod_from_item(item)
                if rel:
                    follow.append(rel)
            self._cache_page(("related", clean_id, 1), follow)

        return {"list": [{
            "vod_id": clean_id,
            "vod_name": vod_name,
            "vod_remarks": it.get("vod_remarks") or "",
            "vod_pic": it.get("vod_pic") or "",
            "type_name": " • ".join(types) if types else "飞鱼",
            "vod_content": vod_content,
            "vod_play_from": self.getName(),
            "vod_play_url": "#".join(self._build_parts(follow, clean_id, vod_name)),
        }]}

    def playerContent(self, flag, id, vipFlags):
        if self.getName() != "飞鱼":
            return {"parse": 0, "url": ""}

        raw = str(id or "")
        if "$" in raw:
            raw = raw.split("$")[-1]
        if raw.startswith("proxy://"):
            return {"parse": 0, "url": raw, "header": self._hdr()}
        if "/proxy?" in raw or "/proxy/?" in raw:
            return {"parse": 0, "url": raw, "header": self._hdr()}
        if raw.startswith("nid:"):
            raw = unquote(raw[4:])
        elif "%" in raw:
            raw = unquote(raw)
        clean_id = re.sub(r"^https?://[^/]+/v/", "", raw).replace("/v/", "").strip()
        if not clean_id:
            return {"parse": 0, "url": ""}

        self._ensure()
        cached = self.play_cache.get(clean_id)
        if cached:
            return {"parse": 0, "url": cached, "header": self._hdr()}

        real_url = self.fix_url(f"/api/hls/{clean_id}")
        url = self._proxy(real_url, "m3u8")
        self.play_cache[clean_id] = url
        self._prefetch_play(real_url, clean_id)
        return {"parse": 0, "url": url, "header": self._hdr()}

