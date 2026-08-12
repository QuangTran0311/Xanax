// Utils
// ════════════════════════════════════════
export function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Dựng giá trị cho data-*-args của hub/actions.js từ các đối số truyền vào.
//
//     `<button data-click="deleteAgent" data-click-args='${jattr(a.id)}'>`
//
// Thuộc tính được bọc bằng nháy ĐƠN vì JSON dùng nháy kép, nên phải thoát
// thêm nháy đơn — JSON.stringify không làm việc đó. Không thoát thì một tên
// có dấu nháy (vd "Bộ 'A'") sẽ cắt sớm thuộc tính và hỏng cả thẻ.
export function jattr(...args) {
  return JSON.stringify(args)
    .replace(/&/g, '&amp;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;');
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
