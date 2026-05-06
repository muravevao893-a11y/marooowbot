const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.ready();
  tg.setHeaderColor('#07080c');
  tg.setBackgroundColor('#07080c');
}

const state = {
  tab: 'free', me: null, leaderboard: null, winners: null, catalog: null, inventory: null, payTab: 'stars'
};
const view = document.getElementById('view');
const toast = document.getElementById('toast');
const sheet = document.getElementById('topupSheet');
const topupContent = document.getElementById('topupContent');

function initData(){ return tg?.initData || ''; }
function h(v){ return String(v ?? '').replace(/[&<>'"]/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[s])); }
function fmt(n){ return new Intl.NumberFormat('ru-RU').format(Number(n||0)); }
function pct(n){ return `${Number(n||0).toFixed(1).replace('.0','')}%`; }
function showToast(text){ toast.textContent=text; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),2300); }
function vibe(type='selectionChanged'){ try{ tg?.HapticFeedback?.[type]?.(); }catch(e){} }
function avatarHtml(){
  const photo = state.me?.telegram?.photo_url || state.me?.user?.photo_url;
  if(photo) return `<img src="${h(photo)}" alt="avatar" />`;
  return `<span class="fallback">${(state.me?.user?.first_name || 'm').slice(0,1).toUpperCase()}</span>`;
}
function username(){ return state.me?.telegram?.username ? '@'+state.me.telegram.username : (state.me?.user?.first_name || 'marooow'); }
function updateBalance(){ document.getElementById('stars').textContent = fmt(state.me?.user?.stars || 0); }
async function api(path, body){
  const res = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({initData:initData(),...(body||{})})});
  const data = await res.json().catch(()=>({ok:false,error:'bad_json'}));
  if(!res.ok || data.ok === false) throw new Error(data.message || data.error || 'Ошибка');
  return data;
}
async function getJson(path){ const res = await fetch(path); const data = await res.json(); if(!res.ok || data.ok===false) throw new Error(data.message||data.error||'Ошибка'); return data; }

async function load(){
  try{
    state.me = await api('/api/me');
    updateBalance();
    render();
    warmLoad();
  }catch(e){
    view.innerHTML = `<div class="error"><b>Открой Mini App из Telegram</b><br><br>Авторизация Mini App работает через кнопку у бота. Если ты открыл ссылку обычным браузером, Telegram не передал профиль.</div>`;
  }
}
async function warmLoad(){
  try{ state.catalog = await getJson('/api/gift-catalog'); if(state.tab==='cases') render(); }catch(e){}
  try{ state.inventory = await api('/api/inventory'); if(state.tab==='profile') render(); }catch(e){}
  try{ state.winners = await getJson('/api/winners'); }catch(e){}
  try{ state.leaderboard = await getJson('/api/leaderboard'); }catch(e){}
}

