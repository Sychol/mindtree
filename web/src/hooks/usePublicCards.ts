import { useCallback, useEffect, useState } from "react";

import { getPublicCards, selectCard } from "../api/cards";
import { toUserMessage } from "../lib/errors";
import type { PublicCardsResponse, SelectCardResponse } from "../types/card";

export function usePublicCards(
  eventSlug: string | undefined,
  sessionId: string | undefined,
  enabled: boolean
) {
  const [data, setData] = useState<PublicCardsResponse | undefined>();
  const [loading, setLoading] = useState(false);
  const [selectingId, setSelectingId] = useState<string | undefined>();
  const [error, setError] = useState<string | undefined>();
  const [selectError, setSelectError] = useState<string | undefined>();

  const load = useCallback(async () => {
    if (!eventSlug || !enabled) {
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      setData(await getPublicCards(eventSlug, sessionId, 10));
    } catch (loadError) {
      setError(toUserMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [enabled, eventSlug, sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const choose = useCallback(
    async (selectedCardId: string): Promise<SelectCardResponse | undefined> => {
      if (!sessionId || selectingId) {
        return undefined;
      }
      setSelectingId(selectedCardId);
      setSelectError(undefined);
      try {
        return await selectCard(sessionId, { selectedCardId });
      } catch (selectCardError) {
        setSelectError(toUserMessage(selectCardError));
        return undefined;
      } finally {
        setSelectingId(undefined);
      }
    },
    [selectingId, sessionId]
  );

  return {
    data,
    loading,
    error,
    selectError,
    selectingId,
    retry: load,
    choose
  };
}
