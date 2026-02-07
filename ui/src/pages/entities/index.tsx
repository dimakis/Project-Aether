import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cpu,
  Search,
  RefreshCw,
  Loader2,
  ChevronRight,
  ChevronDown,
  ArrowUpDown,
  LayoutGrid,
  List,
  MapPin,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { DataViewer } from "@/components/ui/data-viewer";
import { cn } from "@/lib/utils";
import {
  useEntities,
  useDomainsSummary,
  useSyncEntities,
  useAreas,
} from "@/api/hooks";
import type { Entity } from "@/lib/types";
import { DOMAIN_EMOJI, type SortBy, type GroupBy } from "./constants";
import { DomainIcon } from "./DomainIcon";
import { StateIndicator } from "./StateIndicator";
import { EntityListItem } from "./EntityListItem";
import { AutomationYamlCard } from "./AutomationYamlCard";
import { InfoRow } from "./InfoRow";

export function EntitiesPage() {
  const [selectedDomain, setSelectedDomain] = useState<string>("");
  const [selectedAreaId, setSelectedAreaId] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [sortBy, setSortBy] = useState<SortBy>("name");
  const [showAreaFilter, setShowAreaFilter] = useState(false);
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const { data: domains, isLoading: domainsLoading } = useDomainsSummary();
  const { data: entitiesData, isLoading: entitiesLoading } = useEntities(
    selectedDomain || undefined,
    selectedAreaId || undefined,
  );
  const { data: areasData } = useAreas();
  const syncMut = useSyncEntities();

  const areaList = areasData?.areas ?? [];

  // Build area lookup: internal UUID → area name
  const areaLookup = useMemo(() => {
    const map: Record<string, string> = {};
    for (const area of areaList) {
      map[area.id] = area.name;
      map[area.ha_area_id] = area.name;
    }
    return map;
  }, [areaList]);

  const entityList = entitiesData?.entities ?? [];

  // Filter by search
  const filtered = useMemo(() => {
    let result = entityList;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          e.entity_id.toLowerCase().includes(q) ||
          (e.area_id && (areaLookup[e.area_id] ?? "").toLowerCase().includes(q)),
      );
    }
    return result;
  }, [entityList, searchQuery, areaLookup]);

  // Sort
  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.name.localeCompare(b.name);
        case "entity_id":
          return a.entity_id.localeCompare(b.entity_id);
        case "state":
          return (a.state ?? "").localeCompare(b.state ?? "");
        case "area": {
          const aArea = a.area_id ? (areaLookup[a.area_id] ?? "") : "";
          const bArea = b.area_id ? (areaLookup[b.area_id] ?? "") : "";
          // Entities with areas first, then alphabetically
          if (aArea && !bArea) return -1;
          if (!aArea && bArea) return 1;
          return aArea.localeCompare(bArea) || a.name.localeCompare(b.name);
        }
        case "domain":
          return a.domain.localeCompare(b.domain) || a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });
    return arr;
  }, [filtered, sortBy, areaLookup]);

  // Grouped entities
  const groupedEntities = useMemo(() => {
    if (groupBy === "none") return null;
    const groups: Record<string, Entity[]> = {};
    for (const entity of sorted) {
      let key: string;
      switch (groupBy) {
        case "area":
          key = entity.area_id
            ? (areaLookup[entity.area_id] ?? entity.area_id)
            : "Unassigned";
          break;
        case "device":
          key = entity.device_id ?? "No Device";
          break;
        case "domain":
          key = entity.domain;
          break;
        default:
          key = "All";
      }
      if (!groups[key]) groups[key] = [];
      groups[key].push(entity);
    }
    // Sort group names, but put "Unassigned"/"No Device" last
    const sortedKeys = Object.keys(groups).sort((a, b) => {
      const unassigned = ["Unassigned", "No Device"];
      if (unassigned.includes(a) && !unassigned.includes(b)) return 1;
      if (!unassigned.includes(a) && unassigned.includes(b)) return -1;
      return a.localeCompare(b);
    });
    return sortedKeys.map((key) => ({ key, entities: groups[key] }));
  }, [sorted, groupBy, areaLookup]);

  const toggleGroup = (key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const getAreaName = (areaId: string | undefined): string => {
    if (!areaId) return "";
    return areaLookup[areaId] ?? areaId;
  };

  return (
    <div className="flex h-full">
      {/* Left Panel: Domains + Entity List */}
      <div className="flex w-96 flex-col border-r border-border">
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between">
            <h1 className="flex items-center gap-2 text-lg font-semibold">
              <Cpu className="h-5 w-5" />
              Entities
            </h1>
            <Button
              variant="outline"
              size="sm"
              onClick={() => syncMut.mutate(false)}
              disabled={syncMut.isPending}
            >
              {syncMut.isPending ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="mr-1 h-3 w-3" />
              )}
              Sync
            </Button>
          </div>

          {/* Domain chips */}
          <div className="mt-3 flex flex-wrap gap-1">
            <button
              onClick={() => setSelectedDomain("")}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                selectedDomain === ""
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-accent",
              )}
            >
              All
            </button>
            {domainsLoading ? (
              <Skeleton className="h-6 w-32" />
            ) : (
              domains?.map((d) => (
                <button
                  key={d.domain}
                  onClick={() => setSelectedDomain(d.domain)}
                  className={cn(
                    "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                    selectedDomain === d.domain
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground hover:bg-accent",
                  )}
                >
                  {DOMAIN_EMOJI[d.domain] && (
                    <span className="text-[10px]">{DOMAIN_EMOJI[d.domain]}</span>
                  )}
                  {d.domain}
                  <span className="ml-0.5 opacity-60">{d.count}</span>
                </button>
              ))
            )}
          </div>

          {/* Area filter */}
          <div className="mt-2">
            <button
              onClick={() => setShowAreaFilter(!showAreaFilter)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                selectedAreaId
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-accent",
              )}
            >
              <MapPin className="h-3 w-3" />
              {selectedAreaId
                ? `📍 ${getAreaName(selectedAreaId)}`
                : "Filter by Area"}
            </button>
            <AnimatePresence>
              {showAreaFilter && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="overflow-hidden"
                >
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    <button
                      onClick={() => {
                        setSelectedAreaId("");
                        setShowAreaFilter(false);
                      }}
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors",
                        selectedAreaId === ""
                          ? "bg-primary/20 text-primary"
                          : "bg-muted text-muted-foreground hover:bg-accent",
                      )}
                    >
                      All Areas
                    </button>
                    {areaList.map((area) => (
                      <button
                        key={area.id}
                        onClick={() => {
                          setSelectedAreaId(area.id);
                          setShowAreaFilter(false);
                        }}
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors",
                          selectedAreaId === area.id
                            ? "bg-primary/20 text-primary"
                            : "bg-muted text-muted-foreground hover:bg-accent",
                        )}
                      >
                        📍 {area.name}
                        {area.entity_count > 0 && (
                          <span className="ml-0.5 opacity-50">
                            {area.entity_count}
                          </span>
                        )}
                      </button>
                    ))}
                    {areaList.length === 0 && (
                      <p className="px-2 py-1 text-[10px] text-muted-foreground">
                        No areas found — sync entities first
                      </p>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Search + Sort + Group */}
          <div className="mt-3 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search entities or areas..."
                className="pl-8 text-sm"
              />
            </div>
            <div className="relative">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="h-9 cursor-pointer appearance-none rounded-md border border-border bg-background px-2.5 pr-7 text-xs transition-colors hover:bg-accent focus:outline-none focus:ring-1 focus:ring-ring"
                title="Sort by"
              >
                <option value="name">Name</option>
                <option value="area">Area</option>
                <option value="domain">Domain</option>
                <option value="state">State</option>
                <option value="entity_id">Entity ID</option>
              </select>
              <ArrowUpDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
            </div>
          </div>

          {/* Group By */}
          <div className="mt-2 flex items-center gap-1.5">
            <span className="text-[10px] text-muted-foreground">Group:</span>
            {(
              [
                { value: "none", label: "None", icon: List },
                { value: "area", label: "Area", icon: MapPin },
                { value: "domain", label: "Domain", icon: Cpu },
                { value: "device", label: "Device", icon: LayoutGrid },
              ] as const
            ).map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => {
                  setGroupBy(value);
                  setCollapsedGroups(new Set());
                }}
                className={cn(
                  "flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-medium transition-colors",
                  groupBy === value
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-accent",
                )}
              >
                <Icon className="h-2.5 w-2.5" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Entity List */}
        <div className="flex-1 overflow-auto">
          {entitiesLoading ? (
            <div className="space-y-1 p-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : sorted.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-center">
              <Cpu className="mb-2 h-8 w-8 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">No entities found</p>
            </div>
          ) : groupBy !== "none" && groupedEntities ? (
            <div className="p-2">
              {groupedEntities.map(({ key, entities: groupEntities }) => {
                const isCollapsed = collapsedGroups.has(key);
                return (
                  <div key={key} className="mb-1">
                    <button
                      onClick={() => toggleGroup(key)}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left transition-colors hover:bg-accent"
                    >
                      {isCollapsed ? (
                        <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
                      )}
                      <span className="text-xs font-semibold">{key}</span>
                      <Badge
                        variant="secondary"
                        className="ml-auto text-[9px]"
                      >
                        {groupEntities.length}
                      </Badge>
                    </button>
                    {!isCollapsed && (
                      <div className="ml-3 space-y-0.5 border-l border-border/50 pl-2">
                        {groupEntities.map((entity) => (
                          <EntityListItem
                            key={entity.id}
                            entity={entity}
                            isSelected={selectedEntity?.id === entity.id}
                            areaName={getAreaName(entity.area_id)}
                            onSelect={() => setSelectedEntity(entity)}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-0.5 p-2">
              {sorted.map((entity) => (
                <EntityListItem
                  key={entity.id}
                  entity={entity}
                  isSelected={selectedEntity?.id === entity.id}
                  areaName={getAreaName(entity.area_id)}
                  onSelect={() => setSelectedEntity(entity)}
                />
              ))}
            </div>
          )}
          <div className="px-4 py-2 text-xs text-muted-foreground">
            {sorted.length} entities
            {selectedAreaId && ` in ${getAreaName(selectedAreaId)}`}
            {groupBy !== "none" &&
              groupedEntities &&
              ` in ${groupedEntities.length} groups`}
          </div>
        </div>
      </div>

      {/* Detail Panel */}
      <div className="flex-1 overflow-auto">
        <AnimatePresence mode="wait">
          {selectedEntity ? (
            <motion.div
              key={selectedEntity.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="p-6"
            >
              <div className="mb-6">
                <div className="flex items-center gap-3">
                  <DomainIcon
                    domain={selectedEntity.domain}
                    state={selectedEntity.state}
                    size="lg"
                  />
                  <div>
                    <h2 className="text-xl font-semibold">
                      {selectedEntity.name}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      {selectedEntity.entity_id}
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">State</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-baseline gap-2">
                      <p className="text-2xl font-semibold">
                        {selectedEntity.state ?? "unknown"}
                      </p>
                      <StateIndicator state={selectedEntity.state} size="lg" />
                    </div>
                    {selectedEntity.unit_of_measurement && (
                      <p className="mt-1 text-sm text-muted-foreground">
                        {selectedEntity.unit_of_measurement}
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Info</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <InfoRow
                      label="Domain"
                      value={selectedEntity.domain}
                      emoji={DOMAIN_EMOJI[selectedEntity.domain]}
                    />
                    <InfoRow
                      label="Area"
                      value={
                        selectedEntity.area_id
                          ? `📍 ${getAreaName(selectedEntity.area_id)}`
                          : "—"
                      }
                    />
                    <InfoRow
                      label="Device Class"
                      value={selectedEntity.device_class ?? "—"}
                    />
                    <InfoRow
                      label="Icon"
                      value={selectedEntity.icon ?? "—"}
                    />
                  </CardContent>
                </Card>
              </div>

              {/* HA YAML Config (for automations/scripts) */}
              {(selectedEntity.domain === "automation" ||
                selectedEntity.domain === "script") && (
                <AutomationYamlCard
                  entityId={selectedEntity.entity_id}
                  domain={selectedEntity.domain}
                />
              )}

              {/* Attributes with YAML/JSON viewer */}
              {selectedEntity.attributes &&
                Object.keys(selectedEntity.attributes).length > 0 && (
                  <Card className="mt-4">
                    <CardHeader>
                      <CardTitle className="text-sm">Attributes</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <DataViewer
                        data={selectedEntity.attributes}
                        defaultMode="yaml"
                        allowToggle
                        collapsible
                        maxHeight={500}
                      />
                    </CardContent>
                  </Card>
                )}
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex h-full flex-col items-center justify-center text-muted-foreground"
            >
              <Cpu className="mb-3 h-10 w-10 text-muted-foreground/20" />
              <p className="text-sm">Select an entity to view details</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
