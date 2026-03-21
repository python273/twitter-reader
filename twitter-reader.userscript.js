// ==UserScript==
// @name        Twitter Reader Buttons
// @namespace   Violentmonkey Scripts
// @match       https://x.com/*
// @noframes
// @grant       none
// @version     1.5
// ==/UserScript==

const BUTTONS = [
  { id: 'quick25', text: 'Middle (25 req)', limit: 25 },
  { id: 'quick5',  text: 'Quick (5 req)',   limit: 5 },
  { id: 'thread',  text: 'Thread',         limit: null },
];

const LOCALHOST = 'http://localhost:3412';

const container = document.createElement('div');
container.setAttribute('style', `
  position:fixed;
  top:16px;
  right:16px;
  z-index:9999;
  display:flex;
  gap:20px;
`);
document.body.appendChild(container);

function createButton(cfg) {
  const a = document.createElement('a');
  a.id = cfg.id;
  a.textContent = cfg.text;
  a.href = '#';
  a.setAttribute('style', `
    background:#fff;
    color:#111;
    border:1px solid #ccc;
    border-radius:4px;
    padding:6px 12px;
    font-size:14px;
    text-decoration:none;
    box-shadow:0 2px 8px rgba(0,0,0,0.07);
    display:none;
  `);
  container.appendChild(a);
  return a;
}

const btnMap = {};
BUTTONS.forEach(cfg => { btnMap[cfg.id] = createButton(cfg); });

const isStatusPage = () => /\/status\/\d+/.test(location.pathname);

function updateButtons() {
  const visible = isStatusPage();
  BUTTONS.forEach(cfg => {
    const el = btnMap[cfg.id];
    if (visible) {
      const url = new URL(LOCALHOST);
      url.searchParams.set('url', location.href);
      if (cfg.limit) url.searchParams.set('limit_requests', cfg.limit);
      el.href = url.toString();
      el.style.display = 'inline-block';
    } else {
      el.style.display = 'none';
    }
  });
}

function dispatchLocationChange() {
  window.dispatchEvent(new Event('vm-locationchange'));
}

const origPush = history.pushState;
history.pushState = function (...args) {
  const ret = origPush.apply(this, args);
  dispatchLocationChange();
  return ret;
};
const origReplace = history.replaceState;
history.replaceState = function (...args) {
  const ret = origReplace.apply(this, args);
  dispatchLocationChange();
  return ret;
};

window.addEventListener('popstate', dispatchLocationChange);
window.addEventListener('vm-locationchange', updateButtons);

let lastHref = location.href;
setInterval(() => {
  if (location.href !== lastHref) {
    lastHref = location.href;
    updateButtons();
  }
}, 500);

updateButtons();