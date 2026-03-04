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

Please analyze this energy data and generate a Python script that:
1. Identifies the top energy consumers
2. Detects peak usage times
3. Finds opportunities for energy savings
4. Calculates potential savings if usage is shifted to off-peak hours

Output insights as JSON to stdout with type="energy_optimization".
