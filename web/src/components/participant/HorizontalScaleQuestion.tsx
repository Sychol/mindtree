import type { CSSProperties } from "react";

import type { AnswerValue } from "../../types/answer";
import type { Question, QuestionOption } from "../../types/question";

type HorizontalScaleQuestionProps = {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue | undefined) => void;
};

function isSameValue(value: AnswerValue | undefined, optionValue: QuestionOption["value"]): boolean {
  if (Array.isArray(value)) {
    return value.some((candidate) => String(candidate) === String(optionValue));
  }
  return String(value) === String(optionValue);
}

function optionNumber(option: QuestionOption): string {
  return String(option.value);
}

function endpointLabel(option: QuestionOption): string {
  const value = String(option.value);
  const label = option.label.trim();
  if (label.startsWith(`${value}(`) && label.endsWith(")")) {
    return label.slice(value.length + 1, -1);
  }
  return label;
}

export function HorizontalScaleQuestion({ question, value, onChange }: HorizontalScaleQuestionProps) {
  const optionCount = question.options.length;
  const gridStyle = {
    "--scale-option-count": optionCount
  } as CSSProperties;
  const minWidth = Math.max(360, optionCount * 58 + 180);
  const leftEndpoint = question.options[0] ? endpointLabel(question.options[0]) : "";
  const rightEndpoint = question.options.at(-1) ? endpointLabel(question.options.at(-1)!) : "";

  return (
    <fieldset className="scale-question horizontal-scale-question">
      <legend className="sr-only">{question.title}</legend>
      <div className="scale-question__scroller">
        <div className="scale-question__grid horizontal-scale-question__grid" style={{ ...gridStyle, minWidth }}>
          <span className="scale-question__endpoint horizontal-scale-question__endpoint" aria-hidden="true" />
          <div className="scale-question__numbers horizontal-scale-question__numbers" aria-hidden="true">
            {question.options.map((option) => (
              <span key={String(option.value)}>{optionNumber(option)}</span>
            ))}
          </div>
          <span className="scale-question__endpoint horizontal-scale-question__endpoint" aria-hidden="true" />

          <span className="scale-question__endpoint horizontal-scale-question__endpoint scale-question__endpoint--left">{leftEndpoint}</span>
          <div className="scale-question__choices horizontal-scale-question__options">
            {question.options.map((option) => {
              const inputId = `${question.id}-${String(option.value)}`;
              return (
                <label key={String(option.value)} className="scale-question__option" htmlFor={inputId}>
                  <input
                    id={inputId}
                    className="scale-question__radio horizontal-scale-question__radio"
                    type="radio"
                    name={`question-${question.id}`}
                    checked={isSameValue(value, option.value)}
                    onChange={() => onChange(option.value)}
                  />
                  <span className="scale-question__radio-face" aria-hidden="true" />
                  <span className="sr-only">{option.label}</span>
                </label>
              );
            })}
          </div>
          <span className="scale-question__endpoint horizontal-scale-question__endpoint scale-question__endpoint--right">{rightEndpoint}</span>
        </div>
      </div>
    </fieldset>
  );
}
