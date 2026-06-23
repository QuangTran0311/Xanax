-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "username" VARCHAR(100) NOT NULL,
    "email" VARCHAR(255),
    "role" VARCHAR(20) NOT NULL DEFAULT 'owner',
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sessions" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "title" TEXT,
    "status" VARCHAR(20) NOT NULL DEFAULT 'active',
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "endedAt" TIMESTAMP(3),
    "totalMessages" INTEGER NOT NULL DEFAULT 0,
    "totalToolCalls" INTEGER NOT NULL DEFAULT 0,
    "totalCostUsd" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "summary" TEXT,
    "tags" TEXT[],
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "messages" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "sequenceNo" INTEGER NOT NULL,
    "role" VARCHAR(20) NOT NULL,
    "contentType" VARCHAR(30) NOT NULL DEFAULT 'text',
    "content" TEXT,
    "artifactId" TEXT,
    "modelId" VARCHAR(100),
    "inputTokens" INTEGER,
    "outputTokens" INTEGER,
    "costUsd" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "messages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tool_calls" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "messageId" TEXT NOT NULL,
    "sequenceNo" INTEGER NOT NULL,
    "toolName" VARCHAR(100) NOT NULL,
    "inputParams" JSONB,
    "outputResult" JSONB,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "errorMsg" TEXT,
    "latencyMs" INTEGER,
    "costUsd" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "calledAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP(3),

    CONSTRAINT "tool_calls_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "artifacts" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "toolCallId" TEXT,
    "artifactType" VARCHAR(30) NOT NULL,
    "fileName" VARCHAR(255),
    "mimeType" VARCHAR(100),
    "sizeBytes" INTEGER,
    "storageRef" TEXT NOT NULL,
    "checksum" VARCHAR(64),
    "isDeleted" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "artifacts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "execution_logs" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "toolCallId" TEXT,
    "level" VARCHAR(10) NOT NULL,
    "message" TEXT NOT NULL,
    "context" JSONB,
    "loggedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "execution_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "model_registry" (
    "modelId" VARCHAR(100) NOT NULL,
    "provider" VARCHAR(50) NOT NULL,
    "modality" VARCHAR(20) NOT NULL,
    "subTypes" TEXT[],
    "contextWindow" INTEGER,
    "supportsStream" BOOLEAN NOT NULL DEFAULT true,
    "inputFormats" TEXT[],
    "outputFormats" TEXT[],
    "costPer1kInput" DOUBLE PRECISION,
    "costPer1kOutput" DOUBLE PRECISION,
    "costPerUnit" DOUBLE PRECISION,
    "apiEndpoint" TEXT,
    "apiKeyRef" VARCHAR(100),
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "notes" TEXT,
    "addedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "model_registry_pkey" PRIMARY KEY ("modelId")
);

