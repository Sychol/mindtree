import { Route, Routes } from "react-router-dom";

import { ConsentPage } from "../pages/participant/ConsentPage";
import { LandingPage } from "../pages/participant/LandingPage";
import { ParticipantPlaceholderPage } from "../pages/participant/ParticipantPlaceholderPage";
import { QuestionReviewPage } from "../pages/participant/QuestionReviewPage";
import { QuestionsPage } from "../pages/participant/QuestionsPage";
import { SubmitResultPage } from "../pages/participant/SubmitResultPage";

export function ParticipantRoutes() {
  return (
    <Routes>
      <Route index element={<LandingPage />} />
      <Route path="consent" element={<ConsentPage />} />
      <Route path="questions" element={<QuestionsPage />} />
      <Route path="questions/review" element={<QuestionReviewPage />} />
      <Route path="submit-result" element={<SubmitResultPage />} />
      <Route path="summary" element={<ParticipantPlaceholderPage step="summary" />} />
      <Route path="cards/new" element={<ParticipantPlaceholderPage step="cards-new" />} />
      <Route path="cards/select" element={<ParticipantPlaceholderPage step="cards-select" />} />
      <Route path="replies/new" element={<ParticipantPlaceholderPage step="replies-new" />} />
      <Route path="complete" element={<ParticipantPlaceholderPage step="complete" />} />
      <Route path="help" element={<ParticipantPlaceholderPage step="help" />} />
      <Route path="*" element={<LandingPage />} />
    </Routes>
  );
}
