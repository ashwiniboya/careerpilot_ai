/**
 * CareerPilot AI — Frontend Application JavaScript
 *
 * Handles:
 *   - Authentication (login/register → JWT storage)
 *   - View navigation
 *   - Dashboard data loading & chart rendering
 *   - Streaming SSE chat with typing indicators
 *   - Resume drag-and-drop upload
 *   - WebSocket mock interview session
 *   - Job application tracker (Kanban)
 *   - Roadmap timeline rendering
 *   - Toast notifications
 */

'use strict';

/* ============================================================
   CONFIG
   ============================================================ */

const API_BASE = '';   // Same origin (FastAPI serves this SPA)
let JWT_TOKEN  = localStorage.getItem('careerpilot_token') || null;
let CURRENT_USER = null;

/* ============================================================
   UTILITIES
   ============================================================ */

function $id(id) { return document.getElementById(id); }

function showToast(message, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', info: '💡' };
  const container = $id('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${message}</span>`;
  container.appendChild(toast);
  toast.addEventListener('click', () => toast.remove());
  setTimeout(() => toast.remove(), duration);
}

function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (JWT_TOKEN) headers['Authorization'] = `Bearer ${JWT_TOKEN}`;
  return fetch(API_BASE + path, { ...options, headers });
}

function setLoading(btnId, spinnerId, loading) {
  const btn = $id(btnId);
  const spinner = $id(spinnerId);
  if (!btn) return;
  btn.disabled = loading;
  if (spinner) spinner.classList.toggle('hidden', !loading);
  const text = btn.querySelector('.btn-text');
  if (text) text.style.opacity = loading ? '0.5' : '1';
}

/* ============================================================
   AUTH
   ============================================================ */

function switchAuthTab(tab) {
  $id('login-form').classList.toggle('hidden', tab !== 'login');
  $id('register-form').classList.toggle('hidden', tab !== 'register');
  $id('tab-login').classList.toggle('active', tab === 'login');
  $id('tab-register').classList.toggle('active', tab === 'register');
}