-- CreateTable
CREATE TABLE "model_usage_logs" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "toolCallId" TEXT,
    "modelId" VARCHAR(100) NOT NULL,
    "taskType" VARCHAR(50) NOT NULL,
    "inputTokens" INTEGER,
    "outputTokens" INTEGER,
    "inputChars" INTEGER,
    "latencyMs" INTEGER,
    "costUsd" DOUBLE PRECISION,
    "success" BOOLEAN NOT NULL DEFAULT true,
    "errorMsg" TEXT,
    "userRating" INTEGER,
    "autoQuality" DOUBLE PRECISION,
    "feedbackNote" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "model_usage_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "model_scores" (
    "id" TEXT NOT NULL,
    "modelId" VARCHAR(100) NOT NULL,
    "taskType" VARCHAR(50) NOT NULL,
    "avgLatencyMs" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "avgCostUsd" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "successRate" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    "qualityScore" DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    "sampleCount" INTEGER NOT NULL DEFAULT 0,
    "finalScore" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "model_scores_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "routing_rules" (
    "id" TEXT NOT NULL,
    "ruleName" VARCHAR(100) NOT NULL,
    "priority" INTEGER NOT NULL DEFAULT 50,
    "modality" VARCHAR(20),
    "conditions" JSONB NOT NULL,
    "preferredModels" TEXT[],
    "excludedModels" TEXT[],
    "overrideScore" BOOLEAN NOT NULL DEFAULT false,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdBy" VARCHAR(20) NOT NULL DEFAULT 'human',
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "routing_rules_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "soul_knowledge" (
    "id" TEXT NOT NULL,
    "agentId" VARCHAR(50) NOT NULL DEFAULT 'hermes',
    "category" VARCHAR(50) NOT NULL,
    "key" VARCHAR(100) NOT NULL,
    "content" TEXT NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "soul_knowledge_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "learned_patterns" (
    "id" TEXT NOT NULL,
    "agentId" VARCHAR(50) NOT NULL DEFAULT 'hermes',
    "pattern" TEXT NOT NULL,
    "source" VARCHAR(20) NOT NULL DEFAULT 'auto_learned',
    "confidence" DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    "useCount" INTEGER NOT NULL DEFAULT 0,
    "lastUsed" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "learned_patterns_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "soul_update_candidates" (
    "id" TEXT NOT NULL,
    "agentId" VARCHAR(50) NOT NULL DEFAULT 'hermes',
    "suggestedKey" VARCHAR(100) NOT NULL,
    "suggestedContent" TEXT NOT NULL,
    "reason" TEXT,
    "sourcePatternId" TEXT,
    "confidence" DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "reviewedBy" VARCHAR(100),
    "reviewedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "soul_update_candidates_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "episodes" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "agentId" VARCHAR(50) NOT NULL DEFAULT 'hermes',
    "taskSummary" TEXT,
    "keyActions" TEXT[],
    "outcome" VARCHAR(20),
    "userRating" INTEGER,
    "reflection" TEXT,
    "embedding" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "episodes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_roles" (
    "id" TEXT NOT NULL,
    "roleCode" VARCHAR(20) NOT NULL,
    "roleName" VARCHAR(100) NOT NULL,
    "expertise" TEXT,
    "systemPrompt" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_roles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "meeting_rooms" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "objective" TEXT,
    "status" VARCHAR(20) NOT NULL DEFAULT 'opened',
    "openedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "closedAt" TIMESTAMP(3),

    CONSTRAINT "meeting_rooms_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "meeting_members" (
    "id" TEXT NOT NULL,
    "meetingId" TEXT NOT NULL,
    "modelId" VARCHAR(100) NOT NULL,
    "roleId" TEXT NOT NULL,
    "isChair" BOOLEAN NOT NULL DEFAULT false,
    "joinedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "meeting_members_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "meeting_turns" (
    "id" TEXT NOT NULL,
    "meetingId" TEXT NOT NULL,
    "memberId" TEXT NOT NULL,
    "turnNo" INTEGER NOT NULL,
    "turnType" VARCHAR(20) NOT NULL,
    "addressedTo" TEXT,
    "content" TEXT NOT NULL,
    "latencyMs" INTEGER,
    "costUsd" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "meeting_turns_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "meeting_reports" (
    "id" TEXT NOT NULL,
    "meetingId" TEXT NOT NULL,
    "authorId" TEXT NOT NULL,
    "summary" TEXT,
    "decisions" TEXT,
    "actionItems" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "meeting_reports_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_username_key" ON "users"("username");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "model_scores_modelId_taskType_key" ON "model_scores"("modelId", "taskType");

-- CreateIndex
CREATE UNIQUE INDEX "routing_rules_ruleName_key" ON "routing_rules"("ruleName");

-- CreateIndex
CREATE UNIQUE INDEX "soul_knowledge_agentId_key_key" ON "soul_knowledge"("agentId", "key");

-- CreateIndex
CREATE UNIQUE INDEX "episodes_sessionId_key" ON "episodes"("sessionId");

-- CreateIndex
CREATE UNIQUE INDEX "agent_roles_roleCode_key" ON "agent_roles"("roleCode");

-- CreateIndex
CREATE UNIQUE INDEX "meeting_rooms_sessionId_key" ON "meeting_rooms"("sessionId");

-- AddForeignKey
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "messages" ADD CONSTRAINT "messages_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tool_calls" ADD CONSTRAINT "tool_calls_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tool_calls" ADD CONSTRAINT "tool_calls_messageId_fkey" FOREIGN KEY ("messageId") REFERENCES "messages"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "artifacts" ADD CONSTRAINT "artifacts_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "artifacts" ADD CONSTRAINT "artifacts_toolCallId_fkey" FOREIGN KEY ("toolCallId") REFERENCES "tool_calls"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "execution_logs" ADD CONSTRAINT "execution_logs_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "execution_logs" ADD CONSTRAINT "execution_logs_toolCallId_fkey" FOREIGN KEY ("toolCallId") REFERENCES "tool_calls"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "model_usage_logs" ADD CONSTRAINT "model_usage_logs_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "model_usage_logs" ADD CONSTRAINT "model_usage_logs_toolCallId_fkey" FOREIGN KEY ("toolCallId") REFERENCES "tool_calls"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "model_usage_logs" ADD CONSTRAINT "model_usage_logs_modelId_fkey" FOREIGN KEY ("modelId") REFERENCES "model_registry"("modelId") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "model_scores" ADD CONSTRAINT "model_scores_modelId_fkey" FOREIGN KEY ("modelId") REFERENCES "model_registry"("modelId") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "soul_update_candidates" ADD CONSTRAINT "soul_update_candidates_sourcePatternId_fkey" FOREIGN KEY ("sourcePatternId") REFERENCES "learned_patterns"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "episodes" ADD CONSTRAINT "episodes_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_rooms" ADD CONSTRAINT "meeting_rooms_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_members" ADD CONSTRAINT "meeting_members_meetingId_fkey" FOREIGN KEY ("meetingId") REFERENCES "meeting_rooms"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_members" ADD CONSTRAINT "meeting_members_modelId_fkey" FOREIGN KEY ("modelId") REFERENCES "model_registry"("modelId") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_members" ADD CONSTRAINT "meeting_members_roleId_fkey" FOREIGN KEY ("roleId") REFERENCES "agent_roles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_turns" ADD CONSTRAINT "meeting_turns_meetingId_fkey" FOREIGN KEY ("meetingId") REFERENCES "meeting_rooms"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_turns" ADD CONSTRAINT "meeting_turns_memberId_fkey" FOREIGN KEY ("memberId") REFERENCES "meeting_members"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_reports" ADD CONSTRAINT "meeting_reports_meetingId_fkey" FOREIGN KEY ("meetingId") REFERENCES "meeting_rooms"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "meeting_reports" ADD CONSTRAINT "meeting_reports_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "meeting_members"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
