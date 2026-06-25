import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { bulkUpload, downloadTemplate } from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { BulkUploadResult } from "../types";

export default function BulkUpload() {
  const [params] = useSearchParams();
  const connectionId = Number(params.get("connection"));
  const [file, setFile] = useState<File | null>(null);
  const [validOnly, setValidOnly] = useState(true);
  const [result, setResult] = useState<BulkUploadResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);

  const submit = async () => {
    if (!file) return;
    if (!connectionId) {
      setError("Select a store from Listings before uploading.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await bulkUpload(connectionId, file, validOnly));
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const downloadErrors = () => {
    if (!result) return;
    const rows = result.rows.filter((r) => !r.valid);
    const csv = [
      "Row,Variant Key,SKU,Errors",
      ...rows.map(
        (r) =>
          `${r.row_number},"${r.variant_key}","${r.sku}","${r.errors.join(" | ")}"`
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lasoo-upload-errors.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Bulk Upload</h1>
        <p className="text-sm text-gray-500">
          Upload a CSV/Excel file. We validate each row before importing.
        </p>
      </div>

      <div className="card space-y-4">
        <button
          type="button"
          className="text-sm text-brand-600 hover:underline disabled:opacity-50"
          disabled={downloadingTemplate}
          onClick={async () => {
            setError("");
            setDownloadingTemplate(true);
            try {
              await downloadTemplate();
            } catch (e) {
              setError(apiErrorMessage(e));
            } finally {
              setDownloadingTemplate(false);
            }
          }}
        >
          ↓ {downloadingTemplate ? "Downloading…" : "Download CSV template"}
        </button>
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block text-sm"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={validOnly}
            onChange={(e) => setValidOnly(e.target.checked)}
          />
          Import valid rows only (skip rows with errors)
        </label>
        <button className="btn-primary" disabled={!file || loading} onClick={submit}>
          {loading ? "Uploading…" : "Upload & Preview"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      {result && (
        <div className="card">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm">
              <strong>{result.imported}</strong> imported of{" "}
              <strong>{result.total_rows}</strong> rows.
            </p>
            {result.rows.some((r) => !r.valid) && (
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
                  <th className="px-3 py-2">Variant Key</th>
                  <th className="px-3 py-2">SKU</th>
                  <th className="px-3 py-2">Result</th>
                  <th className="px-3 py-2">Errors</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((r, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="px-3 py-2">{r.row_number}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.variant_key}</td>
                    <td className="px-3 py-2">{r.sku}</td>
                    <td className="px-3 py-2">
                      {r.imported ? (
                        <span className="text-green-600">Imported</span>
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
