// ==UserScript==
// @name         かわいいね！速報 タイトル → supjav 検索
// @namespace    kawaiine-supjav
// @version      1.0.0
// @description  kawaiine-sokuhou.com の各作品タイトル横に「supjav」検索ボタンを追加。クリックでタイトル全文を supjav.com で検索します（元の DMM リンクはそのまま）。
// @match        *://kawaiine-sokuhou.com/*
// @match        *://www.kawaiine-sokuhou.com/*
// @run-at       document-idle
// @grant        none
// @host         https://kawaiine-sokuhou.com/shinjin/archive/2026/7/p=1.php
// ==/UserScript==

(function () {
  'use strict';

  // ボタンのスタイル（タイトルと同じ行に表示）
  const STYLE_ID = 'kawaiine-supjav-style';
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
.supjav-btn {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 8px;
  font-size: 12px;
  line-height: 1.7;
  font-weight: bold;
  color: #fff !important;
  background: #e60012;
  border-radius: 4px;
  text-decoration: none !important;
  vertical-align: middle;
  white-space: nowrap;
}
.supjav-btn:hover {
  background: #ff4b5c;
}
`;
    document.head.appendChild(style);
  }

  // タイトル → supjav 検索 URL（スペースは '+' に変換、WordPress の ?s= 形式）
  function toSupjavUrl(title) {
    const q = encodeURIComponent(title).replace(/%20/g, '+');
    return 'https://supjav.com/?s=' + q;
  }

  function process() {
    const links = document.querySelectorAll('div.title > a[href*="al.fanza.co.jp"]');
    links.forEach((a) => {
      if (a.dataset.supjavDone) return; // 処理済み
      a.dataset.supjavDone = '1';

      const title = (a.textContent || '').trim();
      if (!title) return;

      const btn = document.createElement('a');
      btn.href = toSupjavUrl(title);
      btn.target = '_blank';
      btn.rel = 'noopener noreferrer';
      btn.className = 'supjav-btn';
      btn.title = 'supjav で「' + title + '」を検索';
      btn.textContent = 'supjav';
      a.insertAdjacentElement('afterend', btn);
    });
  }

  process();

  // 動的コンテンツ（ページング・LazyLoad など）にも対応
  const observer = new MutationObserver(() => process());
  observer.observe(document.body, { childList: true, subtree: true });
})();
