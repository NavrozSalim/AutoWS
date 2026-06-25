import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { connect } from "../api/lasoo";
import { apiErrorMessage } from "../api/client";

const DEFAULT_ENDPOINTS = {
  test: "/Core/TestNoAuthentication/1.0.0",
  bulk_upsert: "/Variants/BulkUpsert/1.0.0",
  bulk_delete: "/Variants/BulkDelete/1.0.0",
  variants_search: "/Variants/Search/1.0.0",
  orders: "/Invoices/Search/1.0.0",
  create_test_order: "/Orders/CreateTestOrder/1.0.0",
  shipping: "/Shipments/Upsert/1.0.0",
  shipments_search: "/Shipments/Search/1.0.0",
};

const DEFAULT_STAGING_BASE_URL = "https://stage.api.lasoo.com.au";

export default function ConnectMarketplace() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    store_name: "",
    retailer_name: "",
    contact_email: "",
    staging_base_url: DEFAULT_STAGING_BASE_URL,
    staging_auth_key: "",
    production_base_url: "",
    production_auth_key: "",
  });
  const [endpoints, setEndpoints] = useState(DEFAULT_ENDPOINTS);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.staging_auth_key.trim()) return setError("Staging AuthKey is required.");
    if (!form.staging_base_url.trim()) return setError("Staging API base URL is required.");
    setLoading(true);
    try {
      const conn = await connect({ ...form, endpoints });
      navigate(`/connections/${conn.id}`);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-bold">Connect Lasoo</h1>
      <p className="mb-6 text-sm text-gray-500">
        Always start with Staging. Production is unlocked after the staging checklist is
        complete.
      </p>

      <form onSubmit={submit} className="space-y-6">
        <div className="card space-y-4">
          <div>
            <label className="label">Store Name *</label>
            <input
              className="input"
              value={form.store_name}
              onChange={(e) => set("store_name", e.target.value)}
              required
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Retailer Name</label>
              <input
                className="input"
                value={form.retailer_name}
                onChange={(e) => set("retailer_name", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Contact Email</label>
              <input
                type="email"
                className="input"
                value={form.contact_email}
                onChange={(e) => set("contact_email", e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-800">Staging (required)</h2>
          <div>
            <label className="label">Staging API Base URL *</label>
            <input
              className="input"
              placeholder="https://stage.api.lasoo.com.au"
              value={form.staging_base_url}
              onChange={(e) => set("staging_base_url", e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">Staging AuthKey *</label>
            <input
              type="password"
              className="input"
              value={form.staging_auth_key}
              onChange={(e) => set("staging_auth_key", e.target.value)}
              required
            />
            <p className="mt-1 text-xs text-gray-400">
              Stored encrypted. Never shown again after saving.
            </p>
          </div>
        </div>

        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-800">Production (optional now)</h2>
          <div>
            <label className="label">Production API Base URL</label>
            <input
              className="input"
              placeholder="https://api.lasoo.com.au/connect"
              value={form.production_base_url}
              onChange={(e) => set("production_base_url", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Production AuthKey</label>
            <input
              type="password"
              className="input"
              value={form.production_auth_key}
              onChange={(e) => set("production_auth_key", e.target.value)}
            />
          </div>
        </div>

        <div className="card">
          <button
            type="button"
            className="text-sm font-medium text-brand-600"
            onClick={() => setShowAdvanced((s) => !s)}
          >
            {showAdvanced ? "▼" : "▶"} Advanced: endpoint paths
          </button>
          {showAdvanced && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {Object.entries(endpoints).map(([key, value]) => (
                <div key={key}>
                  <label className="label capitalize">{key.replace(/_/g, " ")}</label>
                  <input
                    className="input"
                    value={value}
                    onChange={(e) =>
                      setEndpoints((p) => ({ ...p, [key]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex gap-3">
          <button className="btn-primary" disabled={loading}>
            {loading ? "Saving…" : "Save Connection"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => navigate("/")}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
