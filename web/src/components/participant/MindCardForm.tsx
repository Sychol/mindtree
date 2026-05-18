import type { FormEvent } from "react";

import { Button } from "../common/Button";

type MindCardFormProps = {
  content: string;
  pending?: boolean;
  submitLabel?: string;
  pendingLabel?: string;
  onContentChange: (value: string) => void;
  onSubmit: () => void;
};

export function MindCardForm({
  content,
  pending = false,
  submitLabel = "카드 추가하기",
  pendingLabel = "저장 중",
  onContentChange,
  onSubmit
}: MindCardFormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form className="flow-form" onSubmit={handleSubmit}>
      <label className="text-field">
        <span>마음카드</span>
        <textarea
          maxLength={300}
          onChange={(event) => onContentChange(event.target.value)}
          placeholder="예: 제가 구조하지 못했던 사람이 있었어요. 어쩔 수 없는 상황이었지만, 그때 너무 무력감을 느꼈어요. 그때의 감정이 아직도 생생해요."
          value={content}
        />
      </label>
      <p className="field-help">{content.length}/300</p>
      <p className="field-help">상황을 구체적으로 식별할 수 있는 장소, 날짜, 이름, 사건명은 적지 말아 주세요.</p>

      <Button disabled={pending || !content.trim()} fullWidth type="submit">
        {pending ? pendingLabel : submitLabel}
      </Button>
    </form>
  );
}
