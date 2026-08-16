const HOST = 'https://accfanan.x18c87so.work';
const TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI2NTgxMjQ2NyIsImlhdCI6MTc4NjY0NjkwOCwibmJmIjoxNzg2NjY0OTIyLCJleHAiOjE5NDQzNDQ5MjJ9.7poZoAttovGH_UnkM0ZKYVjExOVGc8Uh5U62TVVQNuE';
const DEVICE_ID = 'h5_7c768c18bd97473c9f9d23b25c21f';
const IMG_DOMAIN = 'https://wiuuh1425js3.iumigc.com/';
const UA = 'Mozilla/5.0 (Linux; Android 12; SM-G9750 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 Mobile Safari/537.36';
const XOR_KEY = [50,48,50,48,45,122,113,51,45,56,56,56];

const CAT_MAP = {
    'jx': '4', 'dm': '2', 'lifan': '24', 'rebao': '53',
    'luanlun': '27', 'guochan': '28', 'wanghuang': '30',
    'luoli': '52', 'av': '57', 'chuanmei': '58', 'zhongkou': '59',
};

const FILTERS = {
    'dm': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '同人', 'v': '同人'}, {'n': '国漫', 'v': '国漫'},
        {'n': '3D', 'v': '3D'}, {'n': 'MMD', 'v': 'MMD'}, {'n': '原神', 'v': '原神'},
        {'n': '崩坏3', 'v': '崩坏3'}, {'n': '番剧', 'v': '番剧'},
    ]}],
    'rebao': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '熟女肥逼', 'v': '熟女肥逼'}, {'n': '人妖伪娘', 'v': '人妖伪娘'},
        {'n': '美胸巨乳', 'v': '美胸巨乳'}, {'n': '探花偷拍', 'v': '探花偷拍'}, {'n': '少女萝莉', 'v': '少女萝莉'},
        {'n': '强奸迷奸', 'v': '强奸迷奸'}, {'n': '多人群p', 'v': '多人群p'}, {'n': '调教SM', 'v': '调教SM'},
        {'n': '泄露流出', 'v': '泄露流出'}, {'n': '媚黑骚逼', 'v': '媚黑骚逼'}, {'n': '孕妇做爱', 'v': '孕妇做爱'},
        {'n': '校园霸凌', 'v': '校园霸凌'},
    ]}],
    'luanlun': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '父女', 'v': '父女'}, {'n': '母子', 'v': '母子'},
        {'n': '兄妹', 'v': '兄妹'}, {'n': '姐弟', 'v': '姐弟'}, {'n': '岳母', 'v': '岳母'},
        {'n': '嫂子', 'v': '嫂子'}, {'n': '侄女', 'v': '侄女'}, {'n': '师生', 'v': '师生'},
        {'n': '小姨子', 'v': '小姨子'}, {'n': '小马拉大车', 'v': '小马拉大车'},
    ]}],
    'guochan': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '情侣自拍', 'v': '情侣自拍'}, {'n': '三级片', 'v': '三级片'},
        {'n': '户外露出', 'v': '户外露出'}, {'n': '颜值女神', 'v': '颜值女神'}, {'n': '反差婊', 'v': '反差婊'},
        {'n': '明星换脸', 'v': '明星换脸'}, {'n': '推油按摩', 'v': '推油按摩'}, {'n': '网红博主', 'v': '网红博主'},
        {'n': '偷情出轨', 'v': '偷情出轨'}, {'n': '主播大秀', 'v': '主播大秀'}, {'n': '真实换妻', 'v': '真实换妻'},
        {'n': '合集盘点', 'v': '合集盘点'},
    ]}],
    'wanghuang': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '白桃少女', 'v': '白桃少女'}, {'n': '台北娜娜', 'v': '台北娜娜'},
        {'n': '柚子猫', 'v': '柚子猫'}, {'n': '桥本香菜', 'v': '桥本香菜'}, {'n': '饼干姐姐', 'v': '饼干姐姐'},
        {'n': '小欣奈', 'v': '小欣奈'}, {'n': '御梦子', 'v': '御梦子'}, {'n': '捅主任', 'v': '捅主任'},
        {'n': '黑椒盖饭', 'v': '黑椒盖饭'}, {'n': '冉冉学姐', 'v': '冉冉学姐'}, {'n': '鸡教练', 'v': '鸡教练'},
        {'n': '唐伯虎', 'v': '唐伯虎'}, {'n': '咪妮', 'v': '咪妮'}, {'n': '玩偶姐姐', 'v': '玩偶姐姐'},
        {'n': '情深叉喔', 'v': '情深叉喔'}, {'n': '水冰月', 'v': '水冰月'}, {'n': '米胡桃', 'v': '米胡桃'},
        {'n': '白菜妹妹', 'v': '白菜妹妹'}, {'n': '二代cc', 'v': '二代cc'},
    ]}],
    'luoli': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '护士', 'v': '护士'}, {'n': '白虎嫩妹', 'v': '白虎嫩妹'},
        {'n': '女仆', 'v': '女仆'}, {'n': 'cosplay', 'v': 'cosplay'}, {'n': '洛丽塔', 'v': '洛丽塔'},
        {'n': 'JK学生', 'v': 'JK学生'}, {'n': '丝袜美腿', 'v': '丝袜美腿'}, {'n': '激情自慰', 'v': '激情自慰'},
        {'n': '空姐', 'v': '空姐'}, {'n': '泳装', 'v': '泳装'}, {'n': '职场OL', 'v': '职场OL'},
        {'n': '骚萝破处', 'v': '骚萝破处'},
    ]}],
    'av': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '最新AV', 'v': '最新AV'}, {'n': '人妻偷情', 'v': '人妻偷情'},
        {'n': '暗黑迷奸', 'v': '暗黑迷奸'}, {'n': '日本JK', 'v': '日本JK'}, {'n': '无码破解', 'v': '无码破解'},
        {'n': '中文AV', 'v': '中文AV'}, {'n': 'FC2', 'v': 'FC2'}, {'n': '重口AV', 'v': '重口AV'},
    ]}],
    'chuanmei': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '麻豆传媒', 'v': '麻豆传媒'}, {'n': 'jvid', 'v': 'jvid'},
        {'n': '蜜桃传媒', 'v': '蜜桃传媒'}, {'n': '天美传媒', 'v': '天美传媒'}, {'n': '糖心vlog', 'v': '糖心vlog'},
        {'n': '性视界', 'v': '性视界'},
    ]}],
    'zhongkou': [{'key': 'videoTag', 'name': '分类', 'value': [
        {'n': '全部', 'v': ''}, {'n': '屎尿', 'v': '屎尿'}, {'n': '四爱', 'v': '四爱'},
        {'n': '血腥暴力', 'v': '血腥暴力'}, {'n': '肛交菊花', 'v': '肛交菊花'}, {'n': '道具', 'v': '道具'},
        {'n': '捆绑', 'v': '捆绑'}, {'n': '男同真爱', 'v': '男同真爱'}, {'n': '虐待', 'v': '虐待'},
        {'n': '人兽', 'v': '人兽'}, {'n': '踩踏虐鸡', 'v': '踩踏虐鸡'}, {'n': '恋物足交', 'v': '恋物足交'},
    ]}],
};

