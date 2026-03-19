import Card from "./Card";
import type { CryptoServiceExplanation, ExplanationSection } from "../api/types";

function sentences(text: string) {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function SectionCard({ title, section }: { title: string; section: ExplanationSection }) {
  return (
    <Card title={title} className="explanation-card">
      <div className="explanation-headline">{section.headline}</div>
      <ul className="explanation-list">
        {section.bullets.map((bullet, index) => (
          <li key={`${title}-${index}`}>{bullet}</li>
        ))}
      </ul>
    </Card>
  );
}

export default function ExplanationCards({ explanation }: { explanation?: CryptoServiceExplanation | null }) {
  if (!explanation) return null;

  const summaryParts = sentences(explanation.overall_summary);

  return (
    <div className="content-stack">
      <Card title="Narrative analysis" className="summary-card">
        <div className="summary-banner">
          {summaryParts.length ? (
            summaryParts.map((part, index) => <p key={index}>{part}</p>)
          ) : (
            <p>{explanation.overall_summary}</p>
          )}
        </div>
      </Card>

      <div className="three-col-grid">
        <SectionCard title="Regime matching readout" section={explanation.sections.regime_matching} />
        <SectionCard title="Scenario engine readout" section={explanation.sections.scenario_engine} />
        <SectionCard title="Risk and portfolio readout" section={explanation.sections.risk_portfolio} />
      </div>

      <Card className="disclaimer-card">
        <div className="disclaimer-label">Method note</div>
        <div className="disclaimer-note">{explanation.disclaimer}</div>
      </Card>
    </div>
  );
}
