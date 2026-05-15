import { useCallback, useEffect, useState } from "react";

import { getDisplaySnapshot } from "../api/display";
import type { DisplaySnapshot } from "../types/display";

type DisplaySnapshotState = {
  snapshot: DisplaySnapshot | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
};

export function useDisplaySnapshot(eventSlug: string): DisplaySnapshotState {
  const [snapshot, setSnapshot] = useState<DisplaySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const retry = useCallback(() => {
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    getDisplaySnapshot(eventSlug)
      .then((nextSnapshot) => {
        if (!active) {
          return;
        }
        setSnapshot(nextSnapshot);
      })
      .catch((caught: unknown) => {
        if (!active) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "snapshot을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [eventSlug, reloadToken]);

  return {
    snapshot,
    loading,
    error,
    retry
  };
}
