export type ReplyType = "comfort" | "empathy" | "small_coping";

export type CreateReplyRequest = {
  targetCardId: string;
  replyType: ReplyType;
  content: string;
};

export type CreateReplyResponse = {
  reply: {
    id: string;
    replyType: ReplyType | string;
    safetyStatus: string;
    publicStatus: string;
  };
  keywordJob?: {
    id: string;
    status: string;
  } | null;
  completion: {
    eligible: boolean;
    code?: string | null;
  };
  sessionStatus: string;
};
