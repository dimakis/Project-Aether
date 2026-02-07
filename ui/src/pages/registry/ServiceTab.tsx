import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Wrench, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataViewer } from "@/components/ui/data-viewer";
import { cn } from "@/lib/utils";
import type { Service } from "@/lib/types";
import { EmptyState } from "./EmptyState";

interface ServiceTabProps {
  services: Service[];
  domains: string[];
  isLoading: boolean;
  searchQuery: string;
}

export function ServiceTab({
  services,
  domains,
  isLoading,
  searchQuery,
}: ServiceTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [domainFilter, setDomainFilter] = useState("");
  const [sortKey, setSortKey] = useState<"name" | "domain">("name");

  const filtered = useMemo(() => {
    let result = services;
    if (domainFilter) {
      result = result.filter((s) => s.domain === domainFilter);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.service.toLowerCase().includes(q) ||
          s.domain.toLowerCase().includes(q) ||
          (s.name ?? "").toLowerCase().includes(q) ||
          (s.description ?? "").toLowerCase().includes(q),
      );
    }
    return [...result].sort((a, b) => {
      if (sortKey === "domain") return a.domain.localeCompare(b.domain) || a.service.localeCompare(b.service);
      return `${a.domain}.${a.service}`.localeCompare(`${b.domain}.${b.service}`);
    });
  }, [services, searchQuery, domainFilter, sortKey]);

  if (isLoading)
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );

  return (
    <div>
      {/* Domain filter chips */}
      {domains.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-1">
          <button
            onClick={() => setDomainFilter("")}
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
              domainFilter === ""
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground hover:bg-accent",
            )}
          >
            All
          </button>
          {domains.slice(0, 20).map((d) => (
            <button
              key={d}
              onClick={() => setDomainFilter(domainFilter === d ? "" : d)}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                domainFilter === d
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-accent",
              )}
            >
              {d}
            </button>
          ))}
        </div>
      )}

      <div className="mb-3 flex items-center justify-between">
        {(searchQuery || domainFilter) && filtered.length !== services.length ? (
          <p className="text-xs text-muted-foreground">
            Showing {filtered.length} of {services.length}
          </p>
        ) : (
          <div />
        )}
        <select
          aria-label="Sort"
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as "name" | "domain")}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground"
        >
          <option value="name">Name</option>
          <option value="domain">Domain</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState type="services" />
      ) : (
        <div className="space-y-2">
          {filtered.map((svc) => (
            <Card
              key={svc.id}
              className={cn(
                "cursor-pointer transition-all hover:shadow-md",
                expandedId === svc.id && "ring-1 ring-primary/30",
              )}
              onClick={() =>
                setExpandedId(expandedId === svc.id ? null : svc.id)
              }
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
                    <Wrench className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">
                      {svc.domain}.{svc.service}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {svc.name || svc.description || "No description"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {svc.is_seeded && (
                      <Badge variant="secondary" className="text-[10px]">
                        Seeded
                      </Badge>
                    )}
                    <ChevronRight
                      className={cn(
                        "h-3.5 w-3.5 text-muted-foreground transition-transform",
                        expandedId === svc.id && "rotate-90",
                      )}
                    />
                  </div>
                </div>

                <AnimatePresence>
                  {expandedId === svc.id && (
                    <motion.div
                      data-testid="expand-motion"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div
                        className="mt-4 space-y-3 border-t border-border/50 pt-4"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {svc.description && (
                          <p className="text-xs text-muted-foreground">
                            {svc.description}
                          </p>
                        )}
                        {svc.target &&
                          Object.keys(svc.target).length > 0 && (
                            <div>
                              <h4 className="mb-2 text-xs font-medium text-muted-foreground">
                                Target
                              </h4>
                              <DataViewer
                                data={svc.target}
                                defaultMode="yaml"
                                maxHeight={200}
                              />
                            </div>
                          )}
                        {svc.fields &&
                          Object.keys(svc.fields).length > 0 && (
                            <div>
                              <h4 className="mb-2 text-xs font-medium text-muted-foreground">
                                Fields
                              </h4>
                              <DataViewer
                                data={svc.fields}
                                defaultMode="yaml"
                                collapsible
                                maxHeight={300}
                              />
                            </div>
                          )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