let _token = TOKEN;

function _md5(s) {
    try { return CryptoJS.MD5(s).toString(); }
    catch(e) {
        function _rl(n,c){return(n<<c)|(n>>>(32-c));}
        function _cmn(q,a,b,x,s,t){a=(((a+q)&0xffffffff)+((b&0xffffffff)+((x&0xffffffff)+((t&0xffffffff)))))&0xffffffff;return((a<<s)|(a>>>(32-s)));}
        function _ff(a,b,c,d,x,s,t){return _cmn((b&c)|((~b)&d),a,b,x,s,t);}
        function _gg(a,b,c,d,x,s,t){return _cmn((b&d)|(c&(~d)),a,b,x,s,t);}
        function _hh(a,b,c,d,x,s,t){return _cmn(b^c^d,a,b,x,s,t);}
        function _ii(a,b,c,d,x,s,t){return _cmn(c^(b|(~d)),a,b,x,s,t);}
        function _bt(s){let n=s.length,state=[1732584193,4023233417,2562383102,271733878],i;let w=[];for(i=0;i<n*8;i+=8)w[i>>5]|=(s.charCodeAt(i/8)&0xff)<<(i%32);w[n*8>>5]|=0x80<<(n*8%32);w[(((n+64)>>>9)<<4)+14]=n*8;let a=state[0],b=state[1],c=state[2],d=state[3];for(i=0;i<w.length;i+=16){let oa=a,ob=b,oc=c,od=d;a=_ff(a,b,c,d,w[i],7,3614090360);d=_ff(d,a,b,c,w[i+1],12,3905402710);c=_ff(c,d,a,b,w[i+2],17,606105819);b=_ff(b,c,d,a,w[i+3],22,3250441966);a=_ff(a,b,c,d,w[i+4],7,4118548399);d=_ff(d,a,b,c,w[i+5],12,1200080426);c=_ff(c,d,a,b,w[i+6],17,2821735955);b=_ff(b,c,d,a,w[i+7],22,4249261313);a=_ff(a,b,c,d,w[i+8],7,1770035416);d=_ff(d,a,b,c,w[i+9],12,2336552879);c=_ff(c,d,a,b,w[i+10],17,4294925233);b=_ff(b,c,d,a,w[i+11],22,2304563134);a=_ff(a,b,c,d,w[i+12],7,1804603682);d=_ff(d,a,b,c,w[i+13],12,4254626195);c=_ff(c,d,a,b,w[i+14],17,2792965006);b=_ff(b,c,d,a,w[i+15],22,1236535329);a=_gg(a,b,c,d,w[i+1],5,4129170786);d=_gg(d,a,b,c,w[i+6],9,3225465664);c=_gg(c,d,a,b,w[i+11],14,643717713);b=_gg(b,c,d,a,w[i],20,3921069994);a=_gg(a,b,c,d,w[i+5],5,3593408604);d=_gg(d,a,b,c,w[i+10],9,38016083);c=_gg(c,d,a,b,w[i+15],14,3634488961);b=_gg(b,c,d,a,w[i+4],20,3889429448);a=_gg(a,b,c,d,w[i+9],5,568446438);d=_gg(d,a,b,c,w[i+14],9,3275163606);c=_gg(c,d,a,b,w[i+3],14,4107603335);b=_gg(b,c,d,a,w[i+8],20,1163531501);a=_gg(a,b,c,d,w[i+13],5,2850285829);d=_gg(d,a,b,c,w[i+2],9,4243563512);c=_gg(c,d,a,b,w[i+7],14,1735328473);b=_gg(b,c,d,a,w[i+12],20,2368359562);a=_hh(a,b,c,d,w[i+5],4,1272893353);d=_hh(d,a,b,c,w[i+8],11,4139469664);c=_hh(c,d,a,b,w[i+11],16,3200236656);b=_hh(b,c,d,a,w[i+14],23,681279174);a=_hh(a,b,c,d,w[i+1],4,3936430074);d=_hh(d,a,b,c,w[i+4],11,3585372222);c=_hh(c,d,a,b,w[i+7],16,76029189);b=_hh(b,c,d,a,w[i+10],23,3654602809);a=_hh(a,b,c,d,w[i+13],4,3873151461);d=_hh(d,a,b,c,w[i],11,530742520);c=_hh(c,d,a,b,w[i+3],16,3570075683);b=_hh(b,c,d,a,w[i+6],23,1094730640);a=_hh(a,b,c,d,w[i+9],4,1272893353);d=_hh(d,a,b,c,w[i+12],11,1554986371);c=_hh(c,d,a,b,w[i+15],16,3127144090);b=_hh(b,c,d,a,w[i+2],23,718787259);a=_ii(a,b,c,d,w[i],6,3220324291);d=_ii(d,a,b,c,w[i+7],10,325883790);c=_ii(c,d,a,b,w[i+14],15,3921009510);b=_ii(b,c,d,a,w[i+5],21,4294604198);a=_ii(a,b,c,d,w[i+12],6,2923127282);d=_ii(d,a,b,c,w[i+3],10,426960872);c=_ii(c,d,a,b,w[i+10],15,3440353234);b=_ii(b,c,d,a,w[i+1],21,3495327696);a=_ii(a,b,c,d,w[i+8],6,762760074);d=_ii(d,a,b,c,w[i+15],10,4058365548);c=_ii(c,d,a,b,w[i+6],15,3253937590);b=_ii(b,c,d,a,w[i+13],21,3050519390);a=_ii(a,b,c,d,w[i+4],6,752134366);d=_ii(d,a,b,c,w[i+11],10,3551537187);c=_ii(c,d,a,b,w[i+2],15,3347076658);b=_ii(b,c,d,a,w[i+9],21,2935565168);a=_ii(a,b,c,d,w[i+14],6,275424022);d=_ii(d,a,b,c,w[i+11],10,2926520808);c=_ii(c,d,a,b,w[i+4],15,3824822025);b=_ii(b,c,d,a,w[i+9],21,3480954580);a=_ii(a,b,c,d,w[i+12],6,2857825104);d=_ii(d,a,b,c,w[i+1],10,2866666688);c=_ii(c,d,a,b,w[i+8],15,3715738753);b=_ii(b,c,d,a,w[i+15],21,3259121080);a=_ii(a,b,c,d,w[i+3],6,2763147749);d=_ii(d,a,b,c,w[i+10],10,4060649904);c=_ii(c,d,a,b,w[i+5],15,3344665587);b=_ii(b,c,d,a,w[i+2],21,3271055571);a=_ii(a,b,c,d,w[i+9],6,2957110211);d=_ii(d,a,b,c,w[i+6],10,2967979657);c=_ii(c,d,a,b,w[i+11],15,3634488961);b=_ii(b,c,d,a,w[i+14],21,2810845715);a=_ii(a,b,c,d,w[i+4],6,2656043715);d=_ii(d,a,b,c,w[i+11],10,2919606890);c=_ii(c,d,a,b,w[i+1],15,3281632855);b=_ii(b,c,d,a,w[i+8],21,3257593700);a=((a+oa)&0xffffffff);b=((b+ob)&0xffffffff);c=((c+oc)&0xffffffff);d=((d+od)&0xffffffff);}let r=[a,b,c,d];let h='';for(i=0;i<4;i++){let v=r[i];for(let j=0;j<4;j++)h+='0123456789abcdef'[v>>(j*8+4)&15]+'0123456789abcdef'[v>>(j*8)&15];}return h;}
        return _bt(s);
    }
}

