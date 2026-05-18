import { useEffect, useState, type FormEvent } from "react";

import type {
  AdminSurveyQuestionItem,
  SurveyQuestionPresentationUpdateRequest
} from "../../types/survey";

type SurveyQuestionPresentationEditorProps = {
  question?: AdminSurveyQuestionItem;
  saving: boolean;
  onSave: (questionNo: number, payload: SurveyQuestionPresentationUpdateRequest) => Promise<void>;
};

function hasTitleOverride(question: AdminSurveyQuestionItem): boolean {
  return question.displayTitle !== question.title;
}

function hasDescriptionOverride(question: AdminSurveyQuestionItem): boolean {
  return (question.displayDescription ?? "") !== (question.description ?? "");
}

export function SurveyQuestionPresentationEditor({
  question,
  saving,
  onSave
}: SurveyQuestionPresentationEditorProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!question) {
      setTitle("");
      setDescription("");
      return;
    }
    setTitle(hasTitleOverride(question) ? question.displayTitle : "");
    setDescription(hasDescriptionOverride(question) ? question.displayDescription ?? "" : "");
  }, [question]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!question) {
      return;
    }
    await onSave(question.questionNo, {
      title: title.trim() || null,
      description: description.trim() || null,
      reason
    });
    setReason("");
  };

  if (!question) {
    return <div className="admin-empty">편집할 문항을 선택하세요.</div>;
  }

  return (
    <form className="admin-survey-editor admin-survey-question-editor" onSubmit={handleSubmit}>
      <div className="admin-survey-readonly-grid">
        <span>questionNo: {question.questionNo}</span>
        <span>questionKey: {question.questionKey}</span>
        <span>scaleCode: {question.scaleCode}</span>
        <span>questionType: {question.questionType}</span>
        <span>required: {question.required ? "true" : "false"}</span>
        <span>options: {question.optionsCount}</span>
      </div>
      <div className="admin-alert">
        questionNo, questionKey, scaleCode, questionType, options, scoreMap, required는 수정할 수 없습니다.
      </div>
      <label className="admin-field">
        원본 제목
        <textarea className="admin-textarea" value={question.title} readOnly />
      </label>
      <label className="admin-field">
        표시 제목 override
        <textarea
          className="admin-textarea"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="비워두면 원본 제목을 사용합니다."
        />
      </label>
      <label className="admin-field">
        표시 설명 override
        <textarea
          className="admin-textarea"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="비워두면 원본 설명을 사용합니다."
        />
      </label>
      <label className="admin-field">
        변경 사유
        <input className="admin-input" value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      <div className="admin-form-actions">
        <button className="admin-button admin-button--primary" type="submit" disabled={saving}>
          {saving ? "저장 중" : "문항 표시문구 저장"}
        </button>
      </div>
    </form>
  );
}
