export type AnswerValue = string | number | boolean | string[] | number[];

export type DraftAnswer = {
  questionId: string;
  questionNo: number;
  answerValue: AnswerValue;
};

export type DraftAnswerMap = Record<string, DraftAnswer>;

export type BulkAnswersRequest = {
  answers: Array<{
    questionId: string;
    answerValue: AnswerValue;
  }>;
  clientProgress?: {
    lastQuestionNo?: number;
  };
};

export type BulkAnswersResponse = {
  savedCount: number;
  missingQuestionNos?: number[];
  sessionStatus: string;
  scoring?: {
    calculated: boolean;
    scaleScores?: Array<{
      scaleCode: string;
      rawScore: number;
      severityLevel?: string | null;
    }>;
    riskFlags?: {
      phq9Item9Positive?: boolean;
      crisisExpressionDetected?: boolean;
      traumaHighSignal?: boolean;
      moralInjuryHighSignal?: boolean;
      publicRestriction?: boolean;
      helpNoticeRequired?: boolean;
    } | null;
  };
};