function _hdr() {
    let t = String(Date.now());
    let s = _md5(t.substring(3, 8));
    let sid = _md5(String(Date.now())).substring(0, 16);
    return {
        'User-Agent': UA,
        'Accept': 'application/json, text/plain, */*',
        'Referer': HOST + '/',
        'Origin': HOST,
        'device': 'Android',
        'appVersion': '1.9.6',
        'User-Mark': 'xhp',
        'deviceId': DEVICE_ID,
        'aut': _token,
        't': t,
        's': s,
        'sid': sid,
    };
}

function _dec(encData) {
    try {
        let k = CryptoJS.enc.Utf8.parse(_token.substring(2, 18));
        let raw = CryptoJS.enc.Base64.parse(encData);
        let dec = CryptoJS.AES.decrypt({ciphertext: raw}, k, {
            iv: k, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7
        });
        let d = CryptoJS.enc.Utf8.stringify(dec);
        if (d && (d[0] === '[' || d[0] === '{')) return JSON.parse(d);
        return d;
    } catch(e) {
        return null;
    }
}

function _api(path, params) {
    for (let i = 0; i < 3; i++) {
        let h = _hdr();
        let p = Object.assign({}, params || {});
        p._t = h.t;
        let qs = Object.keys(p).map(k => k + '=' + encodeURIComponent(p[k])).join('&');
        let url = HOST + '/api' + path + '?' + qs;
        try {
            let res = req(url, {headers: h, timeout: 15000});
            let text = res.content;
            if (!text) continue;
            let j = JSON.parse(text);
            if (j.code === 301) continue;
            if (j.code !== 200) return null;
            if (j.encData) return _dec(j.encData);
            return j.data !== undefined ? j.data : j;
        } catch(e) {
            continue;
        }
    }
    return null;
}

