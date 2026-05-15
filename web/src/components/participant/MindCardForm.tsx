import type { FormEvent } from "react";

import { Button } from "../common/Button";
import type { MindCardPromptType } from "../../types/card";

type MindCardFormProps = {
  promptType: MindCardPromptType;
  content: string;
  pending?: boolean;
  onPromptTypeChange: (value: MindCardPromptType) => void;
  onContentChange: (value: string) => void;
  onSubmit: () => void;
};

const PROMPTS: Array<{ value: MindCardPromptType; label: string }> = [
  { value: "to_past_me", label: "그때의 나에게" },
  { value: "to_now_me", label: "지금의 나에게" },
  { value: "to_colleague", label: "동료에게" },
  { value: "stress_memory", label: "마음에 남은 상황" }
];

export function MindCardForm({
  promptType,
  content,
  pending = false,
  onPromptTypeChange,
  onContentChange,
  onSubmit
}: MindCardFormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form className="flow-form" onSubmit={handleSubmit}>
      <div className="segmented-control" role="radiogroup" aria-label="마음카드 작성 관점">
        {PROMPTS.map((prompt) => (
          <button
            aria-checked={promptType === prompt.value}
            className={`segmented-control__item${promptType === prompt.value ? " is-active" : ""}`}
            key={prompt.value}
            onClick={() => onPromptTypeChange(prompt.value)}
            role="radio"
            type="button"
          >
            {prompt.label}
          </button>
        ))}
      </div>

      <label className="text-field">
        <span>마음카드</span>
        <textarea
          maxLength={300}
          onChange={(event) => onContentChange(event.target.value)}
          placeholder="오늘은 조금 쉬어가도 괜찮다."
          value={content}
        />
      </label>
      <p className="field-help">{content.length}/300</p>
      <p className="field-help">실명, 소속, 연락처, 구체적 장소나 사건명은 적지 말아 주세요.</p>

      <Button disabled={pending || !content.trim()} fullWidth type="submit">
        {pending ? "저장 중" : "마음카드 저장"}
      </Button>
    </form>
  );
}
