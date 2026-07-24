import assert from "node:assert/strict";
import test from "node:test";
import { pollTakeoutImport, runExclusiveOperation } from "../src/api/takeoutImport.ts";

const status = (state, message = state) => ({
  jobId: "job-1",
  status: state,
  progress: state === "complete" || state === "failed" ? 100 : 50,
  message,
  errorCode: state === "failed" ? "test_failure" : null,
  importedCount: state === "complete" ? 3 : null,
  trackCount: state === "complete" ? 1 : null,
  playCount: state === "complete" ? 3 : null,
});

test("loading resets after an operation error", async () => {
  const flag = { current: false };
  const loading = [];
  await assert.rejects(
    runExclusiveOperation(flag, (value) => loading.push(value), async () => {
      throw new Error("failed");
    }),
    /failed/,
  );
  assert.equal(flag.current, false);
  assert.deepEqual(loading, [true, false]);
});

test("a duplicate refresh is prevented while one operation is active", async () => {
  const flag = { current: false };
  let release;
  const first = runExclusiveOperation(flag, () => undefined, () => new Promise((resolve) => { release = resolve; }));
  const duplicate = await runExclusiveOperation(flag, () => undefined, async () => undefined);
  assert.equal(duplicate, false);
  release();
  assert.equal(await first, true);
});

test("polling returns the completed profile", async () => {
  const responses = [status("parsing"), status("rebuilding"), status("complete")];
  const result = await pollTakeoutImport(async () => responses.shift() ?? status("complete"), {
    signal: new AbortController().signal,
    intervalMs: 1,
    timeoutMs: 100,
  });
  assert.equal(result.status, "complete");
  assert.equal(result.playCount, 3);
});

test("polling exposes a failed job and stops", async () => {
  await assert.rejects(
    pollTakeoutImport(async () => status("failed", "Rebuild failed safely."), {
      signal: new AbortController().signal,
      intervalMs: 1,
      timeoutMs: 100,
    }),
    /Rebuild failed safely\. \(test_failure\)/,
  );
});

test("polling times out instead of running forever", async () => {
  await assert.rejects(
    pollTakeoutImport(async () => status("parsing"), {
      signal: new AbortController().signal,
      intervalMs: 1,
      timeoutMs: 5,
    }),
    /timed out/,
  );
});