async function handleLogin(e) {
  e.preventDefault();
  setLoading('login-btn', 'login-spinner', true);
  $id('login-error').classList.add('hidden');

  const email    = $id('login-email').value.trim();
  const password = $id('login-password').value;

  try {
    const body = new URLSearchParams({ username: email, password });
    const res  = await fetch(`${API_BASE}/api/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Invalid credentials');
    }

    const data = await res.json();
    JWT_TOKEN = data.access_token;
    localStorage.setItem('careerpilot_token', JWT_TOKEN);
    await initApp();
  } catch (err) {
    const el = $id('login-error');
    el.textContent = err.message;
    el.classList.remove('hidden');
  } finally {
    setLoading('login-btn', 'login-spinner', false);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  setLoading('register-btn', 'register-spinner', true);
  $id('register-error').classList.add('hidden');

  const payload = {
    full_name: $id('reg-name').value.trim(),
    email:     $id('reg-email').value.trim(),
    password:  $id('reg-password').value,
  };

  try {
    const res = await apiFetch('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Registration failed');
    }

    showToast('Account created! Signing you in…', 'success');
    $id('login-email').value    = payload.email;
    $id('login-password').value = payload.password;
    switchAuthTab('login');
    setTimeout(() => $id('login-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })), 300);
  } catch (err) {
    const el = $id('register-error');
    el.textContent = err.message;
    el.classList.remove('hidden');
  } finally {
    setLoading('register-btn', 'register-spinner', false);
  }
}

async function fetchCurrentUser() {
  const res = await apiFetch('/api/auth/me');
  if (!res.ok) throw new Error('Session expired');
  return res.json();
}

function logout() {
  JWT_TOKEN = null;
  CURRENT_USER = null;
  localStorage.removeItem('careerpilot_token');
  $id('auth-overlay').classList.remove('hidden');
  $id('auth-overlay').style.display = 'flex';
  showToast('Signed out successfully', 'info');
}

$id('logout-btn').addEventListener('click', logout);

/* ============================================================
   NAVIGATION
   ============================================================ */

const VIEWS = ['dashboard', 'chat', 'resume', 'interview', 'roadmap', 'applications'];

function navigateTo(viewName) {
  VIEWS.forEach(v => {
    const view = $id(`view-${v}`);
    const nav  = $id(`nav-${v}`);
    if (view) view.classList.toggle('active', v === viewName);
    if (view) view.classList.toggle('hidden', v !== viewName);
    if (nav)  nav.classList.toggle('active', v === viewName);
  });

  // Lazy-load view data
  if (viewName === 'dashboard')    loadDashboard();
  if (viewName === 'roadmap')      loadRoadmap();
  if (viewName === 'applications') loadApplications();
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    navigateTo(item.dataset.view);
  });
});

/* ============================================================
   INIT APP
   ============================================================ */

async function initApp() {
  try {
    CURRENT_USER = await fetchCurrentUser();

    // Hide auth overlay
    const overlay = $id('auth-overlay');
    overlay.style.display = 'none';

    // Update sidebar user info
    $id('sidebar-user-name').textContent  = CURRENT_USER.full_name || CURRENT_USER.email;
    $id('sidebar-user-email').textContent = CURRENT_USER.email;
    $id('user-avatar-mini').textContent   = (CURRENT_USER.full_name || CURRENT_USER.email)[0].toUpperCase();

    navigateTo('dashboard');
  } catch {
    // Show auth overlay
    $id('auth-overlay').style.display = 'flex';
  }
}

/* ============================================================
   DASHBOARD
   ============================================================ */

let chartsRendered = false;

async function loadDashboard() {
  try {
    const [metricsRes, atsRes, interviewRes, skillsRes] = await Promise.all([
      apiFetch('/api/dashboard/metrics'),
      apiFetch('/api/dashboard/ats-history'),
      apiFetch('/api/dashboard/interview-history'),
      apiFetch('/api/dashboard/skills'),
    ]);

    const metrics   = await metricsRes.json();
    const atsData   = await atsRes.json();
    const ivData    = await interviewRes.json();
    const skillData = await skillsRes.json();

    renderKPIs(metrics);
    renderATSChart(atsData);
    renderInterviewChart(ivData);
    renderSkillRadar(skillData);

    const badge = $id('data-source-badge');
    badge.textContent = metrics.data_source === 'live' ? 'Live Data' : 'Demo Mode';
    badge.style.background = metrics.data_source === 'live' ? 'var(--green-dim)' : 'var(--amber-dim)';
    badge.style.color       = metrics.data_source === 'live' ? 'var(--green)'    : 'var(--amber)';
  } catch (err) {
    console.error('Dashboard load error:', err);
  }
}

function refreshDashboard() { loadDashboard(); showToast('Dashboard refreshed', 'info', 2000); }

function renderKPIs(m) {
  // ATS
  const ats = m.latest_ats_score;
  $id('kpi-ats-value').textContent = ats != null ? ats.toFixed(1) : '—';
  $id('kpi-ats-trend').textContent = m.ats_score_trend || '';
  if (ats) {
    const circumference = 2 * Math.PI * 24;
    const fill = (ats / 100) * circumference;
    $id('ats-ring').style.strokeDasharray = `${fill} ${circumference}`;
  }

  // Interview
  $id('kpi-interview-value').textContent = m.interview_avg_score != null ? `${m.interview_avg_score}/5` : '—';
  $id('kpi-interview-sub').textContent   = `${m.interview_sessions_completed || 0} sessions`;

  // Roadmap
  const pct = m.roadmap_progress_percent || 0;
  $id('kpi-roadmap-value').textContent = `${pct}%`;
  $id('roadmap-progress-fill').style.width = `${pct}%`;

  // Applications
  $id('kpi-apps-value').textContent = m.active_applications != null ? m.active_applications : '—';
  $id('kpi-apps-sub').textContent   = `${m.total_applications || 0} total tracked`;
}

/* ── Mini Chart Renderer (vanilla canvas, no lib dependency) ── */
function drawLineChart(canvasId, labels, values, color, yLabel = '') {
  const canvas = $id(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || 400;
  const H = canvas.offsetHeight || 180;
  canvas.width = W; canvas.height = H;

  const pad = { top: 20, right: 20, bottom: 36, left: 44 };
  const w = W - pad.left - pad.right;
  const h = H - pad.top  - pad.bottom;

  ctx.clearRect(0, 0, W, H);

  if (!values.length) {
    ctx.fillStyle = 'rgba(255,255,255,0.2)';
    ctx.font = '13px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No data yet', W / 2, H / 2);
    return;
  }

  const min = Math.min(...values) * 0.9;
  const max = Math.max(...values) * 1.05 || 1;

  function xOf(i) { return pad.left + (i / (values.length - 1 || 1)) * w; }
  function yOf(v) { return pad.top + h - ((v - min) / (max - min)) * h; }

  // Grid
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i++) {
    const y = pad.top + (h / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + w, y); ctx.stroke();
  }

  // Gradient fill
  const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + h);
  grad.addColorStop(0, color.replace(')', ', 0.25)').replace('hsl', 'hsla'));
  grad.addColorStop(1, color.replace(')', ', 0)').replace('hsl', 'hsla'));

  ctx.beginPath();
  ctx.moveTo(xOf(0), yOf(values[0]));
  values.forEach((v, i) => { if (i > 0) ctx.lineTo(xOf(i), yOf(v)); });
  ctx.lineTo(xOf(values.length - 1), pad.top + h);
  ctx.lineTo(pad.left, pad.top + h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  ctx.lineCap  = 'round';
  values.forEach((v, i) => {
    if (i === 0) ctx.moveTo(xOf(i), yOf(v));
    else ctx.lineTo(xOf(i), yOf(v));
  });
  ctx.stroke();

  // Dots
  values.forEach((v, i) => {
    ctx.beginPath();
    ctx.arc(xOf(i), yOf(v), 4, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = 'rgba(10,12,20,0.8)';
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  // X labels
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.font = '11px Outfit, sans-serif';
  ctx.textAlign = 'center';
  labels.forEach((lbl, i) => {
    const short = typeof lbl === 'string' ? lbl.slice(-5) : lbl;
    ctx.fillText(short, xOf(i), H - 8);
  });
}

function renderATSChart(data) {
  const labels = data.map(d => d.date);
  const values = data.map(d => d.score);
  drawLineChart('ats-chart', labels, values, 'hsl(190, 95%, 50%)');
}

function renderInterviewChart(data) {
  const labels = data.map(d => d.date);
  const values = data.map(d => d.score);
  drawLineChart('interview-chart', labels, values, 'hsl(265, 80%, 65%)');
}

/* ── Radar Chart ── */
function renderSkillRadar(skills) {
  const canvas = $id('skills-radar');
  if (!canvas || !skills.length) return;
  const ctx    = canvas.getContext('2d');
  const size   = 280;
  canvas.width = size; canvas.height = size;
  const cx = size / 2, cy = size / 2;
  const R  = 110;
  const N  = skills.length;
  const step = (2 * Math.PI) / N;

  ctx.clearRect(0, 0, size, size);

  // Grid rings
  for (let ring = 1; ring <= 5; ring++) {
    const r = (ring / 5) * R;
    ctx.beginPath();
    for (let i = 0; i < N; i++) {
      const a = step * i - Math.PI / 2;
      const x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Axis lines
  for (let i = 0; i < N; i++) {
    const a = step * i - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + R * Math.cos(a), cy + R * Math.sin(a));
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.stroke();
  }

  const polygon = (values, color, fill) => {
    ctx.beginPath();
    values.forEach((v, i) => {
      const a = step * i - Math.PI / 2;
      const r = (v / 5) * R;
      const x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
  };

  // Target (dim)
  polygon(skills.map(s => s.target), 'hsla(265,80%,65%,0.4)', 'hsla(265,80%,65%,0.06)');
  // Current
  polygon(skills.map(s => s.current), 'hsl(190,95%,50%)', 'hsla(190,95%,50%,0.12)');

  // Labels
  ctx.font = '11px Outfit, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  skills.forEach((s, i) => {
    const a = step * i - Math.PI / 2;
    const r = R + 22;
    ctx.fillText(s.skill, cx + r * Math.cos(a), cy + r * Math.sin(a) + 4);
  });
}

/* ============================================================
   CHAT
   ============================================================ */

let chatSessionId = 'session_' + Date.now();
let isStreaming = false;

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function sendSuggestion(text) {
  $id('chat-input').value = text;
  sendMessage();
}

function appendMessage(role, content, agentName = '') {
  const messages = $id('chat-messages');
  const welcome  = messages.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = `
    <div class="msg-avatar">${role === 'user' ? (CURRENT_USER?.full_name || 'U')[0].toUpperCase() : '🤖'}</div>
    <div>
      <div class="msg-bubble">${escapeHtml(content)}</div>
      ${agentName ? `<div class="msg-agent-tag">${agentName}</div>` : ''}
    </div>
  `;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function appendTypingIndicator() {
  const messages = $id('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg assistant';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    </div>
  `;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function removeTypingIndicator() {
  const el = $id('typing-indicator');
  if (el) el.remove();
}

async function sendMessage() {
  if (isStreaming) return;
  const input = $id('chat-input');
  const text  = input.value.trim();
  if (!text) return;

  input.value = '';
  input.style.height = 'auto';
  isStreaming = true;
  $id('send-btn').disabled = true;

  appendMessage('user', text);
  appendTypingIndicator();

  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${JWT_TOKEN}`,
      },
      body: JSON.stringify({ message: text, session_id: chatSessionId }),
    });

    if (!res.ok) throw new Error('Chat request failed');

    removeTypingIndicator();

    const messages = $id('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'msg assistant';

    let agentName = 'orchestrator';
    let bubble;
    let agentTag;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const json = line.slice(6).trim();
        if (!json) continue;

        try {
          const chunk = JSON.parse(json);
          agentName = chunk.agent || agentName;

          if (!bubble) {
            msgDiv.innerHTML = `
              <div class="msg-avatar">🤖</div>
              <div>
                <div class="msg-bubble" id="streaming-bubble"></div>
                <div class="msg-agent-tag" id="streaming-agent">${agentName}</div>
              </div>
            `;
            messages.appendChild(msgDiv);
            bubble = msgDiv.querySelector('#streaming-bubble');
            agentTag = msgDiv.querySelector('#streaming-agent');
            $id('chat-agent-name').textContent = agentName;
          }

          if (chunk.token) {
            fullText += chunk.token;
            bubble.textContent = fullText;
            messages.scrollTop = messages.scrollHeight;
          }

          if (chunk.done) {
            agentTag.textContent = agentName;
            break;
          }
        } catch {}
      }
    }
  } catch (err) {
    removeTypingIndicator();
    appendMessage('assistant', `Error: ${err.message}`);
    showToast('Chat error. Please try again.', 'error');
  } finally {
    isStreaming = false;
    $id('send-btn').disabled = false;
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/* ============================================================
   RESUME
   ============================================================ */

let uploadedResumeText = '';

function handleDragOver(e) {
  e.preventDefault();
  $id('drop-zone').classList.add('drag-over');
}

function handleDragLeave() {
  $id('drop-zone').classList.remove('drag-over');
}

function handleDrop(e) {
  e.preventDefault();
  $id('drop-zone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadResume(file);
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) uploadResume(file);
}

async function uploadResume(file) {
  const allowed = ['.pdf', '.docx', '.txt', '.md'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast(`File type "${ext}" not supported`, 'error');
    return;
  }

  const progressEl = $id('upload-progress');
  const barEl      = $id('upload-bar');
  const statusEl   = $id('upload-status');

  progressEl.classList.remove('hidden');
  barEl.style.width = '20%';
  statusEl.textContent = 'Uploading…';

  const form = new FormData();
  form.append('file', file);

  try {
    barEl.style.width = '50%';
    const res = await fetch(`${API_BASE}/api/resume/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${JWT_TOKEN}` },
      body: form,
    });

    barEl.style.width = '80%';

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }

    const data = await res.json();
    barEl.style.width = '100%';
    statusEl.textContent = 'Upload complete!';

    showToast(`Resume "${file.name}" uploaded successfully`, 'success');
    renderExtractedSkills(data.skills_extracted || []);
    $id('ats-status-badge').textContent = 'Analyzed';

    setTimeout(() => progressEl.classList.add('hidden'), 1500);
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
    barEl.style.background = 'var(--red)';
    showToast(err.message, 'error');
  }
}

function renderExtractedSkills(skills) {
  const cloud = $id('skills-cloud');
  cloud.innerHTML = '';
  if (!skills.length) {
    cloud.innerHTML = '<p class="placeholder-text">No skills detected</p>';
    return;
  }
  const topSkills = skills.slice(0, 6);
  skills.forEach((skill, i) => {
    const tag = document.createElement('span');
    tag.className = 'skill-tag' + (i < topSkills.length ? ' highlight' : '');
    tag.textContent = skill;
    cloud.appendChild(tag);
  });
}

async function analyzeResume() {
  $id('feedback-body').innerHTML = '<div class="loading-shimmer">Analyzing with Gemini 2.5</div>';
  try {
    const res = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: 'Analyze my uploaded resume and provide detailed improvement recommendations with an ATS score breakdown.',
        session_id: chatSessionId,
      }),
    });
    const data = await res.json();
    $id('feedback-body').innerHTML = `<pre style="white-space:pre-wrap;font-size:0.85rem;">${escapeHtml(data.response || data.error || 'No response')}</pre>`;
  } catch (err) {
    $id('feedback-body').innerHTML = `<p class="placeholder-text">Error: ${err.message}</p>`;
  }
}

/* ============================================================
   INTERVIEW (WebSocket)
   ============================================================ */

let interviewWs = null;
let questionNum = 0;

function startInterview() {
  const role    = $id('interview-role').value.trim() || 'Software Engineer';
  const company = $id('interview-company').value.trim();

  $id('interview-setup').classList.add('hidden');
  $id('interview-session').classList.remove('hidden');
  $id('session-summary').classList.add('hidden');

  $id('status-dot').className  = 'status-dot active';
  $id('status-label').textContent = 'Live';
  $id('question-text').textContent = 'Connecting…';
  questionNum = 0;

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws/interview/${chatSessionId}_interview`;

  interviewWs = new WebSocket(wsUrl);

  interviewWs.onopen = () => {
    interviewWs.send(JSON.stringify({ action: 'start', target_role: role, company }));
  };

  interviewWs.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleInterviewMessage(msg);
  };

  interviewWs.onerror = () => {
    showToast('WebSocket error — falling back to REST mode', 'error');
    fallbackInterviewMode(role, company);
  };

  interviewWs.onclose = () => {
    $id('status-dot').className  = 'status-dot idle';
    $id('status-label').textContent = 'Ended';
  };
}

function fallbackInterviewMode(role, company) {
  // REST fallback when WebSocket unavailable
  apiFetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      message: `Start a mock interview for ${role}${company ? ' at ' + company : ''}. Generate the first question.`,
      session_id: chatSessionId + '_interview',
    }),
  }).then(r => r.json()).then(data => {
    questionNum = 1;
    $id('q-current').textContent = questionNum;
    $id('q-total').textContent = '5';
    $id('q-type-badge').textContent = 'Technical';
    $id('question-text').textContent = data.response || 'Could not load question. Please try again.';
  }).catch(() => {
    $id('question-text').textContent = 'Error loading question.';
  });
}

