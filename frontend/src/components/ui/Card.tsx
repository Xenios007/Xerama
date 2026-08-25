import type { ReactNode } from "react";
import "./Card.css";

interface CardProps {
  title?: string;
  children: ReactNode;
}

export function Card({ title, children }: CardProps) {
  return (
    <section className="xr-card">
      {title && <h3 className="xr-card__title">{title}</h3>}
      <div className="xr-card__body">{children}</div>
    </section>
  );
}
