const API = 'http://localhost:8000';

const state = {
  books:      [],
  activeBook: null,
  history:    [],
  streaming:  false,
};

// DOM
const bookList      = document.getElementById('book-list');
const fileInput     = document.getElementById('file-input');
const uploadStatus  = document.getElementById('upload-status');
const emptyState    = document.getElementById('empty-state');
const chatArea      = document.getElementById('chat-area');
const chatTitle     = document.getElementById('chat-title');
const chatMeta      = document.getElementById('chat-meta');
const messages      = document.getElementById('messages');
const chatForm      = document.getElementById('chat-form');
const questionInput = document.getElementById('question-input');
const sendBtn       = document.getElementById('send-btn');
const clearBtn      = document.getElementById('clear-btn');

// ── API ───────────────────────────────────────────────
async function api(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(e.detail || res.statusText);
  }
  return res.json();
}

// ── Toast ─────────────────────────────────────────────
function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ── Books ─────────────────────────────────────────────
async function loadBooks() {
  try { state.books = await api('/books'); }
  catch { state.books = []; }
  renderBooks();
}

function renderBooks() {
  bookList.innerHTML = '';
  if (!state.books.length) {
    bookList.innerHTML = '<li class="empty-books">No books yet.</li>';
    return;
  }
  state.books.forEach(book => {
    const li = document.createElement('li');
    li.className = 'book-item' + (state.activeBook?.id === book.id ? ' active' : '');
    li.innerHTML = `
      <span class="book-name" title="${book.name}">${book.name}</span>
      <span class="book-pages">${book.num_pages}p</span>
      <button class="del-btn" title="Delete">✕</button>
    `;
    li.addEventListener('click', e => {
      if (e.target.closest('.del-btn')) return;
      selectBook(book);
    });
    li.querySelector('.del-btn').addEventListener('click', e => {
      e.stopPropagation();
      deleteBook(book);
    });
    bookList.appendChild(li);
  });
}

function selectBook(book) {
  state.activeBook = book;
  state.history    = [];
  renderBooks();
  chatTitle.textContent = book.name;
  chatMeta.textContent  = `${book.num_pages} pages · ${book.num_chunks} chunks`;
  messages.innerHTML    = '';
  emptyState.classList.add('hidden');
  chatArea.classList.remove('hidden');
  addMsg('ai', `Hello! I've read **${book.name}**. Ask me anything about it.`);
  questionInput.focus();
}

async function deleteBook(book) {
  if (!confirm(`Delete "${book.name}"?`)) return;
  try {
    await api(`/books/${book.id}`, { method: 'DELETE' });
    if (state.activeBook?.id === book.id) {
      state.activeBook = null;
      state.history    = [];
      chatArea.classList.add('hidden');
      emptyState.classList.remove('hidden');
    }
    toast(`"${book.name}" deleted.`);
    await loadBooks();
  } catch (err) { toast(err.message, 'error'); }
}

// ── Upload ────────────────────────────────────────────
fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;
  fileInput.value = '';
  uploadStatus.textContent = `Uploading "${file.name}"…`;
  uploadStatus.classList.remove('hidden');

  const form = new FormData();
  form.append('file', file);
  try {
    const book = await api('/books/upload', { method: 'POST', body: form });
    uploadStatus.classList.add('hidden');
    toast(`"${book.name}" ready — ${book.num_chunks} chunks.`, 'success');
    await loadBooks();
    selectBook(book);
  } catch (err) {
    uploadStatus.classList.add('hidden');
    toast(err.message, 'error');
  }
});

// ── Chat ──────────────────────────────────────────────
chatForm.addEventListener('submit', e => {
  e.preventDefault();
  const q = questionInput.value.trim();
  if (!q || state.streaming) return;
  sendQuestion(q);
});

questionInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatForm.dispatchEvent(new Event('submit')); }
});

questionInput.addEventListener('input', () => {
  questionInput.style.height = 'auto';
  questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + 'px';
});

clearBtn.addEventListener('click', () => {
  state.history    = [];
  messages.innerHTML = '';
  addMsg('ai', `History cleared. Ask me anything about **${state.activeBook.name}**.`);
});

async function sendQuestion(q) {
  state.streaming  = true;
  sendBtn.disabled = true;
  questionInput.value = '';
  questionInput.style.height = 'auto';

  addMsg('user', q);
  const aiEl = addMsg('ai', null);   // streaming placeholder

  try { await stream(q, aiEl); }
  catch (err) {
    aiEl.querySelector('.bubble-text').textContent = `Error: ${err.message}`;
    toast(err.message, 'error');
  } finally {
    state.streaming  = false;
    sendBtn.disabled = false;
    questionInput.focus();
  }
}

async function stream(question, aiEl) {
  const textEl    = aiEl.querySelector('.bubble-text');
  const cursor    = aiEl.querySelector('.cursor');
  const sourcesEl = aiEl.querySelector('.sources');
  let   answer    = '';

  const res = await fetch(`${API}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: state.activeBook.id, question, history: state.history }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(e.detail || res.statusText);
  }

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let   buf     = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop();

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const evt = JSON.parse(line.slice(6));
      if (evt.type === 'token') {
        answer += evt.content;
        textEl.innerHTML = fmt(answer);
        scroll();
      } else if (evt.type === 'sources') {
        cursor?.remove();
        if (evt.content?.length) {
          sourcesEl.innerHTML = 'Sources: ' + evt.content.map(c => `<span class="source-tag">chunk ${c}</span>`).join(' ');
        }
      } else if (evt.type === 'done') {
        state.history.push({ role: 'user',      content: question });
        state.history.push({ role: 'assistant', content: answer   });
        if (state.history.length > 20) state.history = state.history.slice(-20);
      }
    }
  }
}

// ── Helpers ───────────────────────────────────────────
function addMsg(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  const isStreaming = text === null;
  div.innerHTML = `
    <div class="bubble">
      <div class="bubble-text">${text ? fmt(text) : ''}</div>
      ${isStreaming ? '<span class="cursor"></span>' : ''}
      <div class="sources"></div>
    </div>
  `;
  messages.appendChild(div);
  scroll();
  return div;
}

function scroll() { messages.scrollTop = messages.scrollHeight; }

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function fmt(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/\n/g,            '<br>');
}

// ── Init ──────────────────────────────────────────────
loadBooks();