function handleInterviewMessage(msg) {
  if (msg.error) { showToast(msg.error, 'error'); return; }

  if (msg.type === 'question') {
    questionNum++;
    $id('q-current').textContent = questionNum;
    $id('q-total').textContent = '5';

    let parsed = {};
    try { parsed = JSON.parse(msg.data); } catch { parsed = { question: msg.data, category: 'Mixed' }; }

    $id('q-type-badge').textContent = parsed.category || 'Question';
    $id('question-text').textContent = parsed.question || msg.data;
    $id('interview-feedback').classList.add('hidden');
    $id('answer-input').value = '';
  }

  if (msg.type === 'evaluation') {
    let parsed = {};
    try { parsed = JSON.parse(msg.data); } catch {}

    renderFeedback(parsed);

    if (questionNum < 5) {
      // Auto-request next question
      setTimeout(() => {
        if (interviewWs && interviewWs.readyState === WebSocket.OPEN) {
          interviewWs.send(JSON.stringify({ action: 'start', target_role: $id('interview-role').value }));
        }
      }, 2000);
    }
  }

  if (msg.type === 'session_complete') {
    showSessionSummary(msg.data);
  }
}

function renderFeedback(parsed) {
  const feedbackEl = $id('interview-feedback');
  feedbackEl.classList.remove('hidden');

  const scores = parsed.scores || {};
  const scoresHtml = Object.entries(scores).map(([k, v]) => `
    <div class="score-pill">
      <span class="score-pill-value" style="color: ${scoreColor(v)}">${v}/5</span>
      <span class="score-pill-label">${k.replace(/_/g, ' ')}</span>
    </div>
  `).join('');

  $id('feedback-scores').innerHTML = scoresHtml;
  $id('feedback-text').innerHTML = `
    ${parsed.model_answer_hint ? `<p><strong>💡 Hint:</strong> ${escapeHtml(parsed.model_answer_hint)}</p>` : ''}
    ${(parsed.gaps_in_answer || []).length ? `<p><strong>Gaps:</strong> ${escapeHtml(parsed.gaps_in_answer.join(', '))}</p>` : ''}
    ${(parsed.strengths_in_answer || []).length ? `<p><strong>✅ Strengths:</strong> ${escapeHtml(parsed.strengths_in_answer.join(', '))}</p>` : ''}
  `;
}

