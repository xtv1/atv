#!/usr/bin/python
#91jav最新地址： https://91jav8.cc   https://t.me/jav91_b
#91jav永久入口： https://www.91jav1.com
#91jav官方邮箱：91Jav@pm.me
import base64
import json
import re
import requests
from urllib.parse import quote, urljoin
from base.spider import Spider

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    _HAS_CRYPTO = True
except Exception:
    _HAS_CRYPTO = False

class Spider(Spider):
    def getName(self):
        return "91JAV"
    def init(self, extend=""):
        self.name = "91JAV"
        self.host = "https://cabin.zbywlcc.com"
        self.backup_hosts = ["https://born.zbywlcc.com", "https://d1nqsse6ono4lc.cloudfront.net"]
        self.shield = []
        self.readmes = ["https://gitlab.com/91JAV2/dz/-/raw/main/README.md", "https://gitlab.com/91jav1/dz/-/raw/main/README.md"]
        self._readme_done = False
        self._img_cache = {}
        self.aes_key = b"f5d965df75336270"
        self.aes_iv = b"97b60394abc2fbe1"
        if isinstance(extend, str) and extend.strip():
            s = extend.strip()
            if s.startswith("{"):
                try:
                    cfg = json.loads(s)
                    self.host = cfg.get("host", self.host)
                    self.backup_hosts = cfg.get("backup_hosts", []) or []
                    self.shield = cfg.get("shield", []) or []
                except Exception:
                    pass
            elif "://" in s:
                self.host = s
        self.headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36", "Referer": self.host + "/"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.themes = [("2", "角色剧情"), ("3", "中文字幕"), ("4", "制服诱惑"), ("5", "直接开啪"), ("6", "丝袜美腿"), ("7", "捆绑调教"), ("8", "多P群交"), ("10", "羞辱强暴"), ("11", "无码高清"), ("14", "乱伦伦理"), ("15", "人妻诱惑"), ("17", "网黄精选")]
        self.theme_sorts = [{"n": "近期最佳", "v": "hot"}, {"n": "今日更新", "v": "update"}, {"n": "最多观看", "v": "watch"}, {"n": "最高收藏", "v": "favorite"}]
        self.categories = [
            {"type_id": "/new", "type_name": "最新更新"},
            {"type_id": "/theme/detail/3/update", "type_name": "中文字幕"},
            {"type_id": "/theme/detail/11/hot", "type_name": "无码高清"},
            {"type_id": "/heiliao", "type_name": "黑料吃瓜"},
            {"type_id": "/theme", "type_name": "专题合集"},
            {"type_id": "/actress/hot", "type_name": "热门女优"},
        ]
        self.filters = {
            "/theme/detail/3/update": [{"key": "sort", "name": "排序", "value": self.theme_sorts}],
            "/theme/detail/11/hot": [{"key": "sort", "name": "排序", "value": self.theme_sorts}],
            "/theme": [{"key": "sort", "name": "排序", "value": [{"n": "预设排序", "v": "sort"}, {"n": "热度优先", "v": "check_num"}, {"n": "最多影片", "v": "count"}]}],
            "/actress/hot": [{"key": "sort", "name": "排序", "value": [{"n": "热度优先", "v": "hot"}, {"n": "最多影片", "v": "count"}]}],
        }
        self.tids = {"/new": "/new", "/theme": "/theme", "/actress/hot": "/actress/hot", "/heiliao": "/heiliao"}
        self._filters_actress = []
        for tid, _ in self.themes:
            self.tids["/theme/detail/%s/update" % tid] = "/theme/detail/%s/update" % tid
            self.tids["/theme/detail/%s/hot" % tid] = "/theme/detail/%s/hot" % tid
    def _set_host(self, h):
        self.host = h.rstrip("/")
        self.headers["Referer"] = self.host + "/"
        self.session.headers.update(self.headers)
    def _hosts(self):
        return list(dict.fromkeys([self.host] + self.backup_hosts + self.shield))
    def _resolve_readme(self):
        if self._readme_done:
            return
        self._readme_done = True
        for ru in self.readmes:
            try:
                r = self.session.get(ru, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None)
                if r.status_code != 200 or not r.text:
                    continue
                txt = r.text
                targets = []
                m = re.search(r'91JAV\s*国内备用地址\s*[：:]\s*(https?://[^\s<>"\'\)]+)', txt)
                if m:
                    targets.append(("redirect", m.group(1).rstrip("/")))
                m = re.search(r'91JAV\s*国内最新网址\s+(https?://[^\s<>"\'\)]+)', txt)
                if m:
                    targets.append(("publish", m.group(1).rstrip("/")))
                m = re.search(r'91JAV\s*海外永久地址[^v]*?（需要VPN）\s*(https?://[^\s<>"\'\)]+)', txt)
                if m:
                    targets.append(("direct", m.group(1).rstrip("/")))
                for typ, u in targets:
                    if u in self.backup_hosts or u in self.shield or u == self.host or "gitlab" in u or "t.me" in u or "app" in u or "msugpac" in u or "pm.me" in u:
                        continue
                    try:
                        if typ == "redirect":
                            rr = self.session.get(u, headers=self.headers, timeout=10, verify=False, allow_redirects=True, proxies=self.session.proxies or None)
                            fm = re.match(r"(https?://[^/]+)", rr.url)
                            final = fm.group(1) if fm else u
                            if rr.status_code == 200 and ("bind_video_img" in rr.text or "/videos/" in rr.text) and final not in self.backup_hosts and final != self.host:
                                self.backup_hosts.append(final)
                        elif typ == "publish":
                            pub = self.session.get(u, headers=self.headers, timeout=10, verify=False, proxies=self.session.proxies or None)
                            if pub.status_code == 200:
                                for line in re.findall(r'https?://[^"\'\s<>]+', pub.text):
                                    lu = line.rstrip("'\".,;")
                                    if ("cloudfront" in lu or "zbywlcc" in lu or "okknubyz" in lu or "gyqspl" in lu) and lu not in self.backup_hosts and lu != self.host:
                                        self.backup_hosts.append(lu)
                        else:
                            rr = self.session.get(u + "/theme/detail/3/update/", headers=self.headers, timeout=10, verify=False, allow_redirects=True, proxies=self.session.proxies or None)
                            fm = re.match(r"(https?://[^/]+)", rr.url)
                            final = fm.group(1) if fm else u
                            if rr.status_code == 200 and ("bind_video_img" in rr.text or "/videos/" in rr.text) and final not in self.backup_hosts and final != self.host:
                                self.backup_hosts.append(final)
                    except Exception:
                        continue
            except Exception:
                continue
    def _get(self, url):
        url = self._fix(url)
        for attempt in range(2):
            for h in self._hosts():
                try:
                    target = re.sub(r"https?://[^/]+", h, url) if url.startswith("http") else h + url
                    r = self.session.get(target, headers=self.headers, timeout=20, verify=False, proxies=self.session.proxies or None)
                    r.encoding = r.apparent_encoding or "utf-8"
                    if r.status_code == 200 and r.text:
                        if h != self.host:
                            self._set_host(h)
                        return r.text
                except Exception:
                    continue
            if attempt == 0:
                self._resolve_readme()
        return ""
    def _fix(self, url):
        return urljoin(self.host + "/", (url or "").strip().replace("`", "").replace("\\/", "/"))
    def _aes_dec(self, data):
        if not data or not _HAS_CRYPTO:
            return b""
        try:
            return unpad(AES.new(self.aes_key, AES.MODE_CBC, self.aes_iv).decrypt(data), AES.block_size)
        except Exception:
            return b""
    def _pic(self, url):
        u = self._fix(url)
        if not u.startswith("http"):
            return u
        if "assets/images/categories" in u:
            return u
        b64 = base64.b64encode(u.encode()).decode()
        try:
            proxy = self.getProxyUrl() + "&url=" + b64 + "&type=img"
        except Exception:
            proxy = ""
        if proxy and proxy.startswith("http"):
            return proxy
        return "localProxy?type=img&url=" + b64
    def localProxy(self, param):
        if not param or str(param.get("type") or "") != "img":
            return [404, "text/plain", "", ""]
        try:
            u = base64.b64decode(str(param.get("url") or "")).decode("utf-8")
            if u in self._img_cache:
                return [200, "image/jpeg", self._img_cache[u], ""]
            r = self.session.get(u, headers={"User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"), "Referer": self.host + "/"}, timeout=20, verify=False, proxies=self.session.proxies or None)
            data = r.content or b""
            if not data:
                return [404, "text/plain", "", ""]
            dec = self._aes_dec(data)
            if dec and (dec[:3] == b"\xff\xd8\xff" or dec[:4] == b"\x89PNG" or dec[:3] == b"GIF"):
                self._img_cache[u] = dec
                return [200, "image/jpeg", dec, ""]
            self._img_cache[u] = data
            return [200, "image/jpeg", data, ""]
        except Exception:
            return [500, "text/plain", "", ""]
    def _ext(self, extend):
        if isinstance(extend, dict):
            return extend
        if isinstance(extend, str) and extend.strip().startswith("{"):
            try:
                return json.loads(extend)
            except Exception:
                return {}
        return {}
    def _pagecount(self, html, pg):
        nums = []
        for m in re.finditer(r'<a[^>]*class="[^"]*page-link[^"]*"[^>]*href="([^"]*)"', html or ""):
            mm = re.search(r"/(\d+)(?:[;?/]|$)", m.group(1))
            if mm:
                nums.append(int(mm.group(1)))
        for m in re.finditer(r'<a[^>]*class="[^"]*page-link[^"]*"[^>]*>\s*(\d+)\s*</a>', html or ""):
            nums.append(int(m.group(1)))
        nxt = re.search(r'<a[^>]*rel="next"[^>]*>', html or "") or ("下一页" in (html or ""))
        return max(nums + [pg + 1 if nxt else pg])
    def _list(self, html):
        out = []
        seen = set()
        for b in re.split(r'bind_video_img', html or "")[1:]:
            try:
                m = re.search(r'<a\s+href="([^"]*videos/[^"]+)"[^>]*>', b)
                if not m:
                    continue
                href = self._fix(m.group(1))
                if href in seen:
                    continue
                seen.add(href)
                im = re.search(r'<img[^>]*?(?:z-image-loader-url|data-src|src)="([^"]*)"', b)
                pic = self._pic(im.group(1)) if im else ""
                nm = re.search(r'<h3[^>]*class="[^"]*title[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>', b)
                name = ""
                if nm:
                    name = re.sub(r"\s+", " ", nm.group(1)).strip()
                if not name:
                    am = re.search(r'<img[^>]*alt="([^"]*)"', b)
                    name = am.group(1) if am else ""
                if not name:
                    name = href.rsplit("/", 1)[-1]
                rm = re.search(r'<span class="label">([^<]+)</span>', b)
                remarks = rm.group(1) if rm else ""
                if "广告" in remarks:
                    remarks = ""
                out.append({"vod_id": href, "vod_name": name, "vod_pic": pic, "vod_remarks": remarks})
            except Exception:
                continue
        if out:
            return out
        return self._heiliao_list(html)
    def _heiliao_list(self, html):
        out, seen = [], set()
        for m in re.finditer(r'<a class="heiliao-card" href="([^"]+)"(.*?)</a>', html or "", re.S):
            try:
                href = self._fix(m.group(1))
                if href in seen:
                    continue
                seen.add(href)
                seg = m.group(2)
                im = re.search(r'z-image-loader-url="([^"]*)"', seg) or re.search(r'(?:data-src|src)="([^"]*)"', seg)
                pic = self._pic(im.group(1)) if im else ""
                nm = re.search(r'heiliao-card-title">([^<]+)', seg)
                name = re.sub(r"\s+", " ", nm.group(1)).strip() if nm else ""
                if not name:
                    am = re.search(r'alt="([^"]*)"', seg)
                    name = am.group(1) if am else href.rsplit("/", 1)[-1]
                rm = re.search(r'heiliao-date">([^<]+)', seg)
                remarks = (rm.group(1) or "").strip() if rm else ""
                out.append({"vod_id": href, "vod_name": name, "vod_pic": pic, "vod_remarks": remarks})
            except Exception:
                continue
        return out
    def _theme_list(self, html):
        out = []
        seen = set()
        for m in re.finditer(r'<a href="/theme/detail/(\d+)/([a-z]*)"[^>]*>\s*<div class="overlay"></div>\s*<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"(.*?)</a>', html, re.S):
            try:
                tid = m.group(1)
                if tid in seen:
                    continue
                seen.add(tid)
                name = m.group(4).strip()
                pic = self._fix(m.group(3))
                seg = m.group(5)
                cm = re.search(r'<span class="label">(\d+)\s*部影片</span>', seg)
                remarks = (cm.group(1) + " 部影片") if cm else ""
                out.append({"vod_id": "theme$" + tid, "vod_name": name, "vod_pic": pic, "vod_remarks": remarks, "vod_tag": "folder"})
            except Exception:
                continue
        return out
    def _actress_list(self, html):
        out = []
        seen = set()
        for m in re.finditer(r'<a href="/actress/detail/(\d+)/([a-z]+)"[^>]*>\s*<div class="media">(.*?)</a>', html, re.S):
            try:
                aid = m.group(1)
                if aid in seen:
                    continue
                seen.add(aid)
                if aid not in self._filters_actress:
                    self._filters_actress.append(aid)
                seg = m.group(3)
                nm = re.search(r'alt="([^"]*)"', seg)
                name = nm.group(1) if nm else "女优" + aid
                pm = re.search(r'z-image-loader-url="([^"]*)"', seg)
                pic = self._pic(pm.group(1)) if pm else ""
                cm = re.search(r'<span>(\d+)\s*部影片</span>', seg)
                remarks = (cm.group(1) + " 部影片") if cm else ""
                out.append({"vod_id": "actress$" + aid, "vod_name": name, "vod_pic": pic, "vod_remarks": remarks, "vod_tag": "folder"})
            except Exception:
                continue
        return out
    def homeContent(self, filter):
        fl = dict(self.filters)
        for t, _ in self.themes:
            fl["theme$" + t] = [{"key": "sort", "name": "排序", "value": self.theme_sorts}]
        for t in self._filters_actress:
            fl["actress$" + t] = [{"key": "sort", "name": "排序", "value": [{"n": "近期最佳", "v": "hot"}, {"n": "今日更新", "v": "latest"}, {"n": "最多观看", "v": "watch"}, {"n": "最高收藏", "v": "favorite"}]}]
        return {"class": self.categories, "list": self._list(self._get(self.host)), "filters": fl}
    def homeVideoContent(self):
        return {"list": self._list(self._get(self.host + "/new"))}
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        tid = str(tid)
        ex = self._ext(extend)
        sort = ex.get("sort", "") or ""
        if tid.startswith("theme$"):
            t = tid.split("$")[1]
            st = sort if sort in ("hot", "update", "watch", "favorite") else "update"
            ht = self._get(self.host + "/theme/detail/%s/%s/" % (t, st))
            items = self._list(ht)
            return {"page": pg, "pagecount": self._pagecount(ht, pg), "limit": len(items) or 24, "total": 0, "list": items}
        if tid.startswith("actress$"):
            aid = tid.split("$")[1]
            st = sort if sort in ("hot", "latest", "watch", "favorite") else "latest"
            ht = self._get(self.host + "/actress/detail/%s/%s/" % (aid, st))
            items = self._list(ht)
            if "actress$" + aid not in self.filters:
                self.filters["actress$" + aid] = [{"key": "sort", "name": "排序", "value": [{"n": "近期最佳", "v": "hot"}, {"n": "今日更新", "v": "latest"}, {"n": "最多观看", "v": "watch"}, {"n": "最高收藏", "v": "favorite"}]}]
            return {"page": pg, "pagecount": self._pagecount(ht, pg), "limit": len(items) or 24, "total": 0, "list": items}
        if tid == "/theme":
            st = sort if sort in ("sort", "check_num", "count") else "sort"
            ht = self._get(self.host + "/theme/%s" % st)
            items = self._theme_list(ht)
            return {"page": pg, "pagecount": pg, "limit": len(items) or 12, "total": len(items), "list": items}
        if tid == "/actress/hot":
            st = sort if sort in ("hot", "count") else "hot"
            ht = self._get(self.host + "/actress/%s/" % st)
            items = self._actress_list(ht)
            return {"page": pg, "pagecount": self._pagecount(ht, pg) or 1, "limit": len(items) or 24, "total": 0, "list": items}
        base = self.tids.get(tid, tid)
        if sort in ("hot", "update", "watch", "favorite"):
            base = re.sub(r"/(?:hot|update|watch|favorite)$", "/" + sort, base)
        url = self.host + base + (("/" + str(pg)) if pg > 1 else "/")
        ht = self._get(url)
        items = self._list(ht)
        pc = self._pagecount(ht, pg)
        if 0 < len(items) < 20 and pc > pg:
            seen = {it.get("vod_id") for it in items}
            for sp in range(pg + 1, pc + 1):
                extra = self._list(self._get(self.host + str(base).rstrip("/") + "/" + str(sp) + "/"))
                if not extra:
                    break
                for it in extra:
                    vid = it.get("vod_id")
                    if vid and vid not in seen:
                        seen.add(vid)
                        items.append(it)
            pc = pg
        return {"page": pg, "pagecount": pc, "limit": len(items) or 24, "total": 0, "list": items}
    def detailContent(self, ids):
        out = []
        for vid in ids if isinstance(ids, list) else [ids]:
            try:
                sv = str(vid)
                if sv.startswith("theme$") or sv.startswith("actress$"):
                    continue
                url = self._fix(sv)
                html = self._get(url)
                title = ""
                pic = ""
                desc = ""
                tags = ""
                dur = ""
                if "/heiliao/post/" in url:
                    hm = re.search(r'heiliao-detail-title[^>]*>([^<]+)', html) or re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
                    if hm:
                        title = re.sub(r"<[^>]+>", "", hm.group(1)).strip()
                    pm = re.search(r'z-image-loader-url="([^"]+)"', html)
                    if pm:
                        pic = pm.group(1)
                    dm = re.search(r'<div class="heiliao-detail-content">\s*<p>(.*?)</p>', html, re.S)
                    if dm:
                        desc = re.sub(r"<[^>]+>", "", dm.group(1)).strip()
                    play = self._m3u8(html) or url
                    if not title:
                        title = sv
                    desc = (desc or "")[:500]
                    out.append({"vod_id": sv, "vod_name": title, "vod_pic": self._pic(pic), "vod_content": desc, "vod_remarks": "m3u8" if ".m3u8" in play else "", "vod_play_from": "91JAV", "vod_play_url": "正片$" + play})
                    continue
                v = re.search(r'<video[^>]*id="player"[^>]*>', html) or re.search(r'<video[^>]*class="[^"]*dplayer[^"]*"[^>]*>', html)
                if v:
                    tag = v.group(0)
                    tm = re.search(r'data-video_title="([^"]*)"', tag)
                    if tm:
                        title = tm.group(1)
                    pm = re.search(r'data-src="([^"]*)"', tag)
                    if pm:
                        pic = pm.group(1)
                    tg = re.search(r'data-video_tag_name="([^"]*)"', tag)
                    if tg:
                        tags = tg.group(1)
                if not title:
                    hm = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S) or re.search(r'<h2[^>]*>(.*?)</h2>', html, re.S)
                    if hm:
                        title = re.sub(r"<[^>]+>", "", hm.group(1)).strip()
                if not title:
                    title = sv
                if not pic:
                    pm = re.search(r'<img[^>]*?z-image-loader-url="([^"]*)"', html)
                    if pm:
                        pic = pm.group(1)
                jd = re.search(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S)
                if jd:
                    m2 = re.search(r'"description"\s*:\s*"([^"]+)"', jd.group(1))
                    if m2:
                        desc = m2.group(1)
                    m2 = re.search(r'"duration"\s*:\s*"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"', jd.group(1))
                    if m2:
                        hh = int(m2.group(1) or 0)
                        mm = int(m2.group(2) or 0)
                        ss = int(m2.group(3) or 0)
                        dur = ("%02d:%02d:%02d" % (hh, mm, ss)) if hh else ("%02d:%02d" % (mm, ss))
                if not desc:
                    m2 = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
                    if m2:
                        desc = m2.group(1)
                desc = (desc or "")[:500]
                remarks = " ".join(x for x in [dur, tags] if x)
                out.append({"vod_id": sv, "vod_name": title, "vod_pic": self._pic(pic), "vod_content": desc, "vod_remarks": remarks, "vod_play_from": "91JAV", "vod_play_url": "正片$" + sv})
            except Exception:
                continue
        return {"list": out}
    def searchContent(self, key, quick, pg="1"):
        try:
            html = self._get(self.host + "/cn/search/" + quote(str(key)))
            i = html.find('list_videos_common_videos_list')
            if i >= 0:
                j = html.find("</section>", i)
                if j > i:
                    html = html[i:j]
            return {"list": self._list(html), "page": int(pg)}
        except Exception:
            return {"list": [], "page": int(pg)}
    def _m3u8(self, body):
        m = re.search(r'var\s+hlsUrl\s*=\s*["\']([^"\']+)', body or "")
        if m:
            return m.group(1).replace("&amp;", "&")
        m = re.search(r'<video[^>]+src=["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)', body or "", re.I)
        if m:
            return m.group(1).replace("&amp;", "&")
        ms = re.findall(r'https?://[^"\'\s<>]+\.(?:m3u8|mp4)[^"\'\s<>]*', body or "", re.I)
        if ms:
            return ms[0].replace("&amp;", "&")
        return ""
    def playerContent(self, flag, id, vipFlags):
        hd = dict(self.headers)
        u = str(id or "")
        if u.endswith(".m3u8") or ".m3u8?" in u or u.endswith(".mp4"):
            if not u.startswith("http"):
                u = self._fix(u)
            return {"parse": 0, "url": u, "header": hd}
        last = ""
        for h in self._hosts():
            try:
                target = u if u.startswith("http") else h + u
                body = self._get(target)
                url = self._m3u8(body)
                if url:
                    url = url if url.startswith("http") else h + url
                    return {"parse": 0, "url": url, "header": hd}
                last = target
            except Exception:
                continue
        return {"parse": 0 if last.startswith("http") else 1, "url": last, "header": hd}
