import type { ReactNode } from "react";

export default function Card({
  title,
  children,
  className = ""
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`.trim()}>
      {title ? <div className="card-title">{title}</div> : null}
      {children}
    </section>
  );
}
