I have energy data from {entity_count} sensors over the past {hours} hours.
Total energy consumption: {total_kwh} kWh

Data structure (available in /workspace/data.json):
- entities: List of entity data with data_points, stats, etc.
- total_kwh: Total consumption
- hours: Analysis period

Please analyze this energy data and generate a Python script that:
1. Identifies the top energy consumers
2. Detects peak usage times
3. Finds opportunities for energy savings
4. Calculates potential savings if usage is shifted to off-peak hours

Output insights as JSON to stdout with type="energy_optimization".
