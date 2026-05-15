import { useState } from "react";

import { getCompletionCode, redeemCompletionCode } from "../../api/admin";
import { ApiClientError } from "../../api/client";
import type { AdminCompletionCode } from "../../types/admin";

type RewardCodeLookupProps = {
  eventSlug: string;
};

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Request failed.";
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
          Completion code
          <input
            className="admin-input"
            onChange={(event) => setCode(event.target.value)}
            placeholder="TREE-7K2P9Q"
            value={code}
          />
        </label>
        <button className="admin-button admin-button--primary" disabled={!code.trim() || loading} onClick={handleLookup} type="button">
          Lookup
        </button>
      </div>

      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}

      {completionCode ? (
        <div className="admin-detail">
          <dl>
            <div>
              <dt>Code</dt>
              <dd>{completionCode.code}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{completionCode.status}</dd>
            </div>
            <div>
              <dt>Issued</dt>
              <dd>{new Date(completionCode.issuedAt).toLocaleString()}</dd>
            </div>
            <div>
              <dt>Redeemed</dt>
              <dd>{completionCode.redeemedAt ? new Date(completionCode.redeemedAt).toLocaleString() : "-"}</dd>
            </div>
          </dl>
          <label className="admin-field">
            Notes
            <input
              className="admin-input"
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Field booth reward"
              value={notes}
            />
          </label>
          <button
            className="admin-button admin-button--primary"
            disabled={completionCode.status !== "issued" || loading}
            onClick={handleRedeem}
            type="button"
          >
            Redeem
          </button>
        </div>
      ) : null}
    </section>
  );
}
