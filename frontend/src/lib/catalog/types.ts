// F5.5 (MI-34): mirrors backend/app/schemas/catalog.py (F4.4). Decimal fields
// (nominal/lower_tol/upper_tol) come over the wire as strings -- Pydantic v2's
// JSON encoding for Decimal -- never as JS numbers, to avoid float rounding
// on tolerance values.

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProductFamily {
  id: string;
  code: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface PartNumber {
  id: string;
  product_family_id: string;
  code: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CharacteristicClassification {
  id: string;
  code: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Specification {
  id: string;
  characteristic_id: string;
  nominal: string;
  lower_tol: string | null;
  upper_tol: string | null;
  unit: string;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}

export interface SpecificationCreateInput {
  nominal: string;
  lower_tol: string | null;
  upper_tol: string | null;
  unit: string;
}

export interface Characteristic {
  id: string;
  part_number_id: string;
  balloon_number: string;
  name: string;
  characteristic_type: string;
  unit: string;
  classification_id: string;
  created_at: string;
  updated_at: string;
  active_specification: Specification | null;
}

export interface CharacteristicCreateInput {
  part_number_id: string;
  balloon_number: string;
  name: string;
  characteristic_type: string;
  unit: string;
  classification_id: string;
  specification: SpecificationCreateInput;
}

export interface CharacteristicUpdateInput {
  name?: string;
  characteristic_type?: string;
  classification_id?: string;
}

export interface PartNumberCreateInput {
  product_family_id: string;
  code: string;
  name: string;
  description?: string | null;
}
