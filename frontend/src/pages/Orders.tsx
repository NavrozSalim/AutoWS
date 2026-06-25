import { useCallback, useEffect, useState } from "react";
import { createTestOrder, getOrders } from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { Order } from "../types";
import StatusBadge from "../components/StatusBadge";
import StoreSelector from "../components/StoreSelector";
import { useConnections } from "../hooks/useConnections";

export default function Orders() {
  const { connections, selectedId, select } = useConnections();
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    (refresh = false) => {
      if (!selectedId) return;
      setBusy(true);
      getOrders(selectedId, refresh)
        .then((r) => {
          setOrders(r.orders);
          if (refresh) setNotice(r.message);
        })
        .catch((e) => setError(apiErrorMessage(e)))
        .finally(() => setBusy(false));
    },
    [selectedId]
  );

  useEffect(() => {
    load(false);
  }, [load]);

  const fmt = (cents: number | null) =>
    cents == null ? "—" : `$${(cents / 100).toFixed(2)}`;

  const makeTestOrder = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await createTestOrder(selectedId);
      if (res.ok) {
        setNotice(res.message);
        load(true);
      } else {
        setError(res.message || "Could not create test order.");
      }
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
          <h1 className="text-2xl font-bold">Orders / Invoices</h1>
          <p className="text-sm text-gray-500">Retrieved from Lasoo.</p>
        </div>
        <div className="flex items-center gap-3">
          <StoreSelector
            connections={connections}
            selectedId={selectedId}
            onChange={select}
          />
          <button
            className="btn-secondary"
            disabled={busy || !selectedId}
            onClick={makeTestOrder}
          >
            Create Test Order
          </button>
          <button
            className="btn-primary"
            disabled={busy || !selectedId}
            onClick={() => load(true)}
          >
            {busy ? "Fetching…" : "Fetch from Lasoo"}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {notice && <p className="text-sm text-green-600">{notice}</p>}

      <div className="card overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Items</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Shipping</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No orders. Click "Fetch from Lasoo".
                </td>
              </tr>
            ) : (
              orders.map((o) => (
                <tr key={o.id} className="border-b last:border-0">
                  <td className="px-4 py-3 font-mono text-xs">
                    {o.lasoo_invoice_number || o.external_order_key}
                  </td>
                  <td className="px-4 py-3">
                    {o.customer_info_json?.name ||
                      o.customer_info_json?.email ||
                      "—"}
                  </td>
                  <td className="px-4 py-3">
                    {Array.isArray(o.line_items_json)
                      ? o.line_items_json.length
                      : "—"}
                  </td>
                  <td className="px-4 py-3">{fmt(o.total_amount_cents)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={o.status} label={o.status} />
                  </td>
                  <td className="px-4 py-3">{o.shipping_status}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
