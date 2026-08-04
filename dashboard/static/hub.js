// ════════════════════════════════════════
// Bộ icon SVG dùng chung (thay toàn bộ emoji chức năng)
// ════════════════════════════════════════
const ICONS = {
  home: '<path d="M4 11L12 4l8 7" /><path d="M6 10v9a1 1 0 001 1h10a1 1 0 001-1v-9" /><rect x="10" y="14" width="4" height="6" rx="1" fill="currentColor" stroke="none"/>',
  bot: '<rect x="5" y="7" width="14" height="12" rx="5" /><circle cx="9.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="14.5" cy="12.5" r="1.1" fill="currentColor" stroke="none"/><path d="M9.5 16c.8.6 3.2.6 4 0" /><line x1="12" y1="7" x2="12" y2="4.5"/><circle cx="12" cy="4" r="1" fill="currentColor" stroke="none"/>',
  sliders: '<line x1="4" y1="7" x2="20" y2="7"/><circle cx="9" cy="7" r="2" fill="currentColor" stroke="none"/><line x1="4" y1="13" x2="20" y2="13"/><circle cx="15" cy="13" r="2" fill="currentColor" stroke="none"/><line x1="4" y1="19" x2="20" y2="19"/><circle cx="7" cy="19" r="2" fill="currentColor" stroke="none"/>',
  briefcase: '<rect x="3" y="8" width="18" height="11" rx="2"/><path d="M8 8V6a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="3" y1="13" x2="21" y2="13"/>',
  meeting: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.3"/><path d="M15 20c0-2.5 1.8-4.5 4-4.8"/>',
  teach: '<path d="M12 5l9 4-9 4-9-4 9-4z"/><path d="M6 11v4c0 1.5 2.7 3 6 3s6-1.5 6-3v-4"/>',
  workflow: '<circle cx="5" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="19" cy="6" r="2" fill="currentColor" stroke="none"/><circle cx="12" cy="18" r="2" fill="currentColor" stroke="none"/><path d="M7 6h10"/><path d="M12 8v6"/>',
  bolt: '<path d="M13 3L6 14h5l-1 7 7-11h-5l1-7z" fill="currentColor" stroke="none"/>',
  assets: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M4 7.5L12 12l8-4.5"/><path d="M12 12v9"/>',
  brain: '<path d="M9 4a3 3 0 00-3 3v1a3 3 0 000 6v1a3 3 0 003 3M15 4a3 3 0 013 3v1a3 3 0 010 6v1a3 3 0 01-3 3M9 4v16M15 4v16"/>',
  cost: '<circle cx="12" cy="12" r="8"/><path d="M12 7v10M9.5 9.5h4a1.5 1.5 0 010 3h-3a1.5 1.5 0 000 3h4.5"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M21 12h-3M6 12H3M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1M18.4 18.4l-2.1-2.1M7.7 7.7L5.6 5.6"/>',
  folder: '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
  sync: '<path d="M4 12a8 8 0 0114-5.3M20 12a8 8 0 01-14 5.3"/><path d="M18 4v4h-4M6 20v-4h4"/>',
  close: '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>',
  check: '<path d="M4 12l5 5L20 6"/>',
  warning: '<path d="M12 4l9 15.5H3L12 4z"/><line x1="12" y1="10" x2="12" y2="14"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><line x1="12" y1="11" x2="12" y2="16"/><circle cx="12" cy="7.5" r="0.9" fill="currentColor" stroke="none"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3.2 2"/>',
  document: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><line x1="9.5" y1="12" x2="14.5" y2="12"/><line x1="9.5" y1="15.5" x2="14.5" y2="15.5"/>',
  download: '<path d="M12 4v11"/><path d="M7.5 11L12 15.5 16.5 11"/><path d="M5 18.5h14"/>',
  upload: '<path d="M12 19V8"/><path d="M7.5 12L12 7.5 16.5 12"/><path d="M5 19.5h14"/>',
  lock: '<rect x="5.5" y="11" width="13" height="9" rx="2"/><path d="M8 11V7.5a4 4 0 018 0V11"/>',
  plug: '<path d="M9 3v6M15 3v6"/><path d="M6.5 9h11v3a5.5 5.5 0 01-11 0V9z"/><path d="M12 17.5V21"/>',
  people: '<circle cx="8.5" cy="8" r="3"/><path d="M2.5 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.3"/><path d="M15 20c0-2.5 1.8-4.5 4-4.8"/>',
  send: '<path d="M4 12l16-8-6 16-3-6-7-2z"/>',
  edit: '<path d="M15.5 4.5l4 4L8 20H4v-4L15.5 4.5z"/>',
  save: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v6h8V4"/><rect x="8" y="14" width="8" height="6"/>',
  trophy: '<path d="M7 4h10v6a5 5 0 01-10 0V4z"/><path d="M7 6H4v2a3 3 0 003 3M17 6h3v2a3 3 0 01-3 3"/><path d="M12 15v3"/><path d="M8.5 21h7l-1-3h-5l-1 3z"/>',
  puzzle: '<path d="M9 4h4v2.3a1.7 1.7 0 003.4 0V4H20v4h-2.3a1.7 1.7 0 000 3.4H20v4h-4v-2.3a1.7 1.7 0 00-3.4 0V15H9v-4H6.7a1.7 1.7 0 010-3.4H9V4z"/>',
  chart: '<line x1="5" y1="20" x2="5" y2="11"/><line x1="12" y1="20" x2="12" y2="6"/><line x1="19" y1="20" x2="19" y2="14"/><line x1="3" y1="20" x2="21" y2="20"/>',
  tag: '<path d="M12 3h6a2 2 0 012 2v6L11 20 2 11 12 3z"/><circle cx="15" cy="8" r="1.2" fill="currentColor" stroke="none"/>',
  book: '<path d="M4 5.5c2.5-1 5-1 8 0v14c-3-1-5.5-1-8 0z"/><path d="M20 5.5c-2.5-1-5-1-8 0v14c3-1 5.5-1 8 0z"/>',
  image: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M4 17l5-4.5 3.5 3 3-2.5L20 17"/>',
  code: '<path d="M9 8l-4.5 4L9 16"/><path d="M15 8l4.5 4-4.5 4"/>',
  flask: '<path d="M10 3h4M10 3v6l-4.5 8a2 2 0 001.7 3h9.6a2 2 0 001.7-3L14 9V3"/><line x1="8" y1="14" x2="16" y2="14"/>',
  arrowUp: '<line x1="12" y1="19" x2="12" y2="6"/><path d="M7 10.5L12 6 17 10.5"/>',
  arrowDown: '<line x1="12" y1="5" x2="12" y2="18"/><path d="M7 13.5L12 18 17 13.5"/>',
  arrowRight: '<line x1="4" y1="12" x2="19" y2="12"/><path d="M13.5 6.5L19 12l-5.5 5.5"/>',
  arrowLeft: '<line x1="20" y1="12" x2="5" y2="12"/><path d="M10.5 6.5L5 12l5.5 5.5"/>',
  chevronDown: '<path d="M6 9l6 6 6-6"/>',
  sun: '<circle cx="12" cy="12" r="4.2"/><path d="M12 3v2.2M12 18.8V21M4.2 12H2M22 12h-2.2M5.6 5.6l1.5 1.5M16.9 16.9l1.5 1.5M18.4 5.6l-1.5 1.5M7.1 16.9l-1.5 1.5"/>',
  moon: '<path d="M20 13.5A8.5 8.5 0 119.7 3.2 6.8 6.8 0 0020 13.5z"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.3" y1="15.3" x2="20.5" y2="20.5"/>',
};
function icon(name, cls) {
  const inner = ICONS[name] || ICONS.bot;
  return `<svg class="icon${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">${inner}</svg>`;
}

// ════════════════════════════════════════
// State
// ════════════════════════════════════════
let agents = [], skills = [], projects = [], meetings = [], benchmarks = [], departments = [];
let selectedAgentId = null, selectedSkillId = null, selectedDeptFilter = null, selectedSkillTypeFilter = null;
let currentProjectId = null, currentProjectSubTab = 'results';
let currentMeetingId = null, currentMeetingWs = null;
// Mốc thời gian tin nhắn gần nhất trong phòng họp hiện tại — dùng để chèn vạch phân
// tách thời gian (giống Messenger) khi có khoảng lặng > 15 phút giữa 2 tin nhắn.
let lastMessageAt = null;
const SESSION_GAP_MS = 15 * 60 * 1000;
let benchModels = [], benchCases = [];
let currentBenchmarkId = null;


