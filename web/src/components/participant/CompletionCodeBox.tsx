type CompletionCodeBoxProps = {
  code: string;
};

export function CompletionCodeBox({ code }: CompletionCodeBoxProps) {
  return (
    <section className="completion-code-box" aria-label="완료 코드">
      <p>완료 코드</p>
      <strong>{code}</strong>
    </section>
  );
}
