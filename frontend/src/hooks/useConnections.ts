import { useEffect, useState } from "react";
import { listConnections } from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { Connection } from "../types";

const STORAGE_KEY = "leeso_selected_connection";

export function useConnections() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = async () => {
    try {
      const data = await listConnections();
      setConnections(data);
      setSelectedId((prev) => {
        if (prev && data.some((c) => c.id === prev)) return prev;
        const stored = Number(localStorage.getItem(STORAGE_KEY));
        if (stored && data.some((c) => c.id === stored)) return stored;
        return data[0]?.id ?? null;
      });
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
  }, []);

  const select = (id: number) => {
    setSelectedId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  };

  const selected = connections.find((c) => c.id === selectedId) ?? null;

  return { connections, selected, selectedId, select, loading, error, reload };
}
