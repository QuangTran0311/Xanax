// Điểm vào của trang /hub — nạp bằng <script type="module">.
//
// Hai việc: đăng ký hành động cho bộ điều phối sự kiện, rồi khởi động.
//
// hub.html không còn onclick="..." nào; mọi nút khai báo data-click="tên" và
// bộ điều phối trong hub/actions.js tra tên đó trong sổ đăng ký dưới đây.

import { register } from './hub/actions.js';
import { cancelAgentForm, changeAgentWizardStep, checkDeptHeadPrompt, deleteAgent, deleteDepartmentConfirm, editDepartment, goAgentWizardStep, newAgent, openDepartmentModal, renderAgentList, resetDepartmentForm, saveAgent, saveDepartment, selectAgent, toggleAgentSkill, updateAgentPreview } from './hub/agents.js';
import { deleteAssetItem, pickAssetsFile, setAssetsFilter } from './hub/assets.js';
import { logout } from './hub/auth.js';
import { addBenchModel, addTestCase, benchModelInputKeydown, cancelBenchmark, createAndRunBenchmark, openBenchmark, removeBenchModel, removeTestCase, showBenchmarkCreate } from './hub/benchmark.js';
import { exportCostXlsx, loadCostTab, toggleCostDayRow, toggleCostModelRow, toggleTokenColumns } from './hub/cost.js';
import { addAgentModel, init, moveAgentModel, removeAgentModel, selectAvatar, selectAvatarShape } from './hub/init.js';
import { assignFromSuggestion, copyOutput, deleteCard, deleteKnowledgeDoc, deleteProject, openCardModal, openKnowledgeModal, openProjectModal, saveCard, saveOutputNotes, saveProject, setOutputPF, toggleOutputEdit } from './hub/knowledge.js';
import { approveMeetingItems, confirmFinalizeMeeting, createMeeting, deleteMeeting, endMeeting, finalizeMeeting, handleMeetingInputChange, meetingInputKeydown, newMeeting, openMeeting, openMeetingProject, resolveMeetingApproval, sendMeetingMessage, toggleParticipantsDropdown } from './hub/meetings.js';
import { _answerConfirm, closeModal } from './hub/modals.js';
import { deleteCurrentModel, livePreviewLimits, openCurrentModelModal, openModelModal, saveModel, selectModel, switchModelModalTab, testCurrentModel, updateCliModelHints, updateNativeModelHints } from './hub/model-pool.js';
import { openOpsDetails, opsApprove, opsOpenFeedback, opsSaveFeedback } from './hub/ops.js';
import { closeProjectDetail, filterProjectGrid, openCurrentProjectModal, openProjectDetail, switchProjectSubTab } from './hub/projects.js';
import { cancelSkillForm, changeSkillWizardStep, chooseSkillType, deleteSkill, filterSkillsByType, goSkillWizardStep, newSkill, renderSkillList, saveSkill, selectSkill, testSkillConnection, toggleAllMcpTools, toggleMcpTool, toggleSkillSecret, updateBuiltinToolDescription, updateSkillImagePoolField } from './hub/skills.js';
import { switchTab } from './hub/tabs.js';
import { applyLang, applyTheme, loadSettings, saveAnimPref, saveSidebarPref, toggleSidebarIconMode, toggleTheme } from './hub/ui.js';
import { clearSkillFile, handleSkillFileUpload } from './hub/upload.js';
import './hub/actions.js';
import './hub/api.js';
import './hub/avatar.js';
import './hub/icons.js';
import './hub/overview.js';
import './hub/utils.js';

// Hành động dùng bởi data-* trong hub.html.
register({
  // agents
  cancelAgentForm, changeAgentWizardStep, checkDeptHeadPrompt, deleteAgent, goAgentWizardStep, newAgent, openDepartmentModal, renderAgentList, resetDepartmentForm, saveAgent, saveDepartment, updateAgentPreview,
  // assets
  pickAssetsFile,
  // auth
  logout,
  // benchmark
  addBenchModel, addTestCase, benchModelInputKeydown, cancelBenchmark, createAndRunBenchmark, showBenchmarkCreate,
  // cost
  exportCostXlsx, loadCostTab, toggleTokenColumns,
  // init
  addAgentModel,
  // knowledge
  deleteCard, deleteProject, openProjectModal, saveCard, saveProject,
  // meetings
  confirmFinalizeMeeting, createMeeting, endMeeting, finalizeMeeting, handleMeetingInputChange, meetingInputKeydown, newMeeting, sendMeetingMessage, toggleParticipantsDropdown,
  // modals
  _answerConfirm, closeModal,
  // model-pool
  deleteCurrentModel, livePreviewLimits, openCurrentModelModal, openModelModal, saveModel, switchModelModalTab, testCurrentModel, updateCliModelHints, updateNativeModelHints,
  // ops
  opsSaveFeedback,
  // projects
  closeProjectDetail, filterProjectGrid, openCurrentProjectModal, switchProjectSubTab,
  // skills
  cancelSkillForm, changeSkillWizardStep, chooseSkillType, deleteSkill, goSkillWizardStep, newSkill, renderSkillList, saveSkill, testSkillConnection, toggleSkillSecret, updateBuiltinToolDescription, updateSkillImagePoolField,
  // tabs
  switchTab,
  // ui
  applyLang, applyTheme, saveAnimPref, saveSidebarPref, toggleSidebarIconMode, toggleTheme,
  // upload
  clearSkillFile, handleSkillFileUpload,
});

// Cầu tạm còn lại: 58 chỗ onclick="..." vẫn nằm trong template string của
// các hàm render trong hub/*.js, và HTML sinh ra lúc chạy thì chỉ thấy phạm vi
// toàn cục. Chuyển nốt các chỗ đó sang data-* sẽ xoá được cả khối này.
// KHÔNG thêm tên mới vào đây.
Object.assign(window, {
  // agents
  deleteDepartmentConfirm, editDepartment, selectAgent, toggleAgentSkill,
  // assets
  deleteAssetItem, setAssetsFilter,
  // benchmark
  addBenchModel, openBenchmark, removeBenchModel, removeTestCase,
  // cost
  toggleCostDayRow, toggleCostModelRow,
  // init
  moveAgentModel, removeAgentModel, selectAvatar, selectAvatarShape,
  // knowledge
  assignFromSuggestion, copyOutput, deleteKnowledgeDoc, openCardModal, openKnowledgeModal, saveOutputNotes, setOutputPF, toggleOutputEdit,
  // meetings
  approveMeetingItems, deleteMeeting, openMeeting, openMeetingProject, resolveMeetingApproval,
  // model-pool
  selectModel,
  // ops
  openOpsDetails, opsApprove, opsOpenFeedback,
  // projects
  openProjectDetail, switchProjectSubTab,
  // skills
  filterSkillsByType, selectSkill, toggleAllMcpTools, toggleMcpTool,
  // tabs
  switchTab,
});

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
