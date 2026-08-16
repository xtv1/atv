#!/usr/bin/python
# coding=utf-8
import re, json, requests
from urllib.parse import quote, unquote, urlencode
from base.spider import Spider
try:
    from Crypto.Cipher import AES
    from base64 import b64encode
except Exception:
    AES = None
    b64encode = None

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
        self.cat_map = [
            {"type_id": "ai-duanju", "type_name": "AI成人短剧", "path": "/ai-duanju/"},
            {"type_id": "ai-manju", "type_name": "AI成人漫剧", "path": "/ai-manju/"},
            {"type_id": "ai-huanlian", "type_name": "AI换脸", "path": "/ai-huanlian/"},
            {"type_id": "ai-mogai", "type_name": "AI魔改", "path": "/ai-mogai/"},
            {"type_id": "topic", "type_name": "专题", "path": "/topics/", "kind": "topic"},
            {"type_id": "rank", "type_name": "排行榜", "path": "/ranks/hot/", "kind": "rank"},
            {"type_id": "chigua", "type_name": "黄果吃瓜", "path": "/chigua/", "kind": "chigua"}
        ]
        self.key = bytes(int(c) for c in "102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48".split("_"))
        self.iv = bytes(int(c) for c in "57_55_98_54_48_51_57_52_97_98_99_50_102_98_101_49".split("_"))
        self.filter_map = {"": {}}

    def getName(self):
        return self.name

    def init(self, extend=""):
        pass

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

    def fix_url(self, url):
        if not url:
            return ""
        url = url.replace("\\u0026", "&").replace("&amp;", "&")
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def proc_pic(self, pic):
        if not pic:
            return ""
        pic = self.fix_url(pic)
        if AES is None or "127.0.0.1" in pic or "local://" in pic:
            return pic
        return "http://127.0.0.1:9978/proxy?do=pic&url=" + quote(pic)

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

    def extract_rank(self, html):
        result = []
        seen = set()
        for m in re.finditer(r'<div class="hg-rank-item"[^>]*data-track-id="(\d+)"', html):
            try:
                start = m.start()
                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                chunk = html[start:start + 2500]
                seen.add(vod_id)
                link = re.search(r'href="(/detail/%s/)"' % re.escape(vod_id), chunk)
                if not link:
                    continue
                title = re.search(r'data-track-title="([^"]*)"', chunk)
                vod_name = title.group(1) if title else ""
                pic = re.search(r'data-src="(https?://[^"]*)"', chunk)
                vod_pic = self.proc_pic(pic.group(1) if pic else "")
                heat = re.search(r'hg-rank-item__heat-value[^>]*>([^<]*)', chunk)
                vod_remarks = heat.group(1).strip() if heat else ""
                if vod_name:
                    result.append({
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": vod_remarks
                    })
            except Exception:
                continue
        return result

    def extract_topics(self, html):
        result = []
        for m in re.finditer(r'<a class="hg-topic-card" href="(/topics/[^"]*/)"', html):
            try:
                start = m.start()
                chunk = html[start:start + 900]
                title = re.search(r'hg-topic-card__title[^>]*>([^<]*)', chunk)
                vod_name = title.group(1).strip() if title else ""
                meta = re.search(r'hg-topic-card__meta[^>]*>\s*<span>([^<]*)</span>', chunk)
                vod_remarks = meta.group(1).strip() if meta else ""
                pic = re.search(r'data-src="(https?://[^"]*)"', chunk)
                vod_pic = self.proc_pic(pic.group(1) if pic else "")
                if vod_name:
                    result.append({
                        "vod_id": m.group(1),
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": vod_remarks
                    })
            except Exception:
                continue
        return result

    def extract_posts(self, html):
        result = []
        seen = set()
        for m in re.finditer(r'<a class="hg-post-card" href="(/archives/(\d+)/)"', html):
            try:
                start = m.start()
                pid = m.group(2)
                if pid in seen:
                    continue
                seen.add(pid)
                chunk = html[start:start + 1500]
                title = re.search(r'<h3>([^<]*)</h3>', chunk)
                vod_name = title.group(1).strip() if title else ""
                pic = re.search(r'data-src="(https?://[^"]*)"', chunk)
                vod_pic = self.proc_pic(pic.group(1) if pic else "")
                meta = re.search(r'hg-post-card__cat[^>]*>([^<]*)', chunk)
                vod_remarks = meta.group(1).strip() if meta else ""
                if vod_name:
                    result.append({
                        "vod_id": m.group(1),
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": vod_remarks
                    })
            except Exception:
                continue
        return result

    def homeContent(self, filter):
        result = {"class": [], "filters": {}}
        for cat in self.cat_map:
            result["class"].append({"type_id": cat["type_id"], "type_name": cat["type_name"]})
        result["list"] = self.homeVideoContent().get("list", [])
        return result

    def homeVideoContent(self):
        result = {"list": []}
        html = self.getHtml(self.host)
        if not html:
            return result
        cards = self.extract_cards(html)
        seen = set()
        unique = []
        for c in cards:
            if c["vod_id"] not in seen:
                seen.add(c["vod_id"])
                unique.append(c)
        result["list"] = unique[:20]
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        page = int(pg) if pg else 1
        cat = next((c for c in self.cat_map if c["type_id"] == tid or c["type_name"] == tid), None)
        if not cat:
            return result
        kind = cat.get("kind", "")
        base_path = cat["path"].rstrip("/")
        if kind == "topic":
            html = self.getHtml(self.host + base_path + "/")
            if not html:
                return result
            result["list"] = self.extract_topics(re.sub(r'<template[\s\S]*?</template>', '', html))
            result["page"] = page
            return result
        if kind == "rank":
            html = self.getHtml(self.host + base_path + "/")
            if not html:
                return result
            result["list"] = self.extract_rank(html)
            result["page"] = page
            return result
        if kind == "chigua":
            if page <= 1:
                url = self.host + base_path + "/"
            else:
                url = self.host + base_path + "/page/%d/" % page
            html = self.getHtml(url)
            if not html:
                return result
            result["list"] = self.extract_posts(re.sub(r'<template[\s\S]*?</template>', '', html))
            total_m = re.search(r'共 (\d+) 条', html)
            if total_m:
                result["total"] = int(total_m.group(1))
            page_m = re.search(r'第 (\d+)/(\d+) 页', html)
            if page_m:
                result["page"] = int(page_m.group(1))
                result["pagecount"] = int(page_m.group(2))
            result["limit"] = len(result["list"]) if result["list"] else 20
            return result
        if page <= 1:
            url = self.host + base_path + "/"
        else:
            url = self.host + base_path + "/%d/" % page
        html = self.getHtml(url)
        if not html:
            return result
        html = re.sub(r'<template[\s\S]*?</template>', '', html)
        result["list"] = self.extract_cards(html)
        pages = re.search(r'data-pages="(\d+)"', html)
        if pages:
            result["pagecount"] = int(pages.group(1))
        else:
            pager_links = re.findall(r'href="%s/(\d+)/"' % re.escape(base_path), html)
            if pager_links:
                result["pagecount"] = max([int(p) for p in pager_links])
        total = re.search(r'data-panel-total="(\d+)"', html)
        if total:
            result["total"] = int(total.group(1))
        result["page"] = page
        result["limit"] = len(result["list"]) if result["list"] else 20
        return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if isinstance(ids, list) else ids
        if isinstance(vid, str) and (vid.startswith("/topics/") or vid.startswith("/archives/")):
            if vid.startswith("/topics/"):
                return self.topicDetail(vid)
            return self.postDetail(vid)
        m = re.search(r'(\d+)', vid)
        if not m:
            return result
        vid = m.group(1)
        html = self.getHtml("%s/detail/%s/" % (self.host, vid))
        if not html:
            return result
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
                    play_urls.append("第%02d集$%s" % (int(ep_id), eps[ep_id]))
                vod["vod_play_from"] = "黄果短剧"
                vod["vod_play_url"] = "#".join(play_urls)
            else:
                vod["vod_play_from"] = "黄果短剧"
                vod["vod_play_url"] = "第01集$/video/%s/" % vid
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
                play_urls.append("第%02d集$%s" % (idx, src.replace("\\u0026", "&")))
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
                vod["vod_play_url"] = "#".join("第%02d集$%s" % (i + 1, u) for i, u in enumerate(seen))
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
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        play_url = self.fix_url(id) if id else ""
        if play_url.endswith('.m3u8') or 'm3u8' in play_url or '.mp4' in play_url:
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
        result["url"] = m3u8
        result["header"] = json.dumps({"User-Agent": self.header["User-Agent"], "Referer": self.host})
        return result

    def localProxy(self, param):
        result = {"url": "", "header": ""}
        pic = ""
        if param:
            pic = param.get("url") or param.get("pic") or ""
        if not pic:
            return result
        pic = unquote(pic)
        try:
            r = requests.get(pic, headers=self.header, timeout=15, verify=False)
            ct = r.content
            if ct[:3] == b"\xff\xd8\xff" or ct[:8] == b"\x89PNG\r\n\x1a\n":
                result["url"] = "data:image/jpeg;base64,%s" % b64encode(ct).decode()
                return result
            if AES and len(ct) % 16 == 0:
                dec = AES.new(self.key, AES.MODE_CBC, self.iv).decrypt(ct)
                if dec[:3] == b"\xff\xd8\xff":
                    result["url"] = "data:image/jpeg;base64,%s" % b64encode(dec).decode()
                    return result
        except Exception:
            pass
        return result