function _img(url, domain) {
    if (!url) return '';
    if (Array.isArray(url)) url = url[0] || '';
    if (!url) return '';
    if (!url.startsWith('http')) {
        let d = domain || IMG_DOMAIN;
        if (!d.endsWith('/')) d += '/';
        url = d + url.replace(/^\/+/, '');
    }
    try {
        let b = getProxyUrl();
        if (b.indexOf('?') < 0) b += '?do=py';
        return b + '&type=img&url=' + encodeURIComponent(url);
    } catch(e) {
        return url;
    }
}

function _items(data) {
    if (Array.isArray(data)) return data;
    if (typeof data !== 'object' || data === null) return [];
    for (let k of ['data', 'list', 'videoList', 'records']) {
        if (Array.isArray(data[k])) return data[k];
    }
    return [];
}

function _domain(data) {
    return (typeof data === 'object' && data !== null) ? (data.domain || '') : '';
}

function _parseList(data) {
    let domain = _domain(data);
    let items = _items(data);
    let res = [];
    let seen = {};
    for (let item of (items || [])) {
        try {
            if (typeof item !== 'object' || item === null) continue;
            let vid = String(item.videoId || item.id || '');
            if (!vid || seen[vid]) continue;
            seen[vid] = true;
            let name = String(item.title || vid);
            let pic = item.coverImg || '';
            if (Array.isArray(pic)) pic = pic[0] || '';
            let dur = String(item.playTime || '');
            if (dur && /^\d+$/.test(dur)) {
                dur = String(Math.floor(parseInt(dur) / 60)) + ':' + String(parseInt(dur) % 60).padStart(2, '0');
            }
            let sid = vid + '@@@' + '' + '@@@' + encodeURIComponent(name) + '@@@' + encodeURIComponent(typeof pic === 'string' ? pic : '');
            res.push({
                'vod_id': sid,
                'vod_name': name,
                'vod_pic': _img(pic, domain),
                'vod_remarks': dur || '',
            });
        } catch(e) {
            continue;
        }
    }
    return res;
}

