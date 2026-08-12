/** Generated once from backend /api/openapi.json during Phase 1. */
export interface components {
  schemas: {
    "AgentConfigCreate": { "name": string; "role"?: string; "model"?: string; "model_pool_ids"?: Array<number>; "system_prompt"?: string; "avatar_color"?: string; "avatar_icon"?: string; "skills"?: Array<number>; "skill_tools"?: { [key: string]: Array<string> }; "department_id"?: number | null };
    "AgentConfigUpdate": { "name"?: string | null; "role"?: string | null; "model"?: string | null; "model_pool_ids"?: Array<number> | null; "system_prompt"?: string | null; "avatar_color"?: string | null; "avatar_icon"?: string | null; "skills"?: Array<number> | null; "skill_tools"?: { [key: string]: Array<string> } | null; "enabled"?: number | null; "department_id"?: number | null };
    "AgentRunStatus": "pending" | "running" | "completed" | "failed" | "cancelled";
    "AppendSoulRequest": { "content": string };
    "ApproveBody": { "is_test"?: boolean };
    "BenchmarkCreate": { "name": string; "role_description"?: string; "test_cases"?: Array<components["schemas"]["TestCase"]>; "models"?: Array<string> };
    "Body_upload_asset_api_assets_upload_post": { "file": string; "note"?: string };
    "CallToolRequest": { "name": string; "args"?: { [key: string]: unknown } };
    "CloseSessionRequest": { "notes"?: string };
    "ConnectionTest": { "type": string; "config"?: { [key: string]: unknown }; "skill_id"?: number | null };
    "DepartmentCreate": { "name": string; "description"?: string; "color"?: string; "head_agent_id"?: number | null };
    "DepartmentUpdate": { "name"?: string | null; "description"?: string | null; "color"?: string | null; "head_agent_id"?: number | null };
    "DocCreate": { "title": string; "content"?: string; "project_id"?: number | null; "tags"?: string };
    "DocUpdate": { "title"?: string | null; "content"?: string | null; "project_id"?: number | null; "tags"?: string | null };
    "EnqueueTaskRequest": { "name": string; "payload"?: { [key: string]: unknown }; "priority"?: number };
    "FeedbackBody": { "action": string; "text": string; "is_test"?: boolean };
    "HTTPValidationError": { "detail"?: Array<components["schemas"]["ValidationError"]> };
    "ImageSourceChoice": { "node_id": string; "mode"?: string; "asset_id"?: number | null };
    "LoginRequest": { "username": string; "password": string };
    "MatchPreview": { "title"?: string; "description"?: string };
    "MeetingCreate": { "title": string; "topic"?: string; "participants"?: Array<number>; "project_id"?: number | null };
    "MeetingFinalize": { "decision_text": string };
    "MeetingItemsApproval": { "items"?: Array<components["schemas"]["ProposedItemApproval"]> };
    "MeetingUpdate": { "title"?: string | null; "topic"?: string | null; "participants"?: Array<number> | null; "status"?: string | null };
    "ModelPoolCreate": { "name": string; "provider"?: string; "api_style"?: string; "model_id": string; "base_url"?: string; "api_key"?: string; "cli_config_dir"?: string; "category"?: string; "max_requests_per_day"?: number; "max_tokens_per_day"?: number; "price_input_per_1m"?: number; "price_cache_per_1m"?: number; "price_output_per_1m"?: number; "currency"?: string };
    "ModelPoolUpdate": { "name"?: string | null; "provider"?: string | null; "api_style"?: string | null; "model_id"?: string | null; "base_url"?: string | null; "api_key"?: string | null; "cli_config_dir"?: string | null; "category"?: string | null; "max_requests_per_day"?: number | null; "max_tokens_per_day"?: number | null; "price_input_per_1m"?: number | null; "price_cache_per_1m"?: number | null; "price_output_per_1m"?: number | null; "currency"?: string | null; "enabled"?: boolean | null };
    "OutputUpdate": { "pass_fail"?: string | null; "edited_content"?: string | null; "notes"?: string | null; "review_status"?: string | null };
    "ProjectCreate": { "name": string; "description"?: string };
    "ProjectUpdate": { "name"?: string | null; "description"?: string | null; "status"?: string | null };
    "ProposedItemApproval": { "title": string; "description"?: string; "priority"?: string; "assigned_agent_id"?: number | null; "include"?: boolean };
    "SkillCreate": { "name": string; "description"?: string; "type"?: string; "config"?: { [key: string]: unknown } };
    "SkillUpdate": { "name"?: string | null; "description"?: string | null; "type"?: string | null; "config"?: { [key: string]: unknown } | null; "enabled"?: number | null };
    "SpawnAgentRequest": { "task": string; "agent_name"?: string; "metadata"?: { [key: string]: unknown } };
    "SpawnAgentResponse": { "record_id": string; "agent_name": string; "task": string; "status": string; "message": string };
    "StatusBody": { "status": string };
    "TaskStatus": "pending" | "running" | "done" | "failed" | "cancelled";
    "TestCase": { "prompt": string; "criteria"?: string };
    "UpdateSessionRequest": { "status"?: string | null; "result_notes"?: string | null; "title"?: string | null; "task_description"?: string | null; "allowed_tools"?: Array<string> | null };
    "ValidationError": { "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: {  } };
    "WorkItemCreate": { "title": string; "description"?: string; "status"?: string; "priority"?: string; "assigned_agent_id"?: number | null };
    "WorkItemUpdate": { "title"?: string | null; "description"?: string | null; "status"?: string | null; "priority"?: string | null; "assigned_agent_id"?: number | null };
    "WorkflowTaskCreate": { "name": string; "kind"?: string; "description"?: string; "project_id"?: number | null; "agents_json"?: string; "graph_json"?: string; "trigger_type"?: string; "trigger_config_json"?: string; "schedule_enabled"?: boolean; "schedule_cron"?: string };
    "WorkflowTaskUpdate": { "name"?: string | null; "description"?: string | null; "project_id"?: number | null; "agents_json"?: string | null; "graph_json"?: string | null; "trigger_type"?: string | null; "trigger_config_json"?: string | null; "schedule_enabled"?: boolean | null; "schedule_cron"?: string | null; "status"?: string | null; "kind"?: string | null };
    "api__routes__chat__CreateSessionRequest": { "title"?: string };
    "api__routes__training__CreateSessionRequest": { "title": string; "task_description"?: string; "agent_id"?: number | null; "project_id"?: number | null };
  };
}

export interface paths {
  "/api/health": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/health/ready": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/agents/spawn": {
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["SpawnAgentRequest"];
      } };
      responses: {
        "200": { content: { "application/json": components["schemas"]["SpawnAgentResponse"] } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/agents/": {
    get: {
      parameters: {
        "query": { "status"?: components["schemas"]["AgentRunStatus"] | null; "limit"?: number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/agents/stats": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/agents/{record_id}": {
    get: {
      parameters: {
        "path": { "record_id": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "record_id": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/tasks/enqueue": {
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["EnqueueTaskRequest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/tasks/": {
    get: {
      parameters: {
        "query": { "status"?: components["schemas"]["TaskStatus"] | null; "limit"?: number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/tasks/stats": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/tasks/jobs": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/tasks/{task_id}": {
    get: {
      parameters: {
        "path": { "task_id": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "task_id": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/tools/": {
    get: {
      parameters: {
        "query": { "tag"?: string | null };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/tools/mcp/status": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/tools/{tool_name}": {
    get: {
      parameters: {
        "path": { "tool_name": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/tools/call": {
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["CallToolRequest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/chat/sessions": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["api__routes__chat__CreateSessionRequest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/chat/sessions/{session_id}": {
    get: {
      parameters: {
        "path": { "session_id": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "session_id": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/chat/sessions/{session_id}/messages": {
    get: {
      parameters: {
        "path": { "session_id": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/chat/hermes/status": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/auth/login": {
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["LoginRequest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/auth/logout": {
    post: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/auth/me": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/training/sessions": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["api__routes__training__CreateSessionRequest"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/training/sessions/{session_id}": {
    get: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "session_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["UpdateSessionRequest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/training/sessions/{session_id}/tools": {
    get: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/training/sessions/{session_id}/distill": {
    post: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/training/sessions/{session_id}/image/{name}": {
    get: {
      parameters: {
        "path": { "session_id": number; "name": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/training/sessions/{session_id}/close": {
    post: {
      parameters: {
        "path": { "session_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["CloseSessionRequest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/training/sessions/{session_id}/reopen": {
    post: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/training/soul": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/training/soul/append": {
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["AppendSoulRequest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/task-sessions/sessions": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/task-sessions/sessions/{session_id}": {
    get: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/task-sessions/sessions/{session_id}/logs": {
    get: {
      parameters: {
        "path": { "session_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/agent-configs/": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["AgentConfigCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/agent-configs/{agent_id}": {
    get: {
      parameters: {
        "path": { "agent_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "agent_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["AgentConfigUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "agent_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/departments/": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["DepartmentCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/departments/{department_id}": {
    get: {
      parameters: {
        "path": { "department_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "department_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["DepartmentUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "department_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/skills/": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["SkillCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/skills/test-connection": {
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["ConnectionTest"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/skills/{skill_id}": {
    get: {
      parameters: {
        "path": { "skill_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "skill_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["SkillUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "skill_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/skills/{skill_id}/tools": {
    get: {
      parameters: {
        "path": { "skill_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/projects/": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["ProjectCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/projects/{project_id}": {
    get: {
      parameters: {
        "path": { "project_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "project_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["ProjectUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "project_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/projects/{project_id}/archive": {
    get: {
      parameters: {
        "path": { "project_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/projects/{project_id}/archive-file": {
    get: {
      parameters: {
        "path": { "project_id": number };
        "query": { "path": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/projects/items/alerts": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/projects/items/match": {
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["MatchPreview"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/projects/{project_id}/items": {
    get: {
      parameters: {
        "path": { "project_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    post: {
      parameters: {
        "path": { "project_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["WorkItemCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/projects/items/{item_id}": {
    patch: {
      parameters: {
        "path": { "item_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["WorkItemUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "item_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/meetings/": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["MeetingCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/meetings/messages/recent": {
    get: {
      parameters: {
        "query": { "limit"?: number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/meetings/{meeting_id}": {
    get: {
      parameters: {
        "path": { "meeting_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "meeting_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["MeetingUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "meeting_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/meetings/{meeting_id}/finalize": {
    post: {
      parameters: {
        "path": { "meeting_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["MeetingFinalize"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/meetings/{meeting_id}/approve-items": {
    post: {
      parameters: {
        "path": { "meeting_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["MeetingItemsApproval"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/meetings/{meeting_id}/messages": {
    get: {
      parameters: {
        "path": { "meeting_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/benchmarks/": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["BenchmarkCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/benchmarks/{benchmark_id}": {
    get: {
      parameters: {
        "path": { "benchmark_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "benchmark_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/benchmarks/{benchmark_id}/results": {
    get: {
      parameters: {
        "path": { "benchmark_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/tasks": {
    get: {
      parameters: {
        "query": { "project_id"?: number | null; "kind"?: string | null };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["WorkflowTaskCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/tasks/{task_id}": {
    get: {
      parameters: {
        "path": { "task_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "task_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["WorkflowTaskUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "task_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/runs": {
    get: {
      parameters: {
        "query": { "task_id"?: number | null; "project_id"?: number | null; "limit"?: number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/runs/{run_id}": {
    get: {
      parameters: {
        "path": { "run_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "run_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/runs/{run_id}/archive-file": {
    get: {
      parameters: {
        "path": { "run_id": number };
        "query": { "path": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/outputs/{output_id}": {
    patch: {
      parameters: {
        "path": { "output_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["OutputUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/runs/{run_id}/image-source": {
    post: {
      parameters: {
        "path": { "run_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["ImageSourceChoice"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/workflow/hooks/{token}": {
    post: {
      parameters: {
        "path": { "token": string };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool": {
    get: {
      parameters: {
        "query": { "enabled_only"?: boolean };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["ModelPoolCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool/stats": {
    get: {
      parameters: {
        "query": { "limit"?: number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool/cost/summary": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/model-pool/cost/report": {
    get: {
      parameters: {
        "query": { "period"?: string; "date_from"?: string | null; "date_to"?: string | null };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool/cost/report-hourly": {
    get: {
      parameters: {
        "query": { "date"?: string | null };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool/cost/report-calls": {
    get: {
      parameters: {
        "query": { "date"?: string | null };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool/cost/overview": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/model-pool/cost/export.xlsx": {
    get: {
      parameters: {
        "query": { "period"?: string; "date_from"?: string | null; "date_to"?: string | null };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool/{entry_id}": {
    get: {
      parameters: {
        "path": { "entry_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "entry_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["ModelPoolUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "entry_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/model-pool/{entry_id}/test": {
    post: {
      parameters: {
        "path": { "entry_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/knowledge": {
    get: {
      parameters: {
        "query": { "project_id"?: number | null };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    post: {
      requestBody: { content: {
        "application/json": components["schemas"]["DocCreate"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/knowledge/search": {
    get: {
      parameters: {
        "query": { "q": string; "project_id"?: number | null; "top_k"?: number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/knowledge/{doc_id}": {
    get: {
      parameters: {
        "path": { "doc_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    patch: {
      parameters: {
        "path": { "doc_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["DocUpdate"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
    delete: {
      parameters: {
        "path": { "doc_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/ops/items": {
    get: {
      parameters: {
        "query": { "project_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/ops/history": {
    get: {
      parameters: {
        "query": { "project_id": number; "limit"?: number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/ops/items/{item_id}/approve": {
    post: {
      parameters: {
        "path": { "item_id": number };
      };
      requestBody?: { content: {
        "application/json": components["schemas"]["ApproveBody"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/ops/items/{item_id}/feedback": {
    post: {
      parameters: {
        "path": { "item_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["FeedbackBody"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/ops/items/{item_id}": {
    patch: {
      parameters: {
        "path": { "item_id": number };
      };
      requestBody: { content: {
        "application/json": components["schemas"]["StatusBody"];
      } };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/assets/upload": {
    post: {
      requestBody: { content: {
        "multipart/form-data": components["schemas"]["Body_upload_asset_api_assets_upload_post"];
      } };
      responses: {
        "201": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/assets/": {
    get: {
      responses: {
        "200": { content: { "application/json": unknown } };
      };
    };
  };
  "/api/assets/benchmark-results/{result_id}/download": {
    get: {
      parameters: {
        "path": { "result_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/assets/{asset_id}/download": {
    get: {
      parameters: {
        "path": { "asset_id": number };
      };
      responses: {
        "200": { content: { "application/json": unknown } };
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
  "/api/assets/{asset_id}": {
    delete: {
      parameters: {
        "path": { "asset_id": number };
      };
      responses: {
        "204": unknown;
        "422": { content: { "application/json": components["schemas"]["HTTPValidationError"] } };
      };
    };
  };
}

export type LoginRequest = components["schemas"]["LoginRequest"];
export interface LoginResponse { ok: true; username: string; }
export interface CurrentUser { username: string; }
export interface ErrorResponse { detail?: string | Array<{ loc: Array<string | number>; msg: string; type: string }>; message?: string; }
