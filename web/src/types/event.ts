export type PublicEventResponse = {
  event: {
    slug: string;
    name: string;
    status: string;
    description?: string | null;
    consentVersion: string;
    settings: {
      displayEnabled?: boolean;
      maxMindCardsPerSession?: number;
      helpNoticeEnabled?: boolean;
    };
  };
  notices: {
    notDiagnosis: string;
    anonymousKeywordDisplay: string;
  };
};
