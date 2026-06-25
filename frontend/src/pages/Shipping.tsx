import { useCallback, useEffect, useState } from "react";
import { completeShipping, getOrders, sendShipping } from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { Order } from "../types";
import StoreSelector from "../components/StoreSelector";
import { useConnections } from "../hooks/useConnections";

export default function Shipping() {
  const { connections, selectedId, select } = useConnections();
  const [orders, setOrders] = useState<Order[]>([]);
  const [orderId, setOrderId] = useState<number | null>(null);
  const [form, setForm] = useState({
    tracking_number: "",
    carrier: "",
    tracking_url: "",
    shipped_date: "",
  });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    if (!selectedId) return;
    getOrders(selectedId, false)
      .then((r) => setOrders(r.orders))
      .catch((e) => setError(apiErrorMessage(e)));
  }, [selectedId]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderId) return setError("Select an order.");
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await sendShipping({ order_id: orderId, ...form });
      setNotice(res.message);
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const markComplete = async () => {
    if (!orderId) return;
    setBusy(true);
    setError("");
    try {
      const res = await completeShipping(orderId);
      setNotice(res.message);
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Shipping</h1>
          <p className="text-sm text-gray-500">Send tracking info to Lasoo.</p>
        </div>
        <StoreSelector
          connections={connections}
          selectedId={selectedId}
          onChange={select}
        />
      </div>

      <form onSubmit={submit} className="card space-y-4">
        <div>
          <label className="label">Order</label>
          <select
            className="input"
            value={orderId ?? ""}
            onChange={(e) => setOrderId(Number(e.target.value))}
          >
            <option value="">Select an order…</option>
            {orders.map((o) => (
              <option key={o.id} value={o.id}>
                {o.lasoo_invoice_number || o.external_order_key} — {o.status}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Tracking Number</label>
            <input
              className="input"
              value={form.tracking_number}
              onChange={(e) => set("tracking_number", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Carrier</label>
            <input
              className="input"
              value={form.carrier}
              onChange={(e) => set("carrier", e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="label">Tracking URL</label>
          <input
            className="input"
            value={form.tracking_url}
            onChange={(e) => set("tracking_url", e.target.value)}
          />
        </div>
        <div>
          <label className="label">Shipped Date</label>
          <input
            type="date"
            className="input"
            value={form.shipped_date}
            onChange={(e) => set("shipped_date", e.target.value)}
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {notice && <p className="text-sm text-green-600">{notice}</p>}

        <div className="flex gap-3">
          <button className="btn-primary" disabled={busy}>
            Send Shipping Info
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={busy || !orderId}
            onClick={markComplete}
          >
            Mark as Complete
          </button>
        </div>
      </form>
    </div>
  );
}