function scoreColor(v) {
  if (v >= 4) return 'var(--green)';
  if (v >= 3) return 'var(--amber)';
  return 'var(--red)';
}

function showSessionSummary(data) {
  $id('interview-session').classList.add('hidden');
  $id('session-summary').classList.remove('hidden');
  $id('summary-scores').innerHTML = `<p>Session complete! Check your chat for detailed feedback.</p>`;
}

function clearAnswer() { $id('answer-input').value = ''; }

function submitAnswer() {
  const answer = $id('answer-input').value.trim();
  if (!answer) { showToast('Please write an answer first', 'error'); return; }

  if (interviewWs && interviewWs.readyState === WebSocket.OPEN) {
    interviewWs.send(JSON.stringify({ action: 'answer', text: answer }));
  } else {
    // REST fallback
    apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: `Evaluate this interview answer: "${answer}"`,
        session_id: chatSessionId + '_interview',
      }),
    }).then(r => r.json()).then(data => {
      let parsed = {};
      try { parsed = JSON.parse(data.response); } catch {}
      renderFeedback(parsed);
    });
  }
}

function endInterview() {
  if (interviewWs) interviewWs.close();
  $id('interview-session').classList.add('hidden');
  $id('interview-setup').classList.remove('hidden');
}

function restartInterview() {
  $id('session-summary').classList.add('hidden');
  $id('interview-setup').classList.remove('hidden');
}

