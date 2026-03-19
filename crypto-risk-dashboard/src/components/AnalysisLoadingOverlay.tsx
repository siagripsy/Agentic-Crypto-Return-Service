export default function AnalysisLoadingOverlay({
  visible,
  label = "Generating scenarios"
}: {
  visible: boolean;
  label?: string;
}) {
  if (!visible) return null;

  return (
    <div className="analysis-loading-overlay" role="status" aria-live="polite" aria-label={label}>
      <div className="analysis-loader">
        <span className="loader-orbit loader-orbit-a" />
        <span className="loader-orbit loader-orbit-b" />
        <span className="loader-orbit loader-orbit-c" />
        <span className="loader-core" />
      </div>
      <div className="analysis-loading-text">
        <strong>{label}</strong>
        <span>Running regime matching, scenario generation, and portfolio analysis</span>
      </div>
    </div>
  );
}
