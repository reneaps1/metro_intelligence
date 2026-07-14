// F5.5 (MI-34): typed wrappers around F4.4's /catalog endpoints, built on
// lib/api.ts's apiFetch (auth headers, token refresh, and clean error
// messages are already handled there).
import { apiFetch } from "../api";
import type {
  Characteristic,
  CharacteristicCreateInput,
  CharacteristicUpdateInput,
  CharacteristicClassification,
  Page,
  PartNumber,
  PartNumberCreateInput,
  ProductFamily,
  Specification,
  SpecificationCreateInput,
} from "./types";

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function listProductFamilies(): Promise<Page<ProductFamily>> {
  return apiFetch(`/catalog/product-families${query({ page_size: 200 })}`);
}

export function listClassifications(): Promise<Page<CharacteristicClassification>> {
  return apiFetch(`/catalog/characteristic-classifications${query({ page_size: 200 })}`);
}

export function listPartNumbers(params: {
  code?: string;
  productFamilyId?: string;
  page?: number;
}): Promise<Page<PartNumber>> {
  return apiFetch(
    `/catalog/part-numbers${query({
      code: params.code,
      product_family_id: params.productFamilyId,
      page: params.page,
      page_size: 100,
    })}`,
  );
}

export function getPartNumber(id: string): Promise<PartNumber> {
  return apiFetch(`/catalog/part-numbers/${id}`);
}

export function createPartNumber(payload: PartNumberCreateInput): Promise<PartNumber> {
  return apiFetch("/catalog/part-numbers", { method: "POST", body: JSON.stringify(payload) });
}

export function listCharacteristics(partNumberId: string): Promise<Page<Characteristic>> {
  return apiFetch(`/catalog/characteristics${query({ part_number_id: partNumberId, page_size: 200 })}`);
}

export function getCharacteristic(id: string): Promise<Characteristic> {
  return apiFetch(`/catalog/characteristics/${id}`);
}

export function createCharacteristic(payload: CharacteristicCreateInput): Promise<Characteristic> {
  return apiFetch("/catalog/characteristics", { method: "POST", body: JSON.stringify(payload) });
}

export function updateCharacteristic(id: string, payload: CharacteristicUpdateInput): Promise<Characteristic> {
  return apiFetch(`/catalog/characteristics/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function listSpecifications(characteristicId: string): Promise<Specification[]> {
  return apiFetch(`/catalog/characteristics/${characteristicId}/specifications`);
}

export function createSpecificationVersion(
  characteristicId: string,
  payload: SpecificationCreateInput,
): Promise<Specification> {
  return apiFetch(`/catalog/characteristics/${characteristicId}/specifications`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
