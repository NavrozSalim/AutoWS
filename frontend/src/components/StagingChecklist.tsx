import type { ChecklistItem } from "../types";

export default function StagingChecklist({
  items,
  onToggle,
}: {
  items: ChecklistItem[];
  onToggle: (key: string, done: boolean) => void;
}) {
  return (
    <ul className="space-y-2">
      {items.map((item, idx) => (
        <li
          key={item.key}
          className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-3 py-2"
        >
          <div className="flex items-center gap-3">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                item.done ? "bg-green-500 text-white" : "bg-gray-200 text-gray-600"
              }`}
            >
              {item.done ? "✓" : idx + 1}
            </span>
            <span className={item.done ? "text-gray-500 line-through" : "text-gray-800"}>
              {item.label}
            </span>
            {item.auto && (
              <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-600">
                auto
              </span>
            )}
          </div>
          {!item.auto && (
            <label className="flex cursor-pointer items-center gap-1 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={item.done}
                onChange={(e) => onToggle(item.key, e.target.checked)}
              />
              done
            </label>
          )}
        </li>
      ))}
    </ul>
  );
}
