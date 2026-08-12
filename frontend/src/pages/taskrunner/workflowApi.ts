import { apiClient } from "../../api/client";
import type {
  AgentOption,
  ProjectOption,
  SkillOption,
  ToolOption,
  WorkflowOutput,
  WorkflowRun,
  WorkflowTask,
} from "./types";

export const workflowApi = {
  tasks: (kind?: "company" | "automation") =>
    apiClient.get<{ tasks: WorkflowTask[] }>(`/workflow/tasks${kind ? `?kind=${kind}` : ""}`),
  task: (id: number) => apiClient.get<WorkflowTask>(`/workflow/tasks/${id}`),
  createTask: (body: Partial<WorkflowTask> & Pick<WorkflowTask, "name" | "kind">) =>
    apiClient.post<WorkflowTask>("/workflow/tasks", body),
  updateTask: (id: number, body: Partial<WorkflowTask>) =>
    apiClient.patch<WorkflowTask>(`/workflow/tasks/${id}`, body),
  deleteTask: (id: number) => apiClient.delete<void>(`/workflow/tasks/${id}`),
  runs: (taskId: number, limit = 50) =>
    apiClient.get<{ runs: WorkflowRun[] }>(`/workflow/runs?task_id=${taskId}&limit=${limit}`),
  run: (runId: number) => apiClient.get<WorkflowRun>(`/workflow/runs/${runId}`),
  updateOutput: (outputId: number, body: Partial<WorkflowOutput>) =>
    apiClient.patch<{ ok: true }>(`/workflow/outputs/${outputId}`, body),
  chooseImageSource: (runId: number, body: { node_id: string; mode: "generate" | "asset"; asset_id?: number }) =>
    apiClient.post<{ ok: true }>(`/workflow/runs/${runId}/image-source`, body),
  projects: () => apiClient.get<{ projects: ProjectOption[] }>("/projects/"),
  agents: () => apiClient.get<{ agents: AgentOption[] }>("/agent-configs/"),
  skills: () => apiClient.get<{ skills: SkillOption[] }>("/skills/"),
  tools: () => apiClient.get<{ tools: ToolOption[] }>("/tools/"),
};
