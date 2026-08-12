import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const sourceRoot = resolve("src");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? sourceFiles(path) : [path];
  }).filter((path) => /\.(ts|tsx|css)$/.test(path));
}

const allSource = sourceFiles(sourceRoot)
  .map((path) => readFileSync(path, "utf8"))
  .join("\n");
const hubSource = readFileSync(resolve("src/pages/hub/HubPage.tsx"), "utf8");
const clientSource = readFileSync(resolve("src/api/client.ts"), "utf8");
const loginSource = readFileSync(resolve("src/pages/login/LoginPage.tsx"), "utf8");

for (const forbidden of ["postMessage", "embed=1", "data-click"]) {
  assert.equal(allSource.includes(forbidden), false, `frontend/src still contains ${forbidden}`);
}
assert.equal(/<iframe\b/i.test(allSource), false, "frontend/src still renders an iframe");
assert.equal(/window\.(?:top|parent)\b/.test(allSource), false, "frame escape navigation remains");

assert.match(hubSource, /const \[visitedTabs, setVisitedTabs\]/, "Hub no longer records mounted tabs");
assert.match(hubSource, /hidden=\{!isActive\}/, "inactive mounted panels are not hidden in place");
assert.match(hubSource, /savedSubpaths\[item\.tab\]/, "task editor subpaths are not restored on tab return");
assert.match(hubSource, /const WorkspacePage = lazy\(/, "Workspace route is not lazy-loaded");
assert.match(hubSource, /const TaskrunnerPage = lazy\(/, "Taskrunner route is not lazy-loaded");
assert.match(hubSource, /<WorkspacePage embedded/, "Workspace is not mounted directly in Hub");
assert.match(hubSource, /<TaskrunnerPage[\s\S]*embedded/, "Taskrunner is not mounted directly in Hub");

assert.match(clientSource, /window\.location\.assign\(target\)/, "auth redirect no longer uses normal window navigation");
assert.match(loginSource, /window\.location\.assign\("\/v2\/hub"\)/, "React login does not enter the React Hub");

console.log("PASS: no iframe bridge markers, tabs stay mounted, heavy routes are lazy, and auth uses window.location");
