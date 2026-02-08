import { useState } from "react";
import {
  MapPin,
  Plus,
  Trash2,
  Star,
  Loader2,
  CheckCircle,
  XCircle,
  Globe,
  Wifi,
  TestTube,
  Pencil,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useHAZones,
  useCreateZone,
  useUpdateZone,
  useDeleteZone,
  useSetDefaultZone,
  useTestZone,
} from "@/api/hooks";
import type { HAZone, UrlPreference, ZoneTestResult } from "@/api/client/zones";

// ─── URL Preference Toggle ──────────────────────────────────────────────────

const URL_PREF_OPTIONS: { value: UrlPreference; label: string; icon: typeof Wifi; tip: string }[] = [
  { value: "auto", label: "Auto", icon: RefreshCw, tip: "Try local first, fall back to remote" },
  { value: "local", label: "Local", icon: Wifi, tip: "Local URL only" },
  { value: "remote", label: "Remote", icon: Globe, tip: "Remote URL only" },
];

function UrlPreferenceToggle({
  value,
  onChange,
  disabled,
}: {
  value: UrlPreference;
  onChange: (v: UrlPreference) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Connect via
      </span>
      <div className="inline-flex rounded-md border border-border/50 bg-muted/30 p-0.5">
        {URL_PREF_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const active = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              title={opt.tip}
              className={`inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium transition-colors ${
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <Icon className="h-3 w-3" />
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Create / Edit Form ─────────────────────────────────────────────────────

function ZoneForm({
  onSubmit,
  isLoading,
  onCancel,
}: {
  onSubmit: (data: {
    name: string;
    ha_url: string;
    ha_url_remote: string;
    ha_token: string;
    icon: string;
    url_preference: UrlPreference;
  }) => void;
  isLoading: boolean;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [haUrl, setHaUrl] = useState("");
  const [haUrlRemote, setHaUrlRemote] = useState("");
  const [haToken, setHaToken] = useState("");
  const [icon, setIcon] = useState("mdi:home");
  const [urlPref, setUrlPref] = useState<UrlPreference>("auto");

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Plus className="h-4 w-4 text-primary" />
          Add New Zone
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({
              name,
              ha_url: haUrl,
              ha_url_remote: haUrlRemote,
              ha_token: haToken,
              icon,
              url_preference: urlPref,
            });
          }}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              placeholder="Zone name (e.g. Home, Beach House)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              placeholder="Icon (e.g. mdi:home, mdi:beach)"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              placeholder="Local HA URL (e.g. http://192.168.1.50:8123)"
              value={haUrl}
              onChange={(e) => setHaUrl(e.target.value)}
              required
            />
            <Input
              placeholder="Remote HA URL (optional, e.g. https://myha.duckdns.org)"
              value={haUrlRemote}
              onChange={(e) => setHaUrlRemote(e.target.value)}
            />
          </div>
          <Input
            type="password"
            placeholder="Long-lived Access Token"
            value={haToken}
            onChange={(e) => setHaToken(e.target.value)}
            required
          />
          <UrlPreferenceToggle value={urlPref} onChange={setUrlPref} />
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={isLoading || !name || !haUrl || !haToken}>
              {isLoading ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="mr-1.5 h-3.5 w-3.5" />
              )}
              Add Zone
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ─── Zone Card ───────────────────────────────────────────────────────────────

function ZoneCard({ zone }: { zone: HAZone }) {
  const deleteMut = useDeleteZone();
  const setDefaultMut = useSetDefaultZone();
  const updateMut = useUpdateZone();
  const testMut = useTestZone();
  const [testResult, setTestResult] = useState<ZoneTestResult | null>(null);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(zone.name);
  const [editUrl, setEditUrl] = useState(zone.ha_url);
  const [editUrlRemote, setEditUrlRemote] = useState(zone.ha_url_remote ?? "");
  const [editToken, setEditToken] = useState("");

  const handleTest = async () => {
    setTestResult(null);
    const result = await testMut.mutateAsync(zone.id);
    setTestResult(result);
  };

  const handleSave = async () => {
    const payload: Record<string, string> = {};
    if (editName !== zone.name) payload.name = editName;
    if (editUrl !== zone.ha_url) payload.ha_url = editUrl;
    if (editUrlRemote !== (zone.ha_url_remote ?? "")) payload.ha_url_remote = editUrlRemote || "";
    if (editToken) payload.ha_token = editToken;

    if (Object.keys(payload).length > 0) {
      await updateMut.mutateAsync({ id: zone.id, payload });
    }
    setEditing(false);
    setEditToken("");
  };

  const handleCancelEdit = () => {
    setEditing(false);
    setEditName(zone.name);
    setEditUrl(zone.ha_url);
    setEditUrlRemote(zone.ha_url_remote ?? "");
    setEditToken("");
  };

  return (
    <Card className="bg-card/50">
      <CardContent className="pt-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <MapPin className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold">{zone.name}</h3>
                {zone.is_default && (
                  <Badge variant="outline" className="border-primary/30 text-primary text-[10px]">
                    <Star className="mr-0.5 h-2.5 w-2.5" />
                    Default
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{zone.slug}</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setEditing(!editing)}
              title="Edit zone"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            {!zone.is_default && (
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDefaultMut.mutate(zone.id)}
                  disabled={setDefaultMut.isPending}
                  title="Set as default"
                >
                  <Star className="h-3.5 w-3.5" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => deleteMut.mutate(zone.id)}
                  disabled={deleteMut.isPending}
                  className="text-destructive hover:text-destructive"
                  title="Delete zone"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Inline edit form */}
        {editing ? (
          <div className="space-y-2 rounded-lg border border-border/50 bg-muted/30 p-3">
            <Input
              placeholder="Zone name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="h-8 text-xs"
            />
            <div className="grid gap-2 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Local URL
                </label>
                <Input
                  placeholder="http://192.168.1.50:8123"
                  value={editUrl}
                  onChange={(e) => setEditUrl(e.target.value)}
                  className="h-8 font-mono text-xs"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Remote URL
                </label>
                <Input
                  placeholder="https://myha.duckdns.org (optional)"
                  value={editUrlRemote}
                  onChange={(e) => setEditUrlRemote(e.target.value)}
                  className="h-8 font-mono text-xs"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                New Token (leave blank to keep existing)
              </label>
              <Input
                type="password"
                placeholder="Long-lived Access Token"
                value={editToken}
                onChange={(e) => setEditToken(e.target.value)}
                className="h-8 text-xs"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                size="sm"
                onClick={handleSave}
                disabled={updateMut.isPending || !editName || !editUrl}
              >
                {updateMut.isPending ? (
                  <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                ) : (
                  <CheckCircle className="mr-1.5 h-3 w-3" />
                )}
                Save
              </Button>
              <Button size="sm" variant="ghost" onClick={handleCancelEdit}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          /* URLs display */
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs">
              <Wifi className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">Local:</span>
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
                {zone.ha_url}
              </code>
            </div>
            {zone.ha_url_remote ? (
              <div className="flex items-center gap-2 text-xs">
                <Globe className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Remote:</span>
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
                  {zone.ha_url_remote}
                </code>
              </div>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1.5 text-[11px] text-primary/70 transition-colors hover:text-primary"
              >
                <Plus className="h-3 w-3" />
                Add remote URL
              </button>
            )}
          </div>
        )}

        {/* URL preference toggle */}
        <UrlPreferenceToggle
          value={zone.url_preference}
          onChange={(v) =>
            updateMut.mutate({ id: zone.id, payload: { url_preference: v } })
          }
          disabled={updateMut.isPending}
        />

        {/* Test connectivity */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleTest}
            disabled={testMut.isPending}
          >
            {testMut.isPending ? (
              <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
            ) : (
              <TestTube className="mr-1.5 h-3 w-3" />
            )}
            Test Connection
          </Button>
          {testResult && (
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1">
                {testResult.local_ok ? (
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 text-destructive" />
                )}
                <span className={testResult.local_ok ? "text-emerald-400" : "text-destructive"}>
                  Local{testResult.local_version ? ` v${testResult.local_version}` : ""}
                </span>
              </div>
              {testResult.remote_ok !== null && (
                <div className="flex items-center gap-1">
                  {testResult.remote_ok ? (
                    <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-destructive" />
                  )}
                  <span className={testResult.remote_ok ? "text-emerald-400" : "text-destructive"}>
                    Remote{testResult.remote_version ? ` v${testResult.remote_version}` : ""}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export function ZonesPage() {
  const { data: zonesData, isLoading } = useHAZones();
  const createMut = useCreateZone();
  const [showForm, setShowForm] = useState(false);

  const handleCreate = async (data: {
    name: string;
    ha_url: string;
    ha_url_remote: string;
    ha_token: string;
    icon: string;
    url_preference: UrlPreference;
  }) => {
    await createMut.mutateAsync({
      name: data.name,
      ha_url: data.ha_url,
      ha_url_remote: data.ha_url_remote || null,
      ha_token: data.ha_token,
      icon: data.icon || null,
      url_preference: data.url_preference,
    });
    setShowForm(false);
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">HA Zones</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage Home Assistant server connections. Each zone represents a separate HA instance.
          </p>
        </div>
        {!showForm && (
          <Button size="sm" onClick={() => setShowForm(true)}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add Zone
          </Button>
        )}
      </div>

      {showForm && (
        <ZoneForm
          onSubmit={handleCreate}
          isLoading={createMut.isPending}
          onCancel={() => setShowForm(false)}
        />
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : !zonesData?.length ? (
        <Card className="bg-card/50">
          <CardContent className="py-12 text-center">
            <MapPin className="mx-auto h-8 w-8 text-muted-foreground/30" />
            <p className="mt-3 text-sm text-muted-foreground">
              No zones configured. Add your first Home Assistant connection.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {zonesData.map((zone) => (
            <ZoneCard key={zone.id} zone={zone} />
          ))}
        </div>
      )}
    </div>
  );
}
