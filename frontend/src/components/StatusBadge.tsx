const COLORS: Record<string, string> = {
  // connection
  pending: "bg-gray-100 text-gray-700",
  connected_staging: "bg-blue-100 text-blue-700",
  staging_completed: "bg-amber-100 text-amber-700",
  connected_production: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  disconnected: "bg-gray-100 text-gray-500",
  // listing
  draft: "bg-gray-100 text-gray-700",
  validation_failed: "bg-red-100 text-red-700",
  ready: "bg-indigo-100 text-indigo-700",
  uploaded_staging: "bg-blue-100 text-blue-700",
  mapped: "bg-purple-100 text-purple-700",
  uploaded_production: "bg-green-100 text-green-700",
  // order
  new: "bg-gray-100 text-gray-700",
  paid: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-700",
  refunded: "bg-orange-100 text-orange-700",
  sent: "bg-blue-100 text-blue-700",
  shipping_submitted: "bg-blue-100 text-blue-700",
  shipping_complete: "bg-green-100 text-green-700",
};

export default function StatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  const cls = COLORS[status] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {label ?? status}
    </span>
  );
}
