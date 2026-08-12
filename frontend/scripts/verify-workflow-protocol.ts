import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { WORKFLOW_MESSAGE_TYPES } from "../src/pages/taskrunner/protocol";

const backendPath = fileURLToPath(new URL("../../backend/api/websocket_workflow.py", import.meta.url));
const backend = readFileSync(backendPath, "utf8");
const emitted = new Set(
  [...backend.matchAll(/["']type["']\s*:\s*["']([a-z_]+)["']/g)].map((match) => match[1]),
);
const handled = new Set<string>(WORKFLOW_MESSAGE_TYPES);

const missing = [...emitted].filter((type) => !handled.has(type)).sort();
const stale = [...handled].filter((type) => !emitted.has(type)).sort();

if (missing.length || stale.length) {
  if (missing.length) console.error(`Thiếu handler: ${missing.join(", ")}`);
  if (stale.length) console.error(`Không còn được server phát: ${stale.join(", ")}`);
  process.exitCode = 1;
} else {
  console.log(`PASS: ${emitted.size} message type trong websocket_workflow.py đều có nhánh xử lý tường minh.`);
  console.log([...emitted].sort().join("\n"));
}
