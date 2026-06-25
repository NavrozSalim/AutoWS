import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listListings,
  validateListings,
  uploadStaging,
  uploadProduction,
  deleteListing,
} from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { Listing } from "../types";
import StatusBadge from "../components/StatusBadge";
import StoreSelector from "../components/StoreSelector";
import { useConnections } from "../hooks/useConnections";

const FILTERS = [
  { value: "", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "validation_failed", label: "Validation Failed" },
  { value: "ready", label: "Ready" },
  { value: "uploaded_staging", label: "Uploaded Staging" },
  { value: "mapped", label: "Mapped" },
  { value: "uploaded_production", label: "Uploaded Production" },
  { value: "failed", label: "Failed" },
];

export default function ListingDashboard() {
  const { connections, selected, selectedId, select } = useConnections();
  const [listings, setListings] = useState<Listing[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    if (!selectedId) return;
    listListings(selectedId, filter || undefined)
      .then(setListings)
      .catch((e) => setError(apiErrorMessage(e)));
  }, [selectedId, filter]);

  useEffect(() => {
    load();
  }, [load]);

  const wrap = async (fn: () => Promise<string>) => {
    if (!selectedId) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      setNotice(await fn());
      load();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Listings</h1>
          <p className="text-sm text-gray-500">Manage variants and upload to Lasoo.</p>
        </div>
        <StoreSelector
          connections={connections}
          selectedId={selectedId}
          onChange={select}
        />
      </div>

      {connections.length === 0 ? (
        <div className="card text-center text-gray-500">
          Connect a Lasoo store first.{" "}
          <Link className="text-brand-600" to="/connect">
            Connect now
          </Link>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/listings/new?connection=${selectedId}`} className="btn-primary">
              + Create Listing
            </Link>
            <Link to={`/bulk-upload?connection=${selectedId}`} className="btn-secondary">
              Upload CSV/Excel
            </Link>
            <Link
              to={`/inventory-update?connection=${selectedId}`}
              className="btn-secondary"
            >
              Update Inventories
            </Link>
            <button
              className="btn-secondary"
              disabled={busy}
              onClick={() =>
                wrap(async () => (await validateListings(selectedId!)).message)
              }
            >
              Validate Listings
            </button>
            <button
              className="btn-secondary"
              disabled={busy}
              onClick={() => wrap(async () => (await uploadStaging(selectedId!)).message)}
            >
              Upload to Staging
            </button>
            <button
              className="btn-primary"
              disabled={busy || !selected?.staging_complete}
              title={
                selected?.staging_complete
                  ? ""
                  : "Complete the staging checklist first"
              }
              onClick={() =>
                wrap(async () => (await uploadProduction(selectedId!)).message)
              }
            >
              Upload to Production
            </button>
          </div>

          <div className="flex flex-wrap gap-1">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  filter === f.value
                    ? "bg-brand-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {notice && <p className="text-sm text-green-600">{notice}</p>}

          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead className="border-b bg-gray-50 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Variant Key</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Price</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {listings.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                      No listings.
                    </td>
                  </tr>
                ) : (
                  listings.map((l) => (
                    <tr key={l.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs">
                        {l.external_variant_key}
                        {l.validation_errors && l.validation_errors.length > 0 && (
                          <p className="mt-1 text-xs text-red-600">
                            {l.validation_errors[0]}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">{l.title || "—"}</td>
                      <td className="px-4 py-3">{l.sku}</td>
                      <td className="px-4 py-3">
                        ${l.sale_price.toFixed(2)}
                        {l.original_price !== l.sale_price && (
                          <span className="ml-1 text-xs text-gray-400 line-through">
                            ${l.original_price.toFixed(2)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={l.status} label={l.status_label} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/listings/${l.id}/edit`}
                          className="text-brand-600 hover:underline"
                        >
                          Edit
                        </Link>
                        <button
                          className="ml-3 text-red-600 hover:underline"
                          onClick={() =>
                            wrap(async () => {
                              await deleteListing(l.id);
                              return "Listing deleted.";
                            })
                          }
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
