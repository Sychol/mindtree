import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  getAdminSurvey,
  resetAdminSurvey,
  updateAdminSurveyConsent,
  updateAdminSurveyIntro,
  updateAdminSurveyQuestionPresentation,
  updateAdminSurveySection,
  updateAdminSurveyThanks
} from "../../api/admin";
import { SurveyConsentEditor } from "../../components/admin/SurveyConsentEditor";
import { SurveyIntroEditor } from "../../components/admin/SurveyIntroEditor";
import { SurveyPreviewPanel } from "../../components/admin/SurveyPreviewPanel";
import { SurveyQuestionSectionTable } from "../../components/admin/SurveyQuestionSectionTable";
import { SurveySectionOverview } from "../../components/admin/SurveySectionOverview";
import type {
  AdminSurveyResponse,
  SurveyConsentUpdateRequest,
  SurveyIntroUpdateRequest,
  SurveyQuestionPresentationUpdateRequest,
  SurveySectionUpdateRequest,
  SurveyThanksUpdateRequest
} from "../../types/survey";
import { adminErrorMessage } from "../../utils/adminLabels";

type SurveyTab = "flow" | "intro" | "consent" | "questions" | "preview";

const TABS: Array<{ id: SurveyTab; label: string }> = [
  { id: "flow", label: "전체 흐름" },
  { id: "intro", label: "소개 화면" },
  { id: "consent", label: "동의서" },
  { id: "questions", label: "문항 섹션" },
  { id: "preview", label: "미리보기" }
];