/* ============================================================
   ROADMAP
   ============================================================ */

async function loadRoadmap() {
  try {
    const res  = await apiFetch('/api/roadmap');
    const data = await res.json();
    renderRoadmap(data);
  } catch (err) {
    $id('roadmap-timeline').innerHTML = '<p class="placeholder-text">Could not load roadmap.</p>';
  }
}

function renderRoadmap(steps) {
  const timeline = $id('roadmap-timeline');
  if (!steps.length) {
    timeline.innerHTML = '<p class="placeholder-text">No roadmap yet. Ask the AI to generate one!</p>';
    return;
  }

  timeline.innerHTML = steps.map((step, idx) => `
    <div class="timeline-item" style="animation-delay: ${idx * 0.1}s">
      <div class="timeline-dot ${step.status}">
        ${step.status === 'completed' ? '✓' : step.step_num}
      </div>
      <div class="timeline-content">
        <div class="timeline-title">${escapeHtml(step.title)}</div>
        <div class="timeline-desc">${escapeHtml(step.description || '')}</div>
        <div class="timeline-resources">
          ${(step.resources || []).map(r => `<span class="resource-tag">${escapeHtml(typeof r === 'string' ? r : r.title || r)}</span>`).join('')}
        </div>
      </div>
    </div>
  `).join('');
}