// ── Avatar icon sets ──
// Hình đại diện và màu nền được lưu độc lập; dữ liệu màu cũ vẫn tương thích.
const AVATAR_COLORS = {
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
const AVATAR_PALETTE = Object.keys(AVATAR_COLORS);
const AVATAR_PALETTE_LABEL = Object.fromEntries(Object.entries(AVATAR_COLORS).map(([key, value]) => [key, value.label]));
const DEFAULT_AVATAR = 'mint';
const AVATAR_ICONS = {
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
const AVATAR_ICON_LABEL = { bot:'Robot', owl:'Cú', cat:'Mèo', star:'Ngôi sao', cloud:'Đám mây', gem:'Pha lê', rocket:'Tên lửa', atom:'Nguyên tử', bulb:'Bóng đèn', compass:'La bàn', heart:'Trái tim', moon:'Mặt trăng', sun:'Mặt trời', planet:'Hành tinh', flower:'Bông hoa', leaf:'Chiếc lá', crown:'Vương miện', shield:'Khiên', ghost:'Ma nhỏ', fox:'Cáo', panda:'Gấu trúc', bear:'Gấu', dog:'Chó', bird:'Chim', fish:'Cá', butterfly:'Bướm', coffee:'Cà phê', music:'Âm nhạc', camera:'Máy ảnh', mountain:'Núi' };

function avatarShape(iconKey) {
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
function avatarInfo(avatarColor, name, avatarIcon = 'bot') {
  const key = _avatarPaletteKey(avatarColor, name);
  const content = avatarShape(avatarIcon);
  if (key === 'gold') return { content, style: `background:var(--gold-soft);color:var(--gold)` };
  const palette = AVATAR_COLORS[key] || AVATAR_COLORS[DEFAULT_AVATAR];
  return { content, style: `background:${palette.bg};color:${palette.ink}` };
}

function avatarHtml(avatarColor, name, extraClass, avatarIcon = 'bot') {
  const cls = extraClass ? `avatar ${extraClass}` : 'avatar';
  const {content, style} = avatarInfo(avatarColor, name, avatarIcon);
  return `<div class="${cls}" style="${style}">${content}</div>`;
}

// ════════════════════════════════════════
// Init
// ════════════════════════════════════════
async function init() {
  try {
    const me = await api('GET', '/auth/me');
    if (me?.username) {
      document.getElementById('topbar-user-name').textContent = me.username;
      const si = document.getElementById('settings-session-info');
      if (si) si.textContent = t('js.logged_as', me.username);
    }
  } catch {}
  await loadDepartments();
  await Promise.all([loadAgents(), loadSkills(), loadProjects(), loadMeetings(), loadBenchmarks(), loadModelPool()]);
  initAvatarPicker();
  await addTestCase(); // start with one test case
  // Activate tab from URL path (home is default for /hub)
  _syncRunnerIframe();
  switchTab(_tabFromPath(), false);
}

function initAvatarPicker(selectedIconKey = 'bot', selectedColorKey = DEFAULT_AVATAR) {
  const el = document.getElementById('avatar-picker');
  if (!el) return;
  const currentIcon = AVATAR_ICONS[selectedIconKey] ? selectedIconKey : 'bot';
  const currentColor = AVATAR_PALETTE.includes(selectedColorKey) ? selectedColorKey : DEFAULT_AVATAR;
  el.innerHTML = `<div class="avatar-picker-group"><div class="avatar-picker-label">Chọn hình đại diện</div><div class="avatar-shape-grid">` +
    Object.keys(AVATAR_ICONS).map(key => `<div class="avatar-shape-opt${key===currentIcon?' selected':''}" data-avatar-icon="${key}" onclick="selectAvatarShape(this)" title="${AVATAR_ICON_LABEL[key]}">${avatarShape(key)}</div>`).join('') +
    `</div></div><div class="avatar-picker-group"><div class="avatar-picker-label">Chọn màu nền</div><div class="avatar-picker-grid">` + AVATAR_PALETTE.map(key => `
    <div class="avatar-opt${key===currentColor?' selected':''}" data-icon="${key}" onclick="selectAvatar(this)" title="${AVATAR_PALETTE_LABEL[key]}"
         style="background:${AVATAR_COLORS[key].bg};color:${AVATAR_COLORS[key].ink};">${avatarShape(currentIcon)}</div>
  `).join('') + `</div></div>`;
}

function selectAvatarShape(el) {
  document.querySelectorAll('.avatar-shape-opt').forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
  const shape = el.dataset.avatarIcon;
  document.querySelectorAll('.avatar-opt').forEach(color => { color.innerHTML = avatarShape(shape); });
  updateAgentPreview();
}

function selectAvatar(el) {
  document.querySelectorAll('.avatar-opt').forEach(s => s.classList.remove('selected'));
  el.classList.add('selected');
  updateAgentPreview();
}

// ── Danh sách model ưu tiên của nhân viên (tối đa 5, tự fallback khi lỗi) ────
const AGENT_MAX_MODELS = 5;
let agentModelIds = [];

function setAgentModelIds(ids) {
  agentModelIds = Array.isArray(ids) ? [...ids] : [];
  renderAgentModelList();
}

function renderAgentModelList() {
  const el = document.getElementById('agent-model-list');
  if (!el) return;
  if (!agentModelIds.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:4px 0;">Chưa chọn model nào — sẽ dùng model mặc định (Hermes).</div>';
  } else {
    el.innerHTML = agentModelIds.map((id, i) => {
      const m = modelPool.find(x => x.id === id);
      const label = m ? `${esc(m.name)} (${esc(m.model_id)})` : `Model #${id} (đã xoá khỏi pool)`;
      const upBtn = i > 0 ? `<button class="btn btn-ghost btn-sm" onclick="moveAgentModel(${i},-1)" style="padding:2px 6px;" title="Ưu tiên hơn">↑</button>` : '';
      const dnBtn = i < agentModelIds.length - 1 ? `<button class="btn btn-ghost btn-sm" onclick="moveAgentModel(${i},1)" style="padding:2px 6px;" title="Ưu tiên thấp hơn">↓</button>` : '';
      return `<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;background:var(--bg2);border-radius: 0;font-size:12px;">
        <span style="width:18px;height:18px;border-radius:50%;background:var(--cyan);color:#000;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">${i+1}</span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${label}</span>
        ${upBtn}${dnBtn}
        <button class="btn btn-ghost btn-sm" onclick="removeAgentModel(${i})" style="padding:2px 6px;color:var(--red);" title="Xoá khỏi danh sách">${icon('close')}</button>
      </div>`;
    }).join('');
  }
  populateAgentModelAddSelect();
}

function populateAgentModelAddSelect() {
  const sel = document.getElementById('agent-model-add');
  const hint = document.getElementById('agent-model-empty-hint');
  if (!sel) return;
  if (!modelPool.length) {
    hint.style.display = '';
    sel.style.display = 'none';
    return;
  }
  hint.style.display = 'none';
  const remaining = modelPool.filter(m => !agentModelIds.includes(m.id));
  if (agentModelIds.length >= AGENT_MAX_MODELS || !remaining.length) {
    sel.style.display = 'none';
    return;
  }
  sel.style.display = '';
  sel.innerHTML = '<option value="">+ Thêm model vào danh sách ưu tiên...</option>' +
    remaining.map(m => `<option value="${m.id}">${esc(m.name)} (${esc(m.model_id)})</option>`).join('');
}

function addAgentModel(idStr) {
  if (!idStr) return;
  const id = parseInt(idStr);
  if (agentModelIds.length >= AGENT_MAX_MODELS || agentModelIds.includes(id)) return;
  agentModelIds.push(id);
  renderAgentModelList();
}
function removeAgentModel(i) { agentModelIds.splice(i, 1); renderAgentModelList(); }
function moveAgentModel(i, dir) {
  const ni = i + dir;
  if (ni < 0 || ni >= agentModelIds.length) return;
  [agentModelIds[i], agentModelIds[ni]] = [agentModelIds[ni], agentModelIds[i]];
  renderAgentModelList();
}

// ════════════════════════════════════════
// API helpers
// ════════════════════════════════════════
async function checkAuthOrRedirect() {
  try {
    const r = await fetch('/api/health');
    if (r.status === 401) { window.top.location.href = '/login'; return false; }
  } catch (_) {}
  return true;
}

// Heartbeat: tự động redirect về login khi server restart xóa session
setInterval(async () => {
  try {
    const r = await fetch('/api/auth/me');
    if (r.status === 401) window.top.location.href = '/login';
  } catch (_) { /* server đang down, bỏ qua */ }
}, 5000);

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch('/api' + path, opts);
  if (r.status === 401) { window.top.location.href = '/login'; return; }
  if (!r.ok) throw new Error(await r.text());
  if (r.status === 204) return null;
  return r.json();
}

// ════════════════════════════════════════
// ASSETS (Tài sản)
// ════════════════════════════════════════
let allAssets = [];
let assetsFilter = 'all';
const ASSET_SOURCE_LABEL = { all: 'Tất cả', upload: 'Đã upload', workflow: 'Quy trình', benchmark: 'Benchmark' };
const ASSET_ICON = { upload: 'document', workflow: 'settings', benchmark: 'flask' };

async function loadAssets() {
  const data = await api('GET', '/assets/');
  allAssets = data.assets || [];
  renderAssetFilters();
  renderAssets();
}

function renderAssetFilters() {
  const el = document.getElementById('assets-filter-tabs');
  const counts = { all: allAssets.length };
  for (const a of allAssets) counts[a.source] = (counts[a.source] || 0) + 1;
  el.innerHTML = Object.keys(ASSET_SOURCE_LABEL).map(key => `
    <button class="assets-filter-btn${assetsFilter === key ? ' active' : ''}" onclick="setAssetsFilter('${key}')">
      ${ASSET_SOURCE_LABEL[key]} (${counts[key] || 0})
    </button>
  `).join('');
}

function setAssetsFilter(key) {
  assetsFilter = key;
  renderAssetFilters();
  renderAssets();
}

function _formatBytes(n) {
  if (!n) return '';
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderAssets() {
  const el = document.getElementById('assets-list');
  const items = assetsFilter === 'all' ? allAssets : allAssets.filter(a => a.source === assetsFilter);
  if (!items.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('assets')}</div><div class="empty-state-text">Chưa có tài sản nào</div></div>`;
    return;
  }
  el.innerHTML = items.map(a => {
    const totalBytes = (a.files || []).reduce((s, f) => s + (f.size_bytes || 0), 0);
    return `
    <div class="asset-card">
      <div class="asset-card-top">
        <div class="asset-card-icon">${icon(ASSET_ICON[a.source] || 'document')}</div>
        <span class="asset-card-tag tag-${a.source}">${ASSET_SOURCE_LABEL[a.source] || a.source}</span>
      </div>
      <div class="asset-card-name">${esc(a.name)}</div>
      <div class="asset-card-meta">${a.label ? esc(a.label) + ' · ' : ''}${a.files.length} file${totalBytes ? ' · ' + _formatBytes(totalBytes) : ''} · ${esc((a.created_at || '').slice(0, 16))}</div>
      <div class="asset-card-files">
        ${a.files.map(f => `
          <a class="asset-file-row" href="${f.download_url}" target="_blank" rel="noopener" title="${esc(f.note || f.name)}">
            <span class="asset-file-name">${esc(f.name)}</span>
            <span class="asset-file-size">${_formatBytes(f.size_bytes)}</span>
          </a>
        `).join('')}
      </div>
      ${a.deletable ? `<div class="asset-card-actions"><span class="danger" onclick="deleteAssetItem('${a.id}')">Xoá</span></div>` : ''}
    </div>
  `;
  }).join('');
}

async function deleteAssetItem(id) {
  if (!id.startsWith('upload-')) return;
  if (!confirm('Xoá file này?')) return;
  await api('DELETE', '/assets/' + id.replace('upload-', ''));
  await loadAssets();
}

async function uploadAssetFiles(fileList) {
  for (const file of fileList) {
    const form = new FormData();
    form.append('file', file);
    const r = await fetch('/api/assets/upload', { method: 'POST', body: form });
    if (r.status === 401) { window.top.location.href = '/login'; return; }
    if (!r.ok) { alert('Upload thất bại: ' + file.name); continue; }
  }
  await loadAssets();
}

(function initAssetsDropzone() {
  document.addEventListener('DOMContentLoaded', () => {
    const zone = document.getElementById('assets-dropzone');
    const input = document.getElementById('assets-file-input');
    if (!zone || !input) return;
    input.addEventListener('change', () => { if (input.files.length) uploadAssetFiles(input.files); input.value = ''; });
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      if (e.dataTransfer.files.length) uploadAssetFiles(e.dataTransfer.files);
    });
  });
})();

// ════════════════════════════════════════
// MODEL POOL
// ════════════════════════════════════════
let modelPool = [], currentModelId = null;

const CAT_LABEL = { general:'General', coding:'Coding', creative:'Creative', fast:'Fast', analysis:'Analysis' };
const CAT_CLASS = { general:'cat-general', coding:'cat-coding', creative:'cat-creative', fast:'cat-fast', analysis:'cat-analysis' };

async function loadModelPool() {
  const data = await api('GET', '/model-pool');
  modelPool = data.models || [];
  renderModelList();
  loadModelChart();
  renderAgentModelList();
}

function renderModelList() {
  const el = document.getElementById('mp-list');
  const count = document.getElementById('mp-count');
  if (count) count.textContent = `${modelPool.length} model`;
  if (!modelPool.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('puzzle')}</div><div class="empty-state-text">Chưa có model nào</div></div>`;
    return;
  }
  el.innerHTML = modelPool.map(m => {
    const u = m.usage_today || {};
    const reqPct = m.max_requests_per_day ? Math.min(100, (u.request_count||0) / m.max_requests_per_day * 100) : 0;
    const tokPct = m.max_tokens_per_day   ? Math.min(100, ((u.tokens_input||0)+(u.tokens_output||0)) / m.max_tokens_per_day * 100) : 0;
    const barColor = reqPct >= 90 ? 'var(--red)' : reqPct >= 70 ? 'var(--amber)' : 'var(--cyan)';
    const isOff = !m.enabled;
    return `<div class="mp-model-card${currentModelId===m.id?' selected':''}" onclick="selectModel(${m.id})">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <span class="cat-badge ${CAT_CLASS[m.category]||'cat-general'}">${CAT_LABEL[m.category]||m.category}</span>
        ${isOff ? '<span style="font-size:10px;color:var(--muted);">OFF</span>' : ''}
      </div>
      <div class="mp-model-name">${esc(m.name)}</div>
      <div class="mp-model-meta">${esc(m.model_id)} · ${esc(m.provider)}</div>
      ${(m.max_requests_per_day||m.max_tokens_per_day) ? `
        <div class="mp-limit-bar"><div class="mp-limit-fill" style="width:${Math.max(reqPct,tokPct)}%;background:${barColor};"></div></div>
      ` : ''}
    </div>`;
  }).join('');
}

let _mpUsageToday = {};

function _renderLimitBars(maxReq, maxTok) {
  const u = _mpUsageToday;
  const limEl = document.getElementById('mp-d-limits');
  if (!limEl) return;
  const limits = [];
  if (maxReq) {
    const used = u.request_count || 0;
    const pct = Math.min(100, used / maxReq * 100);
    const col = pct >= 90 ? 'var(--red)' : pct >= 70 ? 'var(--amber)' : 'var(--cyan)';
    limits.push(`<div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px;">
        <span>Request/ngày</span><span>${used} / ${maxReq}</span>
      </div>
      <div class="mp-limit-bar" style="height:6px;"><div class="mp-limit-fill" style="width:${pct}%;background:${col};transition:width .25s;"></div></div>
    </div>`);
  }
  if (maxTok) {
    const used = (u.tokens_input || 0) + (u.tokens_output || 0);
    const pct = Math.min(100, used / maxTok * 100);
    const col = pct >= 90 ? 'var(--red)' : pct >= 70 ? 'var(--amber)' : 'var(--cyan)';
    limits.push(`<div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px;">
        <span>Token/ngày</span><span>${_fmtNum(used)} / ${_fmtNum(maxTok)}</span>
      </div>
      <div class="mp-limit-bar" style="height:6px;"><div class="mp-limit-fill" style="width:${pct}%;background:${col};transition:width .25s;"></div></div>
    </div>`);
  }
  limEl.innerHTML = limits.join('') || '<div style="font-size:12px;color:var(--muted);">Không có giới hạn</div>';
}

function livePreviewLimits() {
  const maxReq = parseInt(document.getElementById('mp-modal-max-req').value) || 0;
  const maxTok = parseInt(document.getElementById('mp-modal-max-tok').value) || 0;
  _renderLimitBars(maxReq, maxTok);
}

async function selectModel(id) {
  currentModelId = id;
  renderModelList();
  const entry = await api('GET', `/model-pool/${id}`);
  _mpUsageToday = entry.usage_today || {};
  document.getElementById('mp-empty').style.display = 'none';
  const detail = document.getElementById('mp-detail');
  detail.style.display = 'flex';
  document.getElementById('mp-d-name').textContent = entry.name;
  document.getElementById('mp-d-meta').innerHTML =
    `<span class="cat-badge ${CAT_CLASS[entry.category]||'cat-general'}">${CAT_LABEL[entry.category]||entry.category}</span>
     &nbsp;${esc(entry.model_id)} · ${esc(entry.provider)}`;
  document.getElementById('mp-d-req').textContent  = _mpUsageToday.request_count || 0;
  document.getElementById('mp-d-tin').textContent  = _fmtNum(_mpUsageToday.tokens_input || 0);
  document.getElementById('mp-d-tout').textContent = _fmtNum(_mpUsageToday.tokens_output || 0);
  _renderLimitBars(entry.max_requests_per_day || 0, entry.max_tokens_per_day || 0);
}

async function loadModelChart() {
  const data = await api('GET', '/model-pool/stats?limit=10').catch(() => ({ top_models: [] }));
  const top = data.top_models || [];
  const chart = document.getElementById('mp-chart');
  if (!chart) return;
  if (!top.length) {
    chart.innerHTML = '<div style="font-size:12px;color:var(--muted);margin:auto;">Chưa có dữ liệu</div>';
    return;
  }
  const maxVal = Math.max(...top.map(m => m.total_requests || 0), 1);
  chart.innerHTML = top.map(m => {
    const pct = ((m.total_requests || 0) / maxVal) * 100;
    return `<div class="mp-bar-wrap">
      <div class="mp-bar-label" title="${esc(m.model_id||m.name)}">${esc(m.model_id||m.name)}</div>
      <div class="mp-bar-track"><div class="mp-bar" style="width:${Math.max(pct,1)}%;"></div></div>
      <div class="mp-bar-val">${m.total_requests||0}</div>
    </div>`;
  }).join('');
}

let _modalActiveTab = 'subscription';

const NATIVE_BASE_URLS = { openai: 'https://api.openai.com/v1', anthropic: 'https://api.anthropic.com', gemini: 'https://generativelanguage.googleapis.com' };
const NATIVE_API_STYLES = { openai: 'openai_native', anthropic: 'anthropic_native', gemini: 'gemini_native' };
const NATIVE_PROVIDER_LABELS = { openai: 'OpenAI', anthropic: 'Anthropic', gemini: 'Google Gemini' };
const NATIVE_MODEL_PLACEHOLDERS = { openai: 'gpt-4o', anthropic: 'claude-sonnet-4-5', gemini: 'gemini-2.0-flash' };

function switchModelModalTab(tab) {
  _modalActiveTab = tab;
  document.getElementById('mp-subtab-btn-subscription').classList.toggle('active', tab === 'subscription');
  document.getElementById('mp-subtab-btn-native').classList.toggle('active', tab === 'native');
  document.getElementById('mp-subtab-subscription').style.display = tab === 'subscription' ? '' : 'none';
  document.getElementById('mp-subtab-native').style.display = tab === 'native' ? '' : 'none';
  if (tab === 'native') updateNativeModelHints();
}

function updateNativeModelHints() {
  const p = document.getElementById('mp-modal-native-provider').value;
  document.getElementById('mp-modal-native-model-id').placeholder = NATIVE_MODEL_PLACEHOLDERS[p] || '';
  document.getElementById('mp-modal-native-base-url-preview').value = NATIVE_BASE_URLS[p] || '';
}

function openModelModal(id) {
  const entry = id ? modelPool.find(m => m.id === id) : null;
  document.getElementById('mp-modal-title').textContent = entry ? 'Sửa model' : 'Thêm model';
  document.getElementById('mp-modal-id').value = entry ? entry.id : '';
  document.getElementById('mp-modal-name').value = entry?.name || '';

  const NATIVE_STYLE_TO_PROVIDER = { openai_native: 'openai', anthropic_native: 'anthropic', gemini_native: 'gemini' };
  const isNative = entry && NATIVE_STYLE_TO_PROVIDER[entry.api_style];
  switchModelModalTab(isNative ? 'native' : 'subscription');
  if (isNative) {
    document.getElementById('mp-modal-native-provider').value = NATIVE_STYLE_TO_PROVIDER[entry.api_style];
    document.getElementById('mp-modal-native-model-id').value = entry.model_id || '';
    document.getElementById('mp-modal-native-api-key').value = '';
    updateNativeModelHints();
  } else {
    document.getElementById('mp-modal-provider').value = entry?.provider || '9router';
    document.getElementById('mp-modal-model-id').value = entry?.model_id || '';
    document.getElementById('mp-modal-base-url').value = entry?.base_url || '';
    document.getElementById('mp-modal-api-key').value = '';
  }

  document.getElementById('mp-modal-category').value = entry?.category || 'general';
  document.getElementById('mp-modal-max-req').value = entry?.max_requests_per_day || 0;
  document.getElementById('mp-modal-max-tok').value = entry?.max_tokens_per_day || 0;
  document.getElementById('mp-modal-price-in').value = entry?.price_input_per_1m || 0;
  document.getElementById('mp-modal-price-cache').value = entry?.price_cache_per_1m || 0;
  document.getElementById('mp-modal-price-out').value = entry?.price_output_per_1m || 0;
  document.getElementById('mp-modal-currency').value = entry?.currency || 'USD';
  document.getElementById('model-pool-modal').classList.remove('hidden');
}

async function saveModel() {
  const id = document.getElementById('mp-modal-id').value;
  let conn;
  if (_modalActiveTab === 'native') {
    const p = document.getElementById('mp-modal-native-provider').value;
    conn = {
      provider: NATIVE_PROVIDER_LABELS[p],
      api_style: NATIVE_API_STYLES[p],
      model_id: document.getElementById('mp-modal-native-model-id').value.trim(),
      base_url: NATIVE_BASE_URLS[p],
      api_key: document.getElementById('mp-modal-native-api-key').value,
    };
  } else {
    conn = {
      provider: document.getElementById('mp-modal-provider').value.trim() || '9router',
      api_style: 'openai_compat',
      model_id: document.getElementById('mp-modal-model-id').value.trim(),
      base_url: document.getElementById('mp-modal-base-url').value.trim(),
      api_key: document.getElementById('mp-modal-api-key').value,
    };
  }
  const body = {
    name: document.getElementById('mp-modal-name').value.trim(),
    ...conn,
    category: document.getElementById('mp-modal-category').value,
    max_requests_per_day: parseInt(document.getElementById('mp-modal-max-req').value)||0,
    max_tokens_per_day: parseInt(document.getElementById('mp-modal-max-tok').value)||0,
    price_input_per_1m: parseFloat(document.getElementById('mp-modal-price-in').value)||0,
    price_cache_per_1m: parseFloat(document.getElementById('mp-modal-price-cache').value)||0,
    price_output_per_1m: parseFloat(document.getElementById('mp-modal-price-out').value)||0,
    currency: document.getElementById('mp-modal-currency').value || 'USD',
  };
  if (!body.name || !body.model_id) return showToast('Tên và Model ID là bắt buộc', 'error');
  if (id) {
    if (!body.api_key) delete body.api_key;
    await api('PATCH', `/model-pool/${id}`, body);
  } else {
    await api('POST', '/model-pool', body);
  }
  closeModal('model-pool-modal');
  await loadModelPool();
  if (id && currentModelId == id) _renderLimitBars(body.max_requests_per_day, body.max_tokens_per_day);
}

async function deleteModel(id) {
  if (!id) return;
  if (!(await showConfirm('Xoá model này?'))) return;
  await api('DELETE', `/model-pool/${id}`);
  currentModelId = null;
  document.getElementById('mp-empty').style.display = '';
  document.getElementById('mp-detail').style.display = 'none';
  await loadModelPool();
}

async function testModel(id) {
  const btn = document.getElementById('mp-test-btn');
  if (!btn) return;
  btn.textContent = '⏳ Đang test...';
  btn.style.color = '';
  btn.disabled = true;
  try {
    const res = await api('POST', `/model-pool/${id}/test`);
    if (res.ok) {
      btn.innerHTML = icon('check') + ' Kết nối tốt';
      btn.style.color = 'var(--status-on)';
    } else {
      btn.innerHTML = icon('close') + ' Không kết nối được';
      btn.style.color = 'var(--red)';
      showToast('Không kết nối được tới model: ' + (res.error || 'lỗi không rõ nguyên nhân'), 'error');
    }
  } catch (e) {
    btn.innerHTML = icon('close') + ' Có lỗi xảy ra';
    btn.style.color = 'var(--red)';
    showToast('Không kết nối được tới server: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    setTimeout(() => { btn.innerHTML = icon('plug') + ' Kiểm tra kết nối'; btn.style.color = ''; }, 5000);
  }
}

function _fmtNum(n) {
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000)    return (n/1000).toFixed(1) + 'K';
  return String(n);
}

// ════════════════════════════════════════
// COST TAB
// ════════════════════════════════════════
let _costChartTrend = null, _costChartByModel = null, _lastCostReport = null;

// dd-mm-yyyy — định dạng ngày chuẩn Việt Nam
function _fmtDateVN(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  return `${d}-${m}-${y}`;
}
function _fmtBucketVN(b) {
  return b.bucket_from === b.bucket_to
    ? _fmtDateVN(b.bucket_from)
    : `${_fmtDateVN(b.bucket_from)} → ${_fmtDateVN(b.bucket_to)}`;
}

// Định dạng Date -> "YYYY-MM-DD" theo giờ ĐỊA PHƯƠNG (không dùng toISOString(),
// vì nó quy đổi sang UTC và có thể lùi 1 ngày vào buổi sáng sớm ở múi giờ +).
function _isoLocal(d) {
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function _prevWindow(dateFrom, dateTo) {
  const from = new Date(dateFrom + 'T00:00:00');
  const to = new Date(dateTo + 'T00:00:00');
  const spanDays = Math.round((to - from) / 86400000) + 1;
  const prevTo = new Date(from); prevTo.setDate(prevTo.getDate() - 1);
  const prevFrom = new Date(prevTo); prevFrom.setDate(prevFrom.getDate() - spanDays + 1);
  return { from: _isoLocal(prevFrom), to: _isoLocal(prevTo) };
}

// Khoảng ngày của "kỳ hiện tại" tương ứng với lựa chọn tuần/tháng (dùng cho biểu đồ xu hướng)
function _currentPeriodRange(period) {
  const now = new Date();
  if (period === 'week') {
    const monday = new Date(now); monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
    const sunday = new Date(monday); sunday.setDate(monday.getDate() + 6);
    return { from: _isoLocal(monday), to: _isoLocal(sunday) };
  }
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { from: _isoLocal(start), to: _isoLocal(end) };
}

function _weekdayLabelVN(dateStr) {
  const names = ['CN', 'Th 2', 'Th 3', 'Th 4', 'Th 5', 'Th 6', 'Th 7'];
  const d = new Date(dateStr + 'T00:00:00');
  return `${names[d.getDay()]} ${_fmtDateVN(dateStr).slice(0, 5)}`;
}

// Dựng chuỗi giá trị theo ngày trong tuần (7 điểm), hoặc nhóm 3 ngày/điểm cho tháng
function _buildDaySeries(range, period, byDate) {
  const labels = [], values = [];
  let d = new Date(range.from + 'T00:00:00');
  const end = new Date(range.to + 'T00:00:00');
  if (period === 'week') {
    while (d <= end) {
      const iso = _isoLocal(d);
      labels.push(_weekdayLabelVN(iso));
      values.push(+(byDate[iso] || 0).toFixed(4));
      d.setDate(d.getDate() + 1);
    }
  } else {
    while (d <= end) {
      const groupEnd = new Date(d); groupEnd.setDate(groupEnd.getDate() + 2);
      if (groupEnd.getTime() > end.getTime()) groupEnd.setTime(end.getTime());
      let sum = 0;
      const cursor = new Date(d);
      while (cursor <= groupEnd) {
        sum += byDate[_isoLocal(cursor)] || 0;
        cursor.setDate(cursor.getDate() + 1);
      }
      const dIso = _isoLocal(d), geIso = _isoLocal(groupEnd);
      labels.push(dIso === geIso ? _fmtDateVN(dIso) : `${_fmtDateVN(dIso)}→${_fmtDateVN(geIso)}`);
      values.push(+sum.toFixed(4));
      d.setDate(d.getDate() + 3);
    }
  }
  return { labels, values };
}

async function loadCostTab() {
  const period = document.getElementById('cost-period-select').value;
  const [data, overview] = await Promise.all([
    api('GET', `/model-pool/cost/report?period=${period}`).catch(() => null),
    api('GET', `/model-pool/cost/overview`).catch(() => null),
  ]);
  if (!data) return;
  _lastCostReport = data;
  document.getElementById('cost-range-label').textContent = `${_fmtDateVN(data.date_from)} → ${_fmtDateVN(data.date_to)}`;
  renderCostOverviewCards(overview);
  renderCostDetailTable(data);
  renderCostByModelChart(data);
  await loadCostTrendChart(period);
  toggleTokenColumns(document.getElementById('cost-show-tokens')?.checked);
}

function toggleTokenColumns(visible) {
  document.querySelectorAll('.token-col').forEach(el => {
    el.style.display = visible ? '' : 'none';
  });
}

// Trục x của biểu đồ xu hướng đổi theo period đang chọn:
// ngày → theo giờ (0h-23h) của hôm nay so với hôm qua;
// tuần → từng ngày trong tuần hiện tại (Thứ 2 → Chủ nhật) so với tuần trước;
// tháng → nhóm mỗi 3 ngày trong tháng hiện tại so với tháng trước.
async function loadCostTrendChart(period) {
  if (period === 'day') {
    const today = _isoLocal(new Date());
    const yest = new Date(); yest.setDate(yest.getDate() - 1);
    const [cur, prev] = await Promise.all([
      api('GET', `/model-pool/cost/report-hourly?date=${today}`).catch(() => null),
      api('GET', `/model-pool/cost/report-hourly?date=${_isoLocal(yest)}`).catch(() => null),
    ]);
    renderCostTrendChartHourly(cur, prev);
    return;
  }
  const range = _currentPeriodRange(period);
  const prevRange = _prevWindow(range.from, range.to);
  const [cur, prev] = await Promise.all([
    api('GET', `/model-pool/cost/report?period=day&date_from=${range.from}&date_to=${range.to}`).catch(() => null),
    api('GET', `/model-pool/cost/report?period=day&date_from=${prevRange.from}&date_to=${prevRange.to}`).catch(() => null),
  ]);
  renderCostTrendChartDays(period, cur, range, prev, prevRange);
}

function renderCostTrendChartHourly(data, prevData) {
  const ctx = document.getElementById('cost-trend-chart');
  if (!ctx) return;
  const sumByHour = rows => {
    const arr = new Array(24).fill(0);
    (rows || []).forEach(r => { arr[r.hour] += r.estimated_cost; });
    return arr.map(v => +v.toFixed(4));
  };
  const labels = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}h`);
  const values = sumByHour(data && data.rows);
  const datasets = [{ label: 'Hôm nay', data: values, borderColor: '#22d3ee', tension: 0.3 }];
  if (prevData) {
    datasets.push({ label: 'Hôm qua', data: sumByHour(prevData.rows), borderColor: '#a78bfa', borderDash: [6, 4], tension: 0.3 });
  }
  if (_costChartTrend) _costChartTrend.destroy();
  _costChartTrend = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: { responsive: true, plugins: { legend: { display: true } } },
  });
}

function renderCostTrendChartDays(period, data, range, prevData, prevRange) {
  const ctx = document.getElementById('cost-trend-chart');
  if (!ctx) return;
  const byDate = {};
  ((data && data.rows) || []).forEach(r => { byDate[r.bucket_from] = (byDate[r.bucket_from] || 0) + r.estimated_cost; });
  const { labels, values } = _buildDaySeries(range, period, byDate);

  const datasets = [{ label: 'Kỳ này', data: values, borderColor: '#22d3ee', tension: 0.3 }];
  if (prevData && prevRange) {
    const byPrevDate = {};
    (prevData.rows || []).forEach(r => { byPrevDate[r.bucket_from] = (byPrevDate[r.bucket_from] || 0) + r.estimated_cost; });
    let prevValues = _buildDaySeries(prevRange, period, byPrevDate).values;
    while (prevValues.length < values.length) prevValues.push(0);
    prevValues = prevValues.slice(0, values.length);
    datasets.push({ label: 'Kỳ trước', data: prevValues, borderColor: '#a78bfa', borderDash: [6, 4], tension: 0.3 });
  }

  if (_costChartTrend) _costChartTrend.destroy();
  _costChartTrend = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: { responsive: true, plugins: { legend: { display: true } } },
  });
}

function renderCostOverviewCards(overview) {
  const el = document.getElementById('cost-summary-cards');
  if (!overview) { el.innerHTML = '<div style="font-size:12px;color:var(--muted);">Chưa có dữ liệu</div>'; return; }
  const cardsFor = (totals, label, sub) => Object.entries(totals || {}).map(([cur, v]) => `
    <div class="mp-stat-box" style="min-width:190px;">
      <div class="mp-stat-val">${v.toFixed(4)} ${esc(cur)}</div>
      <div class="mp-stat-lbl">${esc(label)}${sub ? ' · ' + esc(sub) : ''}</div>
    </div>`).join('');
  let html = '';
  html += cardsFor(overview.today.totals, 'Chi phí hôm nay', _fmtDateVN(overview.today.date));
  html += cardsFor(overview.this_week.totals, 'Tổng chi phí tuần này', `${_fmtDateVN(overview.this_week.date_from)} → ${_fmtDateVN(overview.this_week.date_to)}`);
  html += cardsFor(overview.this_month.totals, 'Tổng chi phí tháng này', `${_fmtDateVN(overview.this_month.date_from)} → ${_fmtDateVN(overview.this_month.date_to)}`);
  html += cardsFor(overview.all_time, 'Tổng chi phí từ trước đến giờ');
  el.innerHTML = html || '<div style="font-size:12px;color:var(--muted);">Chưa có dữ liệu</div>';
}

function toggleCostModelRow(rowId) {
  const firstRow = document.querySelector('.' + rowId);
  const willShow = !firstRow || getComputedStyle(firstRow).display === 'none';
  document.querySelectorAll('.' + rowId).forEach(el => { el.style.display = willShow ? 'table-row' : 'none'; });
  const arrow = document.getElementById(rowId + '-arrow');
  if (arrow) arrow.textContent = willShow ? '▾' : '▸';
}

// Theo ngày: chi tiết bấm vào để xem TỪNG LƯỢT GỌI (kèm giờ chính xác).
// Theo tuần/tháng: chi tiết bấm vào để xem tổng theo model trong kỳ đó (như cũ).
function renderCostDetailTable(data) {
  if (data.period === 'day') {
    document.getElementById('cost-detail-title').textContent = 'Chi tiết theo ngày (bấm vào 1 ngày để xem từng lượt gọi model, kèm giờ)';
    document.getElementById('cost-detail-col2-th').textContent = 'Số lượt';
    renderCostDetailTableDaily(data);
  } else {
    document.getElementById('cost-detail-title').textContent = 'Chi tiết theo kỳ (bấm vào 1 dòng để xem chi tiết theo model)';
    document.getElementById('cost-detail-col2-th').textContent = 'Số model';
    renderCostDetailTableGrouped(data);
  }
}

function renderCostDetailTableDaily(data) {
  const tbody = document.getElementById('cost-detail-tbody');
  const rows = data.rows || [];
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);">Không có dữ liệu</td></tr>';
    return;
  }
  // rows đã là 1 dòng / (model, ngày) — gộp theo ngày để làm dòng cha có thể bấm mở.
  const byDay = {};
  rows.forEach(r => {
    const agg = byDay[r.bucket] || (byDay[r.bucket] = {
      bucket_from: r.bucket_from, bucket_to: r.bucket_to, currency: r.currency,
      request_count: 0, tokens_input: 0, tokens_cache: 0, tokens_output: 0, estimated_cost: 0,
    });
    agg.request_count += r.request_count;
    agg.tokens_input += r.tokens_input;
    agg.tokens_cache += r.tokens_cache;
    agg.tokens_output += r.tokens_output;
    agg.estimated_cost += r.estimated_cost;
  });
  const sortedDays = Object.values(byDay).sort((a, b) => a.bucket_from.localeCompare(b.bucket_from));
  let html = '';
  sortedDays.forEach((agg, idx) => {
    const rowId = `cost-day-${idx}`;
    html += `
      <tr id="${rowId}-parent" class="cost-model-row" onclick="toggleCostDayRow('${rowId}','${agg.bucket_from}')">
        <td><span id="${rowId}-arrow">▸</span> ${esc(_fmtBucketVN(agg))}</td>
        <td>${agg.request_count} lượt</td>
        <td>${agg.request_count}</td>
        <td class="token-col">${_fmtNum(agg.tokens_input)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_output)}</td>
        <td>${agg.estimated_cost.toFixed(4)} ${esc(agg.currency)}</td>
      </tr>`;
  });
  tbody.innerHTML = html;
}

// Bấm vào 1 ngày trong bảng "theo ngày" → tải (lazy) chi tiết từng lượt gọi
// (called_at chính xác đến giây) của đúng ngày đó, để tra chi phí 1 lượt chạy ngay lập tức.
async function toggleCostDayRow(rowId, dateStr) {
  const already = document.querySelectorAll('.' + rowId);
  if (already.length) {
    const willShow = already[0].style.display === 'none';
    already.forEach(el => { el.style.display = willShow ? 'table-row' : 'none'; });
    const arrow = document.getElementById(rowId + '-arrow');
    if (arrow) arrow.textContent = willShow ? '▾' : '▸';
    return;
  }
  const arrow = document.getElementById(rowId + '-arrow');
  if (arrow) arrow.textContent = '▾';
  const parentRow = document.getElementById(rowId + '-parent');
  parentRow.insertAdjacentHTML('afterend', `<tr class="${rowId}"><td colspan="7" style="text-align:center;color:var(--muted);font-size:12px;">Đang tải...</td></tr>`);
  const data = await api('GET', `/model-pool/cost/report-calls?date=${dateStr}`).catch(() => null);
  document.querySelectorAll('.' + rowId).forEach(el => el.remove());
  const calls = (data && data.calls) || [];
  let html;
  if (!calls.length) {
    html = `<tr class="${rowId}"><td colspan="7" style="text-align:center;color:var(--muted);font-size:12px;">Không có lượt chạy nào</td></tr>`;
  } else {
    html = calls.map(c => `
      <tr class="${rowId}" style="color:var(--muted);font-size:12px;">
        <td style="padding-left:24px;">${esc((c.called_at || '').split(' ')[1] || c.called_at)}</td>
        <td>${esc(c.name)}</td>
        <td></td>
        <td class="token-col">${_fmtNum(c.tokens_input)}</td>
        <td class="token-col">${_fmtNum(c.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(c.tokens_output)}</td>
        <td>${c.estimated_cost.toFixed(4)} ${esc(c.currency)}</td>
      </tr>`).join('');
  }
  parentRow.insertAdjacentHTML('afterend', html);
  toggleTokenColumns(document.getElementById('cost-show-tokens')?.checked);
}

function renderCostDetailTableGrouped(data) {
  const tbody = document.getElementById('cost-detail-tbody');
  const rows = data.rows || [];
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);">Không có dữ liệu</td></tr>';
    return;
  }
  // Nhóm theo kỳ (tuần/tháng) trước — bấm vào 1 kỳ để xem chi tiết theo model.
  const byBucket = {};
  rows.forEach(r => {
    const agg = byBucket[r.bucket] || (byBucket[r.bucket] = {
      bucket_from: r.bucket_from, bucket_to: r.bucket_to, currency: r.currency,
      request_count: 0, tokens_input: 0, tokens_cache: 0, tokens_output: 0,
      estimated_cost: 0, models: [],
    });
    agg.request_count += r.request_count;
    agg.tokens_input += r.tokens_input;
    agg.tokens_cache += r.tokens_cache;
    agg.tokens_output += r.tokens_output;
    agg.estimated_cost += r.estimated_cost;
    agg.models.push(r);
  });

  const sortedBuckets = Object.values(byBucket).sort((a, b) => a.bucket_from.localeCompare(b.bucket_from));
  let html = '';
  sortedBuckets.forEach((agg, idx) => {
    const rowId = `cost-bucket-${idx}`;
    html += `
      <tr class="cost-model-row" onclick="toggleCostModelRow('${rowId}')">
        <td><span id="${rowId}-arrow">▸</span> ${esc(_fmtBucketVN(agg))}</td>
        <td>${agg.models.length} model</td>
        <td>${agg.request_count}</td>
        <td class="token-col">${_fmtNum(agg.tokens_input)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(agg.tokens_output)}</td>
        <td>${agg.estimated_cost.toFixed(4)} ${esc(agg.currency)}</td>
      </tr>`;
    agg.models.forEach(m => {
      html += `
      <tr class="cost-bucket-row ${rowId}">
        <td style="padding-left:24px;">${esc(m.name)}</td>
        <td></td>
        <td>${m.request_count}</td>
        <td class="token-col">${_fmtNum(m.tokens_input)}</td>
        <td class="token-col">${_fmtNum(m.tokens_cache)}</td>
        <td class="token-col">${_fmtNum(m.tokens_output)}</td>
        <td>${m.estimated_cost.toFixed(4)} ${esc(m.currency)}</td>
      </tr>`;
    });
  });
  tbody.innerHTML = html;
}

function renderCostByModelChart(data) {
  const ctx = document.getElementById('cost-by-model-chart');
  if (!ctx) return;
  const byModel = {};
  (data.rows || []).forEach(r => { byModel[r.name] = (byModel[r.name] || 0) + r.estimated_cost; });
  const labels = Object.keys(byModel);
  const values = labels.map(l => byModel[l]);
  if (_costChartByModel) _costChartByModel.destroy();
  _costChartByModel = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: ['#22d3ee','#a78bfa','#f472b6','#fb923c','#4ade80','#facc15'] }] },
    options: { responsive: true },
  });
}

function exportCostXlsx() {
  const period = document.getElementById('cost-period-select').value;
  window.location.href = `/api/model-pool/cost/export.xlsx?period=${period}`;
}

// ════════════════════════════════════════
// Tab switching
// ════════════════════════════════════════
const _HUB_TABS = new Set(['home','agents','skills','tasks','meeting','train','company-runner','auto-runner','assets','runner','model','cost','settings']);

function switchTab(tab, pushState = true) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tab));
  // Lazy-load iframes on first visit
  const panel = document.getElementById('tab-' + tab);
  const iframe = panel?.querySelector('iframe[data-src]');
  if (iframe && iframe.src === 'about:blank') {
    iframe.src = iframe.dataset.src;
    delete iframe.dataset.src;
  }
  // Update browser URL without reload
  if (pushState) {
    const urlPath = tab === 'home' ? '/hub' : '/hub/' + tab;
    history.pushState({tab}, '', urlPath);
  }
  if (tab === 'company-runner') _syncRunnerIframe('company');
  if (tab === 'auto-runner') _syncRunnerIframe('automation');
  // Refresh data when entering certain tabs
  if (tab === 'home')  renderOverview();
  if (tab === 'model') { loadModelPool(); }
  if (tab === 'assets') { loadAssets(); }
  if (tab === 'cost') { loadCostTab(); }
  if (tab === 'tasks' && currentProjectId) opsRenderSubTab(currentProjectSubTab);
}

// Restore tab on browser back/forward
window.addEventListener('popstate', e => {
  const tab = e.state?.tab || _tabFromPath();
  if (tab === 'company-runner') _syncRunnerIframe('company');
  if (tab === 'auto-runner') _syncRunnerIframe('automation');
  if (_HUB_TABS.has(tab)) switchTab(tab, false);
});

function _tabFromPath() {
  const seg = location.pathname.split('/').filter(Boolean);
  const candidate = seg[1]; // /hub/<candidate>
  if (!candidate) return 'home'; // pathname is exactly /hub
  return _HUB_TABS.has(candidate) ? candidate : 'home';
}

// /hub/company-runner/<id> hoặc /hub/auto-runner/<id> — sub-route mở trang chỉnh sửa quy trình
function _runnerIdFromPath() {
  const seg = location.pathname.split('/').filter(Boolean); // ['hub','company-runner','id']
  if ((seg[1] === 'company-runner' || seg[1] === 'auto-runner' || seg[1] === 'runner') && seg[2]) return decodeURIComponent(seg[2]);
  return null;
}

function _syncRunnerIframe(tabType) {
  const iframeId = tabType === 'company' ? 'company-runner-iframe' : 'auto-runner-iframe';
  const iframe = document.getElementById(iframeId);
  if (!iframe) return;
  const runnerId = _runnerIdFromPath();
  const targetSrc = '/taskrunner' + (runnerId ? '/' + encodeURIComponent(runnerId) : '') + '?embed=1&tab=' + tabType + '&ui=trigger-inspector-4';
  if (iframe.src === 'about:blank') {
    // Chưa từng load — ghi vào data-src để switchTab() lazy-load đúng route
    iframe.dataset.src = targetSrc;
  } else if (!iframe.src.endsWith(targetSrc)) {
    iframe.src = targetSrc;
  }
}

// ════════════════════════════════════════
// Overview / Home
// ════════════════════════════════════════
const _STATUS_LABEL = {
  completed: 'Hoàn thành', failed: 'Thất bại',
  running: 'Đang chạy', cancelled: 'Đã huỷ', pending: 'Chờ xử lý',
};
const _STATUS_COLOR = {
  completed: 'var(--green)', failed: 'var(--red)',
  running: 'var(--cyan)', cancelled: 'var(--muted)', pending: 'var(--amber)',
};

let _homeCostChart = null;

function _homeDate(value) {
  if (!value) return null;
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : value.replace(' ', 'T') + 'Z');
}

function _homeTime(value) {
  const d = _homeDate(value);
  return d && !Number.isNaN(d.getTime()) ? d.toLocaleString('vi-VN') : '—';
}

function _homeRelativeTime(value) {
  const d = _homeDate(value);
  if (!d || Number.isNaN(d.getTime())) return '—';
  const seconds = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (seconds < 60) return 'vừa xong';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} phút trước`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} giờ trước`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} ngày trước`;
  return d.toLocaleDateString('vi-VN');
}

function _renderHomeRuns(runs) {
  const recentEl = document.getElementById('ov-recent-runs');
  if (!recentEl) return;
  if (!runs.length) {
    recentEl.innerHTML = '<div class="home-empty">Chưa có hoạt động nào — khi một quy trình bắt đầu, bạn sẽ thấy ở đây.</div>';
    return;
  }
  recentEl.innerHTML = runs.slice(0, 4).map(r => {
    const st = r.status || 'pending';
    const titleClass = st === 'completed' ? ' is-completed' : st === 'failed' ? ' is-failed' : '';
    return `<div class="recent-run-row" onclick="switchTab('auto-runner')">
      <span style="display:inline-flex;">${icon('sync')}</span>
      <span class="recent-run-name${titleClass}">${esc(r.task_name || 'Quy trình')}</span>
      <span class="recent-run-time">${_homeTime(r.started_at || r.created_at)}</span>
    </div>`;
  }).join('');
}

async function loadHomeRunningTasks(existingRuns) {
  const runs = existingRuns || (await api('GET', '/workflow/runs?limit=20')).runs || [];
  const running = runs.filter(r => r.status === 'running');
  const el = document.getElementById('home-running-tasks');
  if (el) el.innerHTML = running.length ? `<div class="home-widget-list">${running.map(r => `
    <div class="home-list-row">
      <span style="display:inline-flex;color:var(--sky-ink);">${icon('sync')}</span>
      <div class="home-list-main"><div class="home-list-name">${esc(r.task_name || 'Quy trình')}</div>
      <div class="home-list-meta">Bắt đầu ${_homeTime(r.started_at || r.created_at)}</div></div>
    </div>`).join('')}</div>` : '<div class="home-empty">Chưa có tác vụ nào đang chạy — hệ thống đang rảnh.</div>';
  return runs;
}

async function loadHomeConversations() {
  const el = document.getElementById('home-conversations');
  try {
    const data = await api('GET', '/meetings/messages/recent?limit=8');
    const rooms = data.rooms || [];
    if (!el) return;
    if (!rooms.length) {
      el.innerHTML = '<div class="home-empty">Chưa có hội thoại nào — các trao đổi mới trong phòng họp sẽ xuất hiện ở đây.</div>';
      return;
    }
    el.innerHTML = `<div class="home-widget-list">${rooms.map(room => {
      const agent = (typeof agents !== 'undefined' ? agents : []).find(a => a.name === room.last_sender);
      const avatar = room.last_sender_type === 'agent'
        ? avatarHtml(agent?.avatar_color || DEFAULT_AVATAR, room.last_sender, 'avatar-sm')
        : `<span style="display:inline-flex;color:var(--lavender-ink);">${icon('meeting')}</span>`;
      const content = String(room.last_content || '').replace(/\s+/g, ' ').trim();
      const excerpt = content.length > 58 ? content.slice(0, 58).trimEnd() + '…' : content;
      return `<div class="home-list-row">${avatar}<div class="home-list-main">
        <div class="home-list-name">${esc(room.meeting_name || 'Phòng họp')}</div>
        <div class="home-list-meta">${esc(room.last_sender || 'Hệ thống')}: ${esc(excerpt)} · ${_homeRelativeTime(room.last_created_at)}</div>
      </div>${room.message_count ? `<span class="home-list-meta" style="flex-shrink:0;">${room.message_count} tin</span>` : ''}</div>`;
    }).join('')}</div>`;
  } catch (_) {
    if (el) el.innerHTML = '<div class="home-empty">Chưa thể tải hội thoại gần đây.</div>';
  }
}

async function loadHomeCostTrend() {
  const end = new Date();
  const start = new Date(end); start.setDate(start.getDate() - 6);
  const from = _isoLocal(start), to = _isoLocal(end);
  const data = await api('GET', `/model-pool/cost/report?period=day&date_from=${from}&date_to=${to}`).catch(() => null);
  const ctx = document.getElementById('home-cost-trend');
  if (!ctx || !data) return;
  const byDate = {};
  (data.rows || []).forEach(r => { byDate[r.bucket] = (byDate[r.bucket] || 0) + Number(r.estimated_cost || 0); });
  const series = _buildDaySeries({ from, to }, 'week', byDate);
  const trend = series.values.map((_, index, values) => {
    const window = values.slice(Math.max(0, index - 2), index + 1);
    return +(window.reduce((sum, value) => sum + value, 0) / window.length).toFixed(4);
  });
  const totalEl = document.getElementById('home-cost-total');
  if (totalEl) {
    const totals = data.totals || {};
    const totalText = Object.keys(totals).length
      ? Object.entries(totals).map(([currency, value]) => `${Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 4 })} ${currency}`).join(' · ')
      : '0';
    totalEl.innerHTML = `${esc(totalText)}<small>Tổng 7 ngày</small>`;
  }
  if (_homeCostChart) _homeCostChart.destroy();
  const styles = getComputedStyle(document.documentElement);
  const accent = styles.getPropertyValue('--accent').trim();
  const lavender = styles.getPropertyValue('--lavender-ink').trim();
  const chartContext = ctx.getContext('2d');
  const barGradient = chartContext.createLinearGradient(0, 0, 0, 170);
  barGradient.addColorStop(0, accent);
  barGradient.addColorStop(1, styles.getPropertyValue('--accent-soft').trim());
  const hasCost = series.values.some(value => value > 0);
  _homeCostChart = new Chart(ctx, {
    type: 'bar',
    data: { labels: series.labels, datasets: [
      { type: 'bar', label: 'Chi phí', data: series.values, backgroundColor: barGradient, borderColor: accent, borderWidth: 1, borderRadius: 7, borderSkipped: false, maxBarThickness: 26, order: 2 },
      { type: 'line', label: 'Xu hướng 3 ngày', data: trend, borderColor: lavender, backgroundColor: lavender, borderWidth: 2.2, tension: 0.42, pointRadius: 2.5, pointHoverRadius: 5, pointBackgroundColor: styles.getPropertyValue('--bg-card').trim(), pointBorderColor: lavender, pointBorderWidth: 2, fill: false, order: 1 }
    ] },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      animation: { duration: 700, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: styles.getPropertyValue('--text').trim(), titleColor: styles.getPropertyValue('--bg-card').trim(), bodyColor: styles.getPropertyValue('--bg-card').trim(),
          padding: 10, cornerRadius: 9, displayColors: true,
          callbacks: { label: context => ` ${context.dataset.label}: ${Number(context.raw).toLocaleString('vi-VN', { maximumFractionDigits: 4 })}` }
        }
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: styles.getPropertyValue('--muted').trim(), font: { size: 9 }, maxRotation: 0 } },
        y: { display: hasCost, beginAtZero: true, border: { display: false }, grid: { color: styles.getPropertyValue('--border').trim(), drawTicks: false }, ticks: { color: styles.getPropertyValue('--muted').trim(), font: { size: 9 }, padding: 6, maxTicksLimit: 4 } }
      }
    }
  });
}

