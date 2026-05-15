import { Route, Routes } from "react-router-dom";

import { ConsentPage } from "../pages/participant/ConsentPage";
import { CompletePage } from "../pages/participant/CompletePage";
import { LandingPage } from "../pages/participant/LandingPage";
import { MindCardPage } from "../pages/participant/MindCardPage";
import { ParticipantPlaceholderPage } from "../pages/participant/ParticipantPlaceholderPage";
import { QuestionReviewPage } from "../pages/participant/QuestionReviewPage";
import { QuestionsPage } from "../pages/participant/QuestionsPage";
import { ReplyPage } from "../pages/participant/ReplyPage";
import { SelectPeerCardPage } from "../pages/participant/SelectPeerCardPage";
import { SubmitResultPage } from "../pages/participant/SubmitResultPage";
import { SummaryPage } from "../pages/participant/SummaryPage";

export function ParticipantRoutes() {
  return (
    <Routes>
      <Route index element={<LandingPage />} />
      <Route path="consent" element={<ConsentPage />} />
      <Route path="questions" element={<QuestionsPage />} />
      <Route path="questions/review" element={<QuestionReviewPage />} />
      <Route path="submit-result" element={<SubmitResultPage />} />
      <Route path="summary" element={<SummaryPage />} />
      <Route path="cards/new" element={<MindCardPage />} />
      <Route path="cards/select" element={<SelectPeerCardPage />} />
      <Route path="replies/new" element={<ReplyPage />} />
      <Route path="complete" element={<CompletePage />} />
      <Route path="help" element={<ParticipantPlaceholderPage step="help" />} />
      <Route path="*" element={<LandingPage />} />
    </Routes>
  );
}
