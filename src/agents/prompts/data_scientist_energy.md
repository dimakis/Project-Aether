I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh} kWh

Data structure (available in /workspace/data.json):
- total_kwh: float — Total consumption across all sensors
- average_kwh: float — Average per sensor
- entity_count: int — Number of sensors
- hours: int — Analysis period
- entities: list of objects, each with:
    - entity_id: str (e.g. "sensor.washing_machine_energy")
    - friendly_name: str | null
    - device_class: str | null (e.g. "energy", "power")
    - unit: str (e.g. "kWh", "W")
    - data_points: list of {{"timestamp": "ISO-8601", "value": float, "unit": str}}
    - stats: {{"total": float, "average": float, "min": float, "max": float,
              "count": int, "unit": str, "peak_value": float,
              "peak_timestamp": "ISO-8601"|null,
              "daily_totals": {{"YYYY-MM-DD": float}},
              "hourly_averages": {{"0": float, ..., "23": float}}}}
    - start_time: "ISO-8601"
    - end_time: "ISO-8601"

If `tariff_rates` is present in the data and `tariff_rates.configured` is true:
- tariff_rates.rates: dict with "day", "night", "peak" keys, each containing:
    - rate: float (c/kWh)
    - start: str (HH:MM)
    - end: str (HH:MM)
- tariff_rates.currency: str (e.g. "EUR")
- tariff_rates.unit: str (e.g. "c/kWh")
- tariff_rates.plan_name: str
- tariff_rates.current_rate: float
- tariff_rates.current_period: str ("day", "night", or "peak")

Please analyze this energy data and generate a Python script that:
1. Identifies the top energy consumers
2. Detects peak usage times
3. Finds opportunities for energy savings
4. If tariff_rates is available and configured, calculate actual costs per entity using the rates and time-of-day schedule; otherwise estimate potential savings from shifting usage to off-peak hours

When tariff data is available, include in the evidence:
- estimated_cost_eur: total estimated cost for the period
- cost_by_period: dict with day/night/peak cost breakdowns
- potential_savings_eur: estimated savings from shifting peak usage to off-peak

Output insights as JSON to stdout with type="energy_optimization".
