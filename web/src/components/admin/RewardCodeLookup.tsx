import { useState } from "react";

import { getCompletionCode, redeemCompletionCode } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import type { AdminCompletionCode } from "../../types/admin";
import { adminErrorMessage, adminStatusLabel } from "../../utils/adminLabels";

type RewardCodeLookupProps = {
  eventSlug: string;
};

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "완료 코드 요청에 실패했습니다.");
  }
  return "완료 코드 요청에 실패했습니다.";
}

export function RewardCodeLookup({ eventSlug }: RewardCodeLookupProps) {
  const [code, setCode] = useState("");
  const [notes, setNotes] = useState("");
  const [completionCode, setCompletionCode] = useState<AdminCompletionCode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLookup = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCompletionCode(eventSlug, code.trim());
      setCompletionCode(response.completionCode);
    } catch (lookupError) {
      setCompletionCode(null);
      setError(errorText(lookupError));
    } finally {
      setLoading(false);
    }
  };

  const handleRedeem = async () => {
    if (!completionCode) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await redeemCompletionCode(eventSlug, completionCode.code, notes.trim() || undefined);
      setCompletionCode(response.completionCode);
    } catch (redeemError) {
      setError(errorText(redeemError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="admin-section">
      <div className="admin-form-row">
        <label className="admin-field">
          완료 코드
          <input
            className="admin-input"
            onChange={(event) => setCode(event.target.value)}
            placeholder="TREE-7K2P9Q"
            value={code}
          />
        </label>
        <button className="admin-button admin-button--primary" disabled={!code.trim() || loading} onClick={handleLookup} type="button">
          조회
        </button>
      </div>

      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}

      {completionCode ? (
        <div className="admin-detail">
          <dl>
            <div>
              <dt>코드</dt>
              <dd>{completionCode.code}</dd>
            </div>
            <div>
              <dt>상태</dt>
              <dd>{adminStatusLabel(completionCode.status)}</dd>
            </div>
            <div>
              <dt>발급 시각</dt>
              <dd>{new Date(completionCode.issuedAt).toLocaleString()}</dd>
            </div>
            <div>
              <dt>지급 시각</dt>
              <dd>{completionCode.redeemedAt ? new Date(completionCode.redeemedAt).toLocaleString() : "-"}</dd>
            </div>
          </dl>
          <label className="admin-field">
            지급 메모
            <input
              className="admin-input"
              onChange={(event) => setNotes(event.target.value)}
              placeholder="현장 부스 상품 지급"
              value={notes}
            />
          </label>
          <button
            className="admin-button admin-button--primary"
            disabled={completionCode.status !== "issued" || loading}
            onClick={handleRedeem}
            type="button"
          >
            지급 처리
          </button>
        </div>
      ) : null}
    </section>
  );
}