async function loadHomeAlerts() {
  const el = document.getElementById('home-alerts');
  const section = document.getElementById('home-alerts-section');
  try {
    const data = await api('GET', '/projects/items/alerts');
    const alerts = (data.alerts || []).filter(a => !a.status || a.status === 'open');
    section?.classList.toggle('has-alerts', alerts.length > 0);
    if (!el) return;
    el.innerHTML = alerts.length ? alerts.map(a => `<div class="home-alert-row">
      <span style="display:inline-flex;color:var(--peach-ink);">${icon('warning')}</span>
      <div><div class="home-list-name">${esc(a.title || 'Tác vụ cần chú ý')}</div>
      <div class="home-list-meta">${esc(a.reason || 'Cần kiểm tra')} · ${_homeTime(a.created_at)}</div></div>
    </div>`).join('') : '<div style="font-size:12px;color:var(--ink-muted);">Mọi thứ đang ổn — chưa có cảnh báo nào.</div>';
  } catch (_) {
    if (el) el.innerHTML = '<div style="font-size:12px;color:var(--ink-muted);">Chưa thể kiểm tra cảnh báo lúc này.</div>';
  }
}

let overviewClockTimer = null;

function updateOverviewClock() {
  const now = new Date();
  const dateStr = now.toLocaleDateString('vi-VN', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'Asia/Ho_Chi_Minh',
  });
  const timeStr = now.toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Asia/Ho_Chi_Minh',
  });
  const ovDate = document.getElementById('ov-date');
  if (ovDate) {
    ovDate.innerHTML = `<span>${dateStr.charAt(0).toUpperCase() + dateStr.slice(1)}</span>`
      + `<span class="overview-clock-separator">·</span>`
      + `<span class="overview-clock-time">${timeStr}</span>`;
  }
}

function startOverviewClock() {
  updateOverviewClock();
  if (!overviewClockTimer) overviewClockTimer = setInterval(updateOverviewClock, 1000);
}

function _formatHomeCostTotals(totals) {
  const entries = Object.entries(totals || {});
  if (!entries.length) return '0';
  return entries.map(([currency, rawValue]) => {
    const value = Number(rawValue) || 0;
    const rounded = Number(value.toFixed(2));
    const amount = value > 0 && rounded === 0
      ? '< 0,01'
      : value.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return `${amount} ${currency}`;
  }).join(' · ');
}

async function loadHomeCostComparison(todayTotals) {
  const el = document.getElementById('ov-cost-today-sub');
  if (!el) return;
  el.textContent = '';
  el.classList.remove('up', 'down');
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const date = _isoLocal(yesterday);
  const report = await api('GET', `/model-pool/cost/report?period=day&date_from=${date}&date_to=${date}`).catch(() => null);
  const previousTotals = report?.totals || {};
  const currencies = Object.keys(previousTotals);
  if (!currencies.length || currencies.some(currency => !(currency in (todayTotals || {})))) {
    el.textContent = 'chưa đủ dữ liệu';
    return;
  }
  const previous = currencies.reduce((sum, currency) => sum + Number(previousTotals[currency] || 0), 0);
  if (previous <= 0) {
    el.textContent = 'chưa đủ dữ liệu';
    return;
  }
  const current = currencies.reduce((sum, currency) => sum + Number(todayTotals[currency] || 0), 0);
  const change = Math.round((current - previous) / previous * 100);
  if (change === 0) {
    el.textContent = 'Không đổi so với hôm qua';
    return;
  }
  const increased = change > 0;
  el.textContent = `${increased ? '↑' : '↓'} ${Math.abs(change)}% so với hôm qua`;
  el.classList.add(increased ? 'down' : 'up');
}

async function loadHomeMiniStats() {
  document.getElementById('ms-icon-wf').innerHTML = icon('workflow');
  document.getElementById('ms-icon-auto').innerHTML = icon('sync');
  document.getElementById('ms-icon-meet').innerHTML = icon('meeting');
  document.getElementById('ms-icon-tool').innerHTML = icon('code');
  const [workflows, automations, meetingData, skillData] = await Promise.all([
    api('GET', '/workflow/tasks?kind=company').catch(() => null),
    api('GET', '/workflow/tasks?kind=automation').catch(() => null),
    api('GET', '/meetings/').catch(() => null),
    api('GET', '/skills/').catch(() => null),
  ]);
  const setTaskCount = (id, data) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (!data) { el.textContent = '—'; return; }
    const tasks = data.tasks || [];
    el.textContent = `${tasks.filter(task => task.status === 'active').length}/${tasks.length}`;
  };
  setTaskCount('ms-workflows', workflows);
  setTaskCount('ms-automations', automations);
  const meetingsEl = document.getElementById('ms-meetings');
  if (meetingsEl) meetingsEl.textContent = meetingData ? (meetingData.meetings || []).length : '—';
  const toolsEl = document.getElementById('ms-tools');
  if (toolsEl) {
    const items = skillData?.skills || [];
    toolsEl.textContent = skillData
      ? `${items.filter(item => item.enabled !== 0 && item.enabled !== false).length}/${items.length}`
      : '—';
  }
}

async function renderOverview() {
  startOverviewClock();
  const now = new Date();
  document.getElementById('home-running-icon').innerHTML = icon('sync');
  document.getElementById('home-conversation-icon').innerHTML = icon('meeting');
  document.getElementById('home-cost-icon').innerHTML = icon('cost');
  document.getElementById('home-alert-icon').innerHTML = icon('warning');
  const agentsEl = document.getElementById('ov-n-agents');
  if (agentsEl) agentsEl.textContent = typeof agents !== 'undefined' ? agents.length : 0;
  const agentsSubEl = document.getElementById('ov-n-agents-sub');
  if (agentsSubEl) agentsSubEl.textContent = `${agents.filter(agent => agent.enabled !== 0 && agent.enabled !== false).length} đang bật`;

  const [runsResult, overview] = await Promise.all([
    api('GET', '/workflow/runs?limit=20').catch(() => ({ runs: [] })),
    api('GET', '/model-pool/cost/overview').catch(() => null),
  ]);
  const runs = runsResult.runs || [];
  const running = runs.filter(r => r.status === 'running');
  const today = _isoLocal(now);
  const todayRuns = runs.filter(r => {
    const d = _homeDate(r.started_at || r.created_at);
    return d && _isoLocal(d) === today;
  });
  const finished = todayRuns.filter(r => r.status === 'completed' || r.status === 'failed');
  const success = finished.filter(r => r.status === 'completed').length;
  document.getElementById('ov-n-running').textContent = running.length;
  document.getElementById('ov-n-running-sub').textContent = `${todayRuns.length} lượt chạy hôm nay`;
  document.getElementById('ov-success-rate').textContent = finished.length ? `${Math.round(success / finished.length * 100)}%` : '—';
  document.getElementById('ov-success-rate-sub').textContent = `${success}/${finished.length} lượt hoàn thành`;
  const totals = overview?.today?.totals || {};
  document.getElementById('ov-cost-today').textContent = _formatHomeCostTotals(totals);
  _renderHomeRuns(runs);
  await Promise.all([loadHomeRunningTasks(runs), loadHomeConversations(), loadHomeCostTrend(), loadHomeAlerts(), loadHomeCostComparison(totals), loadHomeMiniStats()]);
}

// ════════════════════════════════════════
// Logout / Auth
// ════════════════════════════════════════
async function logout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.top.location.href = '/login';
}

// ════════════════════════════════════════
// AGENTS
// ════════════════════════════════════════
async function loadAgents() {
  const data = await api('GET', '/agent-configs/');
  agents = data.agents || [];
  renderAgentList();
  document.getElementById('agents-count').textContent = t('count.agents', agents.length);
  renderAgentSkillsSelect();
  renderCardAgentSelect();
  renderDepartmentFilter();
}

// ── Phòng ban (Department) helpers — dùng chung ở mọi nơi hiển thị tên nhân viên ──

function agentDeptBadgeHtml(a) {
  if (!a || !a.department_name) return '';
  const c = a.department_color || '#7C6BAE';
  return `<span class="badge" style="background:${c}22;color:${c};font-size:10px;font-weight:600;">${esc(a.department_name)}</span>`;
}

function agentDeptSuffix(a) {
  return (a && a.department_name) ? ` · ${a.department_name}` : '';
}

function agentById(id) {
  return agents.find(x => x.id === id);
}

async function loadDepartments() {
  const data = await api('GET', '/departments/');
  departments = data.departments || [];
  renderDepartmentSelect();
  renderDepartmentModalList();
  renderDepartmentFilter();
}

function renderDepartmentFilter() {
  const el = document.getElementById('agent-dept-filter');
  if (!el) return;
  if (!departments.length) { el.innerHTML = ''; return; }
  const chip = (label, active, onclick, color) => `
    <div onclick="${onclick}" class="badge ${active ? '' : 'badge-muted'}"
         style="cursor:pointer;${active ? `background:${color}22;color:${color};` : ''}">${esc(label)}</div>`;
  const all = chip(`Tất cả (${agents.length})`, selectedDeptFilter === null, 'filterByDepartment(null)', '#7C6BAE');
  const rest = departments.map(d => {
    const count = agents.filter(a => a.department_id === d.id).length;
    return chip(`${d.name} (${count})`, selectedDeptFilter === d.id, `filterByDepartment(${d.id})`, d.color);
  }).join('');
  el.innerHTML = all + rest;
}

function filterByDepartment(deptId) {
  selectedDeptFilter = deptId;
  renderDepartmentFilter();
  renderAgentList();
}

function renderDepartmentSelect() {
  const el = document.getElementById('agent-department');
  if (!el) return;
  const current = el.value;
  el.innerHTML = '<option value="">— Chưa gán phòng ban —</option>' +
    departments.map(d => `<option value="${d.id}">${esc(d.name)}</option>`).join('');
  el.value = current;
}

function checkDeptHeadPrompt() {
  const prompt = document.getElementById('agent-set-head-prompt');
  const checkbox = document.getElementById('agent-set-head-checkbox');
  const deptId = document.getElementById('agent-department').value;
  const dept = deptId ? departments.find(d => d.id === parseInt(deptId)) : null;
  if (dept && !dept.head_agent_id) {
    document.getElementById('agent-set-head-text').textContent = `Đặt làm Trưởng phòng ${dept.name}?`;
    prompt.style.display = 'flex';
  } else {
    checkbox.checked = false;
    prompt.style.display = 'none';
  }
}

function renderAgentList() {
  const el = document.getElementById('agents-list');
  const query = (document.getElementById('agent-search')?.value || '').trim().toLocaleLowerCase('vi');
  const byDepartment = selectedDeptFilter === null ? agents : agents.filter(a => a.department_id === selectedDeptFilter);
  const list = byDepartment.filter(a => !query || `${a.name || ''} ${a.role || ''}`.toLocaleLowerCase('vi').includes(query));
  if (!list.length) {
    const message = agents.length
      ? 'Không tìm thấy nhân viên phù hợp — thử một từ khoá hoặc phòng ban khác.'
      : 'Chưa có nhân viên AI nào — tạo nhân viên đầu tiên của bạn.';
    el.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state-icon">${icon('bot')}</div><div class="empty-state-text">${message}</div></div>`;
    return;
  }
  el.innerHTML = list.map(a => `
    <div class="agent-card" onclick="selectAgent(${a.id})">
      ${avatarHtml(a.avatar_color, a.name, 'avatar-lg', a.avatar_icon || 'bot')}
      <div class="agent-card-name">${esc(a.name)}</div>
      <div class="agent-card-role">${esc(a.role || 'Assistant')}</div>
      <div class="agent-card-badges">${agentDeptBadgeHtml(a)}</div>
      <div class="agent-card-meta">
        <span>${(a.skills || []).length} kỹ năng · ${(a.model_pool_ids || (a.model_pool_id ? [a.model_pool_id] : [])).length} model</span>
        <span class="status-dot-label"><i class="sdot ${a.enabled === false || a.enabled === 0 ? 'idle' : 'on'}"></i>${a.enabled === false || a.enabled === 0 ? 'Tắt' : 'Bật'}</span>
      </div>
    </div>`).join('');
}

// ── Quản lý phòng ban (modal) ──

function openDepartmentModal() {
  resetDepartmentForm();
  renderDepartmentModalList();
  document.getElementById('department-modal').classList.remove('hidden');
}

function renderDepartmentHeadSelect(selectedId) {
  const el = document.getElementById('department-head');
  el.innerHTML = '<option value="">— Chưa có trưởng phòng —</option>' +
    agents.map(a => `<option value="${a.id}">${esc(a.name)} — ${esc(a.role)}</option>`).join('');
  el.value = selectedId || '';
}

function renderDepartmentModalList() {
  const el = document.getElementById('department-list');
  if (!el) return;
  if (!departments.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--muted);">Chưa có phòng ban nào.</div>';
    return;
  }
  el.innerHTML = departments.map(d => {
    const count = agents.filter(a => a.department_id === d.id).length;
    const headTxt = d.head_agent_name ? ` · Trưởng phòng: ${esc(d.head_agent_name)}` : '';
    return `
    <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:var(--radius-sm);box-shadow:var(--shadow);background:var(--bg-card);">
      <div style="width:10px;height:10px;border-radius:50%;background:${d.color};flex-shrink:0;"></div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:13px;font-weight:600;">${esc(d.name)}</div>
        <div style="font-size:11px;color:var(--muted);">${count} nhân viên${headTxt}${d.description ? ' · ' + esc(d.description) : ''}</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="editDepartment(${d.id})">Sửa</button>
      <button class="btn btn-danger btn-sm" onclick="deleteDepartmentConfirm(${d.id})">Xoá</button>
    </div>`;
  }).join('');
}

function hslToHex(h, s, l) {
  h = ((Number(h) % 360) + 360) % 360;
  s = Math.max(0, Math.min(100, Number(s))) / 100;
  l = Math.max(0, Math.min(100, Number(l))) / 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs((h / 60) % 2 - 1));
  const m = l - c / 2;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g] = [c, x];
  else if (h < 120) [r, g] = [x, c];
  else if (h < 180) [g, b] = [c, x];
  else if (h < 240) [g, b] = [x, c];
  else if (h < 300) [r, b] = [x, c];
  else [r, b] = [c, x];
  return '#' + [r, g, b]
    .map(v => Math.round((v + m) * 255).toString(16).padStart(2, '0'))
    .join('')
    .toUpperCase();
}

function hexToHsl(hex) {
  const match = /^#([0-9a-fA-F]{6})$/.exec(hex);
  if (!match) return null;
  const value = parseInt(match[1], 16);
  const r = ((value >> 16) & 255) / 255;
  const g = ((value >> 8) & 255) / 255;
  const b = (value & 255) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  let h = 0;
  if (delta) {
    if (max === r) h = 60 * (((g - b) / delta) % 6);
    else if (max === g) h = 60 * ((b - r) / delta + 2);
    else h = 60 * ((r - g) / delta + 4);
  }
  if (h < 0) h += 360;
  const l = (max + min) / 2;
  const s = delta === 0 ? 0 : delta / (1 - Math.abs(2 * l - 1));
  return { h: Math.round(h), s: Math.round(s * 100), l: Math.round(l * 100) };
}

function setDepartmentColor(hex) {
  const normalized = /^#([0-9a-fA-F]{6})$/.test(hex) ? hex.toUpperCase() : '#7C6BAE';
  const hsl = hexToHsl(normalized);
  document.getElementById('department-color').value = normalized;
  document.getElementById('department-color-hex').value = normalized;
  document.getElementById('department-color-hex').classList.remove('invalid');
  document.getElementById('department-color-preview').style.background = normalized;
  document.getElementById('department-color-hue').value = hsl.h;
}

document.getElementById('department-color-hue').addEventListener('input', event => {
  setDepartmentColor(hslToHex(event.target.value, 52, 50));
});

document.getElementById('department-color-hex').addEventListener('input', event => {
  const input = event.target;
  if (!/^#([0-9a-fA-F]{6})$/.test(input.value)) {
    input.classList.add('invalid');
    return;
  }
  setDepartmentColor(input.value);
});

function editDepartment(id) {
  const d = departments.find(x => x.id === id);
  if (!d) return;
  document.getElementById('department-edit-id').value = d.id;
  document.getElementById('department-name').value = d.name;
  document.getElementById('department-description').value = d.description || '';
  setDepartmentColor(d.color || '#7C6BAE');
  renderDepartmentHeadSelect(d.head_agent_id);
  document.getElementById('department-form-title').textContent = `Sửa phòng ban: ${d.name}`;
  document.getElementById('department-cancel-edit-btn').style.display = '';
}

function resetDepartmentForm() {
  document.getElementById('department-edit-id').value = '';
  document.getElementById('department-name').value = '';
  document.getElementById('department-description').value = '';
  setDepartmentColor('#7C6BAE');
  renderDepartmentHeadSelect(null);
  document.getElementById('department-form-title').textContent = 'Thêm phòng ban mới';
  document.getElementById('department-cancel-edit-btn').style.display = 'none';
}

async function saveDepartment() {
  const id = document.getElementById('department-edit-id').value;
  const name = document.getElementById('department-name').value.trim();
  if (!name) return showToast('Tên phòng ban là bắt buộc', 'error');
  const colorHexEl = document.getElementById('department-color-hex');
  if (!/^#([0-9a-fA-F]{6})$/.test(colorHexEl.value)) {
    colorHexEl.classList.add('invalid');
    return showToast('Mã màu phải có dạng #RRGGBB', 'error');
  }
  setDepartmentColor(colorHexEl.value);
  const headVal = document.getElementById('department-head').value;
  const body = {
    name,
    description: document.getElementById('department-description').value.trim(),
    color: document.getElementById('department-color').value,
    head_agent_id: headVal ? parseInt(headVal) : null,
  };
  try {
    if (id) {
      await api('PATCH', `/departments/${id}`, body);
    } else {
      await api('POST', '/departments/', body);
    }
    if (body.head_agent_id) await ensureHeadSkillOnAgent(body.head_agent_id);
    await loadDepartments();
    await loadAgents();
    resetDepartmentForm();
    showToast('Đã lưu phòng ban.', 'success');
  } catch (e) { showToast('Error: ' + e.message, 'error'); }
}

async function deleteDepartmentConfirm(id) {
  const d = departments.find(x => x.id === id);
  const count = agents.filter(a => a.department_id === id).length;
  const msg = count
    ? `Xoá phòng ban "${d?.name}"? ${count} nhân viên sẽ về trạng thái chưa gán phòng ban.`
    : `Xoá phòng ban "${d?.name}"?`;
  if (!(await showConfirm(msg))) return;
  await api('DELETE', `/departments/${id}`);
  if (selectedDeptFilter === id) selectedDeptFilter = null;
  await loadDepartments();
  await loadAgents();
}

function renderAgentSkillsSelect(selectedIds) {
  const el = document.getElementById('agent-skills-select');
  if (!skills.length) { el.innerHTML = '<span style="font-size:12px;color:var(--muted);">No skills available</span>'; return; }
  const current = selectedIds !== undefined ? selectedIds : getSelectedAgentSkills();
  el.innerHTML = skills.map(s => `
    <div onclick="toggleAgentSkill(${s.id}, this)" data-skill-id="${s.id}"
         class="badge ${current.includes(s.id)?'badge-cyan':'badge-muted'}" style="cursor:pointer;">
      ${esc(s.name)}
    </div>`).join('');
}

function getSelectedAgentSkills() {
  return [...document.querySelectorAll('#agent-skills-select [data-skill-id].badge-cyan')]
    .map(el => parseInt(el.dataset.skillId));
}

// Nhân viên được đặt làm Trưởng phòng mặc định phải có skill quản lý phòng ban
// (xem skills/truong_phong_quan_ly.md) để biết cách dùng dữ liệu nhân sự/công việc
// thực tế được hệ thống chèn sẵn thay vì trả lời chung chung như 1 nhân viên thường.
const HEAD_SKILL_NAME = 'truong_phong_quan_ly';

function withHeadSkill(skillIds) {
  const headSkill = skills.find(s => s.name === HEAD_SKILL_NAME);
  if (!headSkill || skillIds.includes(headSkill.id)) return skillIds;
  return [...skillIds, headSkill.id];
}

async function ensureHeadSkillOnAgent(agentId) {
  const headSkill = skills.find(s => s.name === HEAD_SKILL_NAME);
  if (!headSkill) return;
  const agent = agents.find(a => a.id === agentId) || await api('GET', `/agent-configs/${agentId}`).catch(() => null);
  if (!agent) return;
  const currentSkills = agent.skills || [];
  if (currentSkills.includes(headSkill.id)) return;
  await api('PATCH', `/agent-configs/${agentId}`, { skills: [...currentSkills, headSkill.id] });
}

function toggleAgentSkill(id, el) {
  el.classList.toggle('badge-cyan');
  el.classList.toggle('badge-muted');
}

let agentWizardStep = 1;
let agentWizardMaxStep = 1;

function renderAgentReview() {
  const el = document.getElementById('agent-review-summary');
  if (!el) return;
  const deptId = parseInt(document.getElementById('agent-department').value || '0');
  const dept = departments.find(d => d.id === deptId);
  const selectedSkills = getSelectedAgentSkills().map(id => skills.find(s => s.id === id)?.name).filter(Boolean);
  const selectedModels = agentModelIds.map(id => modelPool.find(m => m.id === id)?.name || `Model #${id}`);
  const prompt = document.getElementById('agent-system-prompt').value.trim();
  const avatarIcon = document.querySelector('.avatar-shape-opt.selected')?.dataset.avatarIcon || 'bot';
  const avatarColor = document.querySelector('.avatar-opt.selected')?.dataset.icon || DEFAULT_AVATAR;
  const item = (label, value) => `<div class="agent-review-item"><div class="agent-review-label">${esc(label)}</div><div class="agent-review-value">${esc(value || 'Chưa thiết lập')}</div></div>`;
  el.innerHTML = [
    item('Tên nhân viên', document.getElementById('agent-name').value.trim()),
    item('Vai trò', document.getElementById('agent-role').value.trim() || 'Assistant'),
    item('Phòng ban', dept?.name || 'Chưa gán phòng ban'),
    item('Ảnh đại diện', `${AVATAR_ICON_LABEL[avatarIcon] || 'Robot'} · ${AVATAR_PALETTE_LABEL[avatarColor] || avatarColor}`),
    item('Model ưu tiên', selectedModels.join(', ') || 'Dùng model mặc định'),
    item('Kỹ năng', selectedSkills.join(', ') || 'Chưa chọn kỹ năng'),
    item('System Prompt', prompt || 'Chưa thiết lập'),
  ].join('');
}

function goAgentWizardStep(step, force = false) {
  step = Math.max(1, Math.min(5, step));
  const editing = Boolean(document.getElementById('agent-id').value);
  if (!force && !editing && step > agentWizardMaxStep + 1) return;
  if (step > 1 && !document.getElementById('agent-name').value.trim()) {
    showToast('Vui lòng nhập tên nhân viên AI trước khi tiếp tục.', 'error');
    document.getElementById('agent-name').focus();
    return;
  }
  agentWizardStep = step;
  agentWizardMaxStep = Math.max(agentWizardMaxStep, step);
  document.querySelectorAll('.agent-wizard-step').forEach(el => el.classList.toggle('active', Number(el.dataset.agentStep) === step));
  const stepIcons = ['bot', 'sliders', 'document', 'bolt', 'check'];
  document.querySelectorAll('.agent-wizard-tab').forEach((el, index) => {
    const isDone = index + 1 < step;
    el.classList.toggle('active', index + 1 === step);
    el.classList.toggle('done', isDone);
    const circle = el.querySelector('span');
    if (circle) circle.innerHTML = isDone && index + 1 !== step ? icon('check') : icon(stepIcons[index]);
  });
  document.getElementById('agent-wizard-back').style.visibility = step === 1 ? 'hidden' : 'visible';
  document.getElementById('agent-wizard-next').style.display = step === 5 ? 'none' : '';
  document.getElementById('agent-wizard-save').style.display = step === 5 ? '' : 'none';
  if (step === 5) renderAgentReview();
}

