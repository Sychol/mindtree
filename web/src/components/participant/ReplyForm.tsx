import type { FormEvent } from "react";

import { Button } from "../common/Button";
import type { ReplyType } from "../../types/reply";

type ReplyFormProps = {
  replyType: ReplyType;
  content: string;
  pending?: boolean;
  onReplyTypeChange: (value: ReplyType) => void;
  onContentChange: (value: string) => void;
  onSubmit: () => void;
};

const REPLY_TYPES: Array<{ value: ReplyType; label: string }> = [
  { value: "comfort", label: "위로" },
  { value: "empathy", label: "공감" },
  { value: "small_coping", label: "작은 대처법" }
];

export function ReplyForm({
  replyType,
  content,
  pending = false,
  onReplyTypeChange,
  onContentChange,
  onSubmit
}: ReplyFormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form className="flow-form" onSubmit={handleSubmit}>
      <div className="segmented-control" role="radiogroup" aria-label="응원 문장 유형">
        {REPLY_TYPES.map((type) => (
          <button
            aria-checked={replyType === type.value}
            className={`segmented-control__item${replyType === type.value ? " is-active" : ""}`}
            key={type.value}
            onClick={() => onReplyTypeChange(type.value)}
            role="radio"
            type="button"
          >
            {type.label}
          </button>
        ))}
      </div>

      <label className="text-field">
        <span>응원 문장</span>
        <textarea
          maxLength={300}
          onChange={(event) => onContentChange(event.target.value)}
          placeholder="그 시간을 버틴 것만으로도 충분히 애쓰셨습니다."
          value={content}
        />
      </label>
      <p className="field-help">{content.length}/300</p>
      <p className="field-help">실명, 소속, 연락처, 구체적 장소나 사건명은 적지 말아 주세요.</p>

      <Button disabled={pending || !content.trim()} fullWidth type="submit">
        {pending ? "저장 중" : "응원 문장 저장"}
      </Button>
    </form>
  );
}
