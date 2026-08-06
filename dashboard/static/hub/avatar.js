import { icon } from './icons.js';



// ── Avatar icon sets ──
// Hình đại diện và màu nền được lưu độc lập; dữ liệu màu cũ vẫn tương thích.
export const AVATAR_COLORS = {
  mint: { label:'Bạc hà', bg:'#D8EEE0', ink:'#3F8A63' }, peach: { label:'Đào', bg:'#FBE3CE', ink:'#C97A3A' },
  lavender: { label:'Oải hương', bg:'#E4DBF7', ink:'#7C6BAE' }, sky: { label:'Trời xanh', bg:'#DCEAF5', ink:'#4A7FA6' },
  rose: { label:'Hoa hồng', bg:'#F7DCE3', ink:'#AE536B' }, coral: { label:'San hô', bg:'#F8D8CF', ink:'#B85D48' },
  amber: { label:'Hổ phách', bg:'#F8E7BE', ink:'#9A6A17' }, lemon: { label:'Chanh', bg:'#F5EFBF', ink:'#81751D' },
  lime: { label:'Chanh xanh', bg:'#E2EDC7', ink:'#64813A' }, forest: { label:'Rừng', bg:'#D3E6D7', ink:'#477655' },
  teal: { label:'Ngọc lam', bg:'#CFE9E5', ink:'#347C73' }, aqua: { label:'Biển sáng', bg:'#D3EDF0', ink:'#397D85' },
  blue: { label:'Lam', bg:'#D6E2F5', ink:'#4B6FA7' }, indigo: { label:'Chàm', bg:'#DCDDF3', ink:'#5E61A0' },
  violet: { label:'Tím', bg:'#E8D9F2', ink:'#82569E' }, plum: { label:'Mận', bg:'#EBD8E7', ink:'#8F557F' },
  sand: { label:'Cát', bg:'#EEE3CF', ink:'#856D48' }, cocoa: { label:'Ca cao', bg:'#E7DAD2', ink:'#805F50' },
  silver: { label:'Bạc', bg:'#E5E8EA', ink:'#606A70' }, slate: { label:'Đá phiến', bg:'#DDE3E7', ink:'#536674' },
};
export const AVATAR_PALETTE = Object.keys(AVATAR_COLORS);
export const AVATAR_PALETTE_LABEL = Object.fromEntries(Object.entries(AVATAR_COLORS).map(([key, value]) => [key, value.label]));
export const DEFAULT_AVATAR = 'mint';
export const AVATAR_ICONS = {
  bot: '<rect x="5" y="7" width="14" height="12" rx="5"/><circle cx="9.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="14.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><path d="M9.5 16c.8.6 3.2.6 4 0M12 7V4.5"/><circle cx="12" cy="4" r="1" fill="currentColor" stroke="none"/>',
  owl: '<path d="M5 9l-1-5 5 3a8 8 0 016 0l5-3-1 5v5a7 7 0 01-14 0z"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="12" r="2"/><path d="M12 14l-1 1h2z"/>',
  cat: '<path d="M5 10L4 4l5 3a8 8 0 016 0l5-3-1 6v5a7 7 0 01-14 0z"/><path d="M8.5 12h.01M15.5 12h.01M9 16c1.7 1 4.3 1 6 0M7 14H3M17 14h4"/>',
  star: '<path d="M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3z"/>',
  cloud: '<path d="M7 18h10a4 4 0 00.5-8A6 6 0 006 8.5 4.8 4.8 0 007 18z"/><path d="M9 14h.01M15 14h.01M10 16c1.2.7 2.8.7 4 0"/>',
  gem: '<path d="M7 4h10l4 5-9 11L3 9l4-5zM3 9h18M7 4l5 5 5-5M12 9v11"/>',
  rocket: '<path d="M14 5c2.5-2 5-2 5-2s0 2.5-2 5l-5 5-4-4 6-4z"/><path d="M8 9H5l-2 4 5 1M12 13v4l-4 2-1-5M6 18l-2 2"/><circle cx="15" cy="7" r="1.3"/>',
  atom: '<circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/><ellipse cx="12" cy="12" rx="9" ry="3.5"/><ellipse cx="12" cy="12" rx="9" ry="3.5" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="9" ry="3.5" transform="rotate(120 12 12)"/>',
  bulb: '<path d="M8 15c-1.2-1-2-2.8-2-4.7a6 6 0 1112 0c0 1.9-.8 3.7-2 4.7-.8.7-1 1.2-1 2H9c0-.8-.2-1.3-1-2zM9 20h6M9 17h6"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5 5-2z"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
  heart: '<path d="M20 8c0 5-8 11-8 11S4 13 4 8a4 4 0 017-2.7L12 6l1-1a4 4 0 017 3z"/>',
  moon: '<path d="M20 14a8 8 0 11-10-10 6.5 6.5 0 0010 10z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
  planet: '<circle cx="12" cy="12" r="5"/><path d="M3 15c2 2 7 .8 11-1s7-4.5 6-6-5-.8-9 1-7 4.5-6 6"/>',
  flower: '<circle cx="12" cy="12" r="2"/><circle cx="12" cy="7" r="3"/><circle cx="17" cy="12" r="3"/><circle cx="12" cy="17" r="3"/><circle cx="7" cy="12" r="3"/>',
  leaf: '<path d="M20 4C10 4 5 8 5 14c0 3 2 5 5 5 6 0 10-7 10-15zM5 20c3-5 7-8 12-11"/>',
  crown: '<path d="M4 7l4 4 4-7 4 7 4-4-2 11H6L4 7zM7 21h10"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
  ghost: '<path d="M5 20V10a7 7 0 0114 0v10l-3-2-2 2-2-2-2 2-2-2-3 2z"/><path d="M9 11h.01M15 11h.01"/>',
  fox: '<path d="M4 5l5 3a8 8 0 016 0l5-3-2 12-6 4-6-4L4 5z"/><path d="M8.5 12h.01M15.5 12h.01M12 15v3"/>',
  panda: '<circle cx="12" cy="13" r="8"/><circle cx="7" cy="6" r="3"/><circle cx="17" cy="6" r="3"/><path d="M9 12h.01M15 12h.01M10 16c1.2.8 2.8.8 4 0"/>',
  bear: '<circle cx="12" cy="13" r="8"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="14" r="2.5"/><path d="M9 11h.01M15 11h.01"/>',
  dog: '<path d="M7 8L3 5v8l4 2M17 8l4-3v8l-4 2"/><circle cx="12" cy="13" r="7"/><path d="M9 12h.01M15 12h.01M12 14l-1 2h2l-1-2z"/>',
  bird: '<path d="M4 15c5 0 7-4 8-9 2 4 5 5 8 5-1 6-5 9-10 9-3 0-5-2-6-5zM13 9l4-4"/>',
  fish: '<path d="M4 12c4-5 9-5 14 0-5 5-10 5-14 0zM18 12l4-4v8l-4-4z"/><circle cx="9" cy="11" r="1" fill="currentColor" stroke="none"/>',
  butterfly: '<path d="M12 10C9 4 4 4 4 8c0 3 3 5 8 5M12 10c3-6 8-6 8-2 0 3-3 5-8 5M12 9v11M9 18l3-5 3 5"/>',
  coffee: '<path d="M5 9h12v6a5 5 0 01-5 5h-2a5 5 0 01-5-5V9zM17 11h2a3 3 0 010 6h-3M8 3v3M12 3v3"/>',
  music: '<path d="M9 18V6l10-2v12M9 10l10-2"/><circle cx="6" cy="18" r="3"/><circle cx="16" cy="16" r="3"/>',
  camera: '<rect x="3" y="7" width="18" height="13" rx="3"/><path d="M8 7l2-3h4l2 3"/><circle cx="12" cy="13" r="4"/>',
  mountain: '<path d="M3 20L10 7l3 5 2-3 6 11H3zM8 11l2 2 2-2"/>',
};
export const AVATAR_ICON_LABEL = { bot:'Robot', owl:'Cú', cat:'Mèo', star:'Ngôi sao', cloud:'Đám mây', gem:'Pha lê', rocket:'Tên lửa', atom:'Nguyên tử', bulb:'Bóng đèn', compass:'La bàn', heart:'Trái tim', moon:'Mặt trăng', sun:'Mặt trời', planet:'Hành tinh', flower:'Bông hoa', leaf:'Chiếc lá', crown:'Vương miện', shield:'Khiên', ghost:'Ma nhỏ', fox:'Cáo', panda:'Gấu trúc', bear:'Gấu', dog:'Chó', bird:'Chim', fish:'Cá', butterfly:'Bướm', coffee:'Cà phê', music:'Âm nhạc', camera:'Máy ảnh', mountain:'Núi' };

