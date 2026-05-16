export type SessionStatus =
  | "created"
  | "consented"
  | "questions_completed"
  | "summary_viewed"
  | "card_created"
  | "reply_created"
  | "completed"
  | "abandoned";

export type SessionInfo = {
  id: string;
  eventSlug: string;
  status: SessionStatus;
  lastStep?: string | null;
  completedAt?: string | null;
};

export type SessionProgress = {
  consentAccepted: boolean;
  questionsCompleted: boolean;
  summaryViewed: boolean;
  mindCardCount: number;
  selectedCard: boolean;
  replyCreated: boolean;
  completionCodeIssued: boolean;
};

export type CreateOrResumeSessionRequest = {
  resumeToken?: string;
  clientMeta?: {
    device?: string;
    timezone?: string;
  };
};

export type CreateOrResumeSessionResponse = {
  session: SessionInfo;
  resumeToken: string;
};

export type SessionStatusResponse = {
  session: SessionInfo;
  progress: SessionProgress;
};

export type ConsentRequest = {
  consentVersion: string;
  acceptedItems: ConsentAcceptedItems;
};

export type ConsentAcceptedItems = {
  researchParticipationConsent: boolean;
  personalDataUseConsent: boolean;
  sensitiveInfoConsent: boolean;
  deidentifiedAiRagUseConsent: boolean;
};

export type ConsentResponse = {
  sessionStatus: SessionStatus;
  acceptedAt: string;
};
