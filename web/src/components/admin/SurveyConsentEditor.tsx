import { useEffect, useState, type FormEvent } from "react";

import type {
  SurveyConsentConfig,
  SurveyConsentItem,
  SurveyConsentSection,
  SurveyConsentUpdateRequest
} from "../../types/survey";

type SurveyConsentEditorProps = {
  consent: SurveyConsentConfig;
  saving: boolean;
  onSave: (payload: SurveyConsentUpdateRequest) => Promise<void>;
};

export function SurveyConsentEditor({ consent, saving, onSave }: SurveyConsentEditorProps) {
  const [title, setTitle] = useState(consent.title);
  const [sections, setSections] = useState<SurveyConsentSection[]>(consent.sections);
  const [items, setItems] = useState<SurveyConsentItem[]>(consent.items);
  const [reason, setReason] = useState("");

  useEffect(() => {
    setTitle(consent.title);
    setSections(consent.sections);
    setItems(consent.items);
  }, [consent]);

  const updateSection = (index: number, patch: Partial<SurveyConsentSection>) => {
    setSections((current) =>
      current.map((section, sectionIndex) =>
        sectionIndex === index ? { ...section, ...patch } : section
      )
    );
  };

  const updateItem = (key: string, patch: Partial<SurveyConsentItem>) => {
    setItems((current) => current.map((item) => (item.key === key ? { ...item, ...patch } : item)));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await onSave({
      title,
      sections,
      items,
      reason
    });
    setReason("");
  };

  return (
    <form className="admin-survey-editor" onSubmit={handleSubmit}>
      <div className="admin-alert">
        동의 항목 key와 필수 여부는 변경할 수 없습니다. 문구만 수정할 수 있습니다.
      </div>
      <label className="admin-field">
        동의서 제목
        <input className="admin-input" maxLength={120} value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>

      <section className="admin-survey-subsection">
        <h3>동의 설명문</h3>
        {sections.map((section, index) => (
          <div className="admin-survey-nested" key={`${section.heading}-${index}`}>
            <label className="admin-field">
              제목
              <input
                className="admin-input"
                value={section.heading}
                onChange={(event) => updateSection(index, { heading: event.target.value })}
              />
            </label>
            <label className="admin-field">
              문단
              <textarea
                className="admin-textarea"
                value={section.paragraphs.join("\n")}
                onChange={(event) =>
                  updateSection(index, {
                    paragraphs: event.target.value.split("\n").map((item) => item.trim()).filter(Boolean)
                  })
                }
              />
            </label>
          </div>
        ))}
      </section>

      <section className="admin-survey-subsection">
        <h3>필수 동의 항목</h3>
        {items.map((item) => (
          <div className="admin-survey-nested" key={item.key}>
            <div className="admin-survey-lock-row">
              <span className="admin-badge">{item.key}</span>
              <span className="admin-badge admin-badge--safe">{item.required ? "required" : "optional"}</span>
            </div>
            <label className="admin-field">
              표시 라벨
              <input
                className="admin-input"
                value={item.label}
                onChange={(event) => updateItem(item.key, { label: event.target.value })}
              />
            </label>
            <label className="admin-field">
              설명
              <textarea
                className="admin-textarea"
                value={item.description}
                onChange={(event) => updateItem(item.key, { description: event.target.value })}
              />
            </label>
          </div>
        ))}
      </section>

      <label className="admin-field">
        변경 사유
        <input className="admin-input" value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      <div className="admin-form-actions">
        <button className="admin-button admin-button--primary" type="submit" disabled={saving || !title.trim()}>
          {saving ? "저장 중" : "동의서 저장"}
        </button>
      </div>
    </form>
  );
}
