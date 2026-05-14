import type { AnswerValue } from "../../types/answer";
import type { Question } from "../../types/question";
import { NoticeBox } from "../common/NoticeBox";

type QuestionRendererProps = {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue | undefined) => void;
};

function isSelected(value: AnswerValue | undefined, optionValue: string | number): boolean {
  if (Array.isArray(value)) {
    return value.some((candidate) => candidate === optionValue);
  }
  return value === optionValue;
}

export function QuestionRenderer({ question, value, onChange }: QuestionRendererProps) {
  if (question.questionType === "multi_select") {
    return (
      <div className="question-options">
        {question.options.map((option) => {
          const selectedValues = Array.isArray(value) ? value : [];
          const checked = selectedValues.some((candidate) => candidate === option.value);
          return (
            <label key={String(option.value)} className="option-row">
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => {
                  const next = event.target.checked
                    ? [...selectedValues, option.value]
                    : selectedValues.filter((candidate) => candidate !== option.value);
                  onChange(next as AnswerValue);
                }}
              />
              <span>{option.label}</span>
            </label>
          );
        })}
      </div>
    );
  }

  if (question.questionType === "text") {
    return (
      <div className="text-answer">
        <NoticeBox tone="warning">
          <p>실명, 소속, 연락처, 구체적 장소나 날짜는 적지 않습니다.</p>
        </NoticeBox>
        <textarea
          maxLength={300}
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value)}
          placeholder="300자 이내로 입력해 주세요."
        />
      </div>
    );
  }

  if (question.questionType === "number" && !question.options.length) {
    return (
      <input
        className="number-input"
        type="number"
        value={typeof value === "number" ? value : ""}
        onChange={(event) => {
          const next = event.target.value === "" ? undefined : Number(event.target.value);
          onChange(next);
        }}
      />
    );
  }

  return (
    <div className={question.questionType === "likert" ? "likert-grid" : "question-options"}>
      {question.options.map((option) => (
        <button
          key={String(option.value)}
          type="button"
          className={isSelected(value, option.value) ? "option-button is-selected" : "option-button"}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
