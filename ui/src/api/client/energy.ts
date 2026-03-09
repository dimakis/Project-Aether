import { request } from "./core";

export interface TariffRate {
  rate: number;
  start: string;
  end: string;
}

export interface TariffResponse {
  configured: boolean;
  plan_name?: string;
  current_period?: string;
  current_rate?: number;
  rates?: {
    day: TariffRate;
    night: TariffRate;
    peak: TariffRate;
  };
  currency?: string;
  unit?: string;
  vat_rate?: number;
}

export const energy = {
  tariffs: () => request<TariffResponse>(`/energy/tariffs`),
};
