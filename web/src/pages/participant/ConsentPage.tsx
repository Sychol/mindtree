import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { submitConsent } from "../../api/sessions";
import { ErrorState } from "../../components/common/ErrorState";
import { LoadingState } from "../../components/common/LoadingState";
import { RetryNotice } from "../../components/common/RetryNotice";
import { ConsentPanel, EMPTY_CONSENT } from "../../components/participant/ConsentPanel";
import { useEventSession } from "../../hooks/useEventSession";
import { toUserMessage } from "../../lib/errors";
import { statusAtLeast } from "../../lib/routeGuards";
import type { ConsentAcceptedItems } from "../../types/session";

const CONSENT_DOCUMENT_SECTIONS = [
  {
    title: "1. 연구 목적",
    body:
      "본 설문은 소방 및 재난 대응 관련 종사자의 심리적 어려움을 파악하여 회복을 돕는 AI 상담 서비스 리본톡 개발 및 학술연구의 기초자료로 활용하기 위한 것입니다. 제출하신 응답은 연구 목적의 학술 연구 분석 및 논문 게재·발표, 서비스 개선에 활용될 수 있으며, 익명화·가명화 처리 후 개인을 식별할 수 없도록 가공된 자료가 AI 학습 또는 검색증강생성(RAG) 데이터 구축에 활용될 수 있습니다."
  },
  {
    title: "2. 연구대상자의 참여기간, 절차 및 방법",
    body:
      "본 연구는 온라인 설문 방식으로 진행됩니다. 연구대상자는 연구 설명문을 확인한 뒤 연구 참여 동의 여부를 선택합니다. 동의한 경우에만 설문 문항으로 이동하며, 설문은 1회 참여로 진행되고 예상 소요시간은 약 15~20분입니다."
  },
  {
    title: "3. 연구대상자에게 예상되는 위험 및 이득",
    body:
      "본 연구 참여로 인한 특별한 신체적 위험은 없습니다. 다만 일부 문항은 심리적 어려움과 관련된 내용을 포함하므로 응답 중 일시적인 불편감을 느낄 수 있습니다. 불편감이 느껴질 경우 언제든지 설문을 중단할 수 있으며 이에 따른 불이익은 없습니다."
  },
  {
    title: "4. 개인정보 보호에 관한 사항",
    body:
      "본 연구는 이름, 연락처, 주민등록번호 등 직접 식별정보를 수집하지 않습니다. 수집된 자료는 연구 목적에 한하여 사용되며, 연구 결과는 개인을 식별할 수 없는 통계자료 또는 비식별화된 형태로만 제시됩니다."
  },
  {
    title: "5. 연구 참여에 따른 손실에 대한 보상",
    body:
      "본 연구 참여로 인한 특별한 손실이나 위험은 없습니다. 다만 설문 작성에 약 15~20분 정도가 소요될 수 있습니다."
  },
  {
    title: "6. 개인정보 제공 및 보관기간에 관한 내용",
    body:
      "수집된 설문 자료는 비식별화하여 연구 목적에 한해 사용합니다. 자료는 접근 권한이 제한된 연구자 계정 또는 암호화된 저장공간에 보관하며, 연구 종료 후 3년간 보관한 뒤 복구가 불가능한 방식으로 삭제 또는 폐기합니다."
  },
  {
    title: "7. 동의의 철회에 관한 사항",
    body:
      "연구 참여는 자발적이며, 언제든지 불이익 없이 중단할 수 있습니다. 제출 전에는 설문 작성을 중단하거나 창을 닫는 방식으로 참여를 철회할 수 있습니다. 제출 이후에는 특정 응답을 식별하기 어려워 개별 자료 삭제가 제한될 수 있습니다."
  },
  {
    title: "8. 연구 관련 문의",
    body:
      "담당연구원: 최동혁 / 소속: 트래시스(주) / 이메일: trasys21@nate.com / 연락처: 062-653-5151"
  }
];

export function ConsentPage() {
  const { eventSlug } = useParams();
  const navigate = useNavigate();
  const { event, sessionState, loading, error, retry } = useEventSession(eventSlug);
  const [acceptedItems, setAcceptedItems] = useState<ConsentAcceptedItems>(EMPTY_CONSENT);
  const [submitError, setSubmitError] = useState<string | undefined>();
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!eventSlug || !sessionState) {
      return;
    }
    if (statusAtLeast(sessionState.session.status, "consented")) {
      navigate(`/e/${encodeURIComponent(eventSlug)}/questions`, { replace: true });
    }
  }, [eventSlug, navigate, sessionState]);

  async function handleSubmit() {
    if (!event || !sessionState) {
      return;
    }
    setPending(true);
    setSubmitError(undefined);
    try {
      await submitConsent(sessionState.session.id, {
        consentVersion: event.event.consentVersion,
        acceptedItems
      });
      navigate(`/e/${encodeURIComponent(event.event.slug)}/questions`);
    } catch (submitFailure) {
      setSubmitError(toUserMessage(submitFailure));
    } finally {
      setPending(false);
    }
  }

  if (loading) {
    return (
      <main className="screen">
        <LoadingState title="동의 화면을 준비하고 있습니다" />
      </main>
    );
  }

  if (error || !event || !sessionState) {
    return (
      <main className="screen">
        <ErrorState message={error ?? "세션 정보를 확인할 수 없습니다."} onRetry={retry} />
      </main>
    );
  }

  return (
    <main className="screen">
      <div className="screen__header">
        <p className="eyebrow">섹션 2 / 8</p>
        <h1>연구 참여 동의설명문 및 동의서</h1>
        <p>{event.event.name}</p>
      </div>
      {submitError ? <RetryNotice message={submitError} onRetry={handleSubmit} pending={pending} /> : null}
      <section className="panel consent-document">
        {CONSENT_DOCUMENT_SECTIONS.map((section) => (
          <article key={section.title} className="consent-section">
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>
      <ConsentPanel
        value={acceptedItems}
        pending={pending}
        onChange={setAcceptedItems}
        onSubmit={handleSubmit}
      />
    </main>
  );
}