function freeView(){
  const ch = state.me.chance, u = state.me.user;
  return `
    <section class="hero">
      <div class="shine"></div>
      <h1>Дропы<br>за активность</h1>
      <p>Пиши комментарии под новыми постами. Если шанс сработает — бот ответит прямо на твой коммент.</p>
      <div class="hero-badge">🎲 Твой шанс ${pct(ch.final)}</div>
      <div class="hero-object">🧸</div>
    </section>
    <div class="grid" style="margin-top:12px">
      <div class="card"><h3>База</h3><p><b>${pct(ch.base)}</b> за нормальный комментарий</p></div>
      <div class="card"><h3>Реф‑бонус</h3><p><b>+${pct(ch.bonus)}</b> · активных: ${fmt(ch.active_refs)}</p></div>
    </div>
    <div class="section-title"><h2>Бонусы</h2><span class="badge">daily</span></div>
    <div class="card big-card">
      <div class="row"><div><h3>Ежедневный бонус</h3><p>+5 внутренних ★ и +100 EXP в профиль.</p></div><button class="btn" onclick="claimDaily()">Забрать</button></div>
    </div>
    <div class="card big-card">
      <div class="row"><div><h3>Реферальный буст</h3><p>1 активный друг = +0.1% к шансу. Максимум бонуса: +${pct(ch.cap)}.</p></div><button class="btn secondary" onclick="copyRef()">Ссылка</button></div>
    </div>
    <div class="small-note">Баланс в Mini App — внутренний баланс проекта. Telegram‑подарки выдаёт бот по правилам дропа.</div>`;
}
function passView(){
  const u=state.me.user; const progress=Math.min(100, Math.round((u.exp/u.next_level_exp)*100));
  const rows = state.leaderboard?.activity?.slice(0,3) || [];
  return `
    <section class="hero">
      <div class="shine"></div><h1>Battle<br>Pass</h1><p>Прокачивай уровень за активность, рефералов и ежедневные бонусы.</p><div class="hero-badge">Level ${u.level}</div><div class="hero-object">👑</div>
    </section>
    <div class="card big-card"><div class="row"><b>${fmt(u.exp)} / ${fmt(u.next_level_exp)} EXP</b><span>${progress}%</span></div><div class="progress" style="margin-top:10px"><span style="width:${progress}%"></span></div></div>
    <div class="grid" style="margin-top:12px"><div class="card"><h3>Premium</h3><p>Скоро: косметика, уровни и ивент‑награды.</p></div><div class="card"><h3>Топ активности</h3><p>${rows[0] ? h(rows[0].username ? '@'+rows[0].username : rows[0].first_name) + ' · ' + fmt(rows[0].score) : 'пока пусто'}</p></div></div>
    <div class="card big-card"><h3>Без ставок</h3><p>Игровые механики используются как фановые/ивентовые режимы для активности, а не как казино.</p></div>`;
}
function gamesView(){
  return `
    <div class="section-title"><h2>Мини‑игры</h2><span class="badge">demo</span></div>
    <div class="grid">
      <div class="card game-card plinko"><div class="game-visual"></div><h3>PLINKO</h3><p>Ивент‑режим без ставок. Скоро.</p><button class="btn secondary" disabled>Скоро</button></div>
      <div class="card game-card crash"><div class="game-visual"></div><h3>CRASH</h3><p>Демо‑режим для активности. Скоро.</p><button class="btn secondary" disabled>Скоро</button></div>
    </div>
    <div class="card big-card"><h3>Правило</h3><p>Не делаем реальные ставки, вывод денег или платное открытие рандомных призов. Только безопасные ивенты и визуальные режимы.</p></div>`;
}
function giftCatalog(){
  const items = state.catalog?.items || [];
  if(!items.length) return `<div class="card big-card"><h3>Каталог Telegram Gifts</h3><p>Пока не загрузился. Открой раздел позже или проверь /gifts в боте.</p></div>`;
  return `<div class="catalog">${items.map(g=>`
    <div class="gift-card">
      ${g.media_url ? `<img class="gift-media" src="${h(g.media_url)}" onerror="this.outerHTML='<div class=&quot;gift-emoji&quot;>${h(g.emoji||'🎁')}</div>'" />` : `<div class="gift-emoji">${h(g.emoji||'🎁')}</div>`}
      <div class="gift-price">★ ${fmt(g.star_count)}</div>
      <div class="gift-id">${h(g.id)}</div>
    </div>`).join('')}</div>`;
}
function casesView(){
  return `
    <section class="hero case-hero"><div class="shine"></div><h1>Кейсы</h1><p>Премиальные витрины подарков и ивент‑дропов.</p><div class="case-chest"></div><button class="btn" disabled>Открыть кейс · скоро</button></section>
    <div class="section-title"><h2>Telegram Gifts</h2><span class="badge">catalog</span></div>
    ${giftCatalog()}
    <div class="case-grid" style="margin-top:12px">
      <div class="card case-card locked"><div class="case-icon">🧸</div><h3>Bear Case</h3><p>скоро</p></div>
      <div class="card case-card locked"><div class="case-icon">💎</div><h3>NFT Case</h3><p>скоро</p></div>
    </div>`;
}
function inventoryHtml(){
  const items = state.inventory?.items || [];
  if(!items.length) return `<div class="inventory-empty"><div class="ico">🎒</div><b>Инвентарь пуст</b><br><span class="muted">Здесь будут подарки, выигранные через &marooow.</span></div>`;
  return `<div class="list">${items.map(i=>`<div class="list-item"><span>${h(i.prize_name||'подарок')}</span><b>${h(i.status||'pending')}</b></div>`).join('')}</div>`;
}
function profileView(){
  const u=state.me.user, ch=state.me.chance;
  return `
    <div class="profile-head">
      <div class="avatar">${avatarHtml()}</div>
      <div class="name">${h(username())}</div>
      <div class="level-pill">★ ${fmt(u.stars)} · Level ${u.level}</div>
    </div>
    <div class="list"><div class="list-item"><span>Твой шанс</span><b>${pct(ch.final)}</b></div><div class="list-item"><span>Побед</span><b>${fmt(u.wins_count)}</b></div><div class="list-item"><span>Активных рефов</span><b>${fmt(ch.active_refs)}</b></div><div class="list-item"><span>Ожидают</span><b>${fmt(ch.pending_refs)}</b></div></div>
    <div class="grid" style="margin-top:12px"><button class="btn" onclick="copyRef()">🔗 Реф. ссылка</button><button class="btn ghost" onclick="openTopup()">★ Пополнить</button></div>
    <div class="section-title"><h2>Инвентарь</h2><span class="badge">wins</span></div>
    ${inventoryHtml()}
    <div class="card big-card"><h3>Telegram‑профиль</h3><p>ID: <b>${u.telegram_id}</b><br>Имя: <b>${h(state.me.telegram?.first_name || u.first_name || '—')}</b><br>Username: <b>${h(state.me.telegram?.username ? '@'+state.me.telegram.username : '—')}</b></p></div>`;
}
function render(){
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active', b.dataset.tab===state.tab));
  const map = {free:freeView, pass:passView, games:gamesView, cases:casesView, profile:profileView};
  view.innerHTML = (map[state.tab] || freeView)();
}