function init(ext) {
    try {
        if (typeof ext === 'string' && ext) {
            let cfg = JSON.parse(ext);
            if (cfg.site) { HOST = cfg.site.replace(/\/+$/, ''); }
            if (cfg.token) { _token = cfg.token; }
        }
    } catch(e) {}
}

function home(filter) {
    let classes = [
        {'type_id': 'jx', 'type_name': '精选'},
        {'type_id': 'dm', 'type_name': '动漫'},
        {'type_id': 'lifan', 'type_name': '里番'},
        {'type_id': 'rebao', 'type_name': '热播'},
        {'type_id': 'luanlun', 'type_name': '乱伦'},
        {'type_id': 'guochan', 'type_name': '国产'},
        {'type_id': 'wanghuang', 'type_name': '网黄'},
        {'type_id': 'luoli', 'type_name': '萝莉'},
        {'type_id': 'av', 'type_name': 'AV'},
        {'type_id': 'chuanmei', 'type_name': '传媒'},
        {'type_id': 'zhongkou', 'type_name': '重口'},
    ];
    let videos = [];
    try {
        let data = _api('/video/getByClassify', {page: 1, pageSize: 20, classifyId: 4, sortType: 0, restricted: 0});
        videos = _parseList(data);
    } catch(e) {}
    return JSON.stringify({'class': classes, 'filters': FILTERS, 'list': videos, 'type': '影视'});
}

function homeVod() {
    try {
        let data = _api('/video/getByClassify', {page: 1, pageSize: 20, classifyId: 4, sortType: 0, restricted: 0});
        return JSON.stringify({'list': _parseList(data)});
    } catch(e) {
        return JSON.stringify({'list': []});
    }
}

function category(tid, pg, filter, extend) {
    let page = parseInt(pg) || 1;
    if (typeof extend === 'string') {
        try { extend = JSON.parse(extend); } catch(e) { extend = {}; }
    }
    extend = extend || {};
    let cid = extend.classifyId || '';
    if (!cid) cid = CAT_MAP[tid] || '';
    let vt = extend.videoTag || '';
    let data;
    if (vt) {
        data = _api('/video/tagTitleList', {tagsTitle: vt, page: page, pageSize: 20, sortType: 0, restricted: 0});
    } else {
        data = _api('/video/getByClassify', {page: page, pageSize: 20, sortType: 0, restricted: 0, classifyId: cid});
    }
    let items = _parseList(data);
    let pc = items.length ? page + 1 : 1;
    return JSON.stringify({page: page, pagecount: pc, limit: 20, total: pc * 20, list: items});
}

