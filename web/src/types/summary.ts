export type SummaryPayload = {
  id?: string;
  finalText: string;
  generationMode: "template" | "llm" | "fallback" | "mock" | string;
  helpNoticeRequired: boolean;
  signals?: string[];
  recommendedAction?: string | null;
  isDiagnosis?: boolean;
};

export type RiskNotice = {
  showHelpNotice: boolean;
  text: string | null;
};

export type SummaryResponse = {
  summary: SummaryPayload;
  riskNotice: RiskNotice;
};

export type SummaryViewedResponse = {
  sessionStatus: string;
  viewedAt: string;
};
