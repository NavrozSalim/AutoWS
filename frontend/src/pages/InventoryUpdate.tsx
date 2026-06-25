import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  downloadInventoryTemplate,
  previewInventoryUpdate,
  updateInventories,
} from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { InventoryUpdateResult } from "../types";

export default function InventoryUpdate() {
  const [params] = useSearchParams();
  const connectionId = Number(params.get("connection"));
  const [file, setFile] = useState<File | null>(null);
  const [validOnly, setValidOnly] = useState(true);
  const [result, setResult] = useState<InventoryUpdateResult | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const requireFile = () => {
    if (!file) {
      setError("Choose a file first.");
      return false;
    }
    if (!connectionId) {
      setError("Select a store from Listings before updating.");
      return false;
    }
    return true;
  };

  const runPreview = async () => {
    if (!requireFile()) return;
    setPreviewing(true);
    setError("");
    setNotice("");
    setResult(null);
    try {
      setResult(await previewInventoryUpdate(connectionId, file!));
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setPreviewing(false);
    }
  };

  const runUpdate = async () => {
    if (!requireFile()) return;
    setUpdating(true);
    setError("");
    setNotice("");
    try {
      const res = await updateInventories(connectionId, file!, validOnly);
      setResult(res);
      if (res.ok) {
        setNotice(res.message || `Updated ${res.updated} product(s).`);
      } else {
        setError(res.message || "Update failed.");
      }
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setUpdating(false);
    }
  };

  const downloadErrors = () => {
    if (!result) return;
    const rows = result.rows.filter((r) => !r.valid);
    const csv = [
      "Row,SKU,Updated Price,Updated Stock,Errors",
      ...rows.map(
        (r) =>
          `${r.row_number},"${r.sku}","${r.updated_price}","${r.updated_stock}","${r.errors.join(
            " | "
          )}"`
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lasoo-inventory-errors.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const busy = previewing || updating;
  const hasErrors = result?.rows.some((r) => !r.valid) ?? false;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Update Inventories</h1>
        <p className="text-sm text-gray-500">
          Update price and stock for products already created for this store.
          Provide <strong>SKU</strong>, <strong>Updated Price</strong>, and{" "}
          <strong>Updated Stock</strong>.
        </p>
      </div>

      <div className="card space-y-4">
        <button
          type="button"
          className="text-sm text-brand-600 hover:underline disabled:opacity-50"
          disabled={downloading}
          onClick={async () => {
            setError("");
            setDownloading(true);
            try {
              await downloadInventoryTemplate();
            } catch (e) {
              setError(apiErrorMessage(e));
            } finally {
              setDownloading(false);
            }
          }}
        >
          ↓ {downloading ? "Downloading…" : "Download inventory template"}
        </button>

        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
            setNotice("");
          }}
          className="block text-sm"
        />

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={validOnly}
            onChange={(e) => setValidOnly(e.target.checked)}
          />
          Update valid rows only (skip rows with errors)
        </label>

        <div className="flex flex-wrap gap-2">
          <button
            className="btn-secondary"
            disabled={!file || busy}
            onClick={runPreview}
          >
            {previewing ? "Checking…" : "Validate / Preview"}
          </button>
          <button
            className="btn-primary"
            disabled={!file || busy}
            onClick={runUpdate}
          >
            {updating ? "Updating…" : "Update Inventories"}
          </button>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {notice && <p className="text-sm text-green-600">{notice}</p>}
      </div>

      {result && (
        <div className="card">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm">
              <strong>{result.valid}</strong> valid,{" "}
              <strong>{result.invalid}</strong> with errors of{" "}
              <strong>{result.total_rows}</strong> rows.
              {result.updated > 0 && (
                <span className="ml-1 text-green-600">
                  {result.updated} updated on {result.environment}.
                </span>
              )}
            </p>
            {hasErrors && (
              <button className="btn-secondary" onClick={downloadErrors}>
                Download error file
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-gray-50 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-3 py-2">Row</th>
                  <th className="px-3 py-2">SKU</th>
                  <th className="px-3 py-2">Price</th>
                  <th className="px-3 py-2">Stock</th>
                  <th className="px-3 py-2">Result</th>
                  <th className="px-3 py-2">Errors</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((r, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="px-3 py-2">{r.row_number}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.sku}</td>
                    <td className="px-3 py-2">
                      {r.old_price != null && (
                        <span className="mr-1 text-xs text-gray-400 line-through">
                          ${r.old_price.toFixed(2)}
                        </span>
                      )}
                      <span>{r.updated_price}</span>
                    </td>
                    <td className="px-3 py-2">
                      {r.old_stock != null && (
                        <span className="mr-1 text-xs text-gray-400 line-through">
                          {r.old_stock}
                        </span>
                      )}
                      <span>{r.updated_stock}</span>
                    </td>
                    <td className="px-3 py-2">
                      {r.updated ? (
                        <span className="text-green-600">Updated</span>
                      ) : r.valid ? (
                        <span className="text-gray-500">Valid</span>
                      ) : (
                        <span className="text-red-600">Errors</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs text-red-600">
                      {r.errors.join(" | ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