function detail(ids) {
    let vid = Array.isArray(ids) ? String(ids[0]) : String(ids);
    let ps = vid.split('@@@');
    let rid = ps.length > 0 ? ps[0] : vid;
    let name = ps.length > 2 ? decodeURIComponent(ps[2]) : rid;
    let pic = ps.length > 3 ? decodeURIComponent(ps[3]) : '';
    let data = _api('/video/getVideoById', {videoId: rid});
    let vname = name, vpic = pic, vcontent = '', video_url = '', auth_key = '', domain = '';
    if (typeof data === 'object' && data !== null) {
        domain = data.domain || '';
        vname = data.title || vname;
        vpic = data.coverImg || vpic;
        if (Array.isArray(vpic)) vpic = vpic[0] || vpic;
        vcontent = data.description || data.synopsis || '';
        video_url = data.videoUrl || data.playUrl || '';
        auth_key = data.authKey || '';
        let tags = data.tagTitles || [];
        if (tags.length) vcontent = '标签: ' + tags.join(' ') + (vcontent ? '\n' + vcontent : '');
    }
    let play_url = '';
    if (video_url) {
        play_url = '播放$' + HOST + '/api/m3u8/h5/decode?path=' + encodeURIComponent(video_url);
    }
    let vod = {
        'vod_id': vid,
        'vod_name': vname,
        'vod_pic': _img(vpic, domain),
        'vod_content': vcontent,
        'vod_play_from': 'AcFanH5',
        'vod_play_url': play_url,
    };
    return JSON.stringify({'list': [vod]});
}

function search(wd, quick, pg) {
    let page = parseInt(pg) || 1;
    let data = _api('/search/keyWordV2', {searchWord: wd, page: page, pageSize: 20});
    let items = [];
    let domain = '';
    if (typeof data === 'object' && data !== null) {
        domain = data.domain || '';
        items = data.videoList || [];
        if (typeof items === 'object' && !Array.isArray(items)) items = items.data || [];
    } else if (Array.isArray(data)) {
        items = data;
    }
    let parsed = _parseList({domain: domain, data: items});
    let pc = parsed.length ? page + 1 : 1;
    return JSON.stringify({list: parsed, page: page, pagecount: pc, limit: 20, total: pc * 20});
}

function play(flag, id, flags) {
    let url = id || '';
    let hdr = {'User-Agent': UA, 'Referer': HOST + '/', 'Origin': HOST};
    if (url.indexOf('.m3u8') >= 0 || url.indexOf('.mp4') >= 0) {
        return JSON.stringify({parse: 0, url: url, header: hdr});
    }
    if (url.indexOf(HOST + '/api/m3u8/') === 0) {
        return JSON.stringify({parse: 0, url: url, header: hdr});
    }
    return JSON.stringify({parse: 1, url: url, header: hdr});
}

function proxy(params) {
    try {
        let pt = params.type || params.do || '';
        let u = params.url || '';
        if (Array.isArray(u)) u = u[0];
        u = u ? decodeURIComponent(u) : '';
        if (pt === 'img' && u) {
            let res = req(u, {headers: {'User-Agent': UA, 'Referer': HOST + '/'}, timeout: 15000});
            let data = new Uint8Array(res.content.length);
            for (let i = 0; i < data.length; i++) data[i] = res.content.charCodeAt(i) & 0xff;
            let n = Math.min(100, data.length);
            for (let i = 0; i < n; i++) data[i] ^= XOR_KEY[i % XOR_KEY.length];
            let ct;
            if (data[0] === 0x89 && data[1] === 0x50) ct = 'image/png';
            else if (data[0] === 0x47 && data[1] === 0x49) ct = 'image/gif';
            else if (data[0] === 0x52 && data[1] === 0x49 && data[8] === 0x57 && data[9] === 0x45) ct = 'image/webp';
            else ct = 'image/jpeg';
            return [200, ct, data];
        }
        return [404, 'text/plain', 'nf'];
    } catch(e) {
        return [500, 'text/plain', 'err'];
    }
}

__JS_SPIDER__ = {
    init: init,
    home: home,
    homeVod: homeVod,
    category: category,
    detail: detail,
    play: play,
    search: search,
    proxy: proxy,
};

export function __jsEvalReturn() {
    return {
        init: init, home: home, homeVod: homeVod, category: category,
        detail: detail, play: play, search: search, proxy: proxy,
    };
}

export default {
    init: init, home: home, homeVod: homeVod, category: category,
    detail: detail, play: play, search: search, proxy: proxy,
};
