import type { ReactNode } from "react";

type DisplayMetricCardProps = {
  iconSrc?: string;
  title: string;
  value?: number | string;
  unit?: string;
  children?: ReactNode;
};

export function DisplayMetricCard({ iconSrc, title, value, unit, children }: DisplayMetricCardProps) {
  return (
    <section className="display-metric-card" aria-label={title}>
      {iconSrc ? <img className="display-metric-card__icon" src={iconSrc} alt="" aria-hidden="true" /> : null}
      <h2>{title}</h2>
      {value !== undefined ? (
        <div className="display-metric-card__value">
          <strong>{typeof value === "number" ? value.toLocaleString("ko-KR") : value}</strong>
          {unit ? <span>{unit}</span> : null}
        </div>
      ) : null}
      {children ? <div className="display-metric-card__body">{children}</div> : null}
    </section>
  );
}
