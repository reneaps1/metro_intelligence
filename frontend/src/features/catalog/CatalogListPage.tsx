import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Box, Search } from "lucide-react";
import { useAuth } from "../../lib/auth/AuthProvider";
import { useAsync } from "../../lib/catalog/hooks";
import { listPartNumbers, listProductFamilies } from "../../lib/catalog/api";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { PartNumberForm } from "./PartNumberForm";

export function CatalogListPage() {
  const { user } = useAuth();
  const canManage = user?.role === "admin";

  const [search, setSearch] = useState("");
  const [familyId, setFamilyId] = useState("");
  const [creating, setCreating] = useState(false);

  const families = useAsync(() => listProductFamilies(), []);
  const parts = useAsync(
    () => listPartNumbers({ productFamilyId: familyId || undefined }),
    [familyId],
  );

  const familyById = useMemo(() => {
    const map = new Map<string, string>();
    for (const family of families.data?.items ?? []) map.set(family.id, family.name);
    return map;
  }, [families.data]);

  const visibleParts = useMemo(() => {
    const items = parts.data?.items ?? [];
    const term = search.trim().toLowerCase();
    if (!term) return items;
    return items.filter(
      (part) => part.code.toLowerCase().includes(term) || part.name.toLowerCase().includes(term),
    );
  }, [parts.data, search]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Parts &amp; Catalog</h1>
          <p className="text-sm text-text-secondary">Master catalog — fictitious demo parts (MI-DEMO-*).</p>
        </div>
        {canManage && (
          <Button onClick={() => setCreating((c) => !c)}>{creating ? "Cancel" : "New part number"}</Button>
        )}
      </div>

      {creating && (
        <PartNumberForm
          families={families.data?.items ?? []}
          onCreated={() => {
            setCreating(false);
            parts.refetch();
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search
            size={16}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-disabled"
            aria-hidden="true"
          />
          <input
            type="search"
            aria-label="Search parts by code or name"
            placeholder="Search by code or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="min-h-[44px] w-full rounded border border-border bg-surface py-2 pl-9 pr-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info"
          />
        </div>
        <select
          aria-label="Filter by product family"
          value={familyId}
          onChange={(e) => setFamilyId(e.target.value)}
          className="min-h-[44px] rounded border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info"
        >
          <option value="">All product families</option>
          {(families.data?.items ?? []).map((family) => (
            <option key={family.id} value={family.id}>
              {family.name}
            </option>
          ))}
        </select>
      </div>

      {parts.loading && parts.data === null && <p className="text-sm text-text-secondary">Loading parts…</p>}
      {parts.error && <p className="text-sm text-status-nok">{parts.error}</p>}

      {parts.data !== null && !parts.error && visibleParts.length === 0 && (
        <p className="text-sm text-text-secondary">No parts match your search.</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visibleParts.map((part) => (
          <Link key={part.id} to={`/catalog/${part.id}`} className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded bg-status-info-bg text-status-info">
                  <Box size={20} />
                </span>
                <div>
                  <p className="font-mono text-xs text-text-secondary">{part.code}</p>
                  <p className="font-medium text-text-primary">{part.name}</p>
                  <p className="mt-1 text-xs text-text-secondary">
                    {familyById.get(part.product_family_id) ?? "—"}
                  </p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
