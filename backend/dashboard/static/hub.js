// Điểm vào của trang /hub — nạp bằng <script type="module">.
//
// Hai việc: đăng ký hành động cho bộ điều phối sự kiện, rồi khởi động.
//
// Không còn onclick="..." ở đâu cả — cả hub.html lẫn HTML sinh ra lúc chạy đều
// khai báo data-click="tên", và hub/actions.js tra tên đó trong sổ dưới đây.
// Nhờ vậy không hàm nào phải nằm trên window nữa.

import { register } from './hub/actions.js';
import { cancelAgentForm, changeAgentWizardStep, checkDeptHeadPrompt, deleteAgent, deleteDepartmentConfirm, editDepartment, filterByDepartment, goAgentWizardStep, newAgent, openDepartmentModal, renderAgentList, resetDepartmentForm, saveAgent, saveDepartment, selectAgent, toggleAgentSkill, updateAgentPreview } from './hub/agents.js';
import { deleteAssetItem, pickAssetsFile, setAssetsFilter } from './hub/assets.js';
import { logout } from './hub/auth.js';
import { addBenchModel, addTestCase, benchModelInputKeydown, cancelBenchmark, createAndRunBenchmark, openBenchmark, removeBenchModel, removeTestCase, setBenchCaseCriteria, setBenchCasePrompt, showBenchmarkCreate } from './hub/benchmark.js';
import { exportCostXlsx, loadCostTab, toggleCostDayRow, toggleCostModelRow, toggleTokenColumns } from './hub/cost.js';
import { addAgentModel, init, moveAgentModel, removeAgentModel, selectAvatar, selectAvatarShape } from './hub/init.js';
import { assignFromSuggestion, copyOutput, deleteCard, deleteKnowledgeDoc, deleteProject, openCardModal, openKnowledgeModal, openProjectModal, saveCard, saveOutputNotes, saveProject, setOutputPF, toggleOutputEdit } from './hub/knowledge.js';
import { approveMeetingItems, confirmFinalizeMeeting, createMeeting, deleteMeeting, endMeeting, finalizeMeeting, handleMeetingInputChange, meetingInputKeydown, newMeeting, openMeeting, openMeetingProject, resolveMeetingApproval, sendMeetingMessage, toggleParticipantsDropdown } from './hub/meetings.js';
import { _answerConfirm, closeModal, dismissToast } from './hub/modals.js';
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

register({
  // agents
  cancelAgentForm, changeAgentWizardStep, checkDeptHeadPrompt, deleteAgent, deleteDepartmentConfirm, editDepartment, filterByDepartment, goAgentWizardStep, newAgent, openDepartmentModal, renderAgentList, resetDepartmentForm, saveAgent, saveDepartment, selectAgent, toggleAgentSkill, updateAgentPreview,
  // assets
  deleteAssetItem, pickAssetsFile, setAssetsFilter,
  // auth
  logout,
  // benchmark
  addBenchModel, addTestCase, benchModelInputKeydown, cancelBenchmark, createAndRunBenchmark, openBenchmark, removeBenchModel, removeTestCase, setBenchCaseCriteria, setBenchCasePrompt, showBenchmarkCreate,
  // cost
  exportCostXlsx, loadCostTab, toggleCostDayRow, toggleCostModelRow, toggleTokenColumns,
  // init
  addAgentModel, moveAgentModel, removeAgentModel, selectAvatar, selectAvatarShape,
  // knowledge
  assignFromSuggestion, copyOutput, deleteCard, deleteKnowledgeDoc, deleteProject, openCardModal, openKnowledgeModal, openProjectModal, saveCard, saveOutputNotes, saveProject, setOutputPF, toggleOutputEdit,
  // meetings
  approveMeetingItems, confirmFinalizeMeeting, createMeeting, deleteMeeting, endMeeting, finalizeMeeting, handleMeetingInputChange, meetingInputKeydown, newMeeting, openMeeting, openMeetingProject, resolveMeetingApproval, sendMeetingMessage, toggleParticipantsDropdown,
  // modals
  _answerConfirm, closeModal, dismissToast,
  // model-pool
  deleteCurrentModel, livePreviewLimits, openCurrentModelModal, openModelModal, saveModel, selectModel, switchModelModalTab, testCurrentModel, updateCliModelHints, updateNativeModelHints,
  // ops
  openOpsDetails, opsApprove, opsOpenFeedback, opsSaveFeedback,
  // projects
  closeProjectDetail, filterProjectGrid, openCurrentProjectModal, openProjectDetail, switchProjectSubTab,
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
