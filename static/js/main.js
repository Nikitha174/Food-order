/* ═══════════════════════════════════════════════════════════
   FoodRush – main.js
═══════════════════════════════════════════════════════════ */

// ── Add to Cart ───────────────────────────────────────────
async function addToCart(foodId, btn) {
  const orig = btn ? btn.innerHTML : '';
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }
  try {
    const res = await fetch('/add-to-cart', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ food_id: foodId })
    });
    const data = await res.json();
    if (data.success) {
      document.querySelectorAll('#cartBadge, .cart-badge-sm').forEach(el => el.textContent = data.cart_count);
      showToast('Added to cart! 🛒');
    }
  } catch (e) { console.error(e); }
  if (btn) { setTimeout(() => { btn.disabled = false; btn.innerHTML = orig || '<i class="fas fa-plus"></i> Add'; }, 600); }
}

// ── Cart Toast ────────────────────────────────────────────
function showToast(msg) {
  const t = document.getElementById('cartToast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

// ── Chatbot ───────────────────────────────────────────────
const chatFab = document.getElementById('chatbotFab');
const chatWindow = document.getElementById('chatbotWindow');
const chatClose = document.getElementById('chatbotClose');
const chatInput = document.getElementById('chatbotInput');
const chatSend = document.getElementById('chatbotSend');
const chatMsgs = document.getElementById('chatbotMessages');

chatFab?.addEventListener('click', () => {
  chatWindow.classList.toggle('open');
  if (chatWindow.classList.contains('open')) chatInput?.focus();
});
chatClose?.addEventListener('click', () => chatWindow.classList.remove('open'));
chatSend?.addEventListener('click', sendChat);
chatInput?.addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

async function sendChat() {
  const msg = chatInput?.value.trim();
  if (!msg) return;
  appendMsg(msg, 'user');
  chatInput.value = '';
  appendMsg('Thinking…', 'bot', 'thinkBubble');
  try {
    const res = await fetch('/chatbot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    document.getElementById('thinkBubble')?.remove();
    appendMsg(data.reply, 'bot');
    speak(data.reply);
    if (data.foods && data.foods.length) appendFoodCards(data.foods);
  } catch {
    document.getElementById('thinkBubble')?.remove();
    appendMsg('Sorry, something went wrong. Please try again.', 'bot');
  }
}

function appendMsg(text, role, id) {
  const wrap = document.createElement('div');
  wrap.className = `chat-msg ${role}`;
  if (id) wrap.id = id;
  wrap.innerHTML = `<div class="chat-bubble">${text}</div>`;
  chatMsgs.append(wrap);
  chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

function appendFoodCards(foods) {
  const wrap = document.createElement('div');
  wrap.className = 'chat-msg bot';
  let html = '<div class="chat-food-cards">';
  foods.forEach(f => {
    html += `<div class="chat-food-card">
      <img src="/static/images/${f.image}" alt="${f.name}" onerror="this.src='/static/images/default.png'"/>
      <div class="cfc-info">
        <strong>${f.name}</strong>
        <span>₹${Math.round(f.price)}</span>
        <span>⭐ ${f.rating}</span>
      </div>
      <button class="cfc-add" onclick="addToCart(${f.id}, this)"><i class="fas fa-plus"></i></button>
    </div>`;
  });
  html += '</div>';
  wrap.innerHTML = html;
  chatMsgs.append(wrap);
  chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

// ── Voice Assistant ───────────────────────────────────────
const voiceBtn = document.getElementById('chatbotVoiceBtn');
const SpeechRecog = window.SpeechRecognition || window.webkitSpeechRecognition;
const synth = window.speechSynthesis;

if (SpeechRecog) {
  const rec = new SpeechRecog();
  rec.interimResults = false;
  rec.lang = 'en-US';

  voiceBtn?.addEventListener('click', () => {
    voiceBtn.classList.contains('listening') ? rec.stop() : rec.start();
  });
  rec.onstart = () => voiceBtn?.classList.add('listening');
  rec.onend = () => voiceBtn?.classList.remove('listening');
  rec.onresult = e => {
    const t = e.results[0][0].transcript;
    if (chatInput) { chatInput.value = t; sendChat(); }
  };
} else {
  if (voiceBtn) voiceBtn.style.display = 'none';
}

function speak(text) {
  if (!synth) return;
  const clean = text.replace(/[\u{1F300}-\u{1FFFF}]/gu, '');
  const utt = new SpeechSynthesisUtterance(clean);
  utt.rate = 0.95;
  synth.cancel();
  synth.speak(utt);
}

// ── Search Suggestions ────────────────────────────────────
let _sugTimer;
function fetchSuggestions(query, containerId, inputId) {
  clearTimeout(_sugTimer);
  const box = document.getElementById(containerId);
  if (!box) return;
  if (query.length < 2) { box.innerHTML = ''; return; }
  _sugTimer = setTimeout(async () => {
    try {
      const res = await fetch('/search-suggestions?q=' + encodeURIComponent(query));
      const items = await res.json();
      box.innerHTML = '';
      items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.innerHTML = `<i class="fas fa-search"></i> ${item}`;
        div.onclick = () => {
          document.getElementById(inputId).value = item;
          box.innerHTML = '';
          window.location.href = '/?search=' + encodeURIComponent(item);
        };
        box.appendChild(div);
      });
    } catch { }
  }, 280);
}
