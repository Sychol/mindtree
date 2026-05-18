import { requestJson } from "./client";
import type {
  CreateMindCardRequest,
  CreateMindCardResponse,
  DeleteMindCardResponse,
  MyMindCardsResponse,
  PublicCardsResponse,
  SelectCardRequest,
  SelectCardResponse,
  UpdateMindCardRequest,
  UpdateMindCardResponse
} from "../types/card";

export function createMindCard(
  sessionId: string,
  request: CreateMindCardRequest
): Promise<CreateMindCardResponse> {
  return requestJson<CreateMindCardResponse>(`/sessions/${encodeURIComponent(sessionId)}/cards`, {
    method: "POST",
    body: request
  });
}

export function listMyMindCards(sessionId: string): Promise<MyMindCardsResponse> {
  return requestJson<MyMindCardsResponse>(`/sessions/${encodeURIComponent(sessionId)}/cards`);
}

export function getMyCards(sessionId: string): Promise<MyMindCardsResponse> {
  return listMyMindCards(sessionId);
}

export function updateMindCard(
  sessionId: string,
  cardId: string,
  request: UpdateMindCardRequest
): Promise<UpdateMindCardResponse> {
  return requestJson<UpdateMindCardResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/cards/${encodeURIComponent(cardId)}`,
    {
      method: "PATCH",
      body: request
    }
  );
}

export function deleteMindCard(sessionId: string, cardId: string): Promise<DeleteMindCardResponse> {
  return requestJson<DeleteMindCardResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/cards/${encodeURIComponent(cardId)}`,
    {
      method: "DELETE"
    }
  );
}

export function getPublicCards(
  eventSlug: string,
  excludeSessionId: string | undefined,
  limit = 10
): Promise<PublicCardsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (excludeSessionId) {
    params.set("excludeSessionId", excludeSessionId);
  }
  return requestJson<PublicCardsResponse>(
    `/events/${encodeURIComponent(eventSlug)}/cards/public?${params.toString()}`
  );
}

export function selectCard(
  sessionId: string,
  request: SelectCardRequest
): Promise<SelectCardResponse> {
  return requestJson<SelectCardResponse>(`/sessions/${encodeURIComponent(sessionId)}/selected-card`, {
    method: "POST",
    body: request
  });
}
