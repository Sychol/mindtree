export type CompletionCode = {
  code: string;
  status: "issued" | "redeemed" | "void" | string;
  issuedAt: string;
};

export type CompletionCodeResponse = {
  completionCode: CompletionCode;
};
