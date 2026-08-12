import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

import {
  editorToGraph,
  graphToEditor,
  parseWorkflowGraph,
  serializeWorkflowGraph,
} from "../src/pages/taskrunner/graphAdapter";

interface GraphRow { id: number; name: string; graph_json: string }

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const database = path.resolve(frontend, "..", "backend", "xanax.db");
const python = String.raw`
import json, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
rows = db.execute("SELECT id,name,graph_json FROM workflow_tasks WHERE trim(graph_json)<>'' ORDER BY id").fetchall()
print(json.dumps([{"id": r[0], "name": r[1], "graph_json": r[2]} for r in rows], ensure_ascii=False))
`;
const query = spawnSync("python", ["-c", python, database], {
  encoding: "utf8",
  env: { ...process.env, PYTHONIOENCODING: "utf-8" },
});
if (query.status !== 0) throw new Error(query.stderr || "Không đọc được workflow_tasks");
const rows = JSON.parse(query.stdout) as GraphRow[];
if (!rows.length) throw new Error("DB thật không có graph_json nào để kiểm");

let nodes = 0;
let edges = 0;
for (const row of rows) {
  const source = parseWorkflowGraph(row.graph_json);
  const editor = graphToEditor(source);
  const roundTrip = editorToGraph(editor.nodes, editor.edges, source);
  const semanticBefore = JSON.stringify(source);
  const semanticAfter = JSON.stringify(roundTrip);
  if (semanticAfter !== semanticBefore) {
    throw new Error(`Workflow #${row.id} (${row.name}) mất dữ liệu qua adapter`);
  }
  const serialized = serializeWorkflowGraph(row.graph_json, roundTrip);
  if (serialized !== row.graph_json) {
    throw new Error(`Workflow #${row.id} (${row.name}) đổi byte: ${row.graph_json.length} -> ${serialized.length}`);
  }
  nodes += source.nodes.length;
  edges += source.edges.length;
  console.log(`OK #${row.id} ${row.name}: ${row.graph_json.length} bytes, ${source.nodes.length} nodes, ${source.edges.length} edges`);
}
console.log(`PASS: ${rows.length} graph_json thật, ${nodes} nodes, ${edges} edges — byte-identical`);
