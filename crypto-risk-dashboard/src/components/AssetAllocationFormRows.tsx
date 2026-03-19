import type { AssetOption } from "../api/types";

export interface AssetRowValue {
  ticker: string;
  percentage: string;
}

export default function AssetAllocationFormRows({
  rows,
  options,
  onChange,
  onAdd,
  onRemove,
  errors,
  canAdd
}: {
  rows: AssetRowValue[];
  options: AssetOption[];
  onChange: (index: number, next: AssetRowValue) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  errors: string[];
  canAdd: boolean;
}) {
  return (
    <div className="form-group">
      <div className="section-label-row">
        <label>Assets</label>
        <button type="button" className="secondary-btn inline-btn" onClick={onAdd} disabled={!canAdd}>
          Add asset
        </button>
      </div>

      <div className="asset-row-list">
        {rows.map((row, index) => {
          const taken = new Set(rows.map((item) => item.ticker).filter(Boolean));
          return (
            <div key={`${index}-${row.ticker || "empty"}`} className="asset-row">
              <select
                value={row.ticker}
                onChange={(e) => onChange(index, { ...row, ticker: e.target.value })}
              >
                <option value="">Select an asset</option>
                {options.map((option) => {
                  const disabled = taken.has(option.yahoo_ticker) && option.yahoo_ticker !== row.ticker;
                  return (
                    <option
                      key={option.yahoo_ticker}
                      value={option.yahoo_ticker}
                      disabled={disabled}
                    >
                      {option.yahoo_ticker} ({option.symbol})
                    </option>
                  );
                })}
              </select>

              <div className="percent-input-wrap">
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.01}
                  value={row.percentage}
                  onChange={(e) => onChange(index, { ...row, percentage: e.target.value })}
                  placeholder="0"
                />
                <span>%</span>
              </div>

              <button
                type="button"
                className="ghost-btn inline-btn"
                onClick={() => onRemove(index)}
                disabled={rows.length <= 1}
              >
                Remove
              </button>
            </div>
          );
        })}
      </div>

      {!!errors.length && (
        <div className="field-error">
          {errors.map((error) => (
            <div key={error}>{error}</div>
          ))}
        </div>
      )}

      <div className="helper-text">
        Choose one or more assets and assign percentages that sum to exactly 100%.
      </div>
    </div>
  );
}