function changeAgentWizardStep(direction) {
  goAgentWizardStep(agentWizardStep + direction);
}

function openAgentWizard(editing) {
  agentWizardMaxStep = editing ? 5 : 1;
  document.getElementById('agent-wizard-layer').style.display = 'flex';
  document.getElementById('agent-form-container').style.display = 'flex';
  goAgentWizardStep(1, true);
}

function selectAgent(id) {
  selectedAgentId = id;
  renderAgentList();
  const a = agents.find(x => x.id === id);
  if (!a) return;
  document.getElementById('agent-form-title').textContent = a.name;
  document.getElementById('agent-delete-btn').style.display = '';
  document.getElementById('agent-id').value = a.id;
  document.getElementById('agent-name').value = a.name;
  document.getElementById('agent-role').value = a.role;
  document.getElementById('agent-department').value = a.department_id || '';
  checkDeptHeadPrompt();
  setAgentModelIds(a.model_pool_ids || (a.model_pool_id ? [a.model_pool_id] : []));
  document.getElementById('agent-system-prompt').value = a.system_prompt;
  initAvatarPicker(a.avatar_icon || 'bot', a.avatar_color);
  renderAgentSkillsSelect(a.skills || []);
  updateAgentPreview();
  openAgentWizard(true);
}

function newAgent() {
  selectedAgentId = null;
  renderAgentList();
  document.getElementById('agent-form-title').textContent = t('js.new_agent');
  document.getElementById('agent-delete-btn').style.display = 'none';
  document.getElementById('agent-id').value = '';
  document.getElementById('agent-name').value = '';
  document.getElementById('agent-role').value = '';
  document.getElementById('agent-department').value = '';
  checkDeptHeadPrompt();
  setAgentModelIds([]);
  document.getElementById('agent-system-prompt').value = '';
  initAvatarPicker('bot', DEFAULT_AVATAR);
  renderAgentSkillsSelect([]);
  updateAgentPreview();
  document.getElementById('agent-set-head-checkbox').checked = false;
  openAgentWizard(false);
}

function cancelAgentForm() {
  selectedAgentId = null;
  document.getElementById('agent-form-container').style.display = 'none';
  document.getElementById('agent-wizard-layer').style.display = 'none';
  renderAgentList();
}

function updateAgentPreview() {
  const name = document.getElementById('agent-name').value || 'A';
  const role = document.getElementById('agent-role').value || 'Assistant';
  const avatarKey = document.querySelector('.avatar-opt.selected')?.dataset.icon || DEFAULT_AVATAR;
  const avatarIcon = document.querySelector('.avatar-shape-opt.selected')?.dataset.avatarIcon || 'bot';
  const previewEl = document.getElementById('agent-preview-avatar');
  const {content, style} = avatarInfo(avatarKey, name, avatarIcon);
  previewEl.innerHTML = content;
  previewEl.style.cssText = style;
  document.getElementById('agent-preview-name').textContent = name;
  document.getElementById('agent-preview-role').textContent = role;
}

async function saveAgent() {
  const id = document.getElementById('agent-id').value;
  const body = {
    name: document.getElementById('agent-name').value.trim(),
    role: document.getElementById('agent-role').value.trim() || 'Assistant',
    model_pool_ids: [...agentModelIds],
    system_prompt: document.getElementById('agent-system-prompt').value,
    avatar_color: document.querySelector('.avatar-opt.selected')?.dataset.icon || DEFAULT_AVATAR,
    avatar_icon: document.querySelector('.avatar-shape-opt.selected')?.dataset.avatarIcon || 'bot',
    skills: getSelectedAgentSkills(),
    department_id: document.getElementById('agent-department').value ? parseInt(document.getElementById('agent-department').value) : null,
  };
  if (!body.name) return showToast('Name is required', 'error');
  const setAsHead = document.getElementById('agent-set-head-checkbox').checked && body.department_id;
  if (setAsHead) body.skills = withHeadSkill(body.skills);
  try {
    let savedId = id ? parseInt(id) : null;
    if (id) {
      await api('PATCH', `/agent-configs/${id}`, body);
    } else {
      const created = await api('POST', '/agent-configs/', body);
      savedId = created.id;
    }
    if (setAsHead) {
      await api('PATCH', `/departments/${body.department_id}`, { head_agent_id: savedId });
      await loadDepartments();
    }
    await loadAgents();
    cancelAgentForm();
    showToast('Đã lưu thay đổi.', 'success');
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

async function deleteAgent() {
  const id = document.getElementById('agent-id').value;
  if (!id) return;
  if (!(await showConfirm('Delete this agent?'))) return;
  await api('DELETE', `/agent-configs/${id}`);
  await loadAgents();
  cancelAgentForm();
}

// ════════════════════════════════════════
// SKILLS
// ════════════════════════════════════════
// skill_id -> { connected, error, tools: [...] }. Nạp rời khỏi loadSkills vì lần
// đầu phải khởi chạy MCP server thật (vài giây), không để nó chặn hiển thị tab.
let mcpStatusBySkill = {};

async function loadSkills() {
  const [data] = await Promise.all([
    api('GET', '/skills/'),
    loadBuiltinTools(),
  ]);
  skills = data.skills || [];
  renderSkillList();
  document.getElementById('skills-count').textContent = t('count.skills', skills.length);
  if (skills.some(s => s.type === 'mcp')) refreshMcpStatus();
}

async function refreshMcpStatus() {
  try {
    const data = await api('GET', '/tools/mcp/status');
    mcpStatusBySkill = Object.fromEntries((data.servers || []).map(s => [s.skill_id, s]));
  } catch (error) {
    console.warn('Không lấy được trạng thái MCP server:', error);
    mcpStatusBySkill = {};
  }
  renderSkillList();
}

const SKILL_TYPE_LABELS = {
  builtin: 'Có sẵn', api: 'API', mcp: 'MCP', custom: 'Custom',
};
let availableBuiltinTools = [];
let skillWizardStep = 1;
let skillWizardMaxStep = 1;

async function loadBuiltinTools(selectedName = '') {
  try {
    const data = await api('GET', '/tools/');
    availableBuiltinTools = data.tools || [];
  } catch (error) {
    console.warn('Không thể tải danh sách công cụ hệ thống:', error);
    availableBuiltinTools = [];
  }
  renderBuiltinToolOptions(selectedName || document.getElementById('skill-builtin-tool')?.value || '');
}

function renderBuiltinToolOptions(selectedName = '') {
  const el = document.getElementById('skill-builtin-tool');
  if (!el) return;
  const known = availableBuiltinTools.some(tool => tool.name === selectedName);
  el.innerHTML = '<option value="">— Chọn công cụ —</option>' +
    (!known && selectedName ? `<option value="${esc(selectedName)}">${esc(selectedName)} (không còn đăng ký)</option>` : '') +
    availableBuiltinTools.map(tool => `<option value="${esc(tool.name)}">${esc(tool.name)} — ${esc(tool.description || '')}</option>`).join('');
  el.value = selectedName;
  updateBuiltinToolDescription();
}

function updateBuiltinToolDescription() {
  const name = document.getElementById('skill-builtin-tool')?.value || '';
  const tool = availableBuiltinTools.find(item => item.name === name);
  const description = document.getElementById('skill-builtin-tool-description');
  if (description) description.textContent = tool?.description || (name ? 'Công cụ này hiện không có trong registry.' : '');
}

function filterSkillsByType(type) {
  selectedSkillTypeFilter = type || null;
  renderSkillList();
}

function renderSkillList() {
  const el = document.getElementById('skills-list');
  const q = (document.getElementById('skill-search')?.value || '').trim().toLowerCase();
  const list = skills.filter(s =>
    (!selectedSkillTypeFilter || s.type === selectedSkillTypeFilter) &&
    (!q || (s.name || '').toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q))
  );
  const filter = document.getElementById('skill-type-filter');
  const chip = (type, label) => {
    const active = selectedSkillTypeFilter === type;
    const count = type ? skills.filter(s => s.type === type).length : skills.length;
    return `<span class="badge ${active ? (type ? `skill-type-${type}` : 'badge-green') : 'badge-muted'}" onclick="filterSkillsByType(${type ? `'${type}'` : 'null'})">${label} (${count})</span>`;
  };
  filter.innerHTML = chip(null, 'Tất cả') + Object.entries(SKILL_TYPE_LABELS).map(([type, label]) => chip(type, label)).join('');
  if (!list.length) {
    el.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state-icon">${icon('bolt')}</div><div class="empty-state-text">${skills.length ? 'Không tìm thấy kỹ năng phù hợp.' : 'Chưa có kỹ năng nào — tạo kỹ năng đầu tiên của bạn.'}</div></div>`;
    return;
  }
  el.innerHTML = list.map(s => s.type === 'mcp' ? mcpSkillCard(s) : plainSkillCard(s)).join('');
}

function skillEnabledMeta(s) {
  const off = s.enabled === false || s.enabled === 0;
  return `<span class="status-dot-label"><i class="sdot ${off ? 'idle' : 'on'}"></i>${off ? 'Tắt' : 'Bật'}</span>`;
}

function plainSkillCard(s) {
  return `
    <div class="skill-card" onclick="selectSkill(${s.id})">
      <div class="skill-card-icon skill-type-${s.type}">${icon('bolt')}</div>
      <div class="skill-card-name">${esc(s.name)}</div>
      <div class="skill-card-description">${esc(s.description || 'Chưa có mô tả')}</div>
      <div class="skill-card-badges"><span class="skill-type-badge skill-type-${s.type}">${esc(SKILL_TYPE_LABELS[s.type] || s.type)}</span></div>
      <div class="skill-card-meta"><span>Cấu hình kết nối</span>${skillEnabledMeta(s)}</div>
    </div>`;
}

// Một MCP server phơi ra nhiều tool, nên card của nó là một khối chứa danh sách
// tool chứ không phải một ô đơn như các loại skill khác.
function mcpSkillCard(s) {
  const status = mcpStatusBySkill[s.id];
  const prefix = status?.prefix || '';
  const tools = (status?.tools || []).map(n => prefix && n.startsWith(prefix) ? n.slice(prefix.length) : n);

  let body;
  if (!status) {
    body = `<span class="skill-mcp-empty">Đang kiểm tra kết nối...</span>`;
  } else if (!status.connected) {
    body = `<span class="skill-mcp-empty">Không kết nối được${status.error ? ' — ' + esc(status.error) : ''}</span>`;
  } else if (!tools.length) {
    body = `<span class="skill-mcp-empty">Server không phơi ra tool nào.</span>`;
  } else {
    body = tools.map(n => `<span class="skill-mcp-tool-chip">${esc(n)}</span>`).join('');
  }

  const total = (status?.available || []).length;
  const count = status?.connected
    ? (total && total !== tools.length ? `đang bật ${tools.length}/${total} tool` : `${tools.length} tool`)
    : 'Chưa kết nối';
  return `
    <div class="skill-card skill-card-mcp" onclick="selectSkill(${s.id})">
      <div class="skill-mcp-head">
        <div class="skill-card-icon skill-type-mcp">${icon('bolt')}</div>
        <div class="skill-mcp-headings">
          <div class="skill-card-name">${esc(s.name)}</div>
          <div class="skill-card-description">${esc(s.description || 'Chưa có mô tả')}</div>
          <div class="skill-card-badges" style="justify-content:flex-start;"><span class="skill-type-badge skill-type-mcp">${esc(SKILL_TYPE_LABELS.mcp)}</span></div>
        </div>
      </div>
      <div class="skill-mcp-toollist">${body}</div>
      <div class="skill-card-meta"><span>${esc(count)}</span>${skillEnabledMeta(s)}</div>
    </div>`;
}

function _clearSkillFilePreview() {
  document.getElementById('skill-file-input').value = '';
  document.getElementById('skill-file-preview').style.display = 'none';
  document.getElementById('skill-upload-zone').style.display = '';
}

function resetSkillConfigFields() {
  ['skill-builtin-tool','skill-api-endpoint','skill-api-key','skill-mcp-target','skill-mcp-token','skill-builtin-legacy','skill-mcp-legacy'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('skill-api-method').value = 'GET';
  document.getElementById('skill-mcp-transport').value = 'stdio';
  document.getElementById('skill-api-extra').value = '{}';
  document.getElementById('skill-config').value = '{}';
  document.getElementById('skill-image-pool-wrap').style.display = 'none';
  document.getElementById('skill-builtin-legacy-wrap').style.display = 'none';
  document.getElementById('skill-mcp-legacy-wrap').style.display = 'none';
  updateBuiltinToolDescription();
}

function updateSkillImagePoolField() {
  const isImageSkill =
    document.getElementById('skill-type').value === 'custom' &&
    document.getElementById('skill-name').value.trim() === 'generate_post_image';
  document.getElementById('skill-image-pool-wrap').style.display = isImageSkill ? '' : 'none';
}

function chooseSkillType(type) {
  if (!Object.hasOwn(SKILL_TYPE_LABELS, type)) return;
  document.getElementById('skill-type').value = type;
  document.querySelectorAll('.skill-type-option').forEach(el => el.classList.toggle('selected', el.dataset.skillType === type));
  document.querySelectorAll('.skill-config-panel').forEach(el => el.classList.toggle('active', el.dataset.configType === type));
  document.getElementById('skill-type-required').style.display = 'none';
  // Chỉ 'api' và 'mcp' mới có kết nối ra ngoài để mà thử.
  document.getElementById('skill-conn-test').style.display = (type === 'api' || type === 'mcp') ? '' : 'none';
  clearSkillConnResult();
  updateSkillImagePoolField();
}

function clearSkillConnResult() {
  const box = document.getElementById('skill-conn-result');
  if (box) { box.innerHTML = ''; box.className = 'skill-conn-result'; }
}

async function testSkillConnection() {
  const type = document.getElementById('skill-type').value;
  if (type !== 'api' && type !== 'mcp') return;
  const config = buildSkillConfig(type);
  if (config === null) return;

  const btn = document.getElementById('skill-conn-btn');
  const box = document.getElementById('skill-conn-result');
  btn.disabled = true;
  btn.textContent = 'Đang thử...';
  box.className = 'skill-conn-result pending';
  box.innerHTML = type === 'mcp'
    ? 'Đang khởi chạy MCP server — lần đầu có thể mất vài giây nếu server phải nạp model.'
    : 'Đang gọi thử endpoint...';

  try {
    // Gửi kèm id skill đang sửa: ô secret hiển thị dạng mặt nạ, backend tra lại
    // giá trị thật từ DB thì mới test được kết nối của skill đã lưu.
    const editingId = parseInt(document.getElementById('skill-id').value, 10);
    const payload = { type, config };
    if (Number.isInteger(editingId)) payload.skill_id = editingId;
    const r = await api('POST', '/skills/test-connection', payload);
    box.className = 'skill-conn-result ' + (r.ok ? 'ok' : 'fail');
    box.innerHTML = r.ok ? renderConnOk(type, r) : renderConnFail(r);
  } catch (error) {
    box.className = 'skill-conn-result fail';
    box.innerHTML = `<div class="skill-conn-title">Không gọi được API kiểm tra</div><div class="skill-conn-detail">${esc(String(error))}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Kiểm tra kết nối';
  }
}

function renderConnOk(type, r) {
  const ms = r.elapsed_ms != null ? ` · ${r.elapsed_ms}ms` : '';
  if (type === 'mcp') {
    const tools = r.tools || [];
    const head = `<div class="skill-conn-title">Kết nối được${ms} — server phơi ra ${tools.length} tool</div>`;
    if (!tools.length) {
      return head + `<div class="skill-conn-detail">Server không khai báo tool nào. Kiểm tra lại lệnh khởi chạy.</div>`;
    }
    // Chưa từng chọn -> mặc định bật hết, giữ nguyên hành vi cũ cho skill đã có.
    if (!Array.isArray(skillMcpSelectedTools)) skillMcpSelectedTools = tools.map(t => t.name);
    mcpAvailableTools = tools.map(t => t.name);
    return head
      + `<div class="skill-conn-detail">Chọn những tool muốn giao cho nhân viên. Bỏ chọn bớt sẽ tiết kiệm token mỗi lượt gọi — mỗi tool được bật đều phải kèm schema vào request.
           <a href="javascript:void(0)" onclick="toggleAllMcpTools(true)">Chọn tất cả</a> ·
           <a href="javascript:void(0)" onclick="toggleAllMcpTools(false)">Bỏ chọn tất cả</a></div>`
      + `<div class="skill-conn-tools" id="skill-mcp-tool-picker">${renderMcpToolPicker(tools)}</div>`;
  }
  const title = r.executed
    ? `Kết nối được — HTTP ${r.status_code}${ms}`
    : `Tới được server — HTTP ${r.status_code}${ms} (chưa gọi thật)`;
  return `<div class="skill-conn-title">${esc(title)}</div>`
    + (r.note ? `<div class="skill-conn-detail">${esc(r.note)}</div>` : '');
}

// Tool của MCP server đang được chọn để giao cho nhân viên.
// null = chưa từng chọn -> backend lấy tất cả (tương thích skill tạo trước tính năng này).
let skillMcpSelectedTools = null;
let mcpAvailableTools = [];

function renderMcpToolPicker(tools) {
  const chosen = new Set(skillMcpSelectedTools || []);
  return tools.map(t => `
    <label class="skill-conn-tool skill-conn-tool-pick${chosen.has(t.name) ? ' picked' : ''}">
      <input type="checkbox" ${chosen.has(t.name) ? 'checked' : ''}
             onchange="toggleMcpTool(${JSON.stringify(t.name).replace(/"/g, '&quot;')}, this.checked)">
      <span>
        <span class="skill-conn-tool-name">${esc(t.name)}</span>
        <span class="skill-conn-tool-desc">${esc((t.description || 'Không có mô tả').split('\n')[0])}</span>
      </span>
    </label>`).join('');
}

function toggleMcpTool(name, on) {
  const set = new Set(skillMcpSelectedTools || []);
  if (on) set.add(name); else set.delete(name);
  skillMcpSelectedTools = mcpAvailableTools.filter(n => set.has(n));
  refreshMcpPickerStyles();
}

function toggleAllMcpTools(on) {
  skillMcpSelectedTools = on ? mcpAvailableTools.slice() : [];
  const box = document.getElementById('skill-mcp-tool-picker');
  if (box) {
    const chosen = new Set(skillMcpSelectedTools);
    box.querySelectorAll('label').forEach(label => {
      const name = label.querySelector('.skill-conn-tool-name')?.textContent || '';
      const input = label.querySelector('input');
      if (input) input.checked = chosen.has(name);
    });
  }
  refreshMcpPickerStyles();
}

function refreshMcpPickerStyles() {
  const box = document.getElementById('skill-mcp-tool-picker');
  if (!box) return;
  box.querySelectorAll('label').forEach(label => {
    label.classList.toggle('picked', !!label.querySelector('input')?.checked);
  });
}

function renderConnFail(r) {
  const what = r.status_code != null ? `HTTP ${r.status_code}` : 'Không kết nối được';
  return `<div class="skill-conn-title">${esc(what)}</div>`
    + `<div class="skill-conn-detail">${esc(r.error || r.note || 'Không rõ nguyên nhân')}</div>`;
}

function toggleSkillSecret(id) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
}

function parseSkillJson(id, label) {
  try { return JSON.parse(document.getElementById(id).value || '{}'); }
  catch { showToast(`${label} phải là JSON hợp lệ`, 'error'); return null; }
}

function buildSkillConfig(type, showErrors = true) {
  if (type === 'builtin') {
    const legacy = parseSkillJson('skill-builtin-legacy', 'Dữ liệu cấu hình cũ');
    if (legacy === null) return null;
    const toolName = document.getElementById('skill-builtin-tool').value;
    if (!toolName) {
      if (showErrors) showToast('Hãy chọn một công cụ hệ thống', 'error');
      return null;
    }
    return { ...legacy, tool_name: toolName };
  }
  if (type === 'api') {
    const extra = parseSkillJson('skill-api-extra', 'Tuỳ chọn nâng cao');
    if (extra === null) return null;
    return {
      ...extra,
      endpoint: document.getElementById('skill-api-endpoint').value.trim(),
      method: document.getElementById('skill-api-method').value,
      api_key: document.getElementById('skill-api-key').value,
    };
  }
  if (type === 'mcp') {
    const legacy = parseSkillJson('skill-mcp-legacy', 'Dữ liệu cấu hình cũ');
    if (legacy === null) return null;
    const cfg = {
      ...legacy,
      target: document.getElementById('skill-mcp-target').value.trim(),
      transport: document.getElementById('skill-mcp-transport').value,
      token: document.getElementById('skill-mcp-token').value,
    };
    // null = chưa từng chọn -> lấy tất cả tool của server (tương thích ngược).
    // Mảng rỗng vẫn được lưu: đó là chủ ý "tắt hết tool của server này".
    if (Array.isArray(skillMcpSelectedTools)) cfg.tools = skillMcpSelectedTools;
    return cfg;
  }
  if (type === 'custom') {
    const custom = parseSkillJson('skill-config', 'Cấu hình Custom');
    if (custom === null) return null;
    delete custom.image_pool_id;
    return custom;
  }
  if (showErrors) showToast('Hãy chọn một loại kết nối', 'error');
  return null;
}

function populateSkillConfig(type, config) {
  resetSkillConfigFields();
  const cfg = config && typeof config === 'object' && !Array.isArray(config) ? config : {};
  if (type === 'builtin') {
    const selectedTool = cfg.tool_name || cfg.builtin_name || '';
    renderBuiltinToolOptions(selectedTool);
    const legacy = { ...cfg }; delete legacy.tool_name; delete legacy.builtin_name;
    if (Object.keys(legacy).length) {
      document.getElementById('skill-builtin-legacy').value = JSON.stringify(legacy, null, 2);
      document.getElementById('skill-builtin-legacy-wrap').style.display = '';
    }
  } else if (type === 'api') {
    document.getElementById('skill-api-endpoint').value = cfg.endpoint || '';
    document.getElementById('skill-api-method').value = ['GET','POST','PUT','PATCH','DELETE'].includes(String(cfg.method).toUpperCase()) ? String(cfg.method).toUpperCase() : 'GET';
    document.getElementById('skill-api-key').value = cfg.api_key || '';
    const extra = { ...cfg }; delete extra.endpoint; delete extra.method; delete extra.api_key;
    document.getElementById('skill-api-extra').value = JSON.stringify(extra, null, 2);
  } else if (type === 'mcp') {
    document.getElementById('skill-mcp-target').value = cfg.target || '';
    document.getElementById('skill-mcp-transport').value = ['stdio','http','sse'].includes(cfg.transport) ? cfg.transport : 'stdio';
    document.getElementById('skill-mcp-token').value = cfg.token || '';
    skillMcpSelectedTools = Array.isArray(cfg.tools) ? cfg.tools.slice() : null;
    const legacy = { ...cfg }; delete legacy.target; delete legacy.transport; delete legacy.token; delete legacy.tools;
    if (Object.keys(legacy).length) {
      document.getElementById('skill-mcp-legacy').value = JSON.stringify(legacy, null, 2);
      document.getElementById('skill-mcp-legacy-wrap').style.display = '';
    }
  } else {
    document.getElementById('skill-config').value = JSON.stringify(config ?? {}, null, 2);
    updateSkillImagePoolField(cfg);
  }
}

function renderSkillReview() {
  const type = document.getElementById('skill-type').value;
  const config = buildSkillConfig(type, false);
  const item = (label, value) => `<div class="skill-review-item"><div class="skill-review-label">${esc(label)}</div><div class="skill-review-value">${esc(value || 'Chưa thiết lập')}</div></div>`;
  document.getElementById('skill-review-summary').innerHTML = [
    item('Tên kỹ năng', document.getElementById('skill-name').value.trim()),
    item('Mô tả', document.getElementById('skill-description').value.trim()),
    item('Loại kết nối', SKILL_TYPE_LABELS[type] || 'Chưa chọn'),
    item('Cấu hình', config ? JSON.stringify(config, null, 2) : 'JSON chưa hợp lệ'),
  ].join('');
}

function goSkillWizardStep(step, force = false) {
  step = Math.max(1, Math.min(3, step));
  const editing = Boolean(document.getElementById('skill-id').value);
  if (!force && !editing && step > skillWizardMaxStep + 1) return;
  if (step === 3) renderSkillReview();
  skillWizardStep = step;
  skillWizardMaxStep = Math.max(skillWizardMaxStep, step);
  document.querySelectorAll('.skill-wizard-step').forEach(el => el.classList.toggle('active', Number(el.dataset.skillStep) === step));
  document.querySelectorAll('.skill-wizard-tab').forEach((el, i) => {
    el.classList.toggle('active', i + 1 === step);
    el.classList.toggle('done', i + 1 < step);
  });
  document.getElementById('skill-wizard-back').style.visibility = step === 1 ? 'hidden' : 'visible';
  document.getElementById('skill-wizard-next').style.display = step === 3 ? 'none' : '';
  document.getElementById('skill-wizard-save').style.display = step === 3 ? '' : 'none';
}

function changeSkillWizardStep(delta) {
  if (delta > 0 && skillWizardStep === 1 && !document.getElementById('skill-name').value.trim()) return showToast('Tên kỹ năng là bắt buộc', 'error');
  if (delta > 0 && skillWizardStep === 2 && !document.getElementById('skill-type').value) {
    document.getElementById('skill-type-required').style.display = '';
    return showToast('Hãy chọn một loại kết nối', 'error');
  }
  goSkillWizardStep(skillWizardStep + delta, true);
}

function selectSkill(id) {
  selectedSkillId = id;
  renderSkillList();
  const s = skills.find(x => x.id === id);
  if (!s) return;
  _clearSkillFilePreview();
  document.getElementById('skill-wizard-layer').style.display = 'flex';
  document.getElementById('skill-form-container').style.display = 'flex';
  document.getElementById('skill-form-title').textContent = s.name;
  document.getElementById('skill-delete-btn').style.display = '';
  document.getElementById('skill-id').value = s.id;
  document.getElementById('skill-name').value = s.name;
  document.getElementById('skill-description').value = s.description || '';
  chooseSkillType(Object.hasOwn(SKILL_TYPE_LABELS, s.type) ? s.type : 'custom');
  populateSkillConfig(Object.hasOwn(SKILL_TYPE_LABELS, s.type) ? s.type : 'custom', s.config);
  skillWizardMaxStep = 3;
  goSkillWizardStep(1, true);
}

function newSkill() {
  selectedSkillId = null;
  renderSkillList();
  _clearSkillFilePreview();
  document.getElementById('skill-wizard-layer').style.display = 'flex';
  document.getElementById('skill-form-container').style.display = 'flex';
  document.getElementById('skill-form-title').textContent = t('js.new_skill');
  document.getElementById('skill-delete-btn').style.display = 'none';
  document.getElementById('skill-id').value = '';
  document.getElementById('skill-name').value = '';
  document.getElementById('skill-description').value = '';
  document.getElementById('skill-type').value = '';
  resetSkillConfigFields();
  // Chưa chọn loại kết nối thì chưa có gì để thử. chooseSkillType() sẽ bật lại
  // khi người dùng chọn api/mcp.
  document.getElementById('skill-conn-test').style.display = 'none';
  clearSkillConnResult();
  skillMcpSelectedTools = null;   // skill mới: chưa chọn gì -> mặc định bật hết sau khi test
  mcpAvailableTools = [];
  document.querySelectorAll('.skill-type-option').forEach(el => el.classList.remove('selected'));
  document.querySelectorAll('.skill-config-panel').forEach(el => el.classList.remove('active'));
  skillWizardMaxStep = 1;
  goSkillWizardStep(1, true);
}

function cancelSkillForm() {
  selectedSkillId = null;
  document.getElementById('skill-form-container').style.display = 'none';
  document.getElementById('skill-wizard-layer').style.display = 'none';
  renderSkillList();
}

async function saveSkill() {
  const id = document.getElementById('skill-id').value;
  const type = document.getElementById('skill-type').value;
  if (!type) return showToast('Hãy chọn một loại kết nối', 'error');
  const config = buildSkillConfig(type);
  if (config === null) return;
  const body = {
    name: document.getElementById('skill-name').value.trim(),
    description: document.getElementById('skill-description').value.trim(),
    type,
    config,
  };
  if (!body.name) return showToast('Name is required', 'error');
  try {
    if (id) { await api('PATCH', `/skills/${id}`, body); }
    else { await api('POST', '/skills/', body); }
    await loadSkills();
    cancelSkillForm();
    renderAgentSkillsSelect();
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

async function deleteSkill() {
  const id = document.getElementById('skill-id').value;
  if (!id) return;
  if (!(await showConfirm('Delete this skill?'))) return;
  await api('DELETE', `/skills/${id}`);
  await loadSkills();
  cancelSkillForm();
}

// ════════════════════════════════════════
// PROJECTS / KANBAN
// ════════════════════════════════════════
async function loadProjects() {
  const data = await api('GET', '/projects/');
  projects = data.projects || [];
  renderProjectGrid();
  if (meetings.length) renderMeetingList();
}

function renderProjectGrid() {
  const grid = document.getElementById('proj-grid');
  if (!grid) return;
  const q = (document.getElementById('proj-search')?.value || '').toLowerCase();
  const list = q ? projects.filter(p => p.name.toLowerCase().includes(q) || (p.description||'').toLowerCase().includes(q)) : projects;
  if (!list.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state-icon">${icon('folder')}</div><div class="empty-state-text">${q ? 'Không tìm thấy dự án nào.' : 'Chưa có dự án nào. Tạo dự án đầu tiên!'}</div></div>`;
    return;
  }
  grid.innerHTML = list.map(p => `
    <div class="proj-card" onclick="openProjectDetail(${p.id})">
      <div class="proj-card-name">${esc(p.name)}</div>
      <div class="proj-card-desc">${esc(p.description || '')}</div>
      <div class="proj-card-stats">
        <span class="proj-stat"><b id="ps-items-${p.id}">—</b> công việc</span>
        <span class="proj-stat"><b id="ps-runs-${p.id}">—</b> lượt chạy</span>
      </div>
    </div>`).join('');
  list.forEach(p => _loadProjCardStats(p.id));
}

