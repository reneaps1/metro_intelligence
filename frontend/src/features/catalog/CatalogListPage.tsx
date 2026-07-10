import { Link } from "react-router-dom";
import { Box } from "lucide-react";
import { useDemoData } from "../../lib/mock/DataProvider";
import { Card } from "../../components/ui/Card";

export function CatalogListPage() {
  const { parts, characteristics } = useDemoData();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Parts &amp; Catalog</h1>
        <p className="text-sm text-text-secondary">Master catalog — fictitious demo parts (MI-DEMO-*).</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {parts.map((part) => {
          const count = characteristics.filter((c) => c.partId === part.id).length;
          return (
            <Link key={part.id} to={`/catalog/${part.id}`} className="block">
              <Card className="h-full transition-shadow hover:shadow-md">
                <div className="flex items-start gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded bg-status-info-bg text-status-info">
                    <Box size={20} />
                  </span>
                  <div>
                    <p className="font-mono text-xs text-text-secondary">{part.code}</p>
                    <p className="font-medium text-text-primary">{part.name}</p>
                    <p className="mt-1 text-xs text-text-secondary">{part.productFamily}</p>
                    <p className="mt-2 text-xs text-text-secondary">{count} characteristics</p>
                  </div>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
