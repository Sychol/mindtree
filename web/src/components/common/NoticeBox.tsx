import type { ReactNode } from "react";

type NoticeBoxProps = {
  title?: string;
  children: ReactNode;
  tone?: "info" | "safe" | "warning";
};

export function NoticeBox({ title, children, tone = "info" }: NoticeBoxProps) {
  return (
    <section className={`notice notice--${tone}`}>
      {title ? <h2>{title}</h2> : null}
      <div>{children}</div>
    </section>
  );
}
