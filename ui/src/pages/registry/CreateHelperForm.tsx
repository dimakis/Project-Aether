import { useState } from "react";
import { motion } from "framer-motion";
import { X, Plus, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useCreateHelper } from "@/api/hooks";
import type { HelperType } from "@/lib/types";

const HELPER_TYPES: { value: HelperType; label: string; description: string }[] = [
  { value: "input_boolean", label: "Toggle", description: "On/off switch" },
  { value: "input_number", label: "Number", description: "Numeric value with min/max" },
  { value: "input_text", label: "Text", description: "Text input field" },
  { value: "input_select", label: "Dropdown", description: "Selection from options" },
  { value: "input_datetime", label: "Date/Time", description: "Date and/or time value" },
  { value: "input_button", label: "Button", description: "Press trigger for automations" },
  { value: "counter", label: "Counter", description: "Increment/decrement counter" },
  { value: "timer", label: "Timer", description: "Countdown timer" },
];

interface CreateHelperFormProps {
  onClose: () => void;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
}

export function CreateHelperForm({ onClose }: CreateHelperFormProps) {
  const [helperType, setHelperType] = useState<HelperType>("input_boolean");
  const [name, setName] = useState("");
  const [inputId, setInputId] = useState("");
  const [idEdited, setIdEdited] = useState(false);
  const [icon, setIcon] = useState("");

  // Type-specific config state
  const [initial, setInitial] = useState("");
  const [min, setMin] = useState("0");
  const [max, setMax] = useState("100");
  const [step, setStep] = useState("1");
  const [unit, setUnit] = useState("");
  const [options, setOptions] = useState("");
  const [hasDate, setHasDate] = useState(true);
  const [hasTime, setHasTime] = useState(true);
  const [duration, setDuration] = useState("");

  const createMut = useCreateHelper();

  function handleNameChange(value: string) {
    setName(value);
    if (!idEdited) {
      setInputId(slugify(value));
    }
  }

  function buildConfig(): Record<string, unknown> {
    const config: Record<string, unknown> = {};

    switch (helperType) {
      case "input_boolean":
        if (initial) config.initial = initial === "true";
        break;
      case "input_number":
        config.min = parseFloat(min) || 0;
        config.max = parseFloat(max) || 100;
        config.step = parseFloat(step) || 1;
        if (unit) config.unit_of_measurement = unit;
        if (initial) config.initial = parseFloat(initial);
        break;
      case "input_text":
        config.min = parseInt(min) || 0;
        config.max = parseInt(max) || 100;
        if (initial) config.initial = initial;
        break;
      case "input_select":
        config.options = options
          .split(",")
          .map((o) => o.trim())
          .filter(Boolean);
        if (initial) config.initial = initial;
        break;
      case "input_datetime":
        config.has_date = hasDate;
        config.has_time = hasTime;
        if (initial) config.initial = initial;
        break;
      case "input_button":
        break;
      case "counter":
        config.initial = parseInt(initial) || 0;
        config.step = parseInt(step) || 1;
        if (min) config.minimum = parseInt(min);
        if (max) config.maximum = parseInt(max);
        break;
      case "timer":
        if (duration) config.duration = duration;
        break;
    }

    return config;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !inputId.trim()) return;

    createMut.mutate(
      {
        helper_type: helperType,
        input_id: inputId,
        name: name.trim(),
        icon: icon || undefined,
        config: buildConfig(),
      },
      {
        onSuccess: (data) => {
          if (data.success) onClose();
        },
      },
    );
  }

  const isValid = name.trim().length > 0 && inputId.trim().length > 0 && /^[a-z][a-z0-9_]*$/.test(inputId);

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="overflow-hidden"
    >
      <Card className="mb-4 border-primary/20">
        <CardContent className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Create Helper</h3>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Helper type selector */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Type</label>
              <div className="flex flex-wrap gap-1.5">
                {HELPER_TYPES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setHelperType(t.value)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                      helperType === t.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-[10px] text-muted-foreground">
                {HELPER_TYPES.find((t) => t.value === helperType)?.description}
              </p>
            </div>

            {/* Name and ID */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Name</label>
                <Input
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="e.g. Vacation Mode"
                  className="h-8 text-sm"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">ID</label>
                <Input
                  value={inputId}
                  onChange={(e) => {
                    setInputId(e.target.value);
                    setIdEdited(true);
                  }}
                  placeholder="e.g. vacation_mode"
                  className="h-8 font-mono text-sm"
                />
              </div>
            </div>

            {/* Icon (optional) */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                Icon <span className="text-muted-foreground/60">(optional)</span>
              </label>
              <Input
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="mdi:toggle-switch"
                className="h-8 text-sm"
              />
            </div>

            {/* Type-specific fields */}
            {helperType === "input_number" && (
              <div className="grid grid-cols-4 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Min</label>
                  <Input value={min} onChange={(e) => setMin(e.target.value)} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Max</label>
                  <Input value={max} onChange={(e) => setMax(e.target.value)} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Step</label>
                  <Input value={step} onChange={(e) => setStep(e.target.value)} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Unit</label>
                  <Input value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="%" className="h-8 text-sm" />
                </div>
              </div>
            )}

            {helperType === "input_text" && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Min Length</label>
                  <Input value={min} onChange={(e) => setMin(e.target.value)} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Max Length</label>
                  <Input value={max} onChange={(e) => setMax(e.target.value)} className="h-8 text-sm" />
                </div>
              </div>
            )}

            {helperType === "input_select" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                  Options <span className="text-muted-foreground/60">(comma-separated)</span>
                </label>
                <Input
                  value={options}
                  onChange={(e) => setOptions(e.target.value)}
                  placeholder="home, away, vacation, guest"
                  className="h-8 text-sm"
                />
              </div>
            )}

            {helperType === "input_datetime" && (
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={hasDate} onChange={(e) => setHasDate(e.target.checked)} />
                  Include date
                </label>
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={hasTime} onChange={(e) => setHasTime(e.target.checked)} />
                  Include time
                </label>
              </div>
            )}

            {helperType === "counter" && (
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Initial</label>
                  <Input value={initial} onChange={(e) => setInitial(e.target.value)} placeholder="0" className="h-8 text-sm" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Min</label>
                  <Input value={min} onChange={(e) => setMin(e.target.value)} className="h-8 text-sm" />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Max</label>
                  <Input value={max} onChange={(e) => setMax(e.target.value)} className="h-8 text-sm" />
                </div>
              </div>
            )}

            {helperType === "timer" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                  Duration <span className="text-muted-foreground/60">(HH:MM:SS)</span>
                </label>
                <Input
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  placeholder="00:30:00"
                  className="h-8 text-sm"
                />
              </div>
            )}

            {(helperType === "input_boolean" || helperType === "input_number" || helperType === "input_text" || helperType === "input_select" || helperType === "input_datetime") && (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                  Initial Value <span className="text-muted-foreground/60">(optional)</span>
                </label>
                <Input
                  value={initial}
                  onChange={(e) => setInitial(e.target.value)}
                  placeholder={
                    helperType === "input_boolean"
                      ? "true or false"
                      : helperType === "input_number"
                        ? "50"
                        : helperType === "input_datetime"
                          ? "2024-01-01 12:00:00"
                          : ""
                  }
                  className="h-8 text-sm"
                />
              </div>
            )}

            {/* Error display */}
            {createMut.data && !createMut.data.success && (
              <p className="text-xs text-destructive">{createMut.data.error || "Failed to create helper"}</p>
            )}

            {/* Submit */}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={!isValid || createMut.isPending}>
                {createMut.isPending ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="mr-1.5 h-3.5 w-3.5" />
                    Create Helper
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </motion.div>
  );
}
