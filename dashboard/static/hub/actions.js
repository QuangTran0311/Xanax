// Điều phối sự kiện tập trung — thay cho onclick="..." nội tuyến.
//
// Vì sao
// ------
// Handler nội tuyến buộc mọi hàm phải là biến toàn cục, nên nó khoá chặt việc
// chia hub.js thành module (phạm vi module không lộ ra window). Nó cũng đòi
// CSP phải bật 'unsafe-inline'. Ở đây mỗi loại sự kiện chỉ có ĐÚNG MỘT
// listener gắn ở document; phần tử chỉ khai báo tên hành động.
//
// Cách dùng trong HTML
// --------------------
//     <button data-click="deleteAgent" data-click-args='[5]'>
//     <input  data-change="saveAnimPref" data-change-args='["$checked"]'>
//
// Đối số nằm trong một mảng JSON nên GIỮ NGUYÊN KIỂU (số vẫn là số, không bị
// biến thành chuỗi như khi đọc từng data-* riêng lẻ). Vài chuỗi là ký hiệu
// đặc biệt, được thay lúc gọi:
//
//     "$el"      phần tử mang thuộc tính
//     "$value"   el.value
//     "$checked" el.checked
//     "$event"   đối tượng sự kiện
//
// Cách dùng trong JS
// ------------------
// Mỗi module tự đăng ký hành động của mình:
//
//     import { register } from './actions.js';
//     register({ deleteAgent, saveAgent });

const REGISTRY = {};

export function register(map) {
  for (const [name, fn] of Object.entries(map)) {
    if (REGISTRY[name] && REGISTRY[name] !== fn) {
      console.warn(`[actions] '${name}' bị đăng ký chồng bởi 2 module khác nhau`);
    }
    REGISTRY[name] = fn;
  }
}

// Dùng cho scripts/smoke_hub.py: đối chiếu mọi data-* trong HTML với sổ đăng
// ký mà không phải bấm thật vào các nút xoá.
export function registeredActions() {
  return Object.keys(REGISTRY);
}

function resolveArgs(el, ev, raw) {
  if (!raw) return [];
  let list;
  try {
    list = JSON.parse(raw);
  } catch {
    console.error('[actions] data-*-args không phải JSON hợp lệ:', raw, el);
    return [];
  }
  return (Array.isArray(list) ? list : [list]).map(a => {
    switch (a) {
      case '$el':      return el;
      case '$value':   return el.value;
      case '$checked': return el.checked;
      case '$event':   return ev;
      default:         return a;
    }
  });
}

// Sự kiện có nổi bọt (bubble) thì uỷ quyền được. 'change'/'input' của form
// control đều nổi bọt, nên cả 4 loại dưới đây dùng chung một cơ chế.
const EVENTS = ['click', 'change', 'input', 'keydown'];

for (const type of EVENTS) {
  document.addEventListener(type, (ev) => {
    const el = ev.target.closest(`[data-${type}]`);
    if (!el) return;

    const name = el.dataset[type];
    const fn = REGISTRY[name];
    if (!fn) {
      console.error(`[actions] chưa đăng ký hành động '${name}'`, el);
      return;
    }

    // <a href="#"> trước đây dựa vào `return false` của handler nội tuyến để
    // khỏi nhảy lên đầu trang. Uỷ quyền không có cơ chế đó, nên chặn ở đây.
    if (type === 'click' && el.tagName === 'A') ev.preventDefault();

    // Không cần stopPropagation cho nút nằm LỒNG trong thẻ cũng bấm được (nút
    // xoá trong thẻ phòng họp, nút duyệt trong thẻ quy trình). Mã cũ phải viết
    // event.stopPropagation() ngay trong onclick vì hai handler nội tuyến đều
    // chạy khi sự kiện nổi bọt. Ở đây cả hai cùng uỷ quyền về document, và
    // closest() luôn trả phần tử TRONG CÙNG — nên chỉ hành động của nút chạy.

    const args = resolveArgs(el, ev, el.dataset[`${type}Args`]);
    fn(...args);
  });
}
