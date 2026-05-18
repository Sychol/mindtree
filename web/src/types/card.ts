import type { SessionStatus } from "./session";

export type MindCardPromptType =
  | "to_past_me"
  | "to_now_me"
  | "to_colleague"
  | "stress_memory";

export type MindCard = {
  id: string;
  promptType: MindCardPromptType | string;
  content: string;
  safetyStatus: "safe" | "review" | "exclude" | string;
  publicStatus: "pending" | "public" | "hidden" | "excluded" | string;
  createdAt?: string | null;
};

export type CreateMindCardRequest = {
  promptType: MindCardPromptType;
  content: string;
};

export type UpdateMindCardRequest = CreateMindCardRequest;

export type CreateMindCardResponse = {
  card: MindCard;
  keywordJob?: {
    id: string;
    status: string;
  } | null;
  sessionStatus: SessionStatus;
};

export type UpdateMindCardResponse = CreateMindCardResponse;

export type DeleteMindCardResponse = {
  deletedCardId: string;
  sessionStatus: SessionStatus;
};

export type MyMindCardsResponse = {
  cards: MindCard[];
};

export type PublicCard = {
  id: string;
  promptType: string;
  content: string;
  createdAt: string;
};

export type PublicMindCard = PublicCard;

export type PublicCardsResponse = {
  cards: PublicCard[];
  fallbackUsed: boolean;
  message?: string | null;
};

export type PublicMindCardsResponse = PublicCardsResponse;

export type SelectCardRequest = {
  selectedCardId: string;
};

export type SelectCardResponse = {
  selectedCardId: string;
  selectedAt: string;
};
