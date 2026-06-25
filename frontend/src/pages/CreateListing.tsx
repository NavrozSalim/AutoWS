import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { createListing, getListing, updateListing } from "../api/lasoo";
import { apiErrorMessage } from "../api/client";
import type { ListingInput } from "../types";

const EMPTY: ListingInput = {
  product_key: "",
  variant_key: "",
  title: "",
  description: "",
  brand: "",
  category: "",
  sku: "",
  barcode: "",
  image_urls: "",
  inventory: 0,
  infinite_quantity: false,
  original_price: 0,
  sale_price: 0,
};

export default function CreateListing() {
  const { id } = useParams();
  const isEdit = !!id;
  const [params] = useSearchParams();
  const connectionId = Number(params.get("connection"));
  const navigate = useNavigate();

  const [form, setForm] = useState<ListingInput>(EMPTY);
  const [errors, setErrors] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit) {
      getListing(Number(id))
        .then((l) =>
          setForm({
            product_key: l.external_product_key,
            variant_key: l.external_variant_key,
            title: l.title,
            description: l.description,
            brand: l.brand,
            category: l.category,
            sku: l.sku,
            barcode: l.barcode,
            image_urls: l.image_urls,
            inventory: l.inventory,
            infinite_quantity: l.infinite_quantity,
            original_price: l.original_price,
            sale_price: l.sale_price,
          })
        )
        .catch((e) => setError(apiErrorMessage(e)));
    }
  }, [id]);

  const set = (k: keyof ListingInput, v: string | number | boolean) =>
    setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setErrors([]);
    setLoading(true);
    try {
      const result = isEdit
        ? await updateListing(Number(id), form)
        : await createListing(connectionId, form);
      if (result.status === "validation_failed" && result.validation_errors) {
        setErrors(result.validation_errors);
      } else {
        navigate(-1);
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-bold">
        {isEdit ? "Edit Listing" : "Create Listing"}
      </h1>
      <p className="mb-6 text-sm text-gray-500">
        Enter simple product fields — we convert them to Lasoo's payload.
      </p>

      {errors.length > 0 && (
        <div className="card mb-4 border-red-200 bg-red-50">
          <p className="mb-2 font-semibold text-red-700">Validation errors:</p>
          <ul className="list-inside list-disc text-sm text-red-600">
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <form onSubmit={submit} className="card space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Product Key *">
            <input
              className="input"
              value={form.product_key}
              onChange={(e) => set("product_key", e.target.value)}
            />
          </Field>
          <Field label="Variant Key *">
            <input
              className="input"
              value={form.variant_key}
              onChange={(e) => set("variant_key", e.target.value)}
            />
          </Field>
        </div>
        <Field label="Title *">
          <input
            className="input"
            value={form.title}
            onChange={(e) => set("title", e.target.value)}
          />
        </Field>
        <Field label="Description *">
          <textarea
            className="input"
            rows={3}
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Brand *">
            <input
              className="input"
              value={form.brand}
              onChange={(e) => set("brand", e.target.value)}
            />
          </Field>
          <Field label="Category">
            <input
              className="input"
              placeholder="Furniture > Living Room > Side Tables"
              value={form.category}
              onChange={(e) => set("category", e.target.value)}
            />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="SKU *">
            <input
              className="input"
              value={form.sku}
              onChange={(e) => set("sku", e.target.value)}
            />
          </Field>
          <Field label="Barcode (optional)">
            <input
              className="input"
              value={form.barcode}
              onChange={(e) => set("barcode", e.target.value)}
            />
          </Field>
        </div>
        <Field label="Image URLs * (separate with | , or ;)">
          <textarea
            className="input"
            rows={2}
            placeholder="https://img1.jpg|https://img2.jpg"
            value={form.image_urls}
            onChange={(e) => set("image_urls", e.target.value)}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Inventory *">
            <input
              type="number"
              className="input"
              value={form.inventory}
              disabled={form.infinite_quantity}
              onChange={(e) => set("inventory", Number(e.target.value))}
            />
          </Field>
          <Field label="Original Price *">
            <input
              type="number"
              step="0.01"
              className="input"
              value={form.original_price}
              onChange={(e) => set("original_price", Number(e.target.value))}
            />
          </Field>
          <Field label="Sale Price *">
            <input
              type="number"
              step="0.01"
              className="input"
              value={form.sale_price}
              onChange={(e) => set("sale_price", Number(e.target.value))}
            />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.infinite_quantity}
            onChange={(e) => set("infinite_quantity", e.target.checked)}
          />
          Infinite Quantity
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex gap-3">
          <button className="btn-primary" disabled={loading}>
            {loading ? "Saving…" : "Save Listing"}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  );
}