export function avatarShape(iconKey) {
  return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${AVATAR_ICONS[iconKey] || AVATAR_ICONS.bot}</svg>`;
}

function _avatarPaletteKey(avatarColor, name) {
  if (avatarColor === 'gold' || avatarColor === 'var(--gold)') return 'gold'; // Xanax hệ thống — không phải 1 trong 4 màu nhân viên
  if (AVATAR_PALETTE.includes(avatarColor)) return avatarColor;
  // Tương thích dữ liệu cũ (emoji hoặc hex) — quy đổi ổn định theo tên để không đổi màu ngẫu nhiên
  const seed = (name || avatarColor || '?').codePointAt(0) || 0;
  return AVATAR_PALETTE[seed % AVATAR_PALETTE.length];
}

// ── Avatar display helper ──
export function avatarInfo(avatarColor, name, avatarIcon = 'bot') {
  const key = _avatarPaletteKey(avatarColor, name);
  const content = avatarShape(avatarIcon);
  if (key === 'gold') return { content, style: `background:var(--gold-soft);color:var(--gold)` };
  const palette = AVATAR_COLORS[key] || AVATAR_COLORS[DEFAULT_AVATAR];
  return { content, style: `background:${palette.bg};color:${palette.ink}` };
}

export function avatarHtml(avatarColor, name, extraClass, avatarIcon = 'bot') {
  const cls = extraClass ? `avatar ${extraClass}` : 'avatar';
  const {content, style} = avatarInfo(avatarColor, name, avatarIcon);
  return `<div class="${cls}" style="${style}">${content}</div>`;
}
