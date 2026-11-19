import { CheckCheck, Square } from 'lucide-react';
import { useMemo } from 'react';

import { categoryLabel } from '../../utils/iam.js';

export function PolicyActionPicker({
  actions,
  selectedActions,
  onChange,
  disabled = false,
}) {
  const selected = useMemo(() => new Set(selectedActions), [selectedActions]);
  const groups = useMemo(() => {
    const map = new Map();
    for (const item of actions) {
      if (!map.has(item.category)) {
        map.set(item.category, []);
      }
      map.get(item.category).push(item);
    }
    return [...map.entries()].sort(([left], [right]) => left.localeCompare(right));
  }, [actions]);

  function toggle(action) {
    if (disabled) {
      return;
    }
    const next = new Set(selected);
    if (next.has(action)) {
      next.delete(action);
    } else {
      next.add(action);
    }
    onChange([...next]);
  }

  function selectCategory(items, allSelected) {
    if (disabled) {
      return;
    }
    const next = new Set(selected);
    for (const item of items) {
      if (allSelected) {
        next.delete(item.action);
      } else {
        next.add(item.action);
      }
    }
    onChange([...next]);
  }

  return (
    <div className="policy-action-picker">
      <div className="policy-picker-summary">
        <strong>{selected.size} actions selected</strong>
        <div className="policy-picker-global-actions">
          <button
            className="inline-action"
            type="button"
            onClick={() => selectCategory(actions, false)}
            disabled={disabled || selected.size === actions.length}
          >
            <CheckCheck size={13} /> Select all
          </button>
          <button
            className="inline-action"
            type="button"
            onClick={() => selectCategory(actions, true)}
            disabled={disabled || selected.size === 0}
          >
            <Square size={13} /> Clear all
          </button>
        </div>
      </div>

      <div className="policy-action-groups">
        {groups.map(([category, items]) => {
          const allSelected = items.every((item) => selected.has(item.action));
          return (
            <section key={category} className="policy-action-group">
              <div className="policy-action-group-heading">
                <div>
                  <h3>{categoryLabel(category)}</h3>
                  <span>
                    {items.filter((item) => selected.has(item.action)).length} of{' '}
                    {items.length} allowed
                  </span>
                </div>
                <button
                  className="inline-action"
                  type="button"
                  onClick={() => selectCategory(items, allSelected)}
                  disabled={disabled}
                >
                  {allSelected ? 'Clear group' : 'Select group'}
                </button>
              </div>
              <div className="policy-action-list">
                {items.map((item) => (
                  <label key={item.action} className="policy-action-row">
                    <input
                      type="checkbox"
                      checked={selected.has(item.action)}
                      onChange={() => toggle(item.action)}
                      disabled={disabled}
                    />
                    <span>
                      <code>{item.action}</code>
                      <small>{item.description}</small>
                    </span>
                  </label>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
