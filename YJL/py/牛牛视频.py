#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
牛牛视频 爬虫 (from APK _1.6.2.apk)
分类参照黄豆短剧的自动获取方式: 优先从API获取, 失败回退APK内置tab_list
API: src2 (3DES-CBC加密, dy.wnhyjc.com) + xxcjpt.com (反转base64)
"""
import base64
import json
import os
import re
import time
import uuid
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urljoin
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        pass


class _Crypto:
    """3DES-CBC 加解密 (src2: iv=51518888, key=ZT8g6QH2kS3Xj7G5wG4JtU1F)"""

    @staticmethod
    def des3_encrypt(data, key, iv):
        cipher = DES3.new(key.encode("utf-8"), DES3.MODE_CBC, iv.encode("utf-8"))
        ct = cipher.encrypt(pad(data.encode("utf-8"), DES3.block_size))
        return base64.b64encode(ct).decode("ascii")

    @staticmethod
    def des3_decrypt(data, key, iv):
        raw = base64.b64decode(data)
        cipher = DES3.new(key.encode("utf-8"), DES3.MODE_CBC, iv.encode("utf-8"))
        pt = unpad(cipher.decrypt(raw), DES3.block_size)
        return pt.decode("utf-8")


class Spider(BaseSpider):
    def __init__(self):
        self.host = "https://dy.wnhyjc.com"
        self.init_url = "http://49.233.217.152:5112/api/user/init"
        self.list_url = "/api/vod/info"
        self.play_url = "/api/vod/play_url"
        self.iv = "51518888"
        self.key = "ZT8g6QH2kS3Xj7G5wG4JtU1F"
        self.replace_domain = "http://xs85.ruxiangsuisu.cn"
        self.play_domain = ""
        self.token = ""
        self.name = "牛牛视频"
        self.device_id = uuid.uuid4().hex
        self.session = requests.Session()
        self.session.headers.update({
            "appid": "jijing",
            "Version-Code": "10000",
            "Channel": "share",
            "Sys-Release": "11",
            "prefersex": "1",
            "Sys-Platform": "Android",
            "User-Agent": "Android",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/vnd.yourapi.v1.full+json",
            "device-id": self.device_id,
        })
        self.class_cache = None
        self.filter_cache = {}
        self.token_time = 0
        self.page_size = 20
        self._xxcjpt_token = "66b30e51a0ab342bc76502b698399356"
        self._xxcjpt_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "origin": "https://sixth.xxcjpt.com",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 abab/113eyhy5u7lhz52p1owi",
            "cookie": "device=113eyhy5u7lhz52p1owi",
        }

    def init(self, extend=""):
        if extend:
            try:
                cfg = json.loads(extend)
                if cfg.get("site"):
                    self.host = cfg["site"].rstrip("/")
                if cfg.get("iv"):
                    self.iv = cfg["iv"]
                if cfg.get("key"):
                    self.key = cfg["key"]
                if cfg.get("replace_domain"):
                    self.replace_domain = cfg["replace_domain"]
                if cfg.get("init_url"):
                    self.init_url = cfg["init_url"]
                if cfg.get("xxcjpt_token"):
                    self._xxcjpt_token = cfg["xxcjpt_token"]
            except Exception:
                pass
        self._get_token()

    def getName(self):
        return self.name

    # ========== Token管理 ==========

    def _get_token(self):
        if self.token and time.time() - self.token_time < 3600:
            return
        try:
            r = self.session.post(self.init_url, data="password=&account=", timeout=15, verify=False)
            r.raise_for_status()
            data = self._decrypt(r.json().get("data", ""))
            if data and data.get("code") == 10000:
                result = data.get("result", {})
                user_info = result.get("user_info", {})
                self.token = user_info.get("token", "")
                sys_conf = result.get("sys_conf", {})
                if sys_conf.get("host_main"):
                    self.host = sys_conf["host_main"].rstrip("/")
                if sys_conf.get("play_domain"):
                    self.play_domain = sys_conf["play_domain"]
                self.token_time = time.time()
        except Exception:
            pass

    def _decrypt(self, enc_str):
        if not enc_str:
            return {}
        try:
            enc_str = enc_str.replace("\n", "").replace(" ", "").replace("\r", "")
            return json.loads(_Crypto.des3_decrypt(enc_str, self.key, self.iv))
        except Exception:
            try:
                return json.loads(enc_str)
            except Exception:
                return {}

    def _api_post(self, path, params=None):
        self._get_token()
        url = self.host + path if path.startswith("/") else path
        headers = dict(self.session.headers)
        if self.token:
            headers["token"] = self.token
        try:
            r = self.session.post(url, data=params or {}, headers=headers, timeout=15, verify=False)
            r.raise_for_status()
            return self._decrypt(r.json().get("data", ""))
        except Exception:
            return {}

    def _xxcjpt_decode(self, text):
        """xxcjpt.com响应: 反转字符串 → base64解码 → JSON"""
        if not text or text.startswith("Error"):
            return None
        try:
            rev = text[::-1]
            pad = len(rev) % 4
            if pad:
                rev += "=" * (4 - pad)
            raw = base64.b64decode(rev)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def _xxcjpt_get(self, vid):
        """调用xxcjpt.com获取视频数据"""
        url = "https://sixth.xxcjpt.com/java/show/%s" % vid
        body = "token=%s&vid=%s&spm=home.latest" % (self._xxcjpt_token, vid)
        try:
            r = requests.post(url, data=body, headers=self._xxcjpt_headers, timeout=15, verify=False)
            return self._xxcjpt_decode(r.text)
        except Exception:
            return None

    # ========== 自动获取分类 (参照黄豆短剧 _classes) ==========
    # APK内置tab_list分类 (从tab_list_json_default.json提取)
    _FALLBACK_CLASSES = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "剧集"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
        {"type_id": "5", "type_name": "短剧"},
        {"type_id": "10", "type_name": "热舞"},
        {"type_id": "7", "type_name": "传媒"},
        {"type_id": "11", "type_name": "直播"},
    ]

    _FALLBACK_FILTERS = {
        "1": {
            "class": "剧情,武侠,战争,奇幻,犯罪,同性,动作,喜剧,爱情,科幻,悬疑,恐怖,动画,纪录片",
            "area": "内地,美国,韩国,日本,法国,英国,泰国,香港,台湾,菲律宾",
            "lang": "国语,英语,粤语,韩语,日语,泰语,法语",
            "year": "2027,2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,2011,2010,2009,2008,2007,2006,2005,2004,2003,2002,2001,1999,1998",
        },
        "2": {
            "class": "剧情,古装,历史,都市,动作,喜剧,爱情,科幻,悬疑,恐怖,动画,武侠,战争,奇幻,犯罪,同性,纪录片",
            "area": "内地,美国,韩国,日本,法国,英国,泰国,香港,台湾",
            "lang": "国语,英语,粤语,韩语,日语,泰语,法语",
            "year": "2027,2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,2011,2010,2009,2008,2007,2006,2005,2004,2003,2002,2001,1999,1998",
        },
        "3": {
            "class": "纪录片,真人秀,相声,脱口秀,音乐",
            "area": "内地,美国,韩国,日本,法国,英国,泰国,香港,台湾",
            "lang": "国语,英语,粤语,韩语,日语,泰语,法语",
            "year": "2027,2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,2011,2010,2009,2008,2007,2006,2005,2004,2003,2002,2001,1999,1998",
        },
        "4": {
            "class": "热血,搞笑,运动,动作,喜剧,爱情,科幻,冒险,恋爱,励志,推理,校园,奇幻,竞技,恐怖,同性",
            "area": "内地,美国,韩国,日本,法国,英国,香港,台湾",
            "lang": "国语,英语,粤语,韩语,日语,法语",
            "year": "2027,2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,2011,2010,2009,2008,2007,2006,2005,2004,2003,2002,2001,1999,1998",
        },
        "5": {
            "class": "都市,反转,萌宝,古装,逆袭,喜剧,闪婚,王妃,校园,民国,年代,脑洞,总裁",
        },
        "7": {
            "class": "麻豆,果冻,蜜桃,精东,糖心,天美,星空,玩偶,探花",
        },
        "10": {
            "class": "",
        },
    }

    def _classes(self):
        """自动获取分类 — 参照黄豆短剧: 优先API获取, 失败回退内置"""
        if self.class_cache:
            return self.class_cache

        arr = []
        # 1) 尝试从src2 API获取分类列表 (API无分类端点, 会失败)
        try:
            data = self._api_post("/api/vod/category", {})
            if not data:
                data = self._api_post("/api/vod/type", {})
            items = self._list(data)
            if items:
                for item in items:
                    tid = str(item.get("type_id") or item.get("id") or "")
                    name = item.get("type_name") or item.get("name") or tid
                    if tid and name:
                        arr.append({"type_id": tid, "type_name": name})
        except Exception:
            pass

        # 2) API失败 → 回退APK内置分类 (等同黄豆短剧的 _FALLBACK_CLASSES)
        if not arr:
            arr = [dict(c) for c in self._FALLBACK_CLASSES]

        self.class_cache = arr
        return arr

    def _filters(self, classes):
        """生成筛选 — 参照黄豆短剧 _filters, 从APK tab_list的type_extend提取"""
        fs = {}
        for c in classes:
            tid = c["type_id"]
            ext = self._FALLBACK_FILTERS.get(tid, {})
            filters = []
            if ext.get("class"):
                vals = [{"n": v, "v": v} for v in ext["class"].split(",")]
                filters.append({"key": "class", "name": "类型", "value": vals})
            if ext.get("area"):
                vals = [{"n": v, "v": v} for v in ext["area"].split(",")]
                filters.append({"key": "area", "name": "地区", "value": vals})
            if ext.get("lang"):
                vals = [{"n": v, "v": v} for v in ext["lang"].split(",")]
                filters.append({"key": "lang", "name": "语言", "value": vals})
            if ext.get("year"):
                vals = [{"n": v, "v": v} for v in ext["year"].split(",")]
                filters.append({"key": "year", "name": "年份", "value": vals})
            fs[tid] = filters
        return fs

    # ========== TVBox Spider 接口 ==========

    def _fetch_batch(self, vid_list, max_workers=10):
        """并发获取多个vod_id的详情"""
        results = {}
        def fetch(vid):
            data = self._api_post(self.list_url, {"vod_id": str(vid)})
            result = data.get("result")
            if result and isinstance(result, dict) and result.get("title"):
                return vid, result
            return vid, None
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(fetch, vid): vid for vid in vid_list}
            for f in as_completed(futures):
                vid, result = f.result()
                if result:
                    results[vid] = result
        return results

    def homeContent(self, filter):
        classes = self._classes()
        batch = self._fetch_batch(range(1, 13))
        items = [self._vod_from_detail(batch[vid]) for vid in sorted(batch.keys())]
        return {
            "class": classes,
            "filters": self._filters(classes),
            "list": items,
        }

    def homeVideoContent(self):
        batch = self._fetch_batch(range(1, 7))
        items = [self._vod_from_detail(batch[vid]) for vid in sorted(batch.keys())]
        return {"list": items}

    def categoryContent(self, tid, pg, filter, extend):
        extend = extend or {}
        pg = int(pg) if str(pg).isdigit() else 1

        # 热舞/传媒类: 用xxcjpt.com源 (vid从10000起)
        if str(tid) in ("10", "7"):
            return self._xxcjpt_category(tid, pg, extend)

        # 电影/剧集/综艺/动漫/短剧: 用src2 API并发枚举vod_id
        batch_size = 40
        start = (pg - 1) * batch_size + 1
        vid_list = list(range(start, start + batch_size))
        batch = self._fetch_batch(vid_list, max_workers=10)
        items = []
        for vid in sorted(batch.keys()):
            result = batch[vid]
            type_pid = str(result.get("type_pid", ""))
            if type_pid == str(tid):
                if self._match_filter(result, extend):
                    items.append(self._vod_from_detail(result))
            if len(items) >= self.page_size:
                break

        pagecount = pg + 1 if items else pg
        return {
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": 99999,
            "list": items,
        }

    def _xxcjpt_category(self, tid, pg, extend):
        """xxcjpt.com分类: 热舞(tid=10) 传媒(tid=7)"""
        page_size = 20
        start = (pg - 1) * page_size + 10000
        items = []
        for vid in range(start, start + page_size):
            data = self._xxcjpt_get(str(vid))
            if data and data.get("code") == 1:
                video = data.get("data", {}).get("video", {})
                if video and video.get("title"):
                    items.append({
                        "vod_id": "x_%s" % video.get("id", vid),
                        "vod_name": video.get("title", ""),
                        "vod_pic": video.get("image", ""),
                        "vod_remarks": self._format_duration(video.get("duration", 0)),
                    })
            if len(items) >= page_size:
                break

        pagecount = pg + 1 if items else pg
        return {
            "page": pg,
            "pagecount": pagecount,
            "limit": page_size,
            "total": 99999,
            "list": items,
        }

    def detailContent(self, ids):
        vid = str(ids[0])

        # xxcjpt源 (id以x_开头)
        if vid.startswith("x_"):
            return self._xxcjpt_detail(vid[2:])

        # src2源
        data = self._api_post(self.list_url, {"vod_id": vid})
        result = data.get("result")

        if not result or not isinstance(result, dict):
            return {"list": []}

        name = result.get("title") or vid
        pic = result.get("pic") or ""
        year = result.get("year") or ""
        area = result.get("area") or ""
        typename = result.get("tags") or ""
        actor = result.get("actor") or ""
        director = result.get("director") or ""
        content = result.get("intro") or ""
        remarks = result.get("remarks") or ""

        map_list = result.get("map_list") or []
        eps = []
        for m in map_list:
            mid = str(m.get("id", ""))
            title = m.get("title") or "高清"
            collection = m.get("collection", 1)
            if collection > 1:
                for i in range(1, collection + 1):
                    eps.append("第%s集$%s_%s" % (i, vid, mid))
            else:
                eps.append("%s$%s_%s" % (title, vid, mid))

        play_url = "#".join(eps) if eps else "高清$%s_1" % vid

        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_year": year,
            "vod_area": area,
            "type_name": typename,
            "vod_actor": actor,
            "vod_director": director,
            "vod_content": content,
            "vod_remarks": remarks,
            "vod_play_from": self.name,
            "vod_play_url": play_url,
        }
        return {"list": [vod]}

    def _xxcjpt_detail(self, vid):
        """xxcjpt.com视频详情"""
        data = self._xxcjpt_get(vid)
        if not data or data.get("code") != 1:
            return {"list": []}

        d = data.get("data", {})
        video = d.get("video", {})
        if not video:
            return {"list": []}

        title = video.get("title") or vid
        pic = video.get("image") or ""
        duration = self._format_duration(video.get("duration", 0))
        content = " ".join(video.get("content", []))
        src = video.get("src") or ""

        guess = d.get("guess", [])
        play_url = "高清$x_%s" % vid

        vod = {
            "vod_id": "x_%s" % vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_year": "",
            "vod_area": "",
            "type_name": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": content,
            "vod_remarks": duration,
            "vod_play_from": self.name,
            "vod_play_url": play_url,
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if str(pg).isdigit() else 1

        # 1) src2 API: 并发枚举vod_id, 匹配标题/演员/导演
        search_range = 100
        start = (pg - 1) * search_range + 1
        vid_list = list(range(start, start + search_range))
        batch = self._fetch_batch(vid_list, max_workers=15)
        items = []
        for vid in sorted(batch.keys()):
            result = batch[vid]
            title = result.get("title", "")
            actor = result.get("actor", "")
            director = result.get("director", "")
            if key in title or key in actor or key in director:
                items.append(self._vod_from_detail(result))
            if len(items) >= 20:
                break

        # 2) xxcjpt.com: 并发搜索 (从10000起, 每页搜索50个)
        if len(items) < 10:
            x_start = 10000 + (pg - 1) * 50
            x_vids = list(range(x_start, x_start + 50))
            x_items = []
            def x_search(vid):
                data = self._xxcjpt_get(str(vid))
                if data and data.get("code") == 1:
                    video = data.get("data", {}).get("video", {})
                    if video and key in (video.get("title") or ""):
                        return {
                            "vod_id": "x_%s" % video.get("id", vid),
                            "vod_name": video.get("title", ""),
                            "vod_pic": video.get("image", ""),
                            "vod_remarks": self._format_duration(video.get("duration", 0)),
                        }
                return None
            with ThreadPoolExecutor(max_workers=10) as pool:
                futures = [pool.submit(x_search, vid) for vid in x_vids]
                for f in as_completed(futures):
                    r = f.result()
                    if r:
                        items.append(r)
                    if len(items) >= 20:
                        break

        pagecount = pg + 1 if len(items) >= self.page_size else pg
        return {
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": 99999,
            "list": items,
        }

    def playerContent(self, flag, id, vipFlags):
        s = str(id)

        # xxcjpt源 (id以x_开头)
        if s.startswith("x_"):
            vid = s[2:]
            data = self._xxcjpt_get(vid)
            if data and data.get("code") == 1:
                src = data.get("data", {}).get("video", {}).get("src", "")
                if src:
                    header = {
                        "User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36",
                        "Referer": "https://sixth.xxcjpt.com",
                    }
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": src,
                        "header": json.dumps(header),
                    }
            return {"parse": 1, "playUrl": "", "url": ""}

        # src2源: id格式 vod_id_vod_map_id
        parts = s.split("_")
        vid = parts[0]
        vod_map_id = parts[1] if len(parts) > 1 else "1"

        data = self._api_post(self.play_url, {"vod_id": vid, "vod_map_id": vod_map_id})
        result = data.get("result", {})
        url = result.get("vod_url") or ""

        if not url:
            return {"parse": 1, "playUrl": "", "url": ""}

        header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.host,
        }
        return {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": json.dumps(header),
        }

    def isVideoContent(self):
        return True

    # ========== 内部方法 ==========

    def _list(self, data):
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ("list", "items", "data", "result", "rows"):
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                return self._list(val)
        return []

    def _vod_from_detail(self, result):
        return {
            "vod_id": str(result.get("vod_id") or result.get("id") or ""),
            "vod_name": result.get("title") or "",
            "vod_pic": result.get("pic") or "",
            "vod_remarks": result.get("remarks") or "",
        }

    def _match_filter(self, result, extend):
        if extend.get("area") and extend["area"] not in (result.get("area") or ""):
            return False
        if extend.get("year") and extend["year"] != (result.get("year") or ""):
            return False
        return True

    def _format_duration(self, seconds):
        if not seconds:
            return ""
        try:
            seconds = int(seconds)
            m = seconds // 60
            s = seconds % 60
            return "%02d:%02d" % (m, s)
        except Exception:
            return ""
