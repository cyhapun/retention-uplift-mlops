import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFile(join(root, path), "utf8");

test("all task routes are present", async () => {
  const routes = await Promise.all([
    read("app/page.tsx"),
    read("app/decisions/page.tsx"),
    read("app/monitoring/page.tsx"),
    read("app/operations/page.tsx"),
    read("app/policy/page.tsx"),
  ]);
  assert.equal(routes.length, 5);
  assert.ok(routes.every((route) => route.includes("Page")));
});

test("navigation exposes active task links and specialist details", async () => {
  const shell = await read("app/components/control-center-shell.tsx");
  const presentation = await read("app/components/presentation.ts");
  for (const href of ["/", "/decisions", "/monitoring", "/operations", "/policy"]) {
    assert.ok(shell.includes(`href: "${href}"`));
  }
  assert.ok(shell.includes("TechnicalDetails"));
  assert.ok(presentation.includes("actionLabel"));
  assert.ok(presentation.includes("reasonLabel"));
});

test("responsive and accessible UX contracts are present", async () => {
  const css = await read("app/globals.css");
  const decisionForm = await read("app/components/decision-form.tsx");
  assert.ok(css.includes("@media (max-width: 820px)"));
  assert.ok(css.includes(":focus-visible"));
  assert.ok(css.includes(".status-message"));
  assert.ok(decisionForm.includes("aria-describedby"));
  assert.ok(decisionForm.includes("aria-live"));
});

test("policy workflow exposes validation, preview, activation, and rollback", async () => {
  const page = await read("app/components/policy-page.tsx");
  for (const endpoint of ["/api/policy/validate", "/api/policy/preview", "/api/policy/activate", "/api/policy/rollback/"]) {
    assert.ok(page.includes(endpoint));
  }
  assert.ok(page.includes("Read-only mode"));
  assert.ok(page.includes("Preview impact"));
});

test("drift simulator exposes guided controls and download routes", async () => {
  const simulator = await read("app/components/drift-simulator.tsx");
  const monitoring = await read("app/components/task-pages.tsx");
  const routes = await Promise.all([
    read("app/api/simulations/route.ts"),
    read("app/api/simulations/[simulationId]/route.ts"),
    read("app/api/simulations/[simulationId]/download/route.ts"),
  ]);
  assert.ok(simulator.includes("Choose which customer attributes change"));
  assert.ok(simulator.includes("Download Parquet"));
  assert.ok(simulator.includes("Download CSV"));
  assert.ok(monitoring.includes("DriftSimulatorPanel"));
  assert.ok(monitoring.includes("PRODUCTION DRIFT"));
  assert.ok(routes.every((route) => route.includes("OPS_ADMIN_TOKEN")));
});