function filterProjectGrid() { renderProjectGrid(); }

async function _loadProjCardStats(pid) {
  try {
    const [items, runs] = await Promise.all([
      api('GET', `/projects/${pid}/items`),
      api('GET', `/workflow/runs?project_id=${pid}&limit=100`),
    ]);
    const ie = document.getElementById(`ps-items-${pid}`);
    const re = document.getElementById(`ps-runs-${pid}`);
    if (ie) ie.textContent = (items.items||[]).length;
    if (re) re.textContent = (runs.runs||[]).length;
  } catch {}
}

async function openProjectDetail(pid) {
  currentProjectId = pid;
  const proj = projects.find(p => p.id === pid);
  document.getElementById('proj-grid-view').style.display = 'none';
  document.getElementById('proj-detail-view').style.display = 'flex';
  document.getElementById('proj-detail-name').textContent = proj?.name || '';
  document.getElementById('proj-detail-desc').textContent = proj?.description || '';
  switchProjectSubTab('overview');
}

function closeProjectDetail() {
  currentProjectId = null;
  document.getElementById('proj-detail-view').style.display = 'none';
  document.getElementById('proj-grid-view').style.display = '';
}

async function switchProjectSubTab(tab) {
  currentProjectSubTab = tab;
  document.querySelectorAll('.proj-subtab').forEach(b => b.classList.toggle('active', b.dataset.subtab === tab));
  document.querySelectorAll('.proj-subtab-panel').forEach(p => p.classList.toggle('active', p.id === 'proj-panel-' + tab));
  await opsRenderSubTab(tab);
}

// ════════════════════════════════════════
// AI COMPANY PROJECT OPERATIONS DASHBOARD
// Một công ty có nhiều dự án; mỗi dự án có nhiều quy trình (workflow); mỗi quy trình
// tạo ra các đầu ra (output) khác nhau. Xanax đóng vai trò giám sát/điều phối, còn
// nhân viên AI (cấu hình ở tab Nhân sự) thực thi theo vai trò đã chọn khi dựng quy
// trình. CEO xem xét & duyệt đầu ra trước khi chuyển sang quy trình/hàng đợi kế tiếp.
// Dữ liệu lấy từ API thật /api/ops/* (xem api/routes/ops.py) — mỗi "item" ứng với
// 1 workflow_outputs thật, opsRuns/opsHistory chỉ là cache phía client cho lần render hiện tại.
// ════════════════════════════════════════
const OPS_STATUS = {
  pending:        { label: 'Chờ xử lý',      color: 'var(--muted)', bg: 'rgba(100,116,139,0.15)' },
  in_progress:    { label: 'Đang thực hiện', color: 'var(--blue)',  bg: 'rgba(var(--blue-rgb),0.15)'  },
  waiting_review: { label: 'Chờ CEO duyệt',  color: 'var(--amber)', bg: 'rgba(var(--amber-rgb),0.15)'  },
  needs_revision: { label: 'Cần chỉnh sửa',  color: '#f97316',      bg: 'rgba(249,115,22,0.15)'  },
  approved:       { label: 'Đã duyệt',       color: 'var(--cyan)',  bg: 'rgba(var(--cyan-rgb),0.15)'   },
  completed:      { label: 'Hoàn thành',     color: 'var(--green)', bg: 'rgba(var(--green-rgb),0.15)'   },
  failed:         { label: 'Thất bại',       color: 'var(--red)',   bg: 'rgba(var(--red-rgb),0.15)'   },
  test:           { label: 'Thử luồng',      color: 'var(--purple)', bg: 'rgba(var(--purple-rgb),0.15)' },
};
const OPS_KANBAN_COLS = ['pending', 'in_progress', 'waiting_review', 'needs_revision', 'approved', 'completed', 'failed', 'test'];
const OPS_OUTPUT_TYPES = { text: 'Văn bản', image: 'Hình ảnh', code: 'Code', report: 'Báo cáo' };
const OPS_PRIORITY_BADGE = { low: 'badge-muted', medium: 'badge-blue', high: 'badge-amber' };
function opsHistoryIcon(type) {
  const map = { run_completed: 'check', run_failed: 'close', run_started: 'bolt', approved: 'check', rejected: 'close', revision_requested: 'edit', queue_transition: 'sync' };
  return icon(map[type] || 'clock');
}

let opsRuns = [];
let opsHistory = [];
let opsFeedbackCtx = null; // { runId, action, isTest } đang chờ CEO nhập phản hồi trong modal

// SQLite lưu datetime dạng UTC "YYYY-MM-DD HH:MM:SS" (không có 'Z') — chuyển sang
// ISO trước khi parse để Date hiểu đúng là giờ UTC thay vì giờ local.
function opsFmtTime(ts) { return ts ? new Date(ts.replace(' ', 'T') + 'Z').toLocaleString('vi-VN') : '—'; }
function opsTimeValue(ts) { return ts ? Date.parse(ts.replace(' ', 'T') + 'Z') || 0 : 0; }
function opsProjectRuns(pid) { return opsRuns.filter(r => r.projectId === pid); }
function opsAgentSummary(r) {
  if (!r.agentCount) return 'Chưa có bước AI';
  if (r.agentCount === 1) return r.agentName || 'Nhân viên AI';
  return `${r.agentCount} nhân viên AI`;
}
function opsAgentListText(r) {
  const names = (r.agents || []).map(a => a.agentName).filter(Boolean);
  if (!names.length) return 'Chưa có bước AI';
  return names.join(', ');
}
function opsAgentDisplayHtml(r, opts = {}) {
  const label = esc(opsAgentSummary(r));
  const title = esc(opsAgentListText(r));
  if (!r.agentCount) return `<span title="${title}">${label}</span>`;
  if (r.agentCount > 1) return `<span title="${title}">${label}</span>`;
  const avatar = avatarHtml(r.agentColor || DEFAULT_AVATAR, r.agentName, 'avatar-sm');
  const dept = agentDeptBadgeHtml(agents.find(a => a.name === r.agentName));
  return `<span title="${title}" style="display:inline-flex;align-items:center;gap:6px;vertical-align:middle;">${avatar}<span>${label}</span>${dept}</span>`;
}

async function opsLoad(pid) {
  const [itemsData, historyData] = await Promise.all([
    api('GET', `/ops/items?project_id=${pid}`),
    api('GET', `/ops/history?project_id=${pid}`),
  ]);
  opsRuns = itemsData.items || [];
  opsHistory = historyData.history || [];
}

// Điểm điều phối chung: nạp lại dữ liệu thật từ server rồi render đúng sub-tab đang active.
async function opsRenderSubTab(tab) {
  if (!currentProjectId) return;
  try {
    await opsLoad(currentProjectId);
  } catch (e) {
    showToast('Không tải được dữ liệu vận hành dự án: ' + e.message, 'error');
    return;
  }
  opsUpdateReviewBadge(currentProjectId);
  if (tab === 'overview') renderOpsOverview(currentProjectId);
  else if (tab === 'runs') renderOpsRuns(currentProjectId);
  else if (tab === 'review') renderOpsReview(currentProjectId);
  else if (tab === 'kanban') renderOpsKanban(currentProjectId);
  else if (tab === 'history') renderOpsHistory(currentProjectId);
}

function opsUpdateReviewBadge(pid) {
  const n = opsProjectRuns(pid).filter(r => r.status === 'waiting_review').length;
  const b = document.getElementById('ops-review-count');
  if (!b) return;
  if (n > 0) { b.textContent = n; b.style.display = 'inline-flex'; } else { b.style.display = 'none'; }
}

// ── Tổng quan ──
function renderOpsOverview(pid) {
  const el = document.getElementById('ops-overview-area');
  if (!el) return;
  const proj = projects.find(p => p.id === pid);
  const runs = opsProjectRuns(pid);
  const workflows = [...new Set(runs.map(r => r.workflowName))];
  const active = runs.filter(r => r.status === 'in_progress').length;
  const pendingApproval = runs.filter(r => r.status === 'waiting_review').length;
  const completed = runs.filter(r => r.status === 'completed').length;
  const failed = runs.filter(r => r.status === 'failed').length;
  const needsRevision = runs.filter(r => r.status === 'needs_revision').length;
  const readyRuns = runs.filter(r => r.readyForNext);
  const nextAction = pendingApproval > 0
    ? `Duyệt ${pendingApproval} kết quả đang chờ ở Hàng chờ duyệt`
    : needsRevision > 0
    ? `Theo dõi ${needsRevision} kết quả đang chờ nhân viên AI chỉnh sửa lại`
    : readyRuns.length > 0
    ? `${readyRuns.length} kết quả đã sẵn sàng chuyển sang bước kế tiếp — chuyển tiếp giúp đội nhé`
    : 'Đội của bạn không có việc gì cần duyệt ngay lúc này — thảnh thơi chút đi';

  el.innerHTML = `
    <div class="ops-grid">
      <div class="ops-card ops-card-wide">
        <div class="ops-card-label">Mục tiêu dự án</div>
        <div style="font-size:14px;font-weight:500;">${esc(proj?.description || 'Chưa có mô tả mục tiêu.')}</div>
        <div style="margin-top:10px;"><span class="badge ${proj ? 'badge-green' : 'badge-muted'}">${proj ? '<span class="sdot on" style="margin-right:5px;"></span>Đang hoạt động' : '—'}</span></div>
      </div>
      <div class="ops-card ops-card-wide" style="border-color:rgba(var(--amber-rgb),0.35);">
        <div class="ops-card-label">Việc bạn cần làm tiếp theo</div>
        <div style="font-size:13px;font-weight:600;margin-top:4px;">${esc(nextAction)}</div>
        ${pendingApproval > 0 ? `<button class="btn btn-primary btn-sm" style="margin-top:8px;" onclick="switchProjectSubTab('review')">Đến Hàng chờ duyệt →</button>` : ''}
      </div>
      <div class="ops-card"><div class="ops-card-label">Quy trình</div><div class="ops-card-value">${workflows.length}</div></div>
      <div class="ops-card"><div class="ops-card-label">Đang thực hiện</div><div class="ops-card-value" style="color:var(--blue)">${active}</div></div>
      <div class="ops-card"><div class="ops-card-label">Chờ CEO duyệt</div><div class="ops-card-value" style="color:var(--amber)">${pendingApproval}</div></div>
      <div class="ops-card">
        <div class="ops-card-label">Hoàn thành / Thất bại</div>
        <div class="ops-card-value"><span style="color:var(--green)">${completed}</span><span style="color:var(--muted);font-size:14px;"> / </span><span style="color:var(--red)">${failed}</span></div>
      </div>
      <div class="ops-card ops-card-wide ops-xanax-card">
        <div style="display:flex;align-items:center;gap:10px;">
          <div class="avatar" style="background:var(--gold-soft);color:var(--gold);">${icon('bot')}</div>
          <div>
            <div style="font-weight:700;font-size:14px;">Xanax — Giám sát &amp; Điều phối</div>
            <div style="font-size:11px;color:var(--muted);">Theo dõi toàn bộ quy trình, điều phối nhân viên AI theo vai trò đã cấu hình ở tab Nhân sự, chờ CEO duyệt trước khi chuyển bước tiếp theo.</div>
          </div>
        </div>
        <div style="display:flex;gap:18px;margin-top:12px;font-size:12px;color:var(--text);">
          <span>${icon('sync')} ${runs.length} lượt chạy</span>
          <span>${icon('people')} ${new Set(runs.flatMap(r => (r.agents || []).map(a => a.agentId || a.agentName))).size} nhân viên AI tham gia</span>
          <span>⏳ ${pendingApproval} chờ duyệt</span>
        </div>
      </div>
    </div>`;
}

// ── Lượt chạy ──
function renderOpsRuns(pid) {
  const tbody = document.getElementById('ops-runs-tbody');
  if (!tbody) return;
  const runs = opsProjectRuns(pid).slice().sort((a, b) => opsTimeValue(b.startedAt || b.finishedAt) - opsTimeValue(a.startedAt || a.finishedAt));
  if (!runs.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:30px;">Chưa có lượt chạy nào</td></tr>`;
    return;
  }
  tbody.innerHTML = runs.map(r => {
    const st = OPS_STATUS[r.status];
    return `<tr>
      <td>${esc(r.workflowName)}</td>
      <td>${OPS_OUTPUT_TYPES[r.outputType] || r.outputType}</td>
      <td>${opsAgentDisplayHtml(r, { withName: true })}</td>
      <td><span class="badge" style="background:${st.bg};color:${st.color};">${st.label}</span></td>
      <td style="font-size:11px;color:var(--muted);">${opsFmtTime(r.startedAt)}</td>
      <td style="font-size:11px;color:var(--muted);">${opsFmtTime(r.finishedAt)}</td>
      <td style="max-width:220px;font-size:12px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(r.summary)}</td>
      <td><button class="btn btn-ghost btn-sm" onclick="openOpsDetails(${r.id})">Xem</button></td>
    </tr>`;
  }).join('');
}

// ── Hàng chờ duyệt (CEO review) ──
function renderOpsReview(pid) {
  const el = document.getElementById('ops-review-list');
  if (!el) return;
  const items = opsProjectRuns(pid).filter(r => r.status === 'waiting_review').sort((a, b) => opsTimeValue(a.startedAt) - opsTimeValue(b.startedAt));
  if (!items.length) {
    el.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('check')}</div><div class="empty-state-text">Không có kết quả nào đang chờ duyệt</div></div>`;
    return;
  }
  el.innerHTML = items.map(r => `
    <div class="ops-review-card">
      <div class="ops-review-card-head">
        <div>
          <div style="font-weight:600;font-size:13px;">${esc(r.workflowName)} <span style="color:var(--muted);font-weight:400;">· ${OPS_OUTPUT_TYPES[r.outputType] || r.outputType}</span></div>
          <div style="font-size:11px;color:var(--muted);margin-top:2px;display:flex;align-items:center;gap:5px;">
            ${opsAgentDisplayHtml(r)} <span>· ${opsFmtTime(r.startedAt)}</span>
          </div>
        </div>
        <span class="badge ${OPS_PRIORITY_BADGE[r.priority] || 'badge-muted'}">${esc(r.priority)}</span>
      </div>
      <div class="ops-review-card-summary">${esc(r.summary)}</div>
      <div class="ops-review-card-actions">
        <button class="btn btn-sm btn-pass" onclick="opsApprove(${r.id})">${icon('check')} Duyệt</button>
        <button class="btn btn-sm btn-fail" onclick="opsOpenFeedback(${r.id},'failed')">${icon('close')} Không đạt</button>
        <button class="btn btn-sm btn-ghost" onclick="opsOpenFeedback(${r.id},'needs_revision')">${icon('edit')} Yêu cầu sửa</button>
        <button class="btn btn-sm ops-btn-test" onclick="opsApprove(${r.id}, true)" title="Chỉ thử luồng quy trình — không ghi lịch sử/bộ nhớ Xanax">${icon('flask')} Thử luồng</button>
        <button class="btn btn-sm btn-ghost" onclick="openOpsDetails(${r.id})">Chi tiết</button>
      </div>
    </div>`).join('');
}

// isTest: true khi bấm nút "Thử luồng" kế bên Duyệt/Không đạt — chỉ để CEO thử luồng
// quy trình, KHÔNG phải quyết định duyệt thật nên server chuyển item sang trạng thái
// riêng "test" (khác Đã duyệt/Chờ xử lý), vẫn hiển thị bình thường trên Kanban/Runs,
// chỉ ra khỏi hàng chờ duyệt vì đã được xử lý. Không ghi lịch sử/bộ nhớ Xanax.
async function opsApprove(runId, isTest) {
  try {
    await api('POST', `/ops/items/${runId}/approve`, { is_test: !!isTest });
    await opsRenderSubTab(currentProjectSubTab);
    showToast(isTest ? 'Đã chuyển sang chế độ thử luồng.' : 'Đã duyệt kết quả.', 'success');
  } catch (e) { showToast('Lỗi: ' + e.message, 'error'); }
}

function opsOpenFeedback(runId, action, isTest) {
  const r = opsRuns.find(x => x.id === runId);
  if (!r) return;
  opsFeedbackCtx = { runId, action, isTest: !!isTest };
  document.getElementById('ops-feedback-title').textContent = action === 'failed' ? 'Đánh dấu Không đạt' : 'Yêu cầu chỉnh sửa';
  document.getElementById('ops-feedback-run-name').textContent = `${r.workflowName} · ${opsAgentSummary(r)}` + (isTest ? ' · chế độ thử luồng' : '');
  document.getElementById('ops-feedback-text').value = '';
  document.getElementById('ops-feedback-modal').classList.remove('hidden');
}

async function opsSaveFeedback() {
  if (!opsFeedbackCtx) return;
  const { runId, action, isTest } = opsFeedbackCtx;
  const text = document.getElementById('ops-feedback-text').value.trim();
  if (!text) { showToast('Vui lòng nhập phản hồi cho nhân viên AI.', 'error'); return; }
  try {
    await api('POST', `/ops/items/${runId}/feedback`, { action, text, is_test: !!isTest });
    document.getElementById('ops-feedback-modal').classList.add('hidden');
    opsFeedbackCtx = null;
    await opsRenderSubTab(currentProjectSubTab);
    showToast(isTest ? 'Đã chuyển sang chế độ thử luồng.' : 'Đã lưu phản hồi.', 'success');
  } catch (e) { showToast('Lỗi: ' + e.message, 'error'); }
}

// ── Chi tiết 1 lượt chạy ──
async function openOpsDetails(runId) {
  const r = opsRuns.find(x => x.id === runId);
  if (!r) return;
  const st = OPS_STATUS[r.status];
  document.getElementById('ops-details-title').textContent = r.workflowName;
  document.getElementById('ops-details-body').innerHTML = `<div style="color:var(--muted);font-size:12px;">Đang tải chi tiết lượt chạy...</div>`;
  document.getElementById('ops-details-modal').classList.remove('hidden');
  try {
    const run = await api('GET', `/workflow/runs/${runId}`);
    const outputs = run.outputs || [];
    const stepHtml = outputs.length
      ? outputs.map(o => `
        <div style="border:1px solid var(--border);border-radius: 0;padding:10px 12px;background:var(--bg3);margin-top:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">
            <div style="display:flex;align-items:center;gap:6px;">
              ${avatarHtml(agentById(o.agent_id)?.avatar_color || r.agentColor || DEFAULT_AVATAR, o.agent_name || 'Nhân viên AI', 'avatar-sm')}
              <span style="font-size:13px;font-weight:600;">Bước ${o.step_order || 0} · ${esc(o.agent_name || 'Nhân viên AI')}${agentDeptSuffix(agentById(o.agent_id))}</span>
            </div>
            <span style="font-size:11px;color:var(--muted);">${opsFmtTime(o.finished_at || o.created_at)}</span>
          </div>
          <div class="output-content">${renderOutputContent(o.edited_content || o.output_content) || '(chưa có nội dung)'}</div>
        </div>`).join('')
      : `<div class="output-content">${renderOutputContent(r.outputPreview)}</div>`;

    document.getElementById('ops-details-body').innerHTML = `
      <div class="form-group"><label class="form-label">Nhân viên AI tham gia</label>
        <div style="font-size:13px;">${esc(opsAgentListText(r))}</div>
      </div>
      <div class="form-group"><label class="form-label">Trạng thái</label>
        <span class="badge" style="background:${st.bg};color:${st.color};">${st.label}</span>
        ${r.readyForNext ? `<span class="badge badge-green" style="margin-left:6px;">${icon('arrowRight')} Sẵn sàng bước kế tiếp</span>` : ''}
      </div>
      <div class="form-group"><label class="form-label">Loại đầu ra</label><div>${OPS_OUTPUT_TYPES[r.outputType] || r.outputType}</div></div>
      <div class="form-group"><label class="form-label">Số bước AI</label><div>${outputs.length || r.outputCount || 0}</div></div>
      <div class="form-group"><label class="form-label">Thời gian</label>
        <div style="font-size:12px;color:var(--muted);">Bắt đầu: ${opsFmtTime(r.startedAt)} · Kết thúc: ${opsFmtTime(r.finishedAt)}</div>
      </div>
      <div class="form-group"><label class="form-label">Tóm tắt</label><div style="font-size:13px;">${esc(r.summary)}</div></div>
      <div class="form-group"><label class="form-label">Chi tiết từng bước</label>${stepHtml}</div>
      ${r.feedback ? `<div class="form-group"><label class="form-label">Phản hồi CEO</label><div style="font-size:13px;color:var(--amber);">${esc(r.feedback)}</div></div>` : ''}
    `;
  } catch (e) {
    document.getElementById('ops-details-body').innerHTML = `<div style="color:var(--red);font-size:12px;">Không tải được chi tiết: ${esc(e.message || 'Lỗi không xác định')}</div>`;
  }
}

// ── Kanban (theo trạng thái lượt chạy) ──
function renderOpsKanban(pid) {
  const board = document.getElementById('ops-kanban-board');
  if (!board) return;
  const runs = opsProjectRuns(pid);
  board.innerHTML = OPS_KANBAN_COLS.map(status => {
    const colRuns = runs.filter(r => r.status === status);
    const st = OPS_STATUS[status];
    return `
      <div class="kanban-col">
        <div class="kanban-col-header">
          <span class="kanban-col-title" style="color:${st.color};">${st.label}</span>
          <span class="kanban-col-count">${colRuns.length}</span>
        </div>
        <div class="kanban-cards" id="ops-col-${status}" ondragover="opsColDragOver(event)" ondragleave="opsColDragLeave(event)" ondrop="opsColDrop(event,'${status}')">
          ${colRuns.map(r => opsRenderKanbanCard(r)).join('')}
        </div>
      </div>`;
  }).join('');
}

function opsRenderKanbanCard(r) {
  const priClass = OPS_PRIORITY_BADGE[r.priority] || 'badge-muted';
  const shortSummary = r.summary.length > 60 ? r.summary.slice(0, 60) + '…' : r.summary;
  const quick = r.status === 'waiting_review' ? `
      <div class="kanban-card-meta" style="margin-top:6px;">
        <button class="btn btn-sm btn-pass" onclick="event.stopPropagation();opsApprove(${r.id})">${icon('check')} Duyệt</button>
        <button class="btn btn-sm btn-fail" onclick="event.stopPropagation();opsOpenFeedback(${r.id},'failed')" title="Không đạt">${icon('close')}</button>
        <button class="btn btn-sm ops-btn-test" onclick="event.stopPropagation();opsApprove(${r.id}, true)" title="Chỉ thử luồng quy trình — không ghi lịch sử/bộ nhớ Xanax">${icon('flask')} Thử luồng</button>
      </div>` : '';
  const readyBadge = r.readyForNext
    ? `<span class="badge badge-green" title="Sẵn sàng chuyển sang quy trình/bước kế tiếp">${icon('arrowRight')} Sẵn sàng bước kế tiếp</span>` : '';
  return `
    <div class="kanban-card" draggable="true" ondragstart="opsCardDragStart(event,${r.id})" onclick="openOpsDetails(${r.id})">
      <div class="kanban-card-title">${esc(r.workflowName)}</div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px;">${OPS_OUTPUT_TYPES[r.outputType] || r.outputType} · ${esc(shortSummary)}</div>
      <div class="kanban-card-meta">
        <span class="badge ${priClass}">${esc(r.priority)}</span>
        <span style="font-size:11px;color:var(--muted);">${opsAgentDisplayHtml(r)}</span>
        ${readyBadge}
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:6px;">${opsFmtTime(r.startedAt)}</div>
      ${quick}
    </div>`;
}

function opsCardDragStart(e, runId) {
  e.dataTransfer.setData('text/plain', String(runId));
  e.dataTransfer.effectAllowed = 'move';
}
function opsColDragOver(e) { e.preventDefault(); e.currentTarget.classList.add('drag-over'); }
function opsColDragLeave(e) { e.currentTarget.classList.remove('drag-over'); }
function opsColDrop(e, status) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const runId = e.dataTransfer.getData('text/plain');
  opsMoveRun(runId, status);
}

// Kéo-thả đổi cột = gọi API thật cập nhật review_status (PATCH /ops/items/{id}).
// Kéo vào "waiting_review" sẽ tự xuất hiện ở tab Hàng chờ duyệt vì cùng đọc từ /ops/items.
async function opsMoveRun(runId, status) {
  const id = Number(runId);
  const r = opsRuns.find(x => x.id === id);
  if (!r || r.status === status) return;
  try {
    await api('PATCH', `/ops/items/${id}`, { status });
    await opsRenderSubTab(currentProjectSubTab);
  } catch (e) { showToast('Lỗi: ' + e.message, 'error'); }
}

// ── Lịch sử ──
function renderOpsHistory(pid) {
  const el = document.getElementById('ops-history-area');
  if (!el) return;
  const items = opsHistory.filter(h => opsRuns.find(r => r.id === h.runId)?.projectId === pid);
  if (!items.length) {
    el.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('clock')}</div><div class="empty-state-text">Chưa có lịch sử nào</div></div>`;
    return;
  }
  el.innerHTML = items.map(h => `
    <div class="history-row">
      <span>${opsHistoryIcon(h.type)}</span>
      <span style="flex:1;font-size:13px;">${esc(h.text)}</span>
      <span style="font-size:11px;color:var(--muted);">${opsFmtTime(h.ts)}</span>
    </div>`).join('');
}

// Gom kết quả hoàn thành/thất bại + phản hồi CEO thành dữ liệu học cho Xanax —
// archivePayload đã được server chuẩn bị sẵn (xem api/routes/ops.py _archive_payload),
// hàm này chỉ gom lại phía client để chuẩn bị gọi API ghi vào SOUL.md sau này.
function opsBuildLearningMemoryEntries(pid) {
  return opsProjectRuns(pid)
    .filter(r => r.archivePayload || r.feedback)
    .map(r => r.archivePayload || {
      workflow: r.workflowName, agent: opsAgentSummary(r), status: r.status,
      summary: r.summary, feedback: r.feedback, finishedAt: r.finishedAt,
    });
}

// ════════════════════════════════════════
// KNOWLEDGE DOCUMENTS (RAG "phòng tư liệu")
// ════════════════════════════════════════
let knowledgeDocs = [];

async function loadKnowledgeDocs(pid) {
  const el = document.getElementById('knowledge-list');
  if (!el) return;
  const data = await api('GET', `/knowledge?project_id=${pid}`).catch(() => ({ documents: [] }));
  knowledgeDocs = data.documents || [];
  if (!knowledgeDocs.length) {
    el.innerHTML = `<div class="empty-state" style="margin-top:40px;"><div class="empty-state-icon">${icon('book')}</div><div class="empty-state-text">Chưa có tài liệu nào cho dự án này</div></div>`;
    return;
  }
  el.innerHTML = knowledgeDocs.map(d => `
    <div style="border:1px solid var(--border);border-radius: 0;padding:12px 14px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
        <div style="font-weight:600;font-size:13px;">${esc(d.title)}</div>
        <div style="display:flex;gap:6px;flex-shrink:0;">
          <button class="btn btn-ghost btn-sm" onclick="openKnowledgeModal(${d.id})">Sửa</button>
          <button class="btn btn-danger btn-sm" onclick="deleteKnowledgeDoc(${d.id})">Xoá</button>
        </div>
      </div>
      ${d.tags ? `<div style="font-size:11px;color:var(--muted);margin-top:3px;">${icon('tag')} ${esc(d.tags)}</div>` : ''}
      <div style="font-size:12px;color:var(--muted);margin-top:6px;white-space:pre-wrap;max-height:80px;overflow:hidden;">${esc((d.content||'').slice(0,300))}</div>
    </div>`).join('');
}

