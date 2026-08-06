// Utils
// ════════════════════════════════════════
export function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Render 1 output content: nếu là ảnh (markdown ![](url) hoặc đường dẫn ảnh trần) thì
// hiển thị <img>, còn lại escape như văn bản thường.
const IMG_PATH_RE = /^(https?:\/\/|\/)\S+\.(png|jpe?g|gif|webp)(\?\S*)?$/i;
const IMG_MD_RE = /!\[([^\]]*)\]\(((?:https?:\/\/|\/)[^\s)]+)\)/g;
export function renderOutputContent(raw) {
  const text = String(raw || '');
  if (!text) return '';
  const trimmed = text.trim();
  if (IMG_PATH_RE.test(trimmed)) {
    return `<img src="${esc(trimmed)}" alt="Ảnh đã tạo" style="max-width:100%;border-radius: 0;">`;
  }
  if (!IMG_MD_RE.test(text)) return esc(text);
  IMG_MD_RE.lastIndex = 0;
  let out = '', lastIndex = 0, m;
  while ((m = IMG_MD_RE.exec(text))) {
    out += esc(text.slice(lastIndex, m.index));
    out += `<img src="${esc(m[2])}" alt="${esc(m[1] || 'Ảnh đã tạo')}" style="max-width:100%;border-radius: 0;margin:6px 0;display:block;">`;
    lastIndex = IMG_MD_RE.lastIndex;
  }
  out += esc(text.slice(lastIndex));
  return out;
}

// ════════════════════════════════════════
