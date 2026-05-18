import { useEffect, useState, type FormEvent } from "react";

import type { SurveyIntroConfig, SurveyIntroUpdateRequest } from "../../types/survey";

type SurveyIntroEditorProps = {
  intro: SurveyIntroConfig;
  saving: boolean;
  onSave: (payload: SurveyIntroUpdateRequest) => Promise<void>;
};

export function SurveyIntroEditor({ intro, saving, onSave }: SurveyIntroEditorProps) {
  const [title, setTitle] = useState(intro.title);
  const [subtitle, setSubtitle] = useState(intro.subtitle ?? "");
  const [paragraphs, setParagraphs] = useState(intro.paragraphs.join("\n"));
  const [showLogo, setShowLogo] = useState(intro.showLogo);
  const [showAppScreens, setShowAppScreens] = useState(intro.showAppScreens);
  const [reason, setReason] = useState("");

  useEffect(() => {
    setTitle(intro.title);
    setSubtitle(intro.subtitle ?? "");
    setParagraphs(intro.paragraphs.join("\n"));
    setShowLogo(intro.showLogo);
    setShowAppScreens(intro.showAppScreens);
  }, [intro]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await onSave({
      title,
      subtitle,
      paragraphs: paragraphs.split("\n").map((item) => item.trim()).filter(Boolean),
      showLogo,
      showAppScreens,
      reason
    });
    setReason("");
  };

  return (
    <form className="admin-survey-editor" onSubmit={handleSubmit}>
      <label className="admin-field">
        제목
        <input className="admin-input" maxLength={100} value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label className="admin-field">
        부제
        <input className="admin-input" maxLength={120} value={subtitle} onChange={(event) => setSubtitle(event.target.value)} />
      </label>
      <label className="admin-field">
        문단
        <textarea
          className="admin-textarea admin-textarea--tall"
          value={paragraphs}
          onChange={(event) => setParagraphs(event.target.value)}
        />
      </label>
      <div className="admin-inline-actions">
        <label className="admin-check">
          <input type="checkbox" checked={showLogo} onChange={(event) => setShowLogo(event.target.checked)} />
          로고 표시
        </label>
        <label className="admin-check">
          <input type="checkbox" checked={showAppScreens} onChange={(event) => setShowAppScreens(event.target.checked)} />
          앱 화면 표시
        </label>
      </div>
      <label className="admin-field">
        변경 사유
        <input className="admin-input" value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      <div className="admin-form-actions">
        <button className="admin-button admin-button--primary" type="submit" disabled={saving || !title.trim()}>
          {saving ? "저장 중" : "소개 화면 저장"}
        </button>
      </div>
    </form>
  );
}
