import assert from "node:assert/strict";

import { buildAttachmentBlock } from "../src/components/ChatAttach";
import { emptyMeetingLiveState, reduceMeetingMessage } from "../src/pages/hub/meetingProtocol";

let state = emptyMeetingLiveState;
const feed = (message: Record<string, unknown> & { type: string }) => { state = reduceMeetingMessage(state, message); };

feed({ type: "history", messages: [
  { id: 1, sender: "user", sender_type: "user", content: "Xin chào", created_at: "2026-01-01 00:00:00" },
  { id: 2, sender: "Hệ thống", sender_type: "system", content: "Đang chạy" },
] });
assert.equal(state.messages.length, 2);
feed({ type: "user_message", sender: "user", content: "@Xanax xem giúp" });
feed({ type: "agent_thinking", agent_id: 0, agent: "Xanax", color: "gold" });
feed({ type: "agent_chunk", agent_id: 0, agent: "Xanax", content: "Đã " });
feed({ type: "agent_chunk", agent_id: 0, agent: "Xanax", content: "rõ." });
assert.equal(state.streams["0"].content, "Đã rõ.");
feed({ type: "agent_done", agent_id: 0 });
assert.equal(state.messages.at(-1)?.content, "Đã rõ.");
feed({ type: "agent_thinking", agent_id: 2, agent: "Prozac" });
feed({ type: "agent_cancelled", agent_id: 2 });
assert.equal(state.streams["2"], undefined);
feed({ type: "participants_updated", participants: [{ id: 2 }, { id: 3 }] });
assert.deepEqual(state.participantIds, [2, 3]);
feed({ type: "workflow_progress", run_id: 91, status: "running", task_name: "Đăng bài", step: 2, total: 4, label: "Đang viết" });
assert.equal(state.progress["91"].step, 2);
feed({ type: "workflow_progress", run_id: 91, status: "waiting", label: "Chờ CEO duyệt" });
assert.equal(state.progress["91"].status, "waiting");
feed({ type: "workflow_progress", run_id: 91, status: "done", label: "Xong" });
assert.equal(state.progress["91"], undefined);
feed({ type: "system_notice", content: "Quy trình đã xong." });

const approval = { type: "approval_request", output_id: 41, run_id: 91, content: "Bản nháp", restored: true } as const;
feed(approval); feed(approval);
assert.equal(Object.keys(state.approvals).length, 1, "replayed approval must be deduplicated by output_id");
feed({ type: "__approval_resolved", output_id: 41, resolution: "approved" });
assert.equal(state.approvals["41"].resolved, "approved");

const source = { type: "image_source_request", run_id: 91, node_id: "image-1", assets: [{ id: 7, filename: "a.png", url: "/a.png" }] } as const;
feed(source); feed(source);
assert.equal(Object.keys(state.imageSources).length, 1, "replayed image gate must be deduplicated by run/node");
feed({ type: "image_source_chosen", run_id: 91, node_id: "image-1", mode: "asset" });
assert.equal(state.imageSources["91:image-1"].resolved, "asset");
feed({ type: "meeting_ended", draft_minutes: "Biên bản nháp" });
assert.equal(state.endedDraft, "Biên bản nháp");
feed({ type: "error", message: "test error" });
assert.equal(state.error, "test error");

const attachment = buildAttachmentBlock([{ name: "brief.txt", abs_path: "D:\\brief.txt", download_url: "/api/assets/1/download", mime: "text/plain" }]);
assert.equal(attachment, "\n\n<!-- FILE PAPA GỬI KÈM — đường dẫn tuyệt đối, dùng cho công cụ:\n- brief.txt → D:\\brief.txt\n-->\n\n[📎 brief.txt](/api/assets/1/download)");

console.log("Meeting protocol: history, stream, cancellation, participants, workflow progress, approval replay, image gate, end/error — OK");
console.log("Attachment payload contract — byte-identical expected string");