document.querySelectorAll('.tabs button').forEach(btn=>btn.addEventListener('click',()=>{state.tab=btn.dataset.tab; render(); vibe();}));
async function claimDaily(){ try{ const d=await api('/api/daily'); showToast(`+${d.stars_added} ★ и +${d.exp_added} EXP`); state.me=await api('/api/me'); updateBalance(); render(); vibe('notificationOccurred'); }catch(e){ showToast(e.message); } }
async function copyRef(){ const link=state.me?.user?.ref_link; if(!link) return; try{ await navigator.clipboard.writeText(link); }catch(e){} showToast('Реферальная ссылка скопирована'); vibe(); }
function openTopup(){ renderTopup(); sheet.classList.add('show'); sheet.setAttribute('aria-hidden','false'); vibe(); }
function closeTopup(){ sheet.classList.remove('show'); sheet.setAttribute('aria-hidden','true'); }
document.getElementById('openTopup').addEventListener('click', openTopup);
document.querySelectorAll('[data-close-sheet]').forEach(x=>x.addEventListener('click',closeTopup));
document.querySelectorAll('.pay-tabs button').forEach(btn=>btn.addEventListener('click',()=>{state.payTab=btn.dataset.pay; document.querySelectorAll('.pay-tabs button').forEach(b=>b.classList.toggle('active', b.dataset.pay===state.payTab)); renderTopup();}));
function renderTopup(){
  if(state.payTab === 'stars'){
    const amounts=[30,100,200,500,1000,2500];
    topupContent.innerHTML = amounts.map(a=>`<div class="topup-row"><strong>★ ${fmt(a)} Stars</strong><button class="btn secondary" onclick="topup(${a})">Пополнить</button></div>`).join('') + `<div class="small-note">Оплата идёт через Telegram Stars invoice. Баланс используется внутри проекта.</div>`;
  }else if(state.payTab === 'ton'){
    topupContent.innerHTML = `<div class="coming"><b>TON пополнение</b><br><br>Для TON нужен отдельный wallet‑connect/платёжный провайдер и проверка транзакций. В этой версии вкладка подготовлена визуально, чтобы не ломать прод.</div>`;
  }else if(state.payTab === 'send'){
    topupContent.innerHTML = `<div class="coming"><b>Send</b><br><br>Подключим после выбора конкретного провайдера/токена и правил начисления. Сейчас безопасная заглушка.</div>`;
  }else{
    topupContent.innerHTML = `<div class="coming"><b>Gifts</b><br><br>Telegram не отдаёт обычному боту полный инвентарь подарков пользователя. Здесь показываем подарки, выигранные через &marooow.</div>`;
  }
}
async function topup(amount){ try{ const d=await api('/api/topup',{amount}); if(tg?.openInvoice){ tg.openInvoice(d.invoice_url, async(status)=>{ if(status==='paid'){ showToast('Пополнение прошло'); state.me=await api('/api/me'); updateBalance(); render(); }}); } else { location.href=d.invoice_url; } }catch(e){ showToast(e.message); } }

load();
