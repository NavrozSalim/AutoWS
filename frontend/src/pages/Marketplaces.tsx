import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listConnections } from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { Connection } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function Marketplaces() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listConnections()
      .then(setConnections)
      .catch((e) => setError(apiErrorMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Marketplaces</h1>
          <p className="text-sm text-gray-500">Connect and manage your Lasoo stores.</p>
        </div>
        <Link to="/connect" className="btn-primary">
          + Connect Marketplace
        </Link>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : connections.length === 0 ? (
        <div className="card text-center">
          <p className="text-gray-500">No stores connected yet.</p>
          <Link to="/connect" className="btn-primary mt-4">
            Connect your first Lasoo store
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {connections.map((c) => (
            <Link key={c.id} to={`/connections/${c.id}`} className="card hover:shadow-md">
              <div className="mb-2 flex items-center justify-between">
                <span className="rounded bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-600">
                  Lasoo
                </span>
                <StatusBadge status={c.status} label={c.status_label} />
              </div>
              <h3 className="text-lg font-semibold">{c.store_name}</h3>
              <p className="text-sm text-gray-500">
                Environment: <span className="font-medium">{c.active_auth_key_type}</span>
              </p>
              <div className="mt-3 h-1.5 w-full rounded-full bg-gray-100">
                <div
                  className="h-1.5 rounded-full bg-brand-500"
                  style={{
                    width: `${
                      (c.checklist.filter((i) => i.done).length / c.checklist.length) * 100
                    }%`,
                  }}
                />
              </div>
              <p className="mt-1 text-xs text-gray-400">
                {c.checklist.filter((i) => i.done).length}/{c.checklist.length} staging steps
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
