import api, { tokenStore } from "./client";
import type {
  BulkUploadResult,
  Connection,
  InventoryUpdateResult,
  Listing,
  ListingInput,
  MessageResponse,
  Order,
} from "../types";

async function postFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);

  const token = tokenStore.getAccess();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`/api${path}`, { method: "POST", headers, body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : `Request failed with status code ${res.status}`;
    throw Object.assign(new Error(message), { response: { status: res.status, data } });
  }
  return data as T;
}

async function downloadCsv(path: string, filename: string): Promise<void> {
  const res = await api.get(path, { responseType: "blob" });
  const blob = new Blob([res.data], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Auth ──
export async function login(username: string, password: string) {
  const res = await api.post("/token/pair", { username, password });
  tokenStore.set(res.data.access, res.data.refresh);
  return res.data;
}

export async function register(username: string, email: string, password: string) {
  return (await api.post("/accounts/register", { username, email, password })).data;
}

// ── Connections ──
export async function listConnections(): Promise<Connection[]> {
  return (await api.get("/lasoo/connections")).data;
}

export async function getConnection(id: number): Promise<Connection> {
  return (await api.get(`/lasoo/connections/${id}`)).data;
}

export interface ConnectPayload {
  store_name: string;
  staging_base_url: string;
  staging_auth_key: string;
  production_base_url?: string;
  production_auth_key?: string;
  retailer_name?: string;
  contact_email?: string;
  endpoints?: Record<string, string>;
}

export async function connect(payload: ConnectPayload): Promise<Connection> {
  return (await api.post("/lasoo/connect", payload)).data;
}

export async function updateConnection(
  id: number,
  payload: Partial<ConnectPayload>
): Promise<Connection> {
  return (await api.put(`/lasoo/connections/${id}`, payload)).data;
}

export async function testConnection(id: number): Promise<MessageResponse> {
  return (await api.post(`/lasoo/connections/${id}/test-connection`)).data;
}

export async function deleteConnection(id: number): Promise<MessageResponse> {
  return (await api.delete(`/lasoo/connections/${id}`)).data;
}

export async function updateChecklist(
  id: number,
  key: string,
  done: boolean
): Promise<Connection> {
  return (await api.post(`/lasoo/connections/${id}/checklist`, { key, done })).data;
}

export async function switchToProduction(id: number): Promise<Connection> {
  return (await api.post(`/lasoo/connections/${id}/switch-to-production`)).data;
}

// ── Listings ──
export async function listListings(
  connectionId?: number,
  status?: string
): Promise<Listing[]> {
  const params: Record<string, string | number> = {};
  if (connectionId) params.connection_id = connectionId;
  if (status) params.status = status;
  return (await api.get("/lasoo/listings", { params })).data;
}

export async function getListing(id: number): Promise<Listing> {
  return (await api.get(`/lasoo/listings/${id}`)).data;
}

export async function createListing(
  connectionId: number,
  payload: ListingInput
): Promise<Listing> {
  return (await api.post(`/lasoo/connections/${connectionId}/listings/create`, payload)).data;
}

export async function updateListing(id: number, payload: ListingInput): Promise<Listing> {
  return (await api.put(`/lasoo/listings/${id}`, payload)).data;
}

export async function deleteListing(id: number): Promise<MessageResponse> {
  return (await api.delete(`/lasoo/listings/${id}`)).data;
}

export async function validateListings(connectionId: number): Promise<MessageResponse> {
  return (await api.post(`/lasoo/connections/${connectionId}/listings/validate`)).data;
}

export async function bulkUpload(
  connectionId: number,
  file: File,
  uploadValidOnly: boolean
): Promise<BulkUploadResult> {
  return postFile<BulkUploadResult>(
    `/lasoo/connections/${connectionId}/listings/bulk-upload?upload_valid_only=${uploadValidOnly}`,
    file
  );
}

export async function uploadStaging(connectionId: number): Promise<MessageResponse> {
  return (await api.post(`/lasoo/connections/${connectionId}/listings/upload-staging`)).data;
}

export async function uploadProduction(connectionId: number): Promise<MessageResponse> {
  return (await api.post(`/lasoo/connections/${connectionId}/listings/upload-production`)).data;
}

export async function downloadTemplate(): Promise<void> {
  return downloadCsv("/lasoo/listings-template.csv", "lasoo-listing-template.csv");
}

// ── Inventory / price updates ──
export async function downloadInventoryTemplate(): Promise<void> {
  return downloadCsv("/lasoo/inventory-template.csv", "lasoo-inventory-template.csv");
}

export async function previewInventoryUpdate(
  connectionId: number,
  file: File
): Promise<InventoryUpdateResult> {
  return postFile<InventoryUpdateResult>(
    `/lasoo/connections/${connectionId}/inventory/preview`,
    file
  );
}

export async function updateInventories(
  connectionId: number,
  file: File,
  updateValidOnly: boolean
): Promise<InventoryUpdateResult> {
  return postFile<InventoryUpdateResult>(
    `/lasoo/connections/${connectionId}/inventory/update?update_valid_only=${updateValidOnly}`,
    file
  );
}

// ── Orders ──
export async function getOrders(
  connectionId: number,
  refresh = false
): Promise<{ ok: boolean; message: string; orders: Order[] }> {
  return (
    await api.get(`/lasoo/connections/${connectionId}/orders`, { params: { refresh } })
  ).data;
}

export async function createTestOrder(
  connectionId: number
): Promise<MessageResponse> {
  return (
    await api.post(`/lasoo/connections/${connectionId}/orders/create-test`)
  ).data;
}

// ── Shipping ──
export async function sendShipping(payload: {
  order_id: number;
  tracking_number: string;
  carrier: string;
  tracking_url?: string;
  shipped_date?: string;
}): Promise<MessageResponse> {
  return (await api.post("/lasoo/shipping/update", payload)).data;
}

export async function completeShipping(orderId: number): Promise<MessageResponse> {
  return (await api.post("/lasoo/shipping/complete", { order_id: orderId })).data;
}
