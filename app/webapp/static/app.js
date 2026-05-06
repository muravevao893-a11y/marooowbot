const tg = window.Telegram?.WebApp;
if (tg) { tg.expand(); tg.ready(); tg.setHeaderColor('#07080c'); tg.setBackgroundColor('#07080c'); }

const state = { tab: 'free', me: null, leaderboard: null, winners: null };
const view = document.getElementById('view');
const toast = document.getElementById('toast');

function showToast(text){ toast.textContent=text; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),2200); }
function initData(){ return tg?.initData || ''; }
async function api(path, body){
  const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({initData:initData(), ...(body||{})})});
  const data = await res.json().catch(()=>({ok:false,error:'bad_json'}));
  if(!res.ok) throw new Error(data.message || data.error || 'Ошибка');
  return data;
}
async function getJson(path){ const res=await fetch(path); return res.json(); }
function fmt(n){ return new Intl.NumberFormat('ru-RU').format(Number(n||0)); }
function pct(n){ return `${Number(n||0).toFixed(1).replace('.0','')}%`; }
function userName(){ return state.me?.user?.username ? '@'+state.me.user.username : (state.me?.user?.first_name || 'marooow'); }
function updateBalance(){ document.getElementById('stars').textContent = fmt(state.me?.user?.stars || 0); }

async function load(){
  try{ state.me = await api('/api/me'); updateBalance(); }
  catch(e){
    view.innerHTML = `<div class="hero"><h1>Открой Mini App из Telegram</h1><p>Авторизация работает только внутри Telegram-кнопки у бота.</p><div class="timer">@marooowbot</div><div class="bear">🧸</div></div>`;
    return;
  }
  render();
}

function freeView(){
  const me=state.me; const ch=me.chance;
  return `
    <section class="hero">
      <h1>Лови мишку<br>за комментарии</h1>
      <p>Пиши под новыми постами. Если шанс сработает — бот ответит прямо на твой комментарий.</p>
      <div class="timer">🎲 Твой шанс: ${pct(ch.final)}</div>
      <div class="bear">🧸</div>
    </section>
    <div class="grid">
      <div class="card"><h3>База</h3><p><b>${pct(ch.base)}</b> за подходящий комментарий</p></div>
      <div class="card"><h3>Реф-бонус</h3><p><b>+${pct(ch.bonus)}</b> · активных: ${ch.active_refs}</p></div>
    </div>
    <div class="section-title"><h2>Бесплатные действия</h2><span class="badge">ежедневно</span></div>
    <div class="card big-card">
      <div class="row"><div><h3>Ежедневный бонус</h3><p>+5 внутренних ⭐ и +100 EXP для профиля</p></div><button class="btn" onclick="claimDaily()">Забрать</button></div>
    </div>
    <div class="card big-card">
      <h3>Как активировать реферала</h3>
      <p>Друг должен нажать /start, подписаться и пообщаться в комментариях. После активности тебе капает +0.1% к шансу.</p>
    </div>`;
}
function passView(){ const u=state.me.user; const progress=Math.min(100, Math.round((u.exp/u.next_level_exp)*100)); return `
  <section class="hero"><h1>Battle Pass</h1><p>Получай EXP за активность, рефов и ежедневные действия.</p><div class="timer">Level ${u.level}</div><div class="bear">🐧</div></section>
  <div class="card big-card"><div class="row"><b>${fmt(u.exp)} / ${fmt(u.next_level_exp)} EXP</b><span>${progress}%</span></div><div class="progress" style="margin-top:10px"><span style="width:${progress}%"></span></div></div>
  <div class="grid"><div class="card"><h3>Premium</h3><p>Скоро: усиленные задания и косметика.</p></div><div class="card"><h3>Лидерборд</h3><p>Соревнуйся по активности и рефам.</p></div></div>`; }
function gamesView(){ return `<div class="section-title"><h2>Игры</h2><span class="badge">скоро</span></div><div class="grid"><div class="card game-card plinko"><h3>PLINKO</h3><p>Мини-игра для ивентов</p><button class="btn secondary">Скоро</button></div><div class="card game-card crash"><h3>CRASH</h3><p>Демо-режим без ставок</p><button class="btn secondary">Скоро</button></div></div><div class="card big-card"><h3>Важно</h3><p>Игры будут только фановые/ивентовые, без казино и реальных ставок.</p></div>`; }
function casesView(){ return `<section class="hero"><h1>Кейсы</h1><p>Красивые витрины для будущих ивентов и промо-дропов.</p><div class="bear">🎁</div></section><div class="grid"><div class="card case-card"><div class="case-emoji">🧸</div><h3>Bear Case</h3><p>скоро</p></div><div class="card case-card"><div class="case-emoji">💎</div><h3>NFT Case</h3><p>скоро</p></div></div>`; }
function profileView(){ const u=state.me.user, ch=state.me.chance; return `<div class="profile-head"><div class="avatar">🧸</div><div class="name">${userName()}</div><div class="muted">⭐ ${fmt(u.stars)} · Level ${u.level}</div></div><div class="list"><div class="list-item"><span>Твой шанс</span><b>${pct(ch.final)}</b></div><div class="list-item"><span>Побед</span><b>${fmt(u.wins_count)}</b></div><div class="list-item"><span>Активных рефов</span><b>${fmt(ch.active_refs)}</b></div><div class="list-item"><span>Ожидают</span><b>${fmt(ch.pending_refs)}</b></div></div><div class="grid" style="margin-top:12px"><button class="btn" onclick="copyRef()">🔗 Реф. ссылка</button><button class="btn ghost" onclick="topup(100)">⭐ Пополнить 100</button></div><div class="card big-card"><h3>Твоя ссылка</h3><p style="word-break:break-all">${u.ref_link}</p></div>`; }

function render(){
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active', b.dataset.tab===state.tab));
  view.innerHTML = ({free:freeView, pass:passView, games:gamesView, cases:casesView, profile:profileView}[state.tab] || freeView)();
}
document.querySelectorAll('.tabs button').forEach(btn=>btn.addEventListener('click',()=>{state.tab=btn.dataset.tab; render(); tg?.HapticFeedback?.selectionChanged();}));
async function claimDaily(){ try{ const d=await api('/api/daily'); showToast(`+${d.stars_added} ⭐ и +${d.exp_added} EXP`); state.me=await api('/api/me'); updateBalance(); render(); }catch(e){ showToast(e.message); } }
async function copyRef(){ const link=state.me?.user?.ref_link; if(!link) return; try{ await navigator.clipboard.writeText(link); }catch(e){} showToast('Реферальная ссылка скопирована'); }
async function topup(amount){ try{ const d=await api('/api/topup',{amount}); if(tg?.openInvoice){ tg.openInvoice(d.invoice_url,()=>{}); } else { location.href=d.invoice_url; } }catch(e){ showToast(e.message); } }
document.getElementById('copyRef').addEventListener('click',copyRef);
load();
