import type { TakeoutImportStatus } from "../types/api";

export interface MutableFlag {
  current: boolean;
}

export async function runExclusiveOperation(
  flag: MutableFlag,
  setLoading: (loading: boolean) => void,
  operation: () => Promise<void>,
): Promise<boolean> {
  if (flag.current) return false;
  flag.current = true;
  setLoading(true);
  try {
    await operation();
    return true;
  } finally {
    flag.current = false;
    setLoading(false);
  }
}

interface PollOptions {
  signal: AbortSignal;
  timeoutMs?: number;
  intervalMs?: number;
  onStatus?: (status: TakeoutImportStatus) => void;
}

export async function pollTakeoutImport(
  getStatus: (signal: AbortSignal) => Promise<TakeoutImportStatus>,
  { signal, timeoutMs = 10 * 60 * 1000, intervalMs = 1000, onStatus }: PollOptions,
): Promise<TakeoutImportStatus> {
  const startedAt = Date.now();
  let networkFailures = 0;
  while (Date.now() - startedAt < timeoutMs) {
    if (signal.aborted) throw new DOMException("Takeout import polling was cancelled.", "AbortError");
    try {
      const status = await getStatus(signal);
      networkFailures = 0;
      onStatus?.(status);
      if (status.status === "complete") return status;
      if (status.status === "failed") {
        throw new Error(`${status.message}${status.errorCode ? ` (${status.errorCode})` : ""}`);
      }
    } catch (error) {
      if (signal.aborted || (error instanceof DOMException && error.name === "AbortError")) throw error;
      if (error instanceof Error && /\([a-z_]+\)$/.test(error.message)) throw error;
      networkFailures += 1;
      if (networkFailures >= 3) {
        throw new Error("Lost contact with the backend while importing. Check that it is running, then retry.");
      }
    }
    await abortableDelay(intervalMs, signal);
  }
  throw new Error("Takeout import timed out. The previous profile is still available; retry after checking the backend.");
}

function abortableDelay(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = globalThis.setTimeout(resolve, milliseconds);
    signal.addEventListener(
      "abort",
      () => {
        globalThis.clearTimeout(timer);
        reject(new DOMException("Takeout import polling was cancelled.", "AbortError"));
      },
      { once: true },
    );
  });
}
