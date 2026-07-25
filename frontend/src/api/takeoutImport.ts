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

interface PollableJob {
  status: string;
  message: string;
  errorCode: string | null;
}

interface PollOptions<T extends PollableJob> {
  signal: AbortSignal;
  timeoutMs?: number;
  intervalMs?: number;
  onStatus?: (status: T) => void;
}

export async function pollTakeoutImport<T extends PollableJob>(
  getStatus: (signal: AbortSignal) => Promise<T>,
  { signal, timeoutMs = 10 * 60 * 1000, intervalMs = 1000, onStatus }: PollOptions<T>,
): Promise<T> {
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
        throw new Error("Lost contact with the backend while processing local music data. Check that it is running, then retry.");
      }
    }
    await abortableDelay(intervalMs, signal);
  }
  throw new Error("Local music processing timed out. Your previous profile is still available; retry after checking the backend.");
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