function openKnowledgeModal(id) {
  const doc = id ? knowledgeDocs.find(d => d.id === id) : null;
  const title = prompt('Tiêu đề tài liệu:', doc?.title || '');
  if (title === null) return;
  if (!title.trim()) { showToast('Tiêu đề không được để trống', 'error'); return; }
  const tags = prompt('Tags (phân cách bởi dấu phẩy, tuỳ chọn):', doc?.tags || '') || '';
  const content = prompt('Nội dung tài liệu:', doc?.content || '');
  if (content === null) return;
  saveKnowledgeDoc(id, title.trim(), content, tags.trim());
}

async function saveKnowledgeDoc(id, title, content, tags) {
  const body = { title, content, tags, project_id: currentProjectId };
  if (id) await api('PATCH', `/knowledge/${id}`, body);
  else await api('POST', '/knowledge', body);
  await loadKnowledgeDocs(currentProjectId);
}

async function deleteKnowledgeDoc(id) {
  if (!(await showConfirm('Xoá tài liệu này?'))) return;
  await api('DELETE', `/knowledge/${id}`);
  await loadKnowledgeDocs(currentProjectId);
}

async function loadProject() {
  if (!currentProjectId) { renderKanban(null); return; }
  const [itemsData, alertsData] = await Promise.all([
    api('GET', `/projects/${currentProjectId}/items`),
    api('GET', '/projects/items/alerts').catch(() => ({ count: 0, alerts: [] })),
  ]);
  renderKanban(itemsData.items || []);
  updateAlertBanner(alertsData.count || 0);
}

async function loadProjectResults(pid) {
  const area = document.getElementById('proj-results-area');
  area.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:20px;">Đang tải...</div>';
  try {
    const data = await api('GET', `/workflow/runs?project_id=${pid}&limit=50`);
    const runs = (data.runs || []).filter(r => r.status !== 'running' && r.status !== 'pending');
    if (!runs.length) {
      area.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('chart')}</div><div class="empty-state-text">Chưa có kết quả nào cho dự án này</div></div>`;
      return;
    }
    area.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:8px 0 16px;">Đang tải chi tiết...</div>';
    const SC = {completed:'var(--green)',failed:'var(--red)',cancelled:'var(--muted)'};
    const SL = {completed:'Hoàn thành',failed:'Thất bại',cancelled:'Đã huỷ'};
    const groups = await Promise.all(runs.map(r => api('GET', `/workflow/runs/${r.id}`).catch(() => null)));
    area.innerHTML = '';
    for (const runData of groups) {
      if (!runData) continue;
      const outputs = runData.outputs || [];
      if (!outputs.length) continue;
      const sc = SC[runData.status] || 'var(--muted)';
      const sl = SL[runData.status] || runData.status;
      const time = runData.started_at ? new Date(runData.started_at + 'Z').toLocaleString('vi-VN') : '—';
      const g = document.createElement('div');
      g.className = 'run-group';
      g.innerHTML = `
        <div class="run-group-header">
          <span>${icon('sync')}</span>
          <span class="run-group-title">${esc(runData.task_name||'Quy trình')}</span>
          <span style="font-size:11px;color:${sc};">${sl}</span>
          <span style="font-size:11px;color:var(--muted);">${time}</span>
        </div>
        <div class="run-group-body">${outputs.map(o => renderOutputItem(o)).join('')}</div>`;
      area.appendChild(g);
    }
  } catch {
    area.innerHTML = '<div style="color:var(--red);font-size:12px;padding:20px;">Không tải được kết quả.</div>';
  }
}

function renderOutputItem(o) {
  const content = renderOutputContent(o.edited_content || o.output_content);
  const pf = o.pass_fail;
  const pfBadge = pf === 'pass'
    ? '<span class="badge" style="background:rgba(var(--green-rgb),0.15);color:var(--green);">' + icon('check') + ' Đạt</span>'
    : pf === 'fail'
    ? '<span class="badge" style="background:rgba(var(--red-rgb),0.15);color:var(--red);">' + icon('close') + ' Không đạt</span>'
    : '';
  return `<div class="output-item" id="oi-${o.id}">
    <div class="output-header">
      <span class="output-agent">Bước ${o.step_order} · ${esc(o.agent_name)}${agentDeptSuffix(agents.find(a => a.name === o.agent_name))}</span>
      ${pfBadge}
    </div>
    <div class="output-content" id="oc-${o.id}" contenteditable="false">${content}</div>
    <div class="output-actions">
      <button class="btn btn-sm btn-pass${pf==='pass'?' selected':''}" ${pf?'disabled':''} ${pf&&pf!=='pass'?'style="display:none"':''} onclick="setOutputPF(${o.id},'pass',this)">${icon('check')} Đạt</button>
      <button class="btn btn-sm btn-fail${pf==='fail'?' selected':''}" ${pf?'disabled':''} ${pf&&pf!=='fail'?'style="display:none"':''} onclick="setOutputPF(${o.id},'fail',this)">${icon('close')} Không đạt</button>
      <button class="btn btn-sm btn-ghost" onclick="toggleOutputEdit(${o.id},this)">${icon('edit')} Sửa</button>
      <button class="btn btn-sm btn-ghost" onclick="copyOutput(${o.id})" title="Sao chép">${icon('document')}</button>
    </div>
    <textarea class="output-notes" placeholder="Ghi chú / phản hồi..." onchange="saveOutputNotes(${o.id},this.value)">${esc(o.notes||'')}</textarea>
  </div>`;
}

async function setOutputPF(outputId, value, btn) {
  const newVal = btn.classList.contains('selected') ? null : value;
  await api('PATCH', `/workflow/outputs/${outputId}`, { pass_fail: newVal });
  loadProjectResults(currentProjectId);
}

function toggleOutputEdit(outputId, btn) {
  const el = document.getElementById('oc-' + outputId);
  if (el.contentEditable === 'true') {
    el.contentEditable = 'false';
    btn.innerHTML = icon('edit') + ' Sửa';
    api('PATCH', `/workflow/outputs/${outputId}`, { edited_content: el.textContent });
  } else {
    el.contentEditable = 'true';
    el.focus();
    btn.innerHTML = icon('save') + ' Lưu';
  }
}

function copyOutput(outputId) {
  navigator.clipboard.writeText(document.getElementById('oc-' + outputId)?.textContent || '');
}

async function saveOutputNotes(outputId, notes) {
  await api('PATCH', `/workflow/outputs/${outputId}`, { notes });
}

async function loadProjectHistory(pid) {
  const area = document.getElementById('proj-history-area');
  area.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:20px;">Đang tải...</div>';
  try {
    const data = await api('GET', `/workflow/runs?project_id=${pid}&limit=50`);
    const runs = data.runs || [];
    if (!runs.length) {
      area.innerHTML = `<div class="empty-state" style="margin-top:60px;"><div class="empty-state-icon">${icon('clock')}</div><div class="empty-state-text">Chưa có lịch sử chạy nào</div></div>`;
      return;
    }
    const SC = {completed:'var(--green)',failed:'var(--red)',running:'var(--cyan)',cancelled:'var(--muted)',pending:'var(--amber)'};
    const SL = {completed:'Hoàn thành',failed:'Thất bại',running:'Đang chạy',cancelled:'Đã huỷ',pending:'Chờ xử lý'};
    area.innerHTML = runs.map(r => {
      const sc = SC[r.status]||'var(--muted)', sl = SL[r.status]||r.status;
      const time = r.started_at ? new Date(r.started_at+'Z').toLocaleString('vi-VN') : '—';
      const trigger = r.triggered_by === 'scheduled' ? icon('clock') + ' Tự động' : icon('people') + ' Thủ công';
      return `<div class="history-row">
        <span>${icon('sync')}</span>
        <span style="flex:1;font-size:13px;font-weight:500;">${esc(r.task_name||'Quy trình')}</span>
        <span style="font-size:11px;color:${sc};">${sl}</span>
        <span style="font-size:11px;color:var(--muted);">${time}</span>
        <span style="font-size:11px;color:var(--muted);">${trigger}</span>
      </div>`;
    }).join('');
  } catch {
    area.innerHTML = '<div style="color:var(--red);font-size:12px;padding:20px;">Không tải được lịch sử.</div>';
  }
}

function renderKanban(items) {
  const board = document.getElementById('kanban-board');
  if (!items) {
    board.innerHTML = `<div class="empty-state" style="width:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;"><div class="empty-state-icon">${icon('document')}</div><div class="empty-state-text">${t('tasks.empty')}</div></div>`;
    return;
  }
  const cols = [
    { key: 'backlog',     label: t('col.backlog'),     color: 'var(--muted)' },
    { key: 'in_progress', label: t('col.in_progress'), color: 'var(--amber)' },
    { key: 'review',      label: t('col.review'),      color: 'var(--blue)' },
    { key: 'done',        label: t('col.done'),        color: 'var(--green)' },
  ];
  board.innerHTML = cols.map(col => {
    const colItems = items.filter(i => i.status === col.key);
    return `
      <div class="kanban-col">
        <div class="kanban-col-header">
          <span class="kanban-col-title" style="color:${col.color};">${col.label}</span>
          <span class="kanban-col-count">${colItems.length}</span>
        </div>
        <div class="kanban-cards" id="col-${col.key}">
          ${colItems.map(i => renderCard(i)).join('')}
        </div>
        <button class="kanban-add-btn" onclick="openCardModal(null, '${col.key}')">${t('tasks.add_item')}</button>
      </div>`;
  }).join('');
}

function renderCard(item) {
  const priClass = { low:'badge-muted', medium:'badge-blue', high:'badge-amber', critical:'badge-red' }[item.priority] || 'badge-muted';
  const assignedAgent = item.assigned_agent_id ? agentById(item.assigned_agent_id) : null;
  const agentHtml = item.agent_name
    ? `<span style="display:inline-flex;align-items:center;gap:4px;">${avatarHtml(item.agent_color || DEFAULT_AVATAR, item.agent_name, 'avatar-sm')}${agentDeptBadgeHtml(assignedAgent)}</span>`
    : '';
  const needsAssign = !item.assigned_agent_id && item.status !== 'done';
  const alertBadge = needsAssign
    ? `<span class="badge badge-amber" title="${t('tasks.unassigned_tip')}">${icon('warning')} ${t('tasks.unassigned')}</span>`
    : '';
  return `
    <div class="kanban-card${needsAssign ? ' kanban-card-unassigned' : ''}" onclick="openCardModal(${item.id})">
      <div class="kanban-card-title">${esc(item.title)}</div>
      <div class="kanban-card-meta">
        <span class="badge ${priClass}">${item.priority}</span>
        ${agentHtml}
        ${alertBadge}
      </div>
    </div>`;
}

function openProjectModal(editId) {
  document.getElementById('project-modal-title').textContent = editId ? t('modal.project.edit') : t('modal.project.new');
  document.getElementById('project-modal-id').value = editId || '';
  if (editId) {
    const p = projects.find(x => x.id === editId);
    document.getElementById('project-modal-name').value = p?.name || '';
    document.getElementById('project-modal-desc').value = p?.description || '';
  } else {
    document.getElementById('project-modal-name').value = '';
    document.getElementById('project-modal-desc').value = '';
  }
  document.getElementById('project-modal').classList.remove('hidden');
}

async function saveProject() {
  const id = document.getElementById('project-modal-id').value;
  const body = {
    name: document.getElementById('project-modal-name').value.trim(),
    description: document.getElementById('project-modal-desc').value.trim(),
  };
  if (!body.name) return showToast(t('js.project_required'), 'error');
  if (id) {
    await api('PATCH', `/projects/${id}`, body);
  } else {
    await api('POST', '/projects/', body);
  }
  await loadProjects();
  closeModal('project-modal');
  // Update detail header if still viewing that project
  if (id && currentProjectId == id) {
    document.getElementById('proj-detail-name').textContent = body.name;
    document.getElementById('proj-detail-desc').textContent = body.description;
  }
}

async function deleteProject() {
  if (!currentProjectId) return;
  if (!(await showConfirm(t('js.del_project')))) return;
  await api('DELETE', `/projects/${currentProjectId}`);
  await loadProjects();
  closeProjectDetail();
}

function renderCardAgentSelect() {
  const sel = document.getElementById('card-agent');
  sel.innerHTML = `<option value="">${t('js.unassigned')}</option>` +
    agents.map(a => `<option value="${a.id}">${esc(a.name)} — ${esc(a.role)}${agentDeptSuffix(a)}</option>`).join('');
}

function openCardModal(itemId, defaultStatus) {
  document.getElementById('card-modal-id').value = itemId || '';
  document.getElementById('card-modal-project').value = currentProjectId || '';
  document.getElementById('card-delete-btn').style.display = itemId ? '' : 'none';
  renderCardAgentSelect();
  clearMatchSection();
  if (itemId) {
    document.getElementById('card-modal-title').textContent = 'Edit Item';
    api('GET', `/projects/${currentProjectId}/items`).then(data => {
      const item = (data.items||[]).find(i => i.id === itemId);
      if (!item) return;
      document.getElementById('card-title').value = item.title;
      document.getElementById('card-desc').value = item.description;
      document.getElementById('card-status').value = item.status;
      document.getElementById('card-priority').value = item.priority;
      document.getElementById('card-agent').value = item.assigned_agent_id || '';
      if (!item.assigned_agent_id) runMatchPreview();
    });
  } else {
    document.getElementById('card-modal-title').textContent = 'New Item';
    document.getElementById('card-title').value = '';
    document.getElementById('card-desc').value = '';
    document.getElementById('card-status').value = defaultStatus || 'backlog';
    document.getElementById('card-priority').value = 'medium';
    document.getElementById('card-agent').value = '';
  }
  document.getElementById('card-modal').classList.remove('hidden');
}

async function saveCard() {
  const id = document.getElementById('card-modal-id').value;
  const pid = document.getElementById('card-modal-project').value;
  const body = {
    title: document.getElementById('card-title').value.trim(),
    description: document.getElementById('card-desc').value.trim(),
    status: document.getElementById('card-status').value,
    priority: document.getElementById('card-priority').value,
    assigned_agent_id: document.getElementById('card-agent').value ? parseInt(document.getElementById('card-agent').value) : null,
  };
  if (!body.title) return showToast('Title is required', 'error');
  if (id) { await api('PATCH', `/projects/items/${id}`, body); }
  else { await api('POST', `/projects/${pid}/items`, body); }
  closeModal('card-modal');
  clearMatchSection();
  await loadProject();
}

async function deleteCard() {
  const id = document.getElementById('card-modal-id').value;
  if (!id) return;
  if (!(await showConfirm('Delete this item?'))) return;
  await api('DELETE', `/projects/items/${id}`);
  closeModal('card-modal');
  clearMatchSection();
  await loadProject();
}

// ── Smart Matching ──────────────────────
let _matchDebounce = null;

function clearMatchSection() {
  document.getElementById('card-match-section').style.display = 'none';
  document.getElementById('card-match-list').innerHTML = '';
}

function runMatchPreview() {
  clearTimeout(_matchDebounce);
  _matchDebounce = setTimeout(async () => {
    const title = document.getElementById('card-title').value.trim();
    const desc  = document.getElementById('card-desc').value.trim();
    if (!title && !desc) { clearMatchSection(); return; }
    try {
      const result = await api('POST', '/projects/items/match', { title, description: desc });
      renderMatchSection(result);
    } catch (_) { clearMatchSection(); }
  }, 350);
}

function renderMatchSection(result) {
  const section = document.getElementById('card-match-section');
  const list    = document.getElementById('card-match-list');
  const suggestions = result?.suggestions || [];
  if (!suggestions.length) { clearMatchSection(); return; }
  list.innerHTML = suggestions.map(c => `
    <div class="match-candidate">
      ${avatarHtml(c.agent_avatar || DEFAULT_AVATAR, c.agent_name, 'avatar-sm')}
      <div class="match-candidate-info">
        <div class="match-candidate-name">${esc(c.agent_name)} <span style="color:var(--muted);font-size:11px;">— ${esc(c.agent_role)}${agentDeptSuffix(agentById(c.agent_id))}</span></div>
        <div class="match-candidate-reason">${esc(c.reason)}</div>
      </div>
      <div style="text-align:right;">
        <div class="match-score-bar"><div class="match-score-fill" style="width:${c.score}%;"></div></div>
        <div class="match-score-text">${Math.round(c.score)}</div>
      </div>
      <button class="btn btn-primary btn-sm" onclick="assignFromSuggestion(${c.agent_id}, '${esc(c.agent_name)}')" title="${t('tasks.assign_now')}">
        ${t('tasks.assign_now')}
      </button>
    </div>`).join('');
  section.style.display = '';
}

function assignFromSuggestion(agentId, agentName) {
  const sel = document.getElementById('card-agent');
  sel.value = agentId;
  if (!sel.value) {
    // agent not in list yet — add it
    const opt = document.createElement('option');
    opt.value = agentId; opt.textContent = agentName;
    sel.appendChild(opt);
    sel.value = agentId;
  }
  clearMatchSection();
}

function updateAlertBanner(count) {
  const banner = document.getElementById('alert-banner');
  const text   = document.getElementById('alert-banner-text');
  if (count > 0) {
    text.textContent = t('tasks.alert_banner', count);
    banner.style.display = 'flex';
  } else {
    banner.style.display = 'none';
  }
}

async function openAlertModal() {
  const data = await api('GET', '/projects/items/alerts').catch(() => ({ alerts: [] }));
  const alerts = data.alerts || [];
  const body = document.getElementById('alert-modal-body');
  if (!alerts.length) {
    body.innerHTML = `<div style="color:var(--muted);font-size:13px;text-align:center;padding:20px 0;">${t('tasks.no_alerts')}</div>`;
  } else {
    body.innerHTML = alerts.map(a => {
      let suggestions = [];
      try { suggestions = JSON.parse(a.suggestions_json || '[]'); } catch(_) {}
      return `
        <div style="background:var(--bg3);border:1px solid var(--border);border-radius: 0;padding:12px 14px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <div>
              <span style="font-size:13px;font-weight:600;">${esc(a.title)}</span>
              <span class="badge badge-muted" style="margin-left:8px;">${esc(a.project_name)}</span>
            </div>
            <span class="badge badge-amber">${icon('warning')} ${t('tasks.unassigned')}</span>
          </div>
          ${suggestions.length ? `<div style="font-size:11px;color:var(--muted);margin-bottom:6px;">${t('tasks.suggestions_hint')}</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            ${suggestions.slice(0,3).map(s => `<span class="badge badge-blue" style="font-size:11px;">${esc(s.agent_name)} (${Math.round(s.score)})</span>`).join('')}
          </div>` : `<div style="font-size:11px;color:var(--muted);">${t('tasks.no_suggestions')}</div>`}
        </div>`;
    }).join('');
  }
  document.getElementById('alert-modal').classList.remove('hidden');
}

// ════════════════════════════════════════
// MEETINGS
// ════════════════════════════════════════
async function loadMeetings() {
  const data = await api('GET', '/meetings/');
  meetings = data.meetings || [];
  renderMeetingList();
}

function renderMeetingList() {
  const el = document.getElementById('meetings-list');
  if (!meetings.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('meeting')}</div><div class="empty-state-text">No meetings yet</div></div>`;
    return;
  }
  const statusMeta = {
    active: { label: 'Đang diễn ra', badge: 'badge-green' },
    ended: { label: 'Đã kết thúc', badge: 'badge-muted' },
    finalized: { label: 'Đã chốt', badge: 'badge-amber' },
  };
  el.innerHTML = meetings.map(m => `
    <div class="list-item${m.id===currentMeetingId?' selected':''}" onclick="openMeeting(${m.id})">
      <div style="flex:1;min-width:0;">
        <div class="list-item-name">${esc(m.title)}</div>
        ${m.project_id ? `<div class="list-item-sub meeting-list-project">${icon('folder')} <span>${esc(projects.find(p => p.id === m.project_id)?.name || 'Dự án liên kết')}</span></div>` : ''}
        <div class="list-item-sub meeting-list-meta">
          <span class="badge ${(statusMeta[m.status] || statusMeta.ended).badge}">${esc((statusMeta[m.status] || {label:m.status}).label)}</span>
          <span>${m.participants.length} nhân viên</span>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm meeting-delete-btn" onclick="event.stopPropagation();deleteMeeting(${m.id})" title="Xoá cuộc họp">${icon('close')}</button>
    </div>`).join('');
}

function newMeeting() {
  document.getElementById('meeting-modal-title').value = '';
  document.getElementById('meeting-modal-topic').value = '';
  const projSel = document.getElementById('meeting-modal-project');
  projSel.innerHTML = '<option value="">— Không gắn dự án —</option>' +
    projects.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
  document.getElementById('meeting-modal').classList.remove('hidden');
}

async function createMeeting() {
  const title = document.getElementById('meeting-modal-title').value.trim();
  const topic = document.getElementById('meeting-modal-topic').value.trim();
  if (!title) return showToast('Title is required', 'error');
  const projVal = document.getElementById('meeting-modal-project').value;
  const m = await api('POST', '/meetings/', { title, topic, participants: [], project_id: projVal ? parseInt(projVal) : null });
  closeModal('meeting-modal');
  await loadMeetings();
  openMeeting(m.id);
}

