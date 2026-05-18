import { useEffect, useMemo, useState, type FormEvent } from "react";

import type {
  AdminSurveyQuestionItem,
  AdminSurveyQuestionsBySection,
  SurveySectionSummary,
  SurveySectionUpdateRequest,
  SurveyQuestionPresentationUpdateRequest
} from "../../types/survey";
import { SurveyQuestionPresentationEditor } from "./SurveyQuestionPresentationEditor";

type SurveyQuestionSectionTableProps = {
  sections: SurveySectionSummary[];
  questionsBySection: AdminSurveyQuestionsBySection[];
  selectedSectionId?: string;
  saving: boolean;
  onSectionSelect: (sectionId: string) => void;
  onSaveSection: (sectionId: string, payload: SurveySectionUpdateRequest) => Promise<void>;
  onSaveQuestion: (questionNo: number, payload: SurveyQuestionPresentationUpdateRequest) => Promise<void>;
};

export function SurveyQuestionSectionTable({
  sections,
  questionsBySection,
  selectedSectionId,
  saving,
  onSectionSelect,
  onSaveSection,
  onSaveQuestion
}: SurveyQuestionSectionTableProps) {
  const editableSections = sections.filter((section) => section.questionNoRange);
  const activeSectionId = selectedSectionId ?? editableSections[0]?.id;
  const activeSummary = sections.find((section) => section.id === activeSectionId);
  const activeQuestions = questionsBySection.find((section) => section.sectionId === activeSectionId);
  const [title, setTitle] = useState(activeSummary?.title ?? "");
  const [description, setDescription] = useState(activeSummary?.description ?? "");
  const [reason, setReason] = useState("");
  const [selectedQuestionNo, setSelectedQuestionNo] = useState<number | undefined>();

  useEffect(() => {
    setTitle(activeSummary?.title ?? "");
    setDescription(activeSummary?.description ?? "");
    setSelectedQuestionNo(activeQuestions?.questions[0]?.questionNo);
  }, [activeQuestions, activeSummary]);

  const selectedQuestion = useMemo(
    () => activeQuestions?.questions.find((question) => question.questionNo === selectedQuestionNo),
    [activeQuestions, selectedQuestionNo]
  );

  const handleSectionSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!activeSectionId) {
      return;
    }
    await onSaveSection(activeSectionId, {
      title,
      description: description.trim() || null,
      reason
    });
    setReason("");
  };

  if (!editableSections.length) {
    return <div className="admin-empty">문항 섹션을 찾을 수 없습니다.</div>;
  }

  return (
    <div className="admin-survey-question-grid">
      <aside className="admin-survey-section-list">
        {editableSections.map((section) => (
          <button
            key={section.id}
            className={`admin-survey-section-button${section.id === activeSectionId ? " is-active" : ""}`}
            type="button"
            onClick={() => onSectionSelect(section.id)}
          >
            <strong>{section.sectionNo}. {section.title}</strong>
            <span>{section.questionNoRange?.join("~")} · {section.questionCount}문항</span>
          </button>
        ))}
      </aside>

      <section className="admin-survey-question-main">
        <form className="admin-survey-editor" onSubmit={handleSectionSubmit}>
          <h3>섹션 표시 설정</h3>
          <label className="admin-field">
            섹션 제목
            <input className="admin-input" value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="admin-field">
            섹션 설명
            <textarea className="admin-textarea" value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label className="admin-field">
            변경 사유
            <input className="admin-input" value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
          <div className="admin-form-actions">
            <button className="admin-button admin-button--primary" type="submit" disabled={saving || !title.trim()}>
              {saving ? "저장 중" : "섹션 저장"}
            </button>
          </div>
        </form>

        <div className="admin-table-wrap">
          <table className="admin-table admin-survey-question-table">
            <thead>
              <tr>
                <th>No</th>
                <th>questionKey</th>
                <th>scale</th>
                <th>type</th>
                <th>원본 제목</th>
                <th>표시 제목</th>
                <th>override</th>
                <th>required</th>
                <th>options</th>
              </tr>
            </thead>
            <tbody>
              {activeQuestions?.questions.map((question) => (
                <tr
                  key={question.id}
                  className={question.questionNo === selectedQuestionNo ? "is-selected" : ""}
                  onClick={() => setSelectedQuestionNo(question.questionNo)}
                >
                  <td>{question.questionNo}</td>
                  <td>{question.questionKey}</td>
                  <td>{question.scaleCode}</td>
                  <td>{question.questionType}</td>
                  <td>{question.title}</td>
                  <td>{question.displayTitle}</td>
                  <td>
                    {question.displayTitle !== question.title || (question.displayDescription ?? "") !== (question.description ?? "")
                      ? "있음"
                      : "-"}
                  </td>
                  <td>{question.required ? "true" : "false"}</td>
                  <td>{question.optionsCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <SurveyQuestionPresentationEditor
          question={selectedQuestion as AdminSurveyQuestionItem | undefined}
          saving={saving}
          onSave={onSaveQuestion}
        />
      </section>
    </div>
  );
}
