import { agents, renderAgentList } from './agents.js';
import { api } from './api.js';
import { logout } from './auth.js';
import { icon } from './icons.js';
import { meetings } from './meetings.js';
import { opsRenderSubTab } from './ops.js';
import { currentProjectId, currentProjectSubTab } from './projects.js';
import { renderSkillList, skills } from './skills.js';

// Sidebar collapse
// ════════════════════════════════════════
export function toggleSidebarIconMode() {
  const sb = document.querySelector('.hub-sidebar');
  const iconMode = sb.classList.toggle('icon-mode');
  localStorage.setItem('hub_sidebar_icon_mode', iconMode ? '1' : '0');
}
export function saveSidebarPref(pinned) {
  localStorage.setItem('hub_sidebar_pinned', pinned ? '1' : '0');
}
export function saveAnimPref(on) {
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

export function t(key, ...args) {
  const dict = I18N[_currentLang] || I18N.en;
  const val = dict[key] ?? (I18N.en[key] ?? key);
  return typeof val === 'function' ? val(...args) : val;
}

export function applyTheme(theme) {
  document.body.classList.toggle('light', theme === 'light');
  document.getElementById('theme-dark')?.classList.toggle('selected', theme === 'dark');
  document.getElementById('theme-light')?.classList.toggle('selected', theme === 'light');
  const btn = document.getElementById('theme-toggle-btn');
  if (btn) btn.innerHTML = theme === 'light' ? icon('moon') : icon('sun');
  localStorage.setItem('hub_theme', theme);
}

export function toggleTheme() {
  const current = document.body.classList.contains('light') ? 'light' : 'dark';
  applyTheme(current === 'light' ? 'dark' : 'light');
}

export function applyLang(lang) {
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

export function loadSettings() {
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