async function openMeeting(id) {
  if (currentMeetingWs) { currentMeetingWs.close(); currentMeetingWs = null; }
  currentMeetingId = id;
  renderMeetingList();
  const m = await api('GET', `/meetings/${id}`).catch(() => meetings.find(x => x.id === id));
  if (!m) return;
  const meetingIndex = meetings.findIndex(x => x.id === id);
  if (meetingIndex >= 0) meetings[meetingIndex] = m;

  document.getElementById('meeting-empty').style.display = 'none';
  document.getElementById('meeting-chat').style.display = 'flex';
  document.getElementById('meeting-title-label').textContent = m.title;
  document.getElementById('meeting-topic-label').textContent = m.topic || '';
  const project = projects.find(p => p.id === m.project_id);
  document.getElementById('meeting-project-label').innerHTML = project
    ? `<span class="meeting-project-link" onclick="openMeetingProject(${project.id})">${icon('folder')} <span>${esc(project.name)}</span></span>`
    : '';
  document.getElementById('meeting-end-btn').style.display = m.status === 'active' ? '' : 'none';
  document.getElementById('meeting-finalize-btn').style.display = m.status === 'ended' ? '' : 'none';
  document.getElementById('meeting-input-area').style.display = m.status === 'active' ? '' : 'none';
  document.getElementById('meeting-messages').innerHTML = '';
  lastMessageAt = null;

  await renderParticipants(m.participants);
  renderMeetingRecord(m);

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws/meeting/${id}`);
  currentMeetingWs = ws;

  ws.onmessage = (e) => handleMeetingMsg(JSON.parse(e.data));
  ws.onerror = () => appendMeetingMsg('system', 'WebSocket error', 'var(--red)');
  ws.onclose = (e) => { if (e.code !== 1000) checkAuthOrRedirect(); };
}

function openMeetingProject(projectId) {
  switchTab('tasks');
  openProjectDetail(projectId);
}

function renderMeetingRecord(m) {
  const panel = document.getElementById('meeting-record-panel');
  if (!m || !['ended', 'finalized'].includes(m.status)) {
    panel.innerHTML = '';
    return;
  }
  const minutes = m.decision_text || m.draft_minutes || 'Chưa có nội dung biên bản.';
  const decided = m.decided_at
    ? ` · Chốt lúc ${_parseServerTime(m.decided_at).toLocaleString('vi-VN')}`
    : '';
  const items = Array.isArray(m.proposed_items) ? m.proposed_items : [];
  const agentOptions = (selectedId) => '<option value="">— Chưa giao —</option>' +
    agents.map(a => `<option value="${a.id}" ${a.id === selectedId ? 'selected' : ''}>${esc(a.name)} — ${esc(a.role || '')}</option>`).join('');
  panel.innerHTML = `
    <details>
      <summary>Biên bản cuộc họp${m.status === 'finalized' ? ' · Đã chốt' : ' · Bản nháp'}${esc(decided)}</summary>
      <div class="meeting-minutes-content">${esc(minutes)}</div>
    </details>
    ${items.length ? `<details open>
      <summary>Đề xuất công việc từ biên bản (${items.length})</summary>
      <div class="meeting-proposals">
        ${items.map((item, index) => `
          <div class="meeting-proposal" data-proposal-index="${index}">
            <input type="checkbox" class="meeting-proposal-include" checked title="Tạo công việc này">
            <div class="meeting-proposal-fields">
              <input class="form-input meeting-proposal-title" value="${esc(item.title || '')}" aria-label="Tiêu đề công việc">
              <textarea class="form-textarea meeting-proposal-description" rows="2" aria-label="Mô tả công việc">${esc(item.description || '')}</textarea>
              <select class="form-select meeting-proposal-priority" aria-label="Độ ưu tiên">
                <option value="low" ${item.priority === 'low' ? 'selected' : ''}>Thấp</option>
                <option value="medium" ${item.priority === 'medium' ? 'selected' : ''}>Trung bình</option>
                <option value="high" ${item.priority === 'high' ? 'selected' : ''}>Cao</option>
              </select>
            </div>
            <div class="meeting-proposal-assignee">
              <select class="form-select meeting-proposal-agent" aria-label="Người được giao">${agentOptions(item.suggested_agent_id)}</select>
              ${item.match_reason ? `<div class="meeting-proposal-reason">${esc(item.match_reason)}</div>` : '<div class="meeting-proposal-reason">Chưa tìm thấy nhân viên đủ điểm phù hợp — hãy chọn thủ công.</div>'}
            </div>
          </div>`).join('')}
        <div class="meeting-proposals-actions">
          <button class="btn btn-primary btn-sm" onclick="approveMeetingItems()">Tạo công việc đã chọn</button>
        </div>
      </div>
    </details>` : ''}`;
}

async function deleteMeeting(id) {
  const meeting = meetings.find(m => m.id === id);
  if (!(await showConfirm(`Xoá cuộc họp “${meeting?.title || id}”?`, 'Xoá cuộc họp'))) return;
  await api('DELETE', `/meetings/${id}`);
  if (currentMeetingId === id) {
    if (currentMeetingWs) currentMeetingWs.close();
    currentMeetingWs = null;
    currentMeetingId = null;
    document.getElementById('meeting-chat').style.display = 'none';
    document.getElementById('meeting-empty').style.display = '';
  }
  await loadMeetings();
  showToast('Đã xoá cuộc họp.', 'success');
}

async function approveMeetingItems() {
  if (!currentMeetingId) return;
  const items = [...document.querySelectorAll('.meeting-proposal')].map(row => ({
    title: row.querySelector('.meeting-proposal-title').value.trim(),
    description: row.querySelector('.meeting-proposal-description').value.trim(),
    priority: row.querySelector('.meeting-proposal-priority').value,
    assigned_agent_id: Number(row.querySelector('.meeting-proposal-agent').value) || null,
    include: row.querySelector('.meeting-proposal-include').checked,
  }));
  if (items.some(item => item.include && !item.title)) {
    showToast('Tiêu đề công việc được chọn không được để trống.', 'error');
    return;
  }
  try {
    const res = await api('POST', `/meetings/${currentMeetingId}/approve-items`, { items });
    const m = await api('GET', `/meetings/${currentMeetingId}`);
    const index = meetings.findIndex(item => item.id === currentMeetingId);
    if (index >= 0) meetings[index] = m;
    renderMeetingRecord(m);
    const count = (res.work_item_ids || []).length;
    showToast(`Đã tạo ${count} công việc. Mở tab Công việc để theo dõi.`, 'success');
  } catch (e) {
    showToast('Không thể tạo công việc: ' + e.message, 'error');
  }
}

async function renderParticipants(ids) {
  const agentObjs = await Promise.all(ids.map(id => {
    const a = agents.find(x => x.id === id);
    return a ? Promise.resolve(a) : api('GET', `/agent-configs/${id}`).catch(()=>null);
  }));
  const list = agentObjs.filter(Boolean);

  document.getElementById('participants-count').textContent = list.length;

  const panel = document.getElementById('participants-dropdown-panel');
  panel.innerHTML = list.length
    ? list.map(a => `
      <div class="participant-chip">
        ${avatarHtml(a.avatar_color, a.name, 'avatar-sm')}
        <span>${esc(a.name)}</span>
        ${agentDeptBadgeHtml(a)}
      </div>`).join('')
    : '<div class="participants-dropdown-empty">Chưa có nhân viên nào trong cuộc họp</div>';
}

function toggleParticipantsDropdown(event) {
  event.stopPropagation();
  document.getElementById('participants-dropdown-panel').classList.toggle('hidden');
}

document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('participants-dropdown');
  const panel = document.getElementById('participants-dropdown-panel');
  if (dropdown && panel && !dropdown.contains(e.target)) panel.classList.add('hidden');
});

// ── Thời gian tin nhắn + vạch phân tách session (giống Messenger) ──

function _parseServerTime(str) {
  // SQLite datetime('now') trả "YYYY-MM-DD HH:MM:SS" (UTC, không có 'Z') -> ép về ISO UTC.
  if (!str) return new Date();
  return new Date(str.includes('T') ? str : str.replace(' ', 'T') + 'Z');
}

function _msgTimeLabel(date) {
  return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function _dividerLabel(date) {
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  const time = _msgTimeLabel(date);
  if (sameDay) return `Hôm nay ${time}`;
  return `${date.toLocaleDateString('vi-VN')} ${time}`;
}

// Chèn vạch phân tách thời gian nếu khoảng cách với tin nhắn trước > 15 phút (hoặc đây là
// tin nhắn đầu tiên của phòng họp) — giống cơ chế "session" của Messenger/Zalo.
function _maybeInsertTimeDivider(date) {
  const ts = date.getTime();
  if (lastMessageAt === null || ts - lastMessageAt > SESSION_GAP_MS) {
    const area = document.getElementById('meeting-messages');
    area.insertAdjacentHTML('beforeend', `<div class="time-divider">${esc(_dividerLabel(date))}</div>`);
  }
  lastMessageAt = ts;
}

// In đậm "@Tên" khi Tên khớp đúng 1 nhân viên hoặc Xanax — áp dụng trước khi đưa qua
// marked.parse() để render ra <strong>@Tên</strong> trong bong bóng chat.
function _boldenMentions(content) {
  const names = [...new Set([...(agents || []).map(a => a.name), 'Xanax'].filter(Boolean))];
  if (!names.length) return content;
  const sorted = names.sort((a, b) => b.length - a.length).map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp('@(' + sorted.join('|') + ')\\b', 'gi');
  return content.replace(re, '**@$1**');
}

function handleMeetingMsg(msg) {
  if (msg.type === 'history') {
    msg.messages.forEach(m => {
      const time = _parseServerTime(m.created_at);
      _maybeInsertTimeDivider(time);
      if (m.sender_type === 'user') appendMeetingMsg('user', m.content, 'var(--cyan)', time);
      else if (m.sender === 'Xanax') appendMeetingMsg('Xanax', m.content, 'var(--gold)', time);
      else {
        const a = agents.find(x => x.name === m.sender);
        appendMeetingMsg(m.sender, m.content, a?.avatar_color || 'var(--purple)', time);
      }
    });
    return;
  }
  if (msg.type === 'user_message') {
    const time = new Date();
    _maybeInsertTimeDivider(time);
    appendMeetingMsg('user', msg.content, 'var(--cyan)', time);
    return;
  }
  if (msg.type === 'agent_thinking') {
    _maybeInsertTimeDivider(new Date());
    appendThinking(msg.agent, msg.agent_id, msg.color);
    return;
  }
  if (msg.type === 'agent_chunk') {
    appendAgentChunk(msg.agent_id, msg.agent, msg.color, msg.content);
    return;
  }
  if (msg.type === 'agent_done') {
    finishAgentMessage(msg.agent_id);
    return;
  }
  if (msg.type === 'agent_cancelled') {
    removeThinking(msg.agent_id);
    return;
  }
  // Thông báo do hệ thống đẩy vào giữa chừng (vd: quy trình đang chờ CEO duyệt).
  // Nội dung đã được lưu vào lịch sử họp phía server, đây chỉ là hiện ngay.
  if (msg.type === 'system_notice') {
    _maybeInsertTimeDivider(new Date());
    appendMeetingMsg('system', msg.content, 'var(--amber)');
    return;
  }
  if (msg.type === 'workflow_progress') {
    renderWorkflowProgress(msg);
    return;
  }
  if (msg.type === 'approval_request') {
    renderApprovalRequest(msg);
    return;
  }
  if (msg.type === 'participants_updated') {
    renderParticipants(msg.participants.map(p => p.id));
    return;
  }
  if (msg.type === 'meeting_ended') {
    appendMeetingMsg('system', 'Cuộc họp đã kết thúc. Xanax đã soạn biên bản nháp — xem lại và bấm "Chốt kế hoạch".', 'var(--muted)');
    const meeting = meetings.find(m => m.id === currentMeetingId);
    if (meeting) {
      meeting.status = 'ended';
      meeting.draft_minutes = msg.draft_minutes || '';
      meeting.proposed_items = [];
      renderMeetingList();
      renderMeetingRecord(meeting);
    }
    document.getElementById('meeting-end-btn').style.display = 'none';
    document.getElementById('meeting-finalize-btn').style.display = '';
    document.getElementById('meeting-input-area').style.display = 'none';
    if (msg.draft_minutes) openFinalizeModal(msg.draft_minutes);
    return;
  }
}

function appendMeetingMsg(sender, content, color, time) {
  const area = document.getElementById('meeting-messages');
  const isUser = sender === 'user';
  const isSystem = sender === 'system';
  const agentForMsg = !isUser && !isSystem ? agents.find(x => x.name === sender) : null;
  const timeLabel = _msgTimeLabel(time || new Date());
  const html = `
    <div class="message-row${isUser?' user-row':''}">
      ${!isUser && !isSystem ? avatarHtml(agentForMsg?.avatar_color || color, sender, 'avatar-sm') : ''}
      <div>
        ${!isUser && !isSystem ? `<div class="message-sender" style="color:${color}">${esc(sender)}${agentDeptSuffix(agentForMsg)}</div>` : ''}
        <div class="message-bubble ${isUser?'user-bubble':'agent-bubble'}" ${isSystem?'style="background:var(--bg3);border-color:var(--border);color:var(--muted);font-style:italic;"':''}>
          ${marked.parse(_boldenMentions(content))}
        </div>
        ${!isSystem ? `<div class="msg-time">${esc(timeLabel)}</div>` : ''}
      </div>
    </div>`;
  area.insertAdjacentHTML('beforeend', html);
  area.scrollTop = area.scrollHeight;
}

// Một bong bóng tiến độ cho mỗi lần chạy, cập nhật tại chỗ thay vì đẩy tin nhắn
// mới liên tục — CEO thấy đang ở bước nào và khi nào xong.
const WF_PROGRESS_STYLE = {
  running:   { icon: '',   color: 'var(--cyan)'  },
  waiting:   { icon: '✋', color: 'var(--amber)' },
  done:      { icon: '✅', color: 'var(--green)' },
  failed:    { icon: '⚠️', color: 'var(--red)'   },
  cancelled: { icon: '⛔', color: 'var(--muted)' },
};

function renderWorkflowProgress(msg) {
  const area = document.getElementById('meeting-messages');
  if (!area) return;
  const style = WF_PROGRESS_STYLE[msg.status] || WF_PROGRESS_STYLE.running;
  const id = `wf-progress-${msg.run_id}`;
  let el = document.getElementById(id);
  if (!el) {
    el = document.createElement('div');
    el.className = 'message-row';
    el.id = id;
    area.appendChild(el);
  }
  const stepText = msg.total ? ` · bước ${msg.step || 0}/${msg.total}` : '';
  const done = msg.status !== 'running' && msg.status !== 'waiting';
  const statusIcon = msg.status === 'running'
    ? '<span class="busy-spinner" aria-hidden="true"></span>'
    : style.icon;
  el.innerHTML = `
    <div>
      <div class="message-sender" style="color:${style.color}">
        ${statusIcon} ${esc(msg.task_name || 'Quy trình')}${esc(stepText)}
      </div>
      <div class="message-bubble agent-bubble"
           style="border-color:${style.color};${done ? '' : 'opacity:.92;'}">
        ${esc(msg.label || '')}${done ? '' : ' <span class="thinking-dots" aria-hidden="true"></span>'}
      </div>
    </div>`;
  area.scrollTop = area.scrollHeight;
}

// ── Duyệt bài ngay trong phòng họp ─────────────────────────────────────────
// CEO xem đủ nội dung + ảnh, sửa được chữ, và chọn duyệt / bắt làm lại mà không
// phải rời phòng họp sang tab Vận hành.
function renderApprovalRequest(msg) {
  const area = document.getElementById('meeting-messages');
  if (!area) return;
  const id = `approval-card-${msg.output_id}`;
  if (document.getElementById(id)) return;   // tránh dựng trùng khi engine báo lại

  const images = (msg.images || []).map(url =>
    `<img src="${esc(url)}" alt="Ảnh của bài đăng" class="approval-image">`).join('');

  const el = document.createElement('div');
  el.className = 'message-row';
  el.id = id;
  el.innerHTML = `
    <div class="approval-card">
      <div class="approval-card-head">
        ✋ ${esc(msg.task_name || 'Quy trình')} — chờ ${esc(msg.approver || 'CEO')} duyệt
        ${esc(msg.deadline_note || '')}
      </div>
      ${msg.note ? `<div class="approval-note">${esc(msg.note)}</div>` : ''}
      ${images ? `<div class="approval-images">${images}</div>` : ''}
      <label class="approval-label">Nội dung bài đăng — sửa trực tiếp trước khi duyệt</label>
      <textarea class="approval-content" rows="10">${esc(msg.content || '')}</textarea>
      <div class="approval-actions">
        <button class="btn btn-sm" onclick="resolveMeetingApproval(${msg.output_id}, false)">
          Không duyệt — làm lại bước trước
        </button>
        <button class="btn btn-sm btn-primary" onclick="resolveMeetingApproval(${msg.output_id}, true)">
          Duyệt &amp; đăng
        </button>
      </div>
      <div class="approval-hint">
        Bấm "Không duyệt" để bước trước chạy lại — nội dung và ảnh sẽ được tạo mới.
      </div>
    </div>`;
  area.appendChild(el);
  area.scrollTop = area.scrollHeight;
}

async function resolveMeetingApproval(outputId, approved) {
  const card = document.getElementById(`approval-card-${outputId}`);
  const textarea = card?.querySelector('.approval-content');
  const buttons = card?.querySelectorAll('button') || [];
  buttons.forEach(b => { b.disabled = true; });
  try {
    await api('PATCH', `/workflow/outputs/${outputId}`, approved
      ? { review_status: 'approved', edited_content: textarea ? textarea.value : undefined }
      : { review_status: 'rejected' });
    if (card) {
      card.innerHTML = `<div class="approval-card resolved">${
        approved ? '✅ Đã duyệt — quy trình đang chạy tiếp.'
                 : '🔄 Đã yêu cầu làm lại — bước trước đang chạy lại.'
      }</div>`;
    }
  } catch (e) {
    buttons.forEach(b => { b.disabled = false; });
    alert('Không gửi được quyết định duyệt: ' + (e?.message || e));
  }
}

function appendThinking(agentName, agentId, color) {
  const area = document.getElementById('meeting-messages');
  const el = document.createElement('div');
  el.className = 'message-row';
  el.id = `thinking-${agentId}`;
  const agentForThink = agents.find(x => x.name === agentName);
  el.innerHTML = `
    ${avatarHtml(agentForThink?.avatar_color || color, agentName, 'avatar-sm')}
    <div>
      <div class="message-sender" style="color:${color}">${esc(agentName)}${agentDeptSuffix(agentForThink)}</div>
      <div class="message-bubble agent-bubble" id="agent-msg-${agentId}" style="color:var(--muted);font-style:italic;">
        <span class="thinking-dots">thinking</span>
      </div>
    </div>`;
  area.appendChild(el);
  area.scrollTop = area.scrollHeight;
}

function appendAgentChunk(agentId, agentName, color, chunk) {
  const msgEl = document.getElementById(`agent-msg-${agentId}`);
  if (!msgEl) { appendMeetingMsg(agentName, chunk, color); return; }
  if (!msgEl.dataset.started) {
    // Bong bóng "thinking" có inline style italic/muted riêng — phải gỡ khi nội dung thật
    // bắt đầu stream vào, nếu không câu trả lời sẽ hiển thị khác font/màu so với tin nhắn
    // đã lưu (đọc lại từ lịch sử), gây cảm giác 2 kiểu chữ khác nhau không cần thiết (đã có
    // vạch phân tách thời gian để phân biệt lượt rồi, không cần phân biệt bằng font nữa).
    msgEl.removeAttribute('style');
    msgEl.innerHTML = '';
    msgEl.dataset.started = '1';
    msgEl.dataset.raw = '';
  }
  msgEl.dataset.raw += chunk;
  msgEl.innerHTML = marked.parse(_boldenMentions(msgEl.dataset.raw));
  const area = document.getElementById('meeting-messages');
  area.scrollTop = area.scrollHeight;
}

function finishAgentMessage(agentId) {
  const el = document.getElementById(`thinking-${agentId}`);
  if (el) el.removeAttribute('id');
  const msgEl = document.getElementById(`agent-msg-${agentId}`);
  if (msgEl) {
    msgEl.removeAttribute('id');
    if (!msgEl.parentElement.querySelector('.msg-time')) {
      msgEl.insertAdjacentHTML('afterend', `<div class="msg-time">${esc(_msgTimeLabel(new Date()))}</div>`);
    }
  }
}

// Gỡ hẳn bong bóng "đang xử lý" khi agent đó rốt cuộc không nói gì (vd Xanax chỉ mời
// nhân viên khác ra trả lời) — tránh kẹt trạng thái "thinking..." vĩnh viễn trên UI.
function removeThinking(agentId) {
  const el = document.getElementById(`thinking-${agentId}`);
  if (el && !document.getElementById(`agent-msg-${agentId}`)?.dataset.started) el.remove();
}

// ── @mention (gọi thẳng 1 nhân viên, bỏ qua bước Xanax cân nhắc) ──
// Xanax không nằm trong agent_configs (không phải 1 nhân viên) nhưng vẫn phải xuất hiện
// mặc định trong danh sách tag vì Xanax là người điều hành cuộc họp — CEO cần gọi lại
// quyền điều phối bất cứ lúc nào (xem addresses_xanax ở api/websocket_meeting.py).
const XANAX_MENTION_ENTRY = { id: 0, name: 'Xanax', role: 'Điều phối viên', avatar_color: 'var(--cyan)', department_name: null };
let mentionMatches = [], mentionActiveIndex = 0, mentionAtPos = -1;

function _mentionQueryAt(text, caret) {
  const uptoCaret = text.slice(0, caret);
  const at = uptoCaret.lastIndexOf('@');
  if (at === -1) return null;
  const query = uptoCaret.slice(at + 1);
  if (/\s/.test(query)) return null; // đã gõ qua khoảng trắng -> không còn đang gõ mention
  return { at, query };
}

function handleMeetingInputChange(e) {
  const inp = e.target;
  const q = _mentionQueryAt(inp.value, inp.selectionStart);
  if (!q) { hideMentionDropdown(); return; }
  mentionAtPos = q.at;
  mentionMatches = [XANAX_MENTION_ENTRY, ...agents].filter(a => a.name.toLowerCase().includes(q.query.toLowerCase()));
  mentionActiveIndex = 0;
  if (!mentionMatches.length) { hideMentionDropdown(); return; }
  renderMentionDropdown();
}

function renderMentionDropdown() {
  const el = document.getElementById('mention-dropdown');
  el.innerHTML = mentionMatches.map((a, i) => `
    <div class="mention-item${i===mentionActiveIndex?' active':''}" onmousedown="event.preventDefault();selectMention(${i})">
      ${avatarHtml(a.avatar_color, a.name, 'avatar-sm')}
      <div><div class="mention-item-name">${esc(a.name)}${agentDeptSuffix(a)}</div><div class="mention-item-role">${esc(a.role)}</div></div>
    </div>`).join('');
  el.classList.remove('hidden');
}

function hideMentionDropdown() {
  mentionMatches = []; mentionAtPos = -1;
  const el = document.getElementById('mention-dropdown');
  el.classList.add('hidden');
  el.innerHTML = '';
}

function selectMention(index) {
  const a = mentionMatches[index];
  const inp = document.getElementById('meeting-input');
  if (!a || mentionAtPos === -1) return;
  const before = inp.value.slice(0, mentionAtPos);
  const after = inp.value.slice(inp.selectionStart);
  inp.value = `${before}@${a.name} ${after}`;
  const caret = before.length + a.name.length + 2;
  inp.focus();
  inp.setSelectionRange(caret, caret);
  hideMentionDropdown();
}

function _extractMentionTargets(content) {
  const lower = content.toLowerCase();
  return agents.filter(a => lower.includes(`@${a.name.toLowerCase()}`)).map(a => a.id);
}

function sendMeetingMessage() {
  if (!currentMeetingWs || currentMeetingWs.readyState !== 1) return;
  const inp = document.getElementById('meeting-input');
  const content = inp.value.trim();
  if (!content) return;
  const targets = _extractMentionTargets(content);
  inp.value = '';
  hideMentionDropdown();
  currentMeetingWs.send(JSON.stringify({ type: 'user_message', content, targets }));
}

function meetingInputKeydown(e) {
  if (mentionMatches.length) {
    if (e.key === 'ArrowDown') { e.preventDefault(); mentionActiveIndex = (mentionActiveIndex + 1) % mentionMatches.length; renderMentionDropdown(); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); mentionActiveIndex = (mentionActiveIndex - 1 + mentionMatches.length) % mentionMatches.length; renderMentionDropdown(); return; }
    if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); selectMention(mentionActiveIndex); return; }
    if (e.key === 'Escape') { hideMentionDropdown(); return; }
  }
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMeetingMessage(); }
}

async function endMeeting() {
  if (!currentMeetingWs) return;
  if (!(await showConfirm('End this meeting?', 'Kết thúc'))) return;
  currentMeetingWs.send(JSON.stringify({ type: 'end_meeting' }));
}

async function finalizeMeeting() {
  if (!currentMeetingId) return;
  const m = await api('GET', `/meetings/${currentMeetingId}`);
  openFinalizeModal(m.draft_minutes || '');
}

function openFinalizeModal(draftText) {
  document.getElementById('finalize-modal-text').value = draftText || '';
  document.getElementById('finalize-modal').classList.remove('hidden');
}

async function confirmFinalizeMeeting() {
  if (!currentMeetingId) return;
  const decision = document.getElementById('finalize-modal-text').value.trim();
  if (!decision) { showToast('Vui lòng nhập nội dung biên bản.', 'error'); return; }
  try {
    const res = await api('POST', `/meetings/${currentMeetingId}/finalize`, { decision_text: decision });
    const n = (res.triggered_workflow_ids || []).length;
    const index = meetings.findIndex(m => m.id === currentMeetingId);
    if (index >= 0) meetings[index] = res;
    closeModal('finalize-modal');
    renderMeetingList();
    renderMeetingRecord(res);
    document.getElementById('meeting-finalize-btn').style.display = 'none';
    const proposals = (res.proposed_items || []).length;
    const triggerText = n ? ` Đã kích hoạt ${n} quy trình.` : '';
    const proposalText = proposals ? ` Xanax đã đề xuất ${proposals} công việc để bạn duyệt.` : '';
    showToast(`Đã chốt biên bản.${triggerText}${proposalText}`, 'success');
  } catch (e) { showToast('Lỗi khi chốt biên bản: ' + e.message, 'error'); }
}

// ════════════════════════════════════════
// BENCHMARK
// ════════════════════════════════════════
async function loadBenchmarks() {
  const data = await api('GET', '/benchmarks/');
  benchmarks = data.benchmarks || [];
  renderBenchmarkList();
}

function renderBenchmarkList() {
  const el = document.getElementById('benchmarks-list');
  if (!benchmarks.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${icon('chart')}</div><div class="empty-state-text">No benchmarks yet</div></div>`;
    return;
  }
  el.innerHTML = benchmarks.map(b => `
    <div class="list-item${b.id===currentBenchmarkId?' selected':''}" onclick="openBenchmark(${b.id})">
      <div style="flex:1;min-width:0;">
        <div class="list-item-name">${esc(b.name)}</div>
        <div class="list-item-sub" style="display:flex;gap:6px;margin-top:3px;">
          <span class="badge ${b.status==='completed'?'badge-green':b.status==='running'?'badge-amber':'badge-muted'}">${b.status}</span>
          <span>${b.models.length} models</span>
        </div>
      </div>
    </div>`).join('');
}

function showBenchmarkCreate() {
  hideBenchmarkViews();
  document.getElementById('benchmark-create-view').style.display = 'flex';
  document.getElementById('benchmark-empty').style.display = 'none';
}

function cancelBenchmark() {
  hideBenchmarkViews();
  document.getElementById('benchmark-empty').style.display = 'flex';
}

function hideBenchmarkViews() {
  ['benchmark-create-view','benchmark-progress-view','benchmark-results-view','benchmark-empty'].forEach(id => {
    document.getElementById(id).style.display = 'none';
  });
}

function addBenchModel() {
  const inp = document.getElementById('bench-model-input');
  const m = inp.value.trim();
  if (!m || benchModels.includes(m)) { inp.value = ''; return; }
  benchModels.push(m);
  inp.value = '';
  renderBenchModels();
}

function removeBenchModel(m) {
  benchModels = benchModels.filter(x => x !== m);
  renderBenchModels();
}

function renderBenchModels() {
  const el = document.getElementById('bench-models-list');
  el.innerHTML = benchModels.map(m => `
    <div class="model-tag">
      ${esc(m)}
      <button class="model-tag-remove" onclick="removeBenchModel('${m}')">×</button>
    </div>`).join('');
}

async function addTestCase() {
  const el = document.getElementById('bench-cases-list');
  const idx = benchCases.length;
  benchCases.push({ prompt: '', criteria: '' });
  const div = document.createElement('div');
  div.className = 'test-case-item';
  div.id = `case-${idx}`;
  div.innerHTML = `
    <button class="test-case-remove" onclick="removeTestCase(${idx})">×</button>
    <div class="form-group" style="margin-bottom:8px;">
      <label class="form-label">${t('js.case_prompt')}</label>
      <textarea class="form-textarea" id="case-prompt-${idx}" rows="2" placeholder="Ask the model to do something..." oninput="benchCases[${idx}].prompt=this.value"></textarea>
    </div>
    <div class="form-group" style="margin-bottom:0;">
      <label class="form-label">${t('js.case_expected')}</label>
      <input class="form-input" id="case-criteria-${idx}" placeholder="What makes a good answer? (optional)" oninput="benchCases[${idx}].criteria=this.value">
    </div>`;
  el.appendChild(div);
}

function removeTestCase(idx) {
  document.getElementById(`case-${idx}`)?.remove();
  benchCases[idx] = null;
}

async function createAndRunBenchmark() {
  const name = document.getElementById('bench-name').value.trim();
  const role = document.getElementById('bench-role').value.trim();
  if (!name) return showToast('Benchmark name is required', 'error');
  if (!benchModels.length) return showToast('Add at least one model to test', 'error');
  const cases = benchCases.filter(Boolean).filter(c => c.prompt.trim());
  if (!cases.length) return showToast('Add at least one test case', 'error');

  try {
    const b = await api('POST', '/benchmarks/', {
      name, role_description: role, test_cases: cases, models: benchModels,
    });
    currentBenchmarkId = b.id;
    await loadBenchmarks();
    runBenchmarkWs(b.id);
  } catch(e) { showToast('Error: ' + e.message, 'error'); }
}

