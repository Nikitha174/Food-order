/* ═══════════════════════════════════════════════════════════
   FoodRush – main.js  (fixed voice assistant + text processing)
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

// ── Client-side Text Preprocessing ───────────────────────
// Cleans chatbot input before sending to the server.
// Mirrors the server-side pipeline for consistency.
function preprocessInput(text) {
  // 1. Trim whitespace
  text = text.trim();
  // 2. Strip emojis (keep only ASCII + common unicode letters)
  text = text.replace(/[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, '').trim();
  // 3. Collapse multiple spaces
  text = text.replace(/\s+/g, ' ');
  // 4. Remove trailing punctuation clutter but keep sentence structure
  text = text.replace(/[!?.,;:]+$/g, '').trim();
  return text;
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
  const raw = chatInput?.value.trim();
  if (!raw) return;

  // Client-side preprocessing before sending
  const msg = preprocessInput(raw);
  if (!msg) return;

  appendMsg(raw, 'user');   // Show original to user
  chatInput.value = '';
  const thinkId = 'thinkBubble_' + Date.now();
  appendMsg('⏳ Thinking…', 'bot', thinkId);

  let data = null;

  // ── Step 1: Fetch from server ──────────────────────────────
  try {
    const res = await fetch('/chatbot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });

    document.getElementById(thinkId)?.remove();

    if (!res.ok) {
      // Show HTTP-level error (e.g. 500 Internal Server Error)
      const errText = await res.text().catch(() => '');
      console.error('[Chatbot] HTTP', res.status, errText);
      appendMsg(`⚠️ Server error (${res.status}). Is the app running? Restart with python app.py`, 'bot');
      return;
    }

    data = await res.json();
  } catch (fetchErr) {
    document.getElementById(thinkId)?.remove();
    console.error('[Chatbot] Fetch failed:', fetchErr);

    if (fetchErr instanceof TypeError && fetchErr.message.includes('fetch')) {
      appendMsg('🔌 Cannot connect to server. Make sure the Flask app is running (python app.py)', 'bot');
    } else {
      appendMsg('⚠️ Network error. Please check your connection and try again.', 'bot');
    }
    return;
  }

  // ── Step 2: Display bot reply ──────────────────────────────
  if (data && data.reply) {
    appendMsg(data.reply, 'bot');
  }

  // ── Step 3: Show food cards ────────────────────────────────
  if (data && data.foods && data.foods.length) {
    try {
      appendFoodCards(data.foods);
    } catch (cardErr) {
      console.warn('[Chatbot] Food card render error:', cardErr);
    }
  }

  // ── Step 4: Speak reply (outside try — TTS errors won't break chat) ──
  if (data && data.reply) {
    speakReply(data.reply);
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

// ── Voice Assistant (Fixed) ───────────────────────────────
const voiceBtn = document.getElementById('chatbotVoiceBtn');
const SpeechRecog = window.SpeechRecognition || window.webkitSpeechRecognition;
const synth = window.speechSynthesis;

if (SpeechRecog) {
  let rec = null;       // recognition instance
  let isListening = false;      // guard flag — prevents double-start crashes
  let silenceTimer = null;      // auto-stop after silence

  function createRecognizer() {
    const r = new SpeechRecog();
    r.continuous = false;  // one utterance at a time
    r.interimResults = false;  // only final results
    r.lang = 'en-IN';  // Indian English — better for food terms
    r.maxAlternatives = 1;

    r.onstart = () => {
      isListening = true;
      voiceBtn?.classList.add('listening');
      voiceBtn.title = 'Listening… Click to stop';
      // Show visual feedback in chatbot input
      if (chatInput) {
        chatInput.placeholder = '🎙️ Listening…';
        chatInput.classList.add('listening');
      }
      // Auto-stop after 8 seconds of no result
      silenceTimer = setTimeout(() => {
        if (isListening) { r.stop(); }
      }, 8000);
    };

    r.onresult = e => {
      clearTimeout(silenceTimer);
      const transcript = e.results[0][0].transcript.trim();
      const confidence = e.results[0][0].confidence;
      console.log(`[Voice] Transcript: "${transcript}" (confidence: ${confidence.toFixed(2)})`);

      if (chatInput) {
        chatInput.value = transcript;
        chatInput.classList.remove('listening');
        chatInput.placeholder = 'Ask me about food…';
      }
      // Auto-send if confidence is reasonable
      if (transcript && confidence > 0.3) {
        sendChat();
      } else if (transcript) {
        // Low confidence — show but don't auto-send
        appendMsg(`🎙️ Did you mean: "<em>${transcript}</em>"? Press send to confirm.`, 'bot');
      }
    };

    r.onerror = e => {
      clearTimeout(silenceTimer);
      isListening = false;
      voiceBtn?.classList.remove('listening');
      if (chatInput) {
        chatInput.classList.remove('listening');
        chatInput.placeholder = 'Ask me about food…';
      }

      // Specific error messages for each error type
      const errorMessages = {
        'no-speech': '🎙️ No speech detected. Please try again!',
        'audio-capture': '🎙️ Microphone not found. Check your device settings.',
        'not-allowed': '🔒 Microphone access denied. Please allow mic permission in browser settings.',
        'network': '🌐 Network error during voice recognition. Check your connection.',
        'aborted': null,   // User cancelled — show nothing
        'service-not-allowed': '🔒 Voice service not allowed. Try using HTTPS.',
      };

      const msg = errorMessages[e.error];
      if (msg) {
        appendMsg(msg, 'bot');
        showToast(msg);
      }
      console.warn('[Voice] Error:', e.error);
    };

    r.onend = () => {
      clearTimeout(silenceTimer);
      isListening = false;
      voiceBtn?.classList.remove('listening');
      voiceBtn.title = 'Click to speak';
      if (chatInput) {
        chatInput.classList.remove('listening');
        chatInput.placeholder = 'Ask me about food…';
      }
      rec = null;   // Allow new instance next time
    };

    return r;
  }

  voiceBtn?.addEventListener('click', () => {
    if (isListening) {
      // Already listening — stop it
      rec?.stop();
      clearTimeout(silenceTimer);
    } else {
      // Not listening — start new session
      // Always create a fresh recognizer (avoids "already started" errors)
      rec = createRecognizer();
      try {
        rec.start();
      } catch (err) {
        console.error('[Voice] Failed to start:', err);
        isListening = false;
        voiceBtn?.classList.remove('listening');
        appendMsg('⚠️ Could not start microphone. Please try again.', 'bot');
      }
    }
  });

} else {
  // Browser doesn't support Speech Recognition
  if (voiceBtn) {
    voiceBtn.style.opacity = '0.4';
    voiceBtn.title = 'Voice not supported in this browser. Try Chrome.';
    voiceBtn.addEventListener('click', () => {
      showToast('🎙️ Voice not supported. Use Chrome or Edge browser.');
    });
  }
}

// ── Text-to-Speech (Bot speaks back) ─────────────────────
function speakReply(text) {
  if (!synth) return;
  // Cancel any ongoing speech first
  synth.cancel();

  // Strip emojis and special chars for clean TTS
  const clean = text
    .replace(/[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, '')
    .replace(/[🌶️🍕🍔🍛🍰🥗💸🎙️⭐]/g, '')
    .trim();

  if (!clean) return;

  const utt = new SpeechSynthesisUtterance(clean);
  utt.rate = 0.92;    // Slightly slower for clarity
  utt.pitch = 1.05;    // Slightly higher — sounds friendly
  utt.volume = 1.0;

  // Pick a voice — prefer a female English voice if available
  const voices = synth.getVoices();
  const preferred = voices.find(v =>
    v.lang.startsWith('en') && v.name.toLowerCase().includes('female')
  ) || voices.find(v =>
    v.lang.startsWith('en-IN') || v.lang.startsWith('en-US')
  );
  if (preferred) utt.voice = preferred;

  utt.onerror = e => console.warn('[TTS] Speech error:', e.error);
  synth.speak(utt);
}

// Voices load asynchronously — pre-load them
if (synth && synth.onvoiceschanged !== undefined) {
  synth.onvoiceschanged = () => synth.getVoices();
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