async function generateRoadmap() {
  showToast('Generating roadmap… this may take a moment', 'info', 6000);
  try {
    const res = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: 'Build me a detailed career roadmap based on my current skills and career goals.',
        session_id: chatSessionId,
      }),
    });
    const data = await res.json();
    showToast('Roadmap generated! Refreshing…', 'success');
    setTimeout(loadRoadmap, 1000);
  } catch (err) {
    showToast('Could not generate roadmap: ' + err.message, 'error');
  }
}

/* ============================================================
   APPLICATIONS
   ============================================================ */

async function loadApplications() {
  try {
    const res  = await apiFetch('/api/applications');
    const apps = await res.json();
    renderKanban(apps);
  } catch (err) {
    $id('app-kanban').innerHTML = '<p class="placeholder-text">Could not load applications.</p>';
  }
}

function renderKanban(apps) {
  const statuses = [
    { key: 'Applied',   label: 'Applied',    cls: 'applied' },
    { key: 'Interview', label: 'Interview',  cls: 'interview' },
    { key: 'Offer',     label: 'Offer',      cls: 'offer' },
    { key: 'Rejected',  label: 'Rejected',   cls: 'rejected' },
  ];

  const kanban = $id('app-kanban');
  kanban.innerHTML = statuses.map(s => {
    const colApps = apps.filter(a => a.status === s.key);
    return `
      <div class="kanban-col ${s.cls}">
        <div class="kanban-col-header">
          <span>${s.label}</span>
          <span class="kanban-count">${colApps.length}</span>
        </div>
        ${colApps.map(a => `
          <div class="app-card" title="${escapeHtml(a.url || '')}">
            <div class="app-company">${escapeHtml(a.company_name)}</div>
            <div class="app-title">${escapeHtml(a.job_title)}</div>
            <div class="app-date">${a.applied_at || '—'}</div>
          </div>
        `).join('')}
      </div>
    `;
  }).join('');
}

function openAddApplication() {
  $id('add-app-modal').classList.remove('hidden');
}

function closeAddApplication() {
  $id('add-app-modal').classList.add('hidden');
}

async function submitApplication(e) {
  e.preventDefault();
  try {
    const res = await apiFetch('/api/applications', {
      method: 'POST',
      body: JSON.stringify({
        company_name: $id('app-company').value.trim(),
        job_title:    $id('app-title').value.trim(),
        url:          $id('app-url').value.trim() || null,
        notes:        $id('app-notes').value.trim() || null,
      }),
    });

    if (!res.ok) throw new Error('Failed to add application');

    showToast('Application added!', 'success');
    closeAddApplication();
    loadApplications();

    // Clear form
    ['app-company','app-title','app-url','app-notes'].forEach(id => $id(id).value = '');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

/* ============================================================
   BOOTSTRAP
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  // Make auth overlay visible
  const overlay = $id('auth-overlay');
  overlay.style.display = JWT_TOKEN ? 'none' : 'flex';

  if (JWT_TOKEN) {
    initApp();
  }
});
