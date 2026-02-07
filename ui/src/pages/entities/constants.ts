import {
  Cpu,
  Lightbulb,
  Thermometer,
  ToggleLeft,
  Wind,
  Droplets,
  Zap,
  Lock,
  Camera,
  Speaker,
  Sun,
  Binary,
} from "lucide-react";

// Domain icon mapping
export const DOMAIN_ICONS: Record<string, typeof Cpu> = {
  light: Lightbulb,
  sensor: Thermometer,
  switch: ToggleLeft,
  climate: Wind,
  fan: Wind,
  binary_sensor: Binary,
  lock: Lock,
  camera: Camera,
  media_player: Speaker,
  cover: Sun,
  water_heater: Droplets,
  automation: Zap,
};

// Domain emoji mapping for visual flair
export const DOMAIN_EMOJI: Record<string, string> = {
  light: "💡",
  sensor: "📊",
  switch: "🔘",
  climate: "🌡️",
  fan: "🌀",
  binary_sensor: "🔲",
  lock: "🔒",
  camera: "📷",
  media_player: "🔊",
  cover: "🪟",
  automation: "⚡",
  water_heater: "🔥",
  person: "👤",
  zone: "📍",
  weather: "🌤️",
  sun: "☀️",
  input_boolean: "✅",
  input_number: "🔢",
  input_select: "📋",
  script: "📜",
  scene: "🎬",
};

export type SortBy = "name" | "entity_id" | "state" | "area" | "domain";
export type GroupBy = "none" | "area" | "device" | "domain";
