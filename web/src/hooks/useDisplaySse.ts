import { useEffect, useRef, useState } from "react";

import { getDisplaySnapshot, getDisplayStreamUrl } from "../api/display";
import type { DisplayConnectionStatus, DisplaySnapshot } from "../types/display";
import { warnIfDisplayContractUnsafe } from "../utils/displayContractCheck";

const POLLING_FALLBACK_INTERVAL_MS = 15000;
const NO_UPDATE_THRESHOLD_MS = 30000;

type DisplaySseState = {
  snapshot: DisplaySnapshot | null;
  connectionStatus: DisplayConnectionStatus;
  lastUpdatedAt: string | null;
};

function parseSnapshot(event: MessageEvent): DisplaySnapshot | null {
  try {
    const snapshot = JSON.parse(event.data) as DisplaySnapshot;
    warnIfDisplayContractUnsafe(snapshot);
    return snapshot;
  } catch {
    return null;
  }
}

export function useDisplaySse(
  eventSlug: string,
  initialSnapshot: DisplaySnapshot | null
): DisplaySseState {
  const [snapshot, setSnapshot] = useState<DisplaySnapshot | null>(initialSnapshot);
  const [connectionStatus, setConnectionStatus] = useState<DisplayConnectionStatus>("connecting");
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(initialSnapshot?.generatedAt ?? null);
  const snapshotRef = useRef<DisplaySnapshot | null>(initialSnapshot);

  useEffect(() => {
    if (!initialSnapshot) {
      return;
    }
    setSnapshot((current) => current ?? initialSnapshot);
    setLastUpdatedAt((current) => current ?? initialSnapshot.generatedAt);
    snapshotRef.current = snapshotRef.current ?? initialSnapshot;
  }, [initialSnapshot]);

  useEffect(() => {
    let disposed = false;
    let fallbackTimeoutId: number | undefined;
    let pollingIntervalId: number | undefined;
    const source = new EventSource(getDisplayStreamUrl(eventSlug));
    const lastSnapshotAtRef = { current: Date.now() };

    const rememberSnapshot = (nextSnapshot: DisplaySnapshot) => {
      snapshotRef.current = nextSnapshot;
      lastSnapshotAtRef.current = Date.now();
      setSnapshot(nextSnapshot);
      setLastUpdatedAt(nextSnapshot.generatedAt);
    };

    const stopPolling = () => {
      if (pollingIntervalId !== undefined) {
        window.clearInterval(pollingIntervalId);
        pollingIntervalId = undefined;
      }
    };

    const pollSnapshot = () => {
      getDisplaySnapshot(eventSlug)
        .then((nextSnapshot) => {
          if (disposed) {
            return;
          }
          rememberSnapshot(nextSnapshot);
          setConnectionStatus("polling");
        })
        .catch(() => {
          if (!disposed && snapshotRef.current) {
            setConnectionStatus("disconnected");
          }
        });
    };

    const startPolling = () => {
      if (pollingIntervalId !== undefined) {
        return;
      }
      setConnectionStatus("polling");
      pollSnapshot();
      pollingIntervalId = window.setInterval(pollSnapshot, POLLING_FALLBACK_INTERVAL_MS);
    };

    const schedulePollingFallback = () => {
      if (fallbackTimeoutId !== undefined) {
        window.clearTimeout(fallbackTimeoutId);
      }
      fallbackTimeoutId = window.setTimeout(() => {
        if (disposed) {
          return;
        }
        if (Date.now() - lastSnapshotAtRef.current >= NO_UPDATE_THRESHOLD_MS) {
          startPolling();
        }
      }, NO_UPDATE_THRESHOLD_MS);
    };

    setConnectionStatus(snapshotRef.current ? "reconnecting" : "connecting");

    source.addEventListener("open", () => {
      if (disposed) {
        return;
      }
      stopPolling();
      setConnectionStatus("connected");
      schedulePollingFallback();
    });

    source.addEventListener("keyword_snapshot", (event) => {
      if (disposed) {
        return;
      }
      const nextSnapshot = parseSnapshot(event);
      if (!nextSnapshot) {
        return;
      }
      rememberSnapshot(nextSnapshot);
      stopPolling();
      setConnectionStatus("connected");
      schedulePollingFallback();
    });

    source.addEventListener("heartbeat", () => {
      if (disposed) {
        return;
      }
      stopPolling();
      setConnectionStatus("connected");
      schedulePollingFallback();
    });

    source.onerror = () => {
      if (disposed) {
        return;
      }
      setConnectionStatus(snapshotRef.current ? "reconnecting" : "connecting");
      schedulePollingFallback();
    };

    return () => {
      disposed = true;
      source.close();
      stopPolling();
      if (fallbackTimeoutId !== undefined) {
        window.clearTimeout(fallbackTimeoutId);
      }
    };
  }, [eventSlug]);

  return {
    snapshot,
    connectionStatus,
    lastUpdatedAt
  };
}
