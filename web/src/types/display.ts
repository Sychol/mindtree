export type DisplayKeyword = {
  text: string;
  weight: number;
  category?: string | null;
};

export type DisplaySnapshot = {
  eventSlug: string;
  participantCount: number;
  completedCount: number;
  topMindKeywords: DisplayKeyword[];
  topSupportKeywords: DisplayKeyword[];
  cloudKeywords: DisplayKeyword[];
  generatedAt: string;
};

export type DisplayConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "polling"
  | "disconnected";