function runBenchmarkWs(benchmarkId) {
  hideBenchmarkViews();
  document.getElementById('benchmark-progress-view').style.display = 'flex';
  const progressList = document.getElementById('benchmark-progress-list');
  progressList.innerHTML = '';

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws/benchmark`);

  const modelStatus = {};

  ws.onopen = () => ws.send(JSON.stringify({ type: 'run', benchmark_id: benchmarkId }));
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'started') {
      benchModels.forEach(m => {
        modelStatus[m] = { status: 'pending', scores: null };
        progressList.insertAdjacentHTML('beforeend', `
          <div class="progress-item" id="prog-${m.replace(/[^a-z0-9]/gi,'_')}">
            <div class="progress-status status-pending" id="dot-${m.replace(/[^a-z0-9]/gi,'_')}"></div>
            <div style="flex:1;">
              <div style="font-size:13px;font-weight:500;">${esc(m)}</div>
              <div style="font-size:11px;color:var(--muted);" id="prog-sub-${m.replace(/[^a-z0-9]/gi,'_')}">${t('js.waiting')}</div>
            </div>
          </div>`);
      });
    }

    if (msg.type === 'progress') {
      const key = msg.model.replace(/[^a-z0-9]/gi,'_');
      const dot = document.getElementById(`dot-${key}`);
      const sub = document.getElementById(`prog-sub-${key}`);
      if (dot) { dot.className = 'progress-status status-running'; }
      if (sub) sub.textContent = `${t('js.case')} ${msg.case_index+1}/${msg.total}: ${msg.prompt}`;
    }

    if (msg.type === 'scored') {
      const key = msg.model.replace(/[^a-z0-9]/gi,'_');
      const dot = document.getElementById(`dot-${key}`);
      const sub = document.getElementById(`prog-sub-${key}`);
      if (dot) dot.className = 'progress-status status-done';
      if (sub) sub.textContent = `${t('js.done_score')} ${msg.scores.total}/10`;
    }

    if (msg.type === 'complete') {
      hideBenchmarkViews();
      document.getElementById('benchmark-results-view').style.display = 'flex';
      document.getElementById('bench-result-title').textContent = benchmarks.find(b=>b.id===benchmarkId)?.name || 'Results';
      showBenchmarkResults(msg.results, msg.recommendation);
      loadBenchmarks();
    }

    if (msg.type === 'error') {
      showToast(t('js.bench_error') + msg.message, 'error');
      hideBenchmarkViews();
      document.getElementById('benchmark-empty').style.display = 'flex';
    }
  };

  ws.onerror = () => {
    showToast(t('js.ws_error'), 'error');
    hideBenchmarkViews();
    document.getElementById('benchmark-empty').style.display = 'flex';
  };
  ws.onclose = (e) => { if (e.code !== 1000) checkAuthOrRedirect(); };
}

async function openBenchmark(id) {
  currentBenchmarkId = id;
  renderBenchmarkList();
  const b = benchmarks.find(x => x.id === id);
  if (!b) return;

  if (b.status !== 'completed') {
    hideBenchmarkViews();
    document.getElementById('benchmark-empty').style.display = 'flex';
    return;
  }

  const data = await api('GET', `/benchmarks/${id}/results`);
  hideBenchmarkViews();
  document.getElementById('benchmark-results-view').style.display = 'flex';
  document.getElementById('bench-result-title').textContent = b.name;

  const results = (data.results || []).map(r => ({ model: r.model, scores: r.scores }));
  const best = results.reduce((a, b) => (b.scores.total > a.scores.total ? b : a), results[0] || {model:'',scores:{total:0}});
  showBenchmarkResults(results, best.model);
}

function showBenchmarkResults(results, recommendation) {
  if (recommendation) {
    document.getElementById('bench-recommendation').style.display = '';
    document.getElementById('bench-recommended-model').textContent = recommendation;
    const scores = results.find(r => r.model === recommendation)?.scores;
    document.getElementById('bench-recommended-reason').textContent =
      scores ? `Chất lượng: ${scores.quality}/10 · Tốc độ: ${scores.speed_score}/10 · Phản hồi TB: ${scores.avg_response_time}s` : '';
  }
  const tbody = document.getElementById('bench-results-tbody');
  const sorted = [...results].sort((a,b) => b.scores.total - a.scores.total);
  tbody.innerHTML = sorted.map((r, i) => {
    const isBest = r.model === recommendation;
    const qualPct = (r.scores.quality / 10 * 100).toFixed(0);
    const speedPct = (r.scores.speed_score / 10 * 100).toFixed(0);
    return `
      <tr class="${isBest?'best-row':''}">
        <td style="font-size:12px;">
          ${isBest?icon('trophy')+' ':''}${esc(r.model)}
        </td>
        <td>
          <div class="score-bar">
            <div class="score-bar-track"><div class="score-bar-fill" style="width:${qualPct}%;background:${r.scores.quality>=7?'var(--green)':r.scores.quality>=4?'var(--amber)':'var(--red)'};"></div></div>
            <span style="font-size:12px;">${r.scores.quality}/10</span>
          </div>
        </td>
        <td>
          <div class="score-bar">
            <div class="score-bar-track"><div class="score-bar-fill" style="width:${speedPct}%;background:var(--blue);"></div></div>
            <span style="font-size:12px;">${r.scores.speed_score}/10</span>
          </div>
        </td>
        <td style="font-size:12px;color:var(--muted);">${r.scores.avg_response_time}s</td>
        <td>
          <span style="font-size:15px;font-weight:700;color:${r.scores.total>=7?'var(--green)':r.scores.total>=4?'var(--amber)':'var(--red)'};">${r.scores.total}</span>
          <span style="font-size:11px;color:var(--muted);">/10</span>
        </td>
      </tr>`;
  }).join('');
}

// ════════════════════════════════════════
// Modals
// ════════════════════════════════════════
function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}
document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) m.classList.add('hidden'); });
});

// ── Confirm popup (thay cho confirm() mặc định của trình duyệt) ─────────────
let _confirmResolve = null;
function showConfirm(message, okLabel) {
  return new Promise(resolve => {
    _confirmResolve = resolve;
    document.getElementById('confirm-modal-body').textContent = message;
    document.getElementById('confirm-modal-ok').textContent = okLabel || 'Xoá';
    document.getElementById('confirm-modal').classList.remove('hidden');
  });
}
function _answerConfirm(result) {
  document.getElementById('confirm-modal').classList.add('hidden');
  if (_confirmResolve) { _confirmResolve(result); _confirmResolve = null; }
}

// ── Toast (thay cho alert() mặc định) ───────────────────────────────────────
function showToast(message, type) {
  type = type || 'info';
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  const iconSvg = icon(type === 'error' ? 'warning' : type === 'success' ? 'check' : 'info');
  el.innerHTML = `<span class="toast-icon">${iconSvg}</span><span class="toast-msg"></span><button class="toast-close" onclick="this.parentElement.remove()">${icon('close')}</button>`;
  el.querySelector('.toast-msg').textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

// ════════════════════════════════════════
// Utils
// ════════════════════════════════════════
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Render 1 output content: nếu là ảnh (markdown ![](url) hoặc đường dẫn ảnh trần) thì
// hiển thị <img>, còn lại escape như văn bản thường.
const IMG_PATH_RE = /^(https?:\/\/|\/)\S+\.(png|jpe?g|gif|webp)(\?\S*)?$/i;
const IMG_MD_RE = /!\[([^\]]*)\]\(((?:https?:\/\/|\/)[^\s)]+)\)/g;
function renderOutputContent(raw) {
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
// Sidebar collapse
// ════════════════════════════════════════
function toggleSidebarIconMode() {
  const sb = document.querySelector('.hub-sidebar');
  const iconMode = sb.classList.toggle('icon-mode');
  localStorage.setItem('hub_sidebar_icon_mode', iconMode ? '1' : '0');
}
function saveSidebarPref(pinned) {
  localStorage.setItem('hub_sidebar_pinned', pinned ? '1' : '0');
}
function saveAnimPref(on) {
  localStorage.setItem('hub_animations', on ? '1' : '0');
  document.body.style.setProperty('--anim-scale', on ? '1' : '0');
}

// ════════════════════════════════════════
// Theme & Language
// ════════════════════════════════════════
const I18N = {
  en: {
    // Sidebar nav
    'nav.home': 'HOME',           'nav.home.title':   'Overview',
    'nav.agents': 'AI EMPLOYEES', 'nav.agents.title': 'AI Employees',
    'nav.skills': 'TOOLS',         'nav.skills.title': 'Tools & Skills',
    'nav.tasks':  'WORKPLACE',     'nav.tasks.title':  'Workplace & Tasks',
    'nav.meeting':'MEETING',      'nav.meeting.title':'AI Meeting Room',
    'nav.bench':  'BRAINS',       'nav.bench.title':  'Brain Benchmark',
    'nav.train':  'TEACH AI',     'nav.train.title':  'Teach AI Employee',
    'nav.company_runner': 'WORKFLOWS', 'nav.company_runner.title': 'Workflows',
    'nav.auto_runner': 'AUTO TASKS', 'nav.auto_runner.title': 'Automated Tasks',
    'nav.assets': 'ASSETS', 'nav.assets.title': 'Assets',
    'nav.runner': 'AUTOMATE',     'nav.runner.title': 'Automations',
    'nav.cost': 'COSTS',          'nav.cost.title':   'Costs & Budgets',
    'nav.config': 'SETTINGS',     'nav.config.title': 'Settings',
    // Topbar
    'topbar.logout': 'Logout',
    // Agents
    'agents.title': 'AI Employees', 'agents.new': '+ New',
    'agents.empty': 'Select an AI employee or create a new one',
    'agents.form.name': 'Name',   'agents.form.role': 'Position / Title',
    'agents.form.model': 'AI Brain (Model)', 'agents.form.color': 'Avatar Color',
    'agents.form.prompt': 'Task Instructions & Personality', 'agents.form.skills': 'Skills / Tools',
    // Skills
    'skills.title': 'Tools & Skills',     'skills.new': '+ New',
    'skills.empty': 'Select a tool or create a new one',
    'skills.form.name': 'Tool Name', 'skills.form.desc': 'Description',
    'skills.form.type': 'Type',   'skills.form.upload': 'Import from File',
    'skills.form.upload_strong': 'Click to upload', 'skills.form.upload_or': 'or drag & drop',
    'skills.form.config': 'Advanced connection settings',
    'skills.type.builtin': 'Built-in system tool',
    'skills.type.api':    'Connect an external service (API)',
    'skills.type.mcp':    'Advanced connection (MCP)',
    'skills.type.custom': 'Custom code (Python)',
    // Tasks
    'tasks.project': 'Project:',  'tasks.select': '— select project —',
    'tasks.new': '+ Project',     'tasks.edit': 'Edit',
    'tasks.empty': 'Select or create a project to get started',
    'tasks.add_item': '+ Add task',
    // Kanban columns
    'col.backlog': 'Backlog',     'col.in_progress': 'In Progress',
    'col.review': 'Review',       'col.done': 'Done',
    // Status / Priority
    'status.backlog': 'Backlog',  'status.in_progress': 'In Progress',
    'status.review': 'Review',    'status.done': 'Done',
    'priority.low': 'Low',        'priority.medium': 'Medium',
    'priority.high': 'High',      'priority.critical': 'Critical',
    // Meeting
    'meeting.title': 'Meetings',  'meeting.new': '+ New',
    'meeting.empty': 'Select a meeting or create one',
    'meeting.end': 'End',
    // Benchmark
    'bench.title': 'Brain Benchmarks',  'bench.new': '+ New',
    'bench.empty': 'Create a benchmark to find the best brain for a role',
    'bench.create': 'New Benchmark', 'bench.run': 'Run Benchmark ▶',
    'bench.running': 'Evaluating Brains', 'bench.results': 'Results',
    'bench.new_bench': 'New Benchmark',
    'bench.recommended': 'Recommended Brain',
    'bench.form.name': 'Benchmark Name', 'bench.form.role': 'Role / Task Description',
    'bench.form.models': 'AI Brains to Test', 'bench.form.add_model': 'Add',
    'bench.form.cases': 'Test Cases',    'bench.add_case': '+ Add Test Case',
    'bench.col.model': 'Brain',   'bench.col.quality': 'Quality',
    'bench.col.speed': 'Speed Score', 'bench.col.time': 'Avg Time',
    'bench.col.total': 'Total Score',
    // Common buttons
    'btn.save': 'Save', 'btn.cancel': 'Cancel', 'btn.delete': 'Delete',
    // Modals
    'modal.project.new': 'New Project', 'modal.project.edit': 'Edit Project',
    'modal.project.name': 'Project Name', 'modal.project.desc': 'Description',
    'modal.card.title': 'Work Item', 'modal.card.title_field': 'Title',
    'modal.card.desc': 'Description', 'modal.card.status': 'Status',
    'modal.card.priority': 'Priority', 'modal.card.agent': 'Assigned AI Employee',
    'modal.card.unassigned': 'Unassigned',
    'modal.card.suggestions': 'AI employee suggestions',
    'modal.alerts.title': 'Unassigned Tasks',
    'tasks.unassigned': 'Unassigned',
    'tasks.unassigned_tip': 'No AI employee assigned to this task',
    'tasks.assign_now': 'Assign',
    'tasks.alert_banner': (n) => `${n} task${n!==1?'s':''} with no matching AI employee`,
    'tasks.no_alerts': 'No open alerts — all tasks are assigned or matched.',
    'tasks.suggestions_hint': 'Top matching AI employees:',
    'tasks.no_suggestions': 'No matching AI employees found. Consider adding a new one.',
    'modal.meeting.title': 'New Meeting', 'modal.meeting.title_field': 'Meeting Title',
    'modal.meeting.topic': 'Topic / Agenda',
    'modal.meeting.start': 'Start Meeting',
    // Settings
    'settings.appearance': 'Appearance', 'settings.dark': 'Dark', 'settings.light': 'Light',
    'settings.language': 'Language', 'settings.interface': 'Interface',
    'settings.sidebar': 'Collapsible Sidebar',
    'settings.sidebar_desc': 'Pin sidebar or collapse for more space',
    'settings.animations': 'Animations',
    'settings.animations_desc': 'Smooth transitions and effects',
    'settings.about': 'About',
    'settings.about_desc': 'Orchestration platform for managing AI employees, tools, tasks and meetings',
    'settings.session': 'Session',
    // Counts
    'count.agents': (n) => `${n} AI employee${n!==1?'s':''}`,
    'count.skills': (n) => `${n} tool${n!==1?'s':''}`,
    // Placeholders
    'ph.agent.name': 'e.g. Atlas',
    'ph.agent.role': 'e.g. Content Writer',
    'ph.agent.model': 'e.g. claude-opus-4-8, gpt-4o, hermes3',
    'ph.agent.prompt': "Describe this AI employee's tasks, guidelines, and communication style...",
    'ph.skill.name': 'e.g. web_search',
    'ph.skill.desc': 'What this tool does...',
    'ph.bench.name': 'e.g. Copywriter Brain Evaluation',
    'ph.bench.role': 'Describe the role: skills needed, responsibilities, expected output style...',
    'ph.bench.model': 'brain name',
    'ph.project.name': 'e.g. Website Redesign',
    'ph.project.desc': 'What are the goals of this project?',
    'ph.card.title': 'Task title...',
    'ph.card.desc': 'Details, acceptance criteria...',
    'ph.meeting.title': 'e.g. Weekly Alignment',
    'ph.meeting.topic': 'What will be discussed in this meeting?',
    'ph.meeting.input': 'Type a message... (Enter to send, Shift+Enter for newline)',
    // Dynamic JS content
    'js.new_agent': 'New AI Employee',  'js.edit_agent': 'Edit AI Employee',
    'js.new_skill': 'New Tool',       'js.edit_skill': 'Edit Tool',
    'js.edit_project': 'Edit Project','js.agents_sub': (n) => `${n} AI employee${n!==1?'s':''}`,
    'js.waiting': 'Waiting...',       'js.case': 'Case',
    'js.done_score': 'Done — Score:',
    'js.logged_as': (u) => `Logged in as ${u}`,
    'js.project_required': 'Project name is required',
    'js.del_project': 'Delete this project and all its items?',
    'js.del_meeting': 'Delete this meeting?',
    'js.del_benchmark': 'Delete this benchmark?',
    'js.bench_error': 'Benchmark error: ',
    'js.ws_error': 'WebSocket error during benchmark',
    'js.unassigned': 'Unassigned',
    'js.no_skills': 'No tools defined',
    'js.case_prompt': 'Prompt',
    'js.case_expected': 'Expected answer (optional)',
  },
  vi: {
    // Sidebar nav
    'nav.home': 'TRANG CHỦ',      'nav.home.title':   'Tổng quan',
    'nav.agents': 'NHÂN VIÊN AI',  'nav.agents.title': 'Nhân viên AI',
    'nav.skills': 'CÔNG CỤ',       'nav.skills.title': 'Công cụ & Kỹ năng',
    'nav.tasks':  'CÔNG VIỆC',     'nav.tasks.title':  'Dự án & Công việc',
    'nav.meeting':'PHÒNG HỌP',     'nav.meeting.title':'Phòng họp AI',
    'nav.bench':  'BỘ NÃO AI',     'nav.bench.title':  'Đánh giá Bộ não',
    'nav.train':  'DẠY AI',        'nav.train.title':  'Dạy Nhân viên AI',
    'nav.company_runner': 'QUY TRÌNH', 'nav.company_runner.title': 'Quy trình',
    'nav.auto_runner': 'TÁC VỤ TỰ ĐỘNG', 'nav.auto_runner.title': 'Tác vụ tự động',
    'nav.assets': 'TÀI SẢN', 'nav.assets.title': 'Tài sản',
    'nav.runner': 'TỰ ĐỘNG',       'nav.runner.title': 'Tự động hóa',
    'nav.cost': 'CHI PHÍ',        'nav.cost.title':   'Ngân sách & Chi phí',
    'nav.config': 'THIẾT LẬP',     'nav.config.title': 'Thiết lập hệ thống',
    // Topbar
    'topbar.logout': 'Đăng xuất',
    // Agents
    'agents.title': 'Nhân viên AI', 'agents.new': '+ Thêm',
    'agents.empty': 'Chọn nhân viên AI hoặc tạo mới',
    'agents.form.name': 'Tên gọi',    'agents.form.role': 'Vị trí / Chức danh',
    'agents.form.model': 'Bộ não AI (Model)', 'agents.form.color': 'Màu avatar',
    'agents.form.prompt': 'Chỉ dẫn nhiệm vụ & Tính cách', 'agents.form.skills': 'Công cụ & Kỹ năng',
    // Skills
    'skills.title': 'Công cụ & Kỹ năng',   'skills.new': '+ Thêm',
    'skills.empty': 'Chọn công cụ hoặc tạo mới',
    'skills.form.name': 'Tên công cụ', 'skills.form.desc': 'Mô tả',
    'skills.form.type': 'Loại kết nối',   'skills.form.upload': 'Nhập từ tệp',
    'skills.form.upload_strong': 'Nhấp để tải lên', 'skills.form.upload_or': 'hoặc kéo thả',
    'skills.form.config': 'Cấu hình kết nối nâng cao',
    'skills.type.builtin': 'Có sẵn trong hệ thống',
    'skills.type.api':    'Kết nối dịch vụ ngoài (API)',
    'skills.type.mcp':    'Kết nối nâng cao (MCP)',
    'skills.type.custom': 'Tự viết mã riêng (Custom)',
    // Tasks
    'tasks.project': 'Dự án:',    'tasks.select': '— chọn dự án —',
    'tasks.new': '+ Dự án mới',   'tasks.edit': 'Sửa',
    'tasks.empty': 'Chọn hoặc tạo dự án để bắt đầu',
    'tasks.add_item': '+ Thêm công việc',
    // Kanban columns
    'col.backlog': 'Chờ xử lý',   'col.in_progress': 'Đang thực hiện',
    'col.review': 'Con người duyệt', 'col.done': 'Hoàn thành',
    // Status / Priority
    'status.backlog': 'Chờ xử lý', 'status.in_progress': 'Đang thực hiện',
    'status.review': 'Chờ duyệt',  'status.done': 'Hoàn thành',
    'priority.low': 'Thấp',        'priority.medium': 'Trung bình',
    'priority.high': 'Cao',        'priority.critical': 'Khẩn cấp',
    // Meeting
    'meeting.title': 'Cuộc họp',   'meeting.new': '+ Thêm cuộc họp',
    'meeting.empty': 'Chọn cuộc họp hoặc tạo mới',
    'meeting.end': 'Kết thúc họp',
    // Benchmark
    'bench.title': 'Đánh giá Bộ não',   'bench.new': '+ Đánh giá mới',
    'bench.empty': 'Tạo bài kiểm tra để tìm ra bộ não AI (model) phù hợp nhất cho vị trí công việc',
    'bench.create': 'Đánh giá mới', 'bench.run': 'Chạy đánh giá ▶',
    'bench.running': 'Đang thử nghiệm các bộ não...', 'bench.results': 'Kết quả',
    'bench.new_bench': 'Đánh giá mới',
    'bench.recommended': 'Bộ não khuyên dùng',
    'bench.form.name': 'Tên bài kiểm tra', 'bench.form.role': 'Mô tả yêu cầu vai trò / vị trí',
    'bench.form.models': 'Các bộ não AI cần so sánh', 'bench.form.add_model': 'Thêm',
    'bench.form.cases': 'Câu hỏi thử nghiệm',     'bench.add_case': '+ Thêm câu hỏi',
    'bench.col.model': 'Bộ não',    'bench.col.quality': 'Chất lượng',
    'bench.col.speed': 'Điểm tốc độ', 'bench.col.time': 'Thời gian TB',
    'bench.col.total': 'Tổng điểm',
    // Common buttons
    'btn.save': 'Lưu lại', 'btn.cancel': 'Hủy', 'btn.delete': 'Xóa',
    // Modals
    'modal.project.new': 'Dự án mới', 'modal.project.edit': 'Chỉnh sửa dự án',
    'modal.project.name': 'Tên dự án', 'modal.project.desc': 'Mô tả mục tiêu',
    'modal.card.title': 'Công việc', 'modal.card.title_field': 'Tên công việc',
    'modal.card.desc': 'Chi tiết yêu cầu', 'modal.card.status': 'Trạng thái',
    'modal.card.priority': 'Độ khẩn cấp', 'modal.card.agent': 'Nhân viên AI phụ trách',
    'modal.card.unassigned': 'Chưa phân công',
    'modal.card.suggestions': 'Gợi ý nhân viên AI phù hợp nhất',
    'modal.alerts.title': 'Công việc chưa có người làm',
    'tasks.unassigned': 'Chưa phân công',
    'tasks.unassigned_tip': 'Chưa giao cho nhân viên AI nào đảm nhận',
    'tasks.assign_now': 'Phân công',
    'tasks.alert_banner': (n) => `${n} công việc cần phân công nhân viên AI phù hợp`,
    'tasks.no_alerts': 'Tất cả công việc đã được giao cho nhân viên AI phù hợp.',
    'tasks.suggestions_hint': 'Nhân viên AI phù hợp nhất:',
    'tasks.no_suggestions': 'Không tìm được nhân viên AI phù hợp. Hãy tạo thêm nhân viên AI mới.',
    'modal.meeting.title': 'Cuộc họp mới', 'modal.meeting.title_field': 'Tên cuộc họp',
    'modal.meeting.topic': 'Chủ đề / Nội dung thảo luận',
    'modal.meeting.start': 'Bắt đầu họp',
    // Settings
    'settings.appearance': 'Giao diện', 'settings.dark': 'Chế độ Tối', 'settings.light': 'Chế độ Sáng',
    'settings.language': 'Ngôn ngữ', 'settings.interface': 'Tùy chỉnh hệ thống',
    'settings.sidebar': 'Thanh bên thu gọn',
    'settings.sidebar_desc': 'Thu nhỏ thanh bên để tăng diện tích làm việc',
    'settings.animations': 'Hiệu ứng chuyển động',
    'settings.animations_desc': 'Bật hiệu ứng chuyển cảnh mượt mà',
    'settings.about': 'Giới thiệu Xanax',
    'settings.about_desc': 'Nền tảng quản lý và điều phối các nhân viên AI hỗ trợ công việc doanh nghiệp',
    'settings.session': 'Phiên đăng nhập',
    // Counts
    'count.agents': (n) => `${n} nhân viên AI`,
    'count.skills': (n) => `${n} công cụ`,
    // Placeholders
    'ph.agent.name': 'vd: Nhân viên Marketing, Nhân viên Dịch thuật',
    'ph.agent.role': 'vd: Chuyên viên viết bài quảng cáo, Chuyên viên dữ liệu',
    'ph.agent.model': 'vd: gpt-4o, hermes3, claude-3-5-sonnet',
    'ph.agent.prompt': 'Mô tả chi tiết nhiệm vụ và cách hành xử của nhân viên AI (ví dụ: Hãy đóng vai một biên tập viên viết bài ngắn quảng cáo sản phẩm...)',
    'ph.skill.name': 'vd: tim_kiem_web, doc_file_excel',
    'ph.skill.desc': 'Mô tả tác dụng của công cụ này...',
    'ph.bench.name': 'vd: Đánh giá bộ não cho Nhân viên Marketing',
    'ph.bench.role': 'Mô tả nhiệm vụ cần bộ não xử lý tốt nhất: viết lách sáng tạo, suy luận logic, hiểu ngôn ngữ Việt...',
    'ph.bench.model': 'tên bộ não (model)',
    'ph.project.name': 'vd: Chiến dịch Marketing Q3',
    'ph.project.desc': 'Mục tiêu chính và các kết quả cần đạt của chiến dịch này là gì?',
    'ph.card.title': 'Tên công việc cần làm...',
    'ph.card.desc': 'Mô tả chi tiết công việc, tài liệu đầu vào và kết quả mong muốn...',
    'ph.meeting.title': 'vd: Họp Lên Ý Tưởng Marketing Q3',
    'ph.meeting.topic': 'Chủ đề và các câu hỏi cần thảo luận trong cuộc họp này?',
    'ph.meeting.input': 'Nhập tin nhắn của bạn... (Ấn Enter gửi, Shift+Enter xuống dòng)',
    // Dynamic JS content
    'js.new_agent': 'Thêm Nhân viên AI',   'js.edit_agent': 'Chỉnh sửa Nhân viên AI',
    'js.new_skill': 'Thêm Công cụ mới',  'js.edit_skill': 'Chỉnh sửa Công cụ',
    'js.edit_project': 'Chỉnh sửa dự án',
    'js.agents_sub': (n) => `${n} nhân viên AI`,
    'js.waiting': 'Đang chờ...',         'js.case': 'Câu hỏi',
    'js.done_score': 'Xong — Điểm chất lượng:',
    'js.logged_as': (u) => `Đăng nhập: ${u}`,
    'js.project_required': 'Tên dự án không được bỏ trống',
    'js.del_project': 'Xóa dự án này và toàn bộ công việc liên quan?',
    'js.del_meeting': 'Xóa cuộc họp này?',
    'js.del_benchmark': 'Xóa bài kiểm tra đánh giá này?',
    'js.bench_error': 'Lỗi bài kiểm tra: ',
    'js.ws_error': 'Lỗi kết nối WebSocket khi đang kiểm tra bộ não',
    'js.unassigned': 'Chưa phân công',
    'js.no_skills': 'Chưa có công cụ nào',
    'js.case_prompt': 'Câu hỏi thử nghiệm',
    'js.case_expected': 'Kết quả mong đợi (nếu có)',
  },
};

let _currentLang = 'vi';

function t(key, ...args) {
  const dict = I18N[_currentLang] || I18N.en;
  const val = dict[key] ?? (I18N.en[key] ?? key);
  return typeof val === 'function' ? val(...args) : val;
}

function applyTheme(theme) {
  document.body.classList.toggle('light', theme === 'light');
  document.getElementById('theme-dark')?.classList.toggle('selected', theme === 'dark');
  document.getElementById('theme-light')?.classList.toggle('selected', theme === 'light');
  const btn = document.getElementById('theme-toggle-btn');
  if (btn) btn.innerHTML = theme === 'light' ? icon('moon') : icon('sun');
  localStorage.setItem('hub_theme', theme);
}

function toggleTheme() {
  const current = document.body.classList.contains('light') ? 'light' : 'dark';
  applyTheme(current === 'light' ? 'dark' : 'light');
}

function applyLang(lang) {
  _currentLang = lang;
  document.documentElement.lang = lang;
  document.getElementById('lang-en')?.classList.toggle('selected', lang === 'en');
  document.getElementById('lang-vi')?.classList.toggle('selected', lang === 'vi');
  localStorage.setItem('hub_lang', lang);
  const dict = I18N[lang] || I18N.en;
  // textContent
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    const val = dict[key] ?? I18N.en[key];
    if (val !== undefined && typeof val !== 'function') el.textContent = val;
  });
  // placeholder
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const key = el.dataset.i18nPh;
    const val = dict[key] ?? I18N.en[key];
    if (val) el.placeholder = val;
  });
  // title attribute (sidebar buttons etc.)
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.dataset.i18nTitle;
    const val = dict[key] ?? I18N.en[key];
    if (val) el.title = val;
  });
  // Re-render dynamic content if already loaded
  if (agents.length) renderAgentList();
  if (skills.length) renderSkillList();
  if (currentProjectId && typeof opsRenderSubTab === 'function') opsRenderSubTab(currentProjectSubTab);
}

function loadSettings() {
  const theme = localStorage.getItem('hub_theme') || 'light';
  applyTheme(theme);
  const lang = localStorage.getItem('hub_lang') || 'vi';
  _currentLang = lang;
  applyLang(lang);
  const sidebarIconMode = localStorage.getItem('hub_sidebar_icon_mode') === '1';
  if (sidebarIconMode) document.querySelector('.hub-sidebar')?.classList.add('icon-mode');
  const pinToggle = document.getElementById('toggle-sidebar-pin');
  if (pinToggle) pinToggle.checked = localStorage.getItem('hub_sidebar_pinned') === '1';
  const animToggle = document.getElementById('toggle-animations');
  if (animToggle) animToggle.checked = localStorage.getItem('hub_animations') !== '0';
  const userEl = document.getElementById('settings-session-info');
  if (userEl) {
    const name = document.getElementById('topbar-user-name')?.textContent || '';
    userEl.textContent = name && name !== '—' ? t('js.logged_as', name) : '';
  }
}

// ════════════════════════════════════════
// Skill file upload
// ════════════════════════════════════════
function handleSkillFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    const ext = file.name.split('.').pop().toLowerCase();
    let parsed = null;

    if (ext === 'json') {
      try {
        parsed = JSON.parse(content);
        document.getElementById('skill-config').value = JSON.stringify(parsed, null, 2);
        if (parsed.name && !document.getElementById('skill-name').value)
          document.getElementById('skill-name').value = parsed.name;
        if (parsed.description && !document.getElementById('skill-description').value)
          document.getElementById('skill-description').value = parsed.description;
      } catch {
        showToast('Invalid JSON file', 'error');
        return;
      }
    } else if (ext === 'md' || ext === 'txt') {
      const lines = content.split('\n');
      const nameLine = lines.find(l => l.startsWith('# ') || l.startsWith('name:'));
      if (nameLine && !document.getElementById('skill-name').value) {
        document.getElementById('skill-name').value = nameLine.replace(/^#\s*|^name:\s*/i, '').trim();
      }
      // Auto-fill description from "description:" line or first paragraph after "## Mô tả" / "## Description"
      const descField = document.getElementById('skill-description');
      if (descField && !descField.value) {
        const descLine = lines.find(l => /^description:/i.test(l));
        if (descLine) {
          descField.value = descLine.replace(/^description:\s*/i, '').trim();
        } else {
          const descHeadIdx = lines.findIndex(l => /^##\s*(mô tả|description)/i.test(l));
          if (descHeadIdx !== -1) {
            const para = lines.slice(descHeadIdx + 1).find(l => l.trim() !== '');
            if (para) descField.value = para.trim();
          }
        }
      }
      document.getElementById('skill-config').value = JSON.stringify({ content }, null, 2);
    } else if (ext === 'yaml' || ext === 'yml') {
      document.getElementById('skill-config').value = JSON.stringify({ raw: content }, null, 2);
    }

    document.getElementById('skill-file-name').textContent = file.name;
    document.getElementById('skill-file-preview').style.display = 'flex';
    document.getElementById('skill-upload-zone').style.display = 'none';
  };
  reader.readAsText(file);
}

function clearSkillFile() {
  document.getElementById('skill-file-input').value = '';
  document.getElementById('skill-file-preview').style.display = 'none';
  document.getElementById('skill-upload-zone').style.display = '';
}

// Drag-and-drop for upload zone
document.addEventListener('DOMContentLoaded', () => {
  const zone = document.getElementById('skill-upload-zone');
  if (!zone) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) {
      const inp = document.getElementById('skill-file-input');
      const dt = new DataTransfer();
      dt.items.add(f);
      inp.files = dt.files;
      inp.dispatchEvent(new Event('change'));
    }
  });
});

// Wire match preview listeners on card modal inputs
document.getElementById('card-title').addEventListener('input', runMatchPreview);
document.getElementById('card-desc').addEventListener('input', runMatchPreview);

// ════════════════════════════════════════
// Boot
// ════════════════════════════════════════
loadSettings();
init();

// ════════════════════════════════════════
// Handle postMessage from taskrunner (run result popup navigation)
// ════════════════════════════════════════
window.addEventListener('message', (event) => {
  const msg = event.data;
  if (!msg || msg.type !== 'xanax:navigate') return;
  switchTab(msg.tab);
  if (msg.tab === 'tasks' && msg.projectId) {
    openProjectDetail(msg.projectId).then(() => {
      if (msg.subtab) switchProjectSubTab(msg.subtab);
    });
  }
});
