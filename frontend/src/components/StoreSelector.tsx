import type { Connection } from "../types";

export default function StoreSelector({
  connections,
  selectedId,
  onChange,
}: {
  connections: Connection[];
  selectedId: number | null;
  onChange: (id: number) => void;
}) {
  if (connections.length === 0) return null;
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-600">Store:</label>
      <select
        className="input max-w-xs"
        value={selectedId ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {connections.map((c) => (
          <option key={c.id} value={c.id}>
            {c.store_name} ({c.active_auth_key_type})
          </option>
        ))}
      </select>
    </div>
  );
}