export function AdminSurveyPage() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const [data, setData] = useState<AdminSurveyResponse | null>(null);
  const [activeTab, setActiveTab] = useState<SurveyTab>("flow");
  const [selectedSectionId, setSelectedSectionId] = useState<string | undefined>("profile");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getAdminSurvey(eventSlug);
      setData(response);
      setSelectedSectionId((current) => current ?? response.questionsBySection[0]?.sectionId);
    } catch (requestError) {
      setError(adminErrorMessage(requestError, "설문 설정을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }, [eventSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  const runMutation = async (message: string, action: () => Promise<unknown>) => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await action();
      await load();
      setSuccess(message);
    } catch (requestError) {
      setError(adminErrorMessage(requestError, "설문 설정을 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  };

  const handleIntroSave = (payload: SurveyIntroUpdateRequest) =>
    runMutation("소개 화면 설정을 저장했습니다.", () => updateAdminSurveyIntro(eventSlug, payload));

  const handleConsentSave = (payload: SurveyConsentUpdateRequest) =>
    runMutation("동의서 설정을 저장했습니다.", () => updateAdminSurveyConsent(eventSlug, payload));

  const handleSectionSave = (sectionId: string, payload: SurveySectionUpdateRequest) =>
    runMutation("섹션 표시 설정을 저장했습니다.", () => updateAdminSurveySection(eventSlug, sectionId, payload));

  const handleQuestionSave = (questionNo: number, payload: SurveyQuestionPresentationUpdateRequest) =>
    runMutation("문항 표시문구를 저장했습니다.", () =>
      updateAdminSurveyQuestionPresentation(eventSlug, questionNo, payload)
    );

  const handleThanksSave = (payload: SurveyThanksUpdateRequest) =>
    runMutation("완료 안내 문구를 저장했습니다.", () => updateAdminSurveyThanks(eventSlug, payload));

  const handleReset = () => {
    const reason = window.prompt("초기화 사유를 입력하세요.", "기본 설문 표시 설정으로 초기화");
    if (reason === null) {
      return;
    }
    void runMutation("설문 표시 설정을 초기화했습니다.", () => resetAdminSurvey(eventSlug, { reason }));
  };

  const handleEditSection = (sectionId: string) => {
    setSelectedSectionId(sectionId);
    setActiveTab(sectionId === "intro" ? "intro" : sectionId === "consent" ? "consent" : "questions");
  };

  const participantUrl = `/e/${encodeURIComponent(eventSlug)}`;
  const totalQuestionCount =
    data?.sectionSummaries.reduce((sum, section) => sum + section.questionCount, 0) ?? 0;

  return (
    <section className="admin-section admin-survey-page">
      <div className="admin-section__header">
        <div>
          <p className="admin-eyebrow">Survey Presentation Manager</p>
          <h2>설문 관리</h2>
          <p className="admin-muted">참가자 설문 화면의 소개문, 동의서, 섹션 제목, 문항 표시문구를 관리합니다.</p>
        </div>
        <div className="admin-inline-actions">
          <a className="admin-button admin-button--secondary" href={participantUrl} target="_blank" rel="noreferrer">
            참가자 화면 바로가기
          </a>
          <button className="admin-button admin-button--secondary" type="button" onClick={handleReset} disabled={saving}>
            기본값 초기화
          </button>
        </div>
      </div>

      <div className="admin-alert admin-alert--warning">
        이 화면은 표시 설정만 관리하며, 점수화 문항 구조는 변경하지 않습니다.
      </div>

      {data ? (
        <div className="admin-alert">
          문항 기준 {data.surveyConfig.version} · 총 {totalQuestionCount}문항
        </div>
      ) : null}

      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      {success ? <div className="admin-alert admin-alert--success">{success}</div> : null}

      <div className="admin-survey-tabs" role="tablist" aria-label="설문 관리 탭">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`admin-survey-tab${activeTab === tab.id ? " is-active" : ""}`}
            type="button"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? <div className="admin-empty">설문 설정을 불러오는 중입니다.</div> : null}

      {data && !loading ? (
        <>
          {activeTab === "flow" ? (
            <SurveySectionOverview sections={data.sectionSummaries} onEditSection={handleEditSection} />
          ) : null}
          {activeTab === "intro" ? (
            <SurveyIntroEditor intro={data.surveyConfig.intro} saving={saving} onSave={handleIntroSave} />
          ) : null}
          {activeTab === "consent" ? (
            <SurveyConsentEditor consent={data.surveyConfig.consent} saving={saving} onSave={handleConsentSave} />
          ) : null}
          {activeTab === "questions" ? (
            <SurveyQuestionSectionTable
              sections={data.sectionSummaries}
              questionsBySection={data.questionsBySection}
              selectedSectionId={selectedSectionId}
              saving={saving}
              onSectionSelect={setSelectedSectionId}
              onSaveSection={handleSectionSave}
              onSaveQuestion={handleQuestionSave}
            />
          ) : null}
          {activeTab === "preview" ? <SurveyPreviewPanel data={data} /> : null}
          {activeTab === "preview" ? (
            <form
              className="admin-survey-editor"
              onSubmit={(event) => {
                event.preventDefault();
                const formData = new FormData(event.currentTarget);
                void handleThanksSave({
                  title: String(formData.get("thanksTitle") ?? ""),
                  paragraphs: String(formData.get("thanksParagraphs") ?? "")
                    .split("\n")
                    .map((item) => item.trim())
                    .filter(Boolean),
                  reason: String(formData.get("reason") ?? "")
                });
                event.currentTarget.reset();
              }}
            >
              <h3>완료 안내 문구</h3>
              <label className="admin-field">
                제목
                <input className="admin-input" name="thanksTitle" defaultValue={data.surveyConfig.thanks.title} />
              </label>
              <label className="admin-field">
                문단
                <textarea className="admin-textarea" name="thanksParagraphs" defaultValue={data.surveyConfig.thanks.paragraphs.join("\n")} />
              </label>
              <label className="admin-field">
                변경 사유
                <input className="admin-input" name="reason" />
              </label>
              <div className="admin-form-actions">
                <button className="admin-button admin-button--primary" type="submit" disabled={saving}>
                  완료 안내 저장
                </button>
              </div>
            </form>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
