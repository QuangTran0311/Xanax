// Điểm vào của trang /hub — nạp bằng <script type="module">.
//
// Cầu `window.*` phía dưới tồn tại vì hub.html còn ~140 handler nội tuyến
// (onclick="...") mà phạm vi module không nhìn thấy. Đây là bắc cầu tạm thời:
// mỗi tab được chuyển sang event delegation thì xoá bớt tên khỏi đây, đến khi
// danh sách rỗng thì xoá cả khối. KHÔNG thêm tên mới vào đây.

import { cancelAgentForm, changeAgentWizardStep, checkDeptHeadPrompt, deleteAgent, deleteDepartmentConfirm, editDepartment, goAgentWizardStep, newAgent, openDepartmentModal, renderAgentList, resetDepartmentForm, saveAgent, saveDepartment, selectAgent, toggleAgentSkill, updateAgentPreview } from './hub/agents.js';
import { deleteAssetItem, setAssetsFilter } from './hub/assets.js';
import { logout } from './hub/auth.js';
import { addBenchModel, addTestCase, cancelBenchmark, createAndRunBenchmark, openBenchmark, removeBenchModel, removeTestCase, showBenchmarkCreate } from './hub/benchmark.js';
import { exportCostXlsx, loadCostTab, toggleCostDayRow, toggleCostModelRow, toggleTokenColumns } from './hub/cost.js';
import { addAgentModel, init, moveAgentModel, removeAgentModel, selectAvatar, selectAvatarShape } from './hub/init.js';
import { assignFromSuggestion, copyOutput, deleteCard, deleteKnowledgeDoc, deleteProject, openCardModal, openKnowledgeModal, openProjectModal, saveCard, saveOutputNotes, saveProject, setOutputPF, toggleOutputEdit } from './hub/knowledge.js';
import { approveMeetingItems, confirmFinalizeMeeting, createMeeting, deleteMeeting, endMeeting, finalizeMeeting, handleMeetingInputChange, meetingInputKeydown, newMeeting, openMeeting, openMeetingProject, resolveMeetingApproval, sendMeetingMessage, toggleParticipantsDropdown } from './hub/meetings.js';
import { _answerConfirm, closeModal } from './hub/modals.js';
import { deleteModel, livePreviewLimits, openModelModal, saveModel, selectModel, switchModelModalTab, testModel, updateCliModelHints, updateNativeModelHints } from './hub/model-pool.js';
import { openOpsDetails, opsApprove, opsOpenFeedback, opsSaveFeedback } from './hub/ops.js';
import { closeProjectDetail, filterProjectGrid, openProjectDetail, switchProjectSubTab } from './hub/projects.js';
import { cancelSkillForm, changeSkillWizardStep, chooseSkillType, deleteSkill, filterSkillsByType, goSkillWizardStep, newSkill, renderSkillList, saveSkill, selectSkill, testSkillConnection, toggleAllMcpTools, toggleMcpTool, toggleSkillSecret, updateBuiltinToolDescription, updateSkillImagePoolField } from './hub/skills.js';
import { switchTab } from './hub/tabs.js';
import { applyLang, applyTheme, loadSettings, saveAnimPref, saveSidebarPref, toggleSidebarIconMode, toggleTheme } from './hub/ui.js';
import { clearSkillFile, handleSkillFileUpload } from './hub/upload.js';
import './hub/api.js';
import './hub/avatar.js';
import './hub/icons.js';
import './hub/overview.js';
import './hub/utils.js';

Object.assign(window, {
  // agents
  cancelAgentForm, changeAgentWizardStep, checkDeptHeadPrompt, deleteAgent, deleteDepartmentConfirm, editDepartment, goAgentWizardStep, newAgent, openDepartmentModal, renderAgentList, resetDepartmentForm, saveAgent, saveDepartment, selectAgent, toggleAgentSkill, updateAgentPreview,
  // assets
  deleteAssetItem, setAssetsFilter,
  // auth
  logout,
  // benchmark
  addBenchModel, addTestCase, cancelBenchmark, createAndRunBenchmark, openBenchmark, removeBenchModel, removeTestCase, showBenchmarkCreate,
  // cost
  exportCostXlsx, loadCostTab, toggleCostDayRow, toggleCostModelRow, toggleTokenColumns,
  // init
  addAgentModel, moveAgentModel, removeAgentModel, selectAvatar, selectAvatarShape,
  // knowledge
  assignFromSuggestion, copyOutput, deleteCard, deleteKnowledgeDoc, deleteProject, openCardModal, openKnowledgeModal, openProjectModal, saveCard, saveOutputNotes, saveProject, setOutputPF, toggleOutputEdit,
  // meetings
  approveMeetingItems, confirmFinalizeMeeting, createMeeting, deleteMeeting, endMeeting, finalizeMeeting, handleMeetingInputChange, meetingInputKeydown, newMeeting, openMeeting, openMeetingProject, resolveMeetingApproval, sendMeetingMessage, toggleParticipantsDropdown,
  // modals
  _answerConfirm, closeModal,
  // model-pool
  deleteModel, livePreviewLimits, openModelModal, saveModel, selectModel, switchModelModalTab, testModel, updateCliModelHints, updateNativeModelHints,
  // ops
  openOpsDetails, opsApprove, opsOpenFeedback, opsSaveFeedback,
  // projects
  closeProjectDetail, filterProjectGrid, openProjectDetail, switchProjectSubTab,
  // skills
  cancelSkillForm, changeSkillWizardStep, chooseSkillType, deleteSkill, filterSkillsByType, goSkillWizardStep, newSkill, renderSkillList, saveSkill, selectSkill, testSkillConnection, toggleAllMcpTools, toggleMcpTool, toggleSkillSecret, updateBuiltinToolDescription, updateSkillImagePoolField,
  // tabs
  switchTab,
  // ui
  applyLang, applyTheme, saveAnimPref, saveSidebarPref, toggleSidebarIconMode, toggleTheme,
  // upload
  clearSkillFile, handleSkillFileUpload,
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
