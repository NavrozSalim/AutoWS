export interface ChecklistItem {
  key: string;
  label: string;
  auto: boolean;
  done: boolean;
}

export interface Connection {
  id: number;
  store_name: string;
  retailer_name: string;
  contact_email: string;
  environment: "staging" | "production";
  active_auth_key_type: "staging" | "production";
  status: string;
  status_label: string;
  staging_base_url: string;
  production_base_url: string;
  endpoints: Record<string, string>;
  has_staging_key: boolean;
  has_production_key: boolean;
  staging_key_masked: string;
  production_key_masked: string;
  checklist: ChecklistItem[];
  staging_complete: boolean;
  last_tested_at: string | null;
  error_message: string;
}

export interface Listing {
  id: number;
  connection_id: number;
  external_product_key: string;
  external_variant_key: string;
  title: string;
  description: string;
  brand: string;
  category: string;
  sku: string;
  barcode: string;
  image_urls: string;
  inventory: number;
  infinite_quantity: boolean;
  original_price: number;
  sale_price: number;
  original_price_cents: number;
  sale_price_cents: number;
  environment: string;
  status: string;
  status_label: string;
  validation_errors: string[] | null;
  last_uploaded_at: string | null;
}

export interface ListingInput {
  product_key: string;
  variant_key: string;
  title: string;
  description: string;
  brand: string;
  category: string;
  sku: string;
  barcode: string;
  image_urls: string;
  inventory: number;
  infinite_quantity: boolean;
  original_price: number;
  sale_price: number;
}

export interface Order {
  id: number;
  lasoo_invoice_number: string;
  external_order_key: string;
  customer_info_json: any;
  line_items_json: any;
  status: string;
  shipping_status: string;
  total_amount_cents: number | null;
  environment: string;
}

export interface MessageResponse {
  ok: boolean;
  message: string;
}

export interface BulkUploadResult {
  total_rows: number;
  imported: number;
  rows: {
    row_number: number;
    sku: string;
    variant_key: string;
    errors: string[];
    valid: boolean;
    imported: boolean;
  }[];
}

export interface InventoryUpdateRow {
  row_number: number;
  sku: string;
  updated_price: string;
  updated_stock: string;
  old_price: number | null;
  old_stock: number | null;
  found: boolean;
  valid: boolean;
  errors: string[];
  updated: boolean;
}

export interface InventoryUpdateResult {
  ok?: boolean;
  message?: string;
  total_rows: number;
  valid: number;
  invalid: number;
  updated: number;
  environment: string;
  rows: InventoryUpdateRow[];
}
