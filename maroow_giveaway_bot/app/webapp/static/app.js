const tg = window.Telegram?.WebApp;
if (tg){ tg.ready(); tg.expand(); tg.setHeaderColor('#050608'); tg.setBackgroundColor('#050608'); }
const initData = tg?.initData || '';
let tonConnect = null;

const state = { tab:'free', payTab:'stars', me:null, gifts:[], inventory:[], winners:[], leaders:null, loading:true, selectedTopup:100, tonInvoice:null, wallet:null };
const view = document.getElementById('view');
const starsEl = document.getElementById('stars');
const sheet = document.getElementById('topupSheet');
const topupContent = document.getElementById('topupContent');
const toastEl = document.getElementById('toast');
const loader = document.getElementById('loader');
const loaderStatus = document.getElementById('loaderStatus');
const shell = document.getElementById('shell');

const fmt = n => new Intl.NumberFormat('ru-RU').format(Number(n||0));
const pct = n => `${Number(n||0).toFixed(Number(n)%1?1:0)}%`;
const h = s => String(s ?? '').replace(/[&<>'"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[m]));
function vibe(type='light'){ try{ tg?.HapticFeedback?.impactOccurred(type); }catch{} }
function toast(text){ toastEl.textContent=text; toastEl.classList.add('show'); setTimeout(()=>toastEl.classList.remove('show'),2500); }
function statusModal(ok,title,text){
  const m=document.getElementById('statusModal'), ico=document.getElementById('statusIcon');
  ico.textContent=ok?'✓':'×'; ico.className='status-ico '+(ok?'ok':'err');
  document.getElementById('statusTitle').textContent=title; document.getElementById('statusText').textContent=text;
  m.setAttribute('aria-hidden','false'); vibe(ok?'medium':'heavy');
}
document.querySelectorAll('[data-close-modal]').forEach(x=>x.addEventListener('click',()=>document.getElementById('statusModal').setAttribute('aria-hidden','true')));

async function api(path, body=null){
  const opts = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({initData, ...body})} : {};
  const res = await fetch(path, opts); const data = await res.json().catch(()=>({ok:false,error:'bad_json'}));
  if(!res.ok && !data.message) data.message = `Ошибка ${res.status}`;
  return data;
}
async function boot(){
  try{
    loaderStatus.textContent='Подгружаем профиль…';
    state.me = await api('/api/me', {});
    if(!state.me.ok) throw new Error(state.me.message || 'auth_failed');
    loaderStatus.textContent='Загружаем подарки…';
    const [gifts, inv, wins, leaders] = await Promise.allSettled([api('/api/gift-catalog'), api('/api/inventory', {}), api('/api/winners'), api('/api/leaderboard')]);
    state.gifts = gifts.value?.items || [];
    state.inventory = inv.value?.items || [];
    state.winners = wins.value?.items || [];
    state.leaders = leaders.value?.ok ? leaders.value : null;
    starsEl.textContent = fmt(state.me.user.stars);
    initTon();
    render();
    setTimeout(()=>{ loader.classList.add('hidden'); shell.classList.add('ready'); }, 450);
  }catch(e){
    loaderStatus.textContent='Ошибка авторизации. Открой Mini App из Telegram.';
    toast('Не удалось загрузить профиль');
    console.error(e);
  }
}
function initTon(){
  if(!window.TON_CONNECT_UI) return;
  try{
    const manifestUrl = `${location.origin}/tonconnect-manifest.json`;
    tonConnect = new TON_CONNECT_UI.TonConnectUI({manifestUrl, buttonRootId:'ton-connect'});
    tonConnect.onStatusChange(wallet=>{ state.wallet = wallet; renderTopup(); });
  }catch(e){ console.warn('ton init failed', e); }
}
function refreshMe(){ return api('/api/me', {}).then(d=>{ if(d.ok){ state.me=d; starsEl.textContent=fmt(d.user.stars); render(); } }); }

function freeScreen(){ const u=state.me.user, c=state.me.chance; return `<div class="screen stack">
  <section class="hero"><div class="shine"></div><h1>Бонусы</h1><p>Забирай ежедневные звёзды, качай уровень и увеличивай шанс на дроп.</p><div class="case-chest"></div></section>
  <div class="stat-grid"><div class="stat"><b>${pct(c.final)}</b><span>твой шанс</span></div><div class="stat"><b>${fmt(u.stars)} ★</b><span>баланс</span></div></div>
  <div class="feature-row row"><div><h3>Ежедневный бонус</h3><p>+5 внутренних ★ и +100 EXP в профиль.</p></div><button class="btn" onclick="claimDaily()">Забрать</button></div>
  <div class="feature-row row"><div><h3>Реферальный буст</h3><p>1 активный друг = +0.1% к шансу. Сейчас: +${pct(c.bonus)}</p></div><button class="btn secondary" onclick="copyRef()">Ссылка</button></div>
  <div class="feature-row"><h3>Как выбить мишку?</h3><p>Пиши комментарии под новыми постами канала. Если шанс сработает — бот ответит тебе прямо под комментом.</p></div>
</div>`; }
function passScreen(){ const u=state.me.user; const progress=Math.min(100, Math.round((u.exp/u.next_level_exp)*100)); return `<div class="screen stack">
  <section class="hero"><div class="shine"></div><h1>Pass</h1><p>Боевой пропуск для ивентов, уровней и будущих наград.</p><div class="case-chest"></div></section>
  <div class="card" style="padding:18px"><div class="row"><div><h3 style="margin:0">Level ${u.level}</h3><p class="small-note">${fmt(u.exp)} / ${fmt(u.next_level_exp)} EXP</p></div><span class="rank-pill">${progress}%</span></div><div class="loader-bar" style="margin:14px 0 0"><i style="width:${Math.max(8,progress)}%;animation:none;transform:none"></i></div></div>
  <div class="grid"><div class="feature-row"><h3>Premium</h3><p>Премиум‑награды для будущих ивентов. Скоро.</p></div><div class="feature-row"><h3>Топы</h3><p>Рейтинги активности и рефов уже работают.</p></div></div>
</div>`; }
function gamesScreen(){ return `<div class="screen stack"><div class="section-title"><span>Мини‑игры</span><span class="rank-pill">fan/demo</span></div>
  <div class="grid"><div class="card game-card plinko"><div class="game-visual"></div><h3>PLINKO</h3><p>Красивый демо‑ивент без ставок.</p><button class="btn secondary" onclick="playDemo('plinko')">Играть</button></div><div class="card game-card crash"><div class="game-visual"></div><h3>CRASH</h3><p>Демо‑режим для активности.</p><button class="btn secondary" onclick="playDemo('crash')">Играть</button></div></div>
  <div class="card game-card roulette"><div class="game-visual"></div><h3>ARCADE</h3><p>Здесь будут безопасные ивент‑игры: без вывода денег и реальных ставок.</p><button class="btn secondary" onclick="playDemo('arcade')">Получить EXP</button></div>
  <div class="feature-row"><h3>Важно</h3><p>Мини‑игры фановые/ивентовые. Реального казино, вывода денег и ставок нет — проект остаётся безопасным.</p></div></div>`; }
function casesScreen(){ const items=state.gifts.slice(0,6).map(g=>`<div class="card case-card"><div class="gift-visual">${g.media_url?`<img src="${g.media_url}" onerror="this.remove()">`:h(g.emoji)}</div><h3>${h(g.emoji)} Gift</h3><p><b>★ ${fmt(g.star_count)}</b>${g.remaining_count?` · осталось ${fmt(g.remaining_count)}`:''}</p><button class="btn secondary" disabled>Витрина</button></div>`).join(''); return `<div class="screen stack">
  <section class="hero case-hero"><div class="shine"></div><h1>Кейсы</h1><p>Премиальные витрины подарков и ивент‑дропов.</p><div class="case-chest"></div><button class="btn" disabled>Открыть кейс · скоро</button></section>
  <div class="section-title"><span>Telegram Gifts</span><button class="btn secondary" onclick="loadGifts()">Обновить</button></div><div class="grid">${items || `<div class="feature-row"><h3>Пока пусто</h3><p>Команда /gifts в боте покажет доступные подарки.</p></div>`}</div></div>`; }
function profileScreen(){ const u=state.me.user, c=state.me.chance, t=state.me.telegram; const inv=state.inventory.map(x=>`<div class="inventory-card"><div style="font-size:30px">🎁</div><div><b>${h(x.prize_name)}</b><p class="small-note">${h(x.status)} · ${new Date(x.created_at).toLocaleDateString('ru-RU')}</p></div></div>`).join(''); const photo=u.photo_url?`<img class="avatar" src="${h(u.photo_url)}">`:`<div class="avatar" style="display:grid;place-items:center;font-size:42px">&</div>`; return `<div class="screen stack">
  <div class="card profile-hero">${photo}<h2>${h(t.first_name||u.first_name||'marooow')}</h2><p class="small-note">${u.username?'@'+h(u.username):'ID '+u.telegram_id}</p><div class="rank-pill">★ ${fmt(u.stars)} · Level ${u.level}</div></div>
  <div class="stat-grid"><div class="stat"><b>${pct(c.final)}</b><span>шанс</span></div><div class="stat"><b>${fmt(c.active_refs)}</b><span>активных рефов</span></div><div class="stat"><b>${fmt(u.wins_count)}</b><span>побед</span></div><div class="stat"><b>${fmt(c.attempts_7d)}</b><span>попыток 7д</span></div></div>
  <div class="grid"><button class="btn" onclick="openTopup()">Пополнить</button><button class="btn secondary" onclick="copyRef()">Реф. ссылка</button></div>
  <div class="section-title"><span>Инвентарь проекта</span><span class="small-note">${state.inventory.length}</span></div>${inv || `<div class="feature-row"><h3>Ничего не найдено</h3><p>Здесь будут подарки, выигранные через &marooow.</p></div>`}
</div>`; }
function render(){ if(!state.me?.ok) return; document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active', b.dataset.tab===state.tab)); const screens={free:freeScreen, pass:passScreen, games:gamesScreen, cases:casesScreen, profile:profileScreen}; view.innerHTML=(screens[state.tab]||freeScreen)(); }
document.querySelectorAll('.tabs button').forEach(btn=>btn.addEventListener('click',()=>{state.tab=btn.dataset.tab; render(); vibe();}));
document.getElementById('openTopup').addEventListener('click', openTopup); document.getElementById('copyRef').addEventListener('click', copyRef);
document.querySelectorAll('[data-close-sheet]').forEach(x=>x.addEventListener('click',()=>sheet.setAttribute('aria-hidden','true')));
document.querySelectorAll('.pay-tabs button').forEach(btn=>btn.addEventListener('click',()=>{state.payTab=btn.dataset.pay; document.querySelectorAll('.pay-tabs button').forEach(b=>b.classList.toggle('active', b.dataset.pay===state.payTab)); renderTopup(); vibe();}));
function openTopup(){ sheet.setAttribute('aria-hidden','false'); renderTopup(); vibe('medium'); }
const amounts=[30,100,200,500,1000,2500,5000];
function renderTopup(){
  document.getElementById('ton-connect')?.classList.toggle('show', state.payTab==='ton');
  if(state.payTab==='stars') topupContent.innerHTML = amounts.map(a=>`<div class="topup-row"><div><strong>★ ${fmt(a)} Stars</strong><br><small>Зачисление на баланс Mini App</small></div><button class="btn secondary" onclick="topupStars(${a})">Оплатить</button></div>`).join('') + `<div class="small-note">Оплата через Telegram Stars invoice. При успехе баланс пополнится автоматически.</div>`;
  else if(state.payTab==='ton'){
    const ton=state.me.ton; const connected = state.wallet?.account?.address;
    topupContent.innerHTML = `<div class="feature-row"><h3>TON пополнение</h3><p>${ton.enabled?`Платёж уйдёт на кошелёк проекта. Курс: 1 TON = ${fmt(ton.stars_per_ton)} ★.`:'TON кошелёк проекта не настроен.'}</p>${connected?`<p class="small-note">Кошелёк подключен: ${connected.slice(0,6)}…${connected.slice(-5)}</p>`:''}</div>` + amounts.map(a=>{const tonAmount=(a/ton.stars_per_ton).toFixed(4);return `<div class="topup-row"><div><strong>★ ${fmt(a)} Stars</strong><br><small>≈ ${tonAmount} TON</small></div><button class="btn secondary" ${ton.enabled?'':'disabled'} onclick="topupTon(${a})">Оплатить TON</button></div>`}).join('') + `<div class="small-note">После отправки транзакции появится ожидание проверки. Для авто‑проверки нужен TONAPI_KEY.</div>`;
  }
  else if(state.payTab==='send') topupContent.innerHTML = amounts.map(a=>`<div class="topup-row"><div><strong>★ ${fmt(a)} Stars</strong><br><small>Будущий Send‑провайдер</small></div><button class="btn secondary" disabled>Скоро</button></div>`).join('') + `<div class="small-note">Send вкладка готова визуально; подключение провайдера делается отдельно.</div>`;
  else topupContent.innerHTML = `<div class="feature-row"><h3>Gifts</h3><p>Подарки отображаются в инвентаре проекта после выигрыша. Импорт личного инвентаря Telegram обычному боту недоступен.</p></div>` + (state.inventory.map(x=>`<div class="inventory-card"><div>🎁</div><div><b>${h(x.prize_name)}</b><p class="small-note">${h(x.status)}</p></div></div>`).join('') || `<div class="feature-row"><h3>Ничего не найдено</h3><p>Пока подарков нет.</p></div>`);
}
async function topupStars(amount){ const r=await api('/api/topup',{amount}); if(!r.ok){statusModal(false,'Ошибка оплаты',r.message||'Не удалось создать счёт');return} try{ tg.openInvoice(r.invoice_url, s=>{ if(s==='paid'){statusModal(true,'Оплата прошла','Баланс скоро обновится. Ожидайте получения товара.'); setTimeout(refreshMe,1200)} else {statusModal(false,'Оплата не прошла','Платёж отменён или не был завершён.')}})}catch{ location.href=r.invoice_url; } }
async function topupTon(amount){
  if(!tonConnect){statusModal(false,'TON недоступен','TonConnect не загрузился. Открой через Telegram и попробуй снова.');return}
  if(!state.wallet){ try{ await tonConnect.openModal(); }catch{} if(!state.wallet){toast('Сначала подключи кошелёк');return} }
  const dep=await api('/api/ton/create',{stars_amount:amount}); if(!dep.ok){statusModal(false,'Ошибка TON',dep.message||'Не удалось создать платёж');return}
  const tx={validUntil: Math.floor(Date.now()/1000)+600, messages:[{address: dep.address, amount: dep.amount_nano}]};
  try{ const sent=await tonConnect.sendTransaction(tx); statusModal(true,'Транзакция отправлена','Проверяем оплату. Если сеть загружена, зачисление может занять пару минут.'); const conf=await api('/api/ton/confirm',{deposit_id:dep.deposit_id,boc:sent?.boc||''}); if(conf.status==='paid'){statusModal(true,'Оплата прошла',`Зачислено ★ ${fmt(conf.stars_added)}. Ожидайте получения товара.`); await refreshMe()} else {statusModal(true,'Платёж ожидает проверки',conf.message||'Транзакция отправлена, ожидаем подтверждение.')} }
  catch(e){statusModal(false,'Оплата не прошла','Транзакция отменена или кошелёк вернул ошибку.');}
}
async function claimDaily(){ const r=await api('/api/daily',{}); if(r.ok){statusModal(true,'Бонус получен',`+${r.stars_added} ★ и +${r.exp_added} EXP`); await refreshMe()} else statusModal(false,'Не получилось',r.message||'Бонус пока недоступен'); }
async function playDemo(game){ const r=await api('/api/play/demo',{game}); if(r.ok){statusModal(true,'Игра завершена',`+${r.exp_added} EXP. Демо‑очки: ${r.demo_points}`); await refreshMe()} else statusModal(false,'Ошибка игры',r.message||'Попробуй позже'); }
async function loadGifts(){ const r=await api('/api/gift-catalog'); if(r.ok){state.gifts=r.items||[]; render(); toast('Подарки обновлены')} else statusModal(false,'Ошибка Gifts',r.message||'Не загрузилось'); }
function copyRef(){ const link=state.me?.user?.ref_link || ''; if(!link) return; navigator.clipboard?.writeText(link); toast('Реферальная ссылка скопирована'); vibe(); }
boot();
