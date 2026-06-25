import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  getConnection,
  testConnection,
  updateChecklist,
  switchToProduction,
  updateConnection,
  deleteConnection,
} from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { Connection } from "../types";
import StatusBadge from "../components/StatusBadge";
import StagingChecklist from "../components/StagingChecklist";

export default function ConnectionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const connId = Number(id);
  const [conn, setConn] = useState<Connection | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [showDelete, setShowDelete] = useState(false);

  // production key form
  const [prodUrl, setProdUrl] = useState("");
  const [prodKey, setProdKey] = useState("");

  const load = () =>
    getConnection(connId)
      .then((c) => {
        setConn(c);
        setProdUrl(c.production_base_url);
      })
      .catch((e) => setError(apiErrorMessage(e)));

  useEffect(() => {
    load();
  }, [connId]);

  const wrap = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!conn) {
    return <p className="text-gray-500">{error || "Loading…"}</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/" className="text-sm text-brand-600">
            ← Marketplaces
          </Link>
          <h1 className="text-2xl font-bold">{conn.store_name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge status={conn.status} label={conn.status_label} />
            <span className="text-sm text-gray-500">
              Active environment: <strong>{conn.active_auth_key_type}</strong>
            </span>
          </div>
        </div>
        <button
          className="btn-secondary"
          disabled={busy}
          onClick={() =>
            wrap(async () => {
              const res = await testConnection(connId);
              if (res.ok) {
                setError("");
                setNotice(res.message || "Connection OK");
              } else {
                setNotice("");
                setError(res.message || "Connection failed.");
              }
              await load();
            })
          }
        >
          Test Connection
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {notice && <p className="text-sm text-green-600">{notice}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-4 font-semibold">Configuration</h2>
          <dl className="space-y-2 text-sm">
            <Row label="Staging Base URL" value={conn.staging_base_url} />
            <Row label="Staging AuthKey" value={conn.staging_key_masked || "—"} />
            <Row
              label="Production Base URL"
              value={conn.production_base_url || "Not set"}
            />
            <Row
              label="Production AuthKey"
              value={conn.has_production_key ? conn.production_key_masked : "Not set"}
            />
            <Row label="Last tested" value={conn.last_tested_at || "Never"} />
          </dl>

          {!conn.has_production_key && (
            <div className="mt-4 space-y-3 border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700">Add production keys</h3>
              <input
                className="input"
                placeholder="Production base URL"
                value={prodUrl}
                onChange={(e) => setProdUrl(e.target.value)}
              />
              <input
                type="password"
                className="input"
                placeholder="Production AuthKey"
                value={prodKey}
                onChange={(e) => setProdKey(e.target.value)}
              />
              <button
                className="btn-secondary"
                disabled={busy || (!prodKey && !prodUrl)}
                onClick={() =>
                  wrap(async () => {
                    await updateConnection(connId, {
                      production_base_url: prodUrl,
                      production_auth_key: prodKey || undefined,
                    });
                    setProdKey("");
                    setNotice("Production keys saved.");
                    await load();
                  })
                }
              >
                Save production keys
              </button>
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="mb-4 font-semibold">Staging Checklist</h2>
          <StagingChecklist
            items={conn.checklist}
            onToggle={(key, done) =>
              wrap(async () => {
                const updated = await updateChecklist(connId, key, done);
                setConn(updated);
              })
            }
          />
          <button
            className="btn-primary mt-5 w-full"
            disabled={busy || !conn.staging_complete || !conn.has_production_key}
            onClick={() =>
              wrap(async () => {
                const updated = await switchToProduction(connId);
                setConn(updated);
                setNotice("Switched to production.");
              })
            }
          >
            {conn.active_auth_key_type === "production"
              ? "Already on Production"
              : "Switch to Production"}
          </button>
          {!conn.staging_complete && (
            <p className="mt-2 text-center text-xs text-gray-400">
              Complete all staging steps to unlock production.
            </p>
          )}
        </div>
      </div>

      <div className="flex gap-3">
        <Link to={`/listings?connection=${conn.id}`} className="btn-secondary">
          View Listings
        </Link>
        <Link to={`/orders?connection=${conn.id}`} className="btn-secondary">
          View Orders
        </Link>
      </div>

      <div className="card border border-red-200">
        <h2 className="mb-1 font-semibold text-red-700">Danger zone</h2>
        <p className="mb-4 text-sm text-gray-500">
          Deleting this store permanently removes it along with all of its
          products, orders, and shipping records stored here. This cannot be
          undone.
        </p>

        {!showDelete ? (
          <button
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            disabled={busy}
            onClick={() => {
              setShowDelete(true);
              setConfirmText("");
            }}
          >
            Delete Store
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-700">
              Type the store name <strong>{conn.store_name}</strong> to confirm.
            </p>
            <input
              className="input"
              placeholder={conn.store_name}
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
            />
            <div className="flex gap-3">
              <button
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                disabled={busy || confirmText.trim() !== conn.store_name}
                onClick={() =>
                  wrap(async () => {
                    await deleteConnection(connId);
                    navigate("/");
                  })
                }
              >
                {busy ? "Deleting…" : "Permanently delete"}
              </button>
              <button
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  setShowDelete(false);
                  setConfirmText("");
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-gray-500">{label}</dt>
      <dd className="truncate font-medium text-gray-800">{value}</dd>
    </div>
  );
}
