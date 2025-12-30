# Smart Spa Heating

A Home Assistant custom integration that intelligently schedules spa/hot tub heating based on electricity prices. It optimizes heating times to avoid expensive peak hours while ensuring your spa is always ready when you need it.

## Features

- **Price-aware scheduling** with 15-minute granularity
- **Automatic peak avoidance** - identifies expensive periods and schedules around them
- **Threshold-based heating** - always heat when prices are low, never heat when prices are high
- **Manual override detection** - respects manual temperature changes
- **Force controls** - manually trigger heating on/off when needed

## Dependencies

This integration requires two entities to be configured in Home Assistant:

### Electricity Price Entity

An entity that provides electricity prices with `today` and `tomorrow` attributes containing price lists.

**Supported integrations:**
- [Nordpool](https://github.com/custom-components/nordpool) - Provides 96 values per day (15-minute intervals)
- Other price integrations with similar data structure

### Climate Entity

A climate entity that controls your spa/hot tub heating. The integration controls the spa by setting the target temperature:
- **Heating temperature** when actively heating
- **Idle temperature** when not heating

## Algorithm

The scheduling algorithm works as follows:

1. **Mark cheap hours as HEATING** - All time slots where the price is below the *Price Threshold* are marked for heating. When electricity is cheap, heat as much as possible.

2. **Mark expensive hours as COOLING** - All time slots where the price is above the *High Price Threshold* are marked as cooling (no heating allowed).

3. **Peak avoidance loop** - For any remaining unmarked time gaps longer than *Heating Frequency*:
   - Find the highest price point in the gap
   - Center a cooling interval of *Heating Frequency* hours around that peak
   - Place a heating period of *Heating Duration* on each side of the cooling interval
   - If a heating period would fall outside available data, extend the other side to compensate

4. **Repeat** until no unmarked gaps exceed the heating frequency limit.

This ensures:
- Maximum heating during cheap periods
- No heating during expensive peaks
- Regular heating intervals to maintain spa temperature

## Settings

All settings can be adjusted in real-time through Home Assistant number entities.

| Setting | Range | Default | Description |
|---------|-------|---------|-------------|
| **Heating Frequency** | 1-48 hours | 12 | Maximum time between heating sessions. The algorithm ensures heating occurs at least this often. |
| **Heating Duration** | 15-240 minutes | 60 | Duration of each scheduled heating session. |
| **Price Threshold** | 0-10 | 0.05 | Always heat when price is below this value. Uses same unit as your price entity. |
| **High Price Threshold** | 0-100 | 5.0 | Never heat when price is above this value. Uses same unit as your price entity. |
| **Heating Temperature** | 20-42°C | 38 | Target temperature when actively heating. |
| **Idle Temperature** | 5-42°C | 20 | Target temperature when not heating (maintains minimal heating). |
| **Manual Override Duration** | 1-12 hours | 3 | How long to respect manual temperature changes before resuming automatic control. |

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Search for "Smart Spa Heating" and install
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services → Add Integration

### Manual

1. Copy the `smart_spa_heating` folder to your `custom_components` directory
2. Restart Home Assistant
3. Add the integration via Settings → Devices & Services → Add Integration

## ApexCharts Configuration

You can visualize the heating schedule using [ApexCharts Card](https://github.com/RomRider/apexcharts-card).

The integration provides a `sensor.smart_spa_heating_planned_temperature` entity with a `data` attribute containing timestamp/temperature pairs for graphing.

### Example Card Configuration

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Spa Heating Schedule
  show_states: true
graph_span: 24h
span:
  start: hour
now:
  show: true
  label: Now
yaxis:
  - id: temp
    min: 15
    max: 42
    decimals: 0
    apex_config:
      title:
        text: "°C"
  - id: price
    opposite: true
    min: 0
    decimals: 2
    apex_config:
      title:
        text: "Price"
series:
  - entity: sensor.smart_spa_heating_planned_temperature
    name: Planned Temp
    yaxis_id: temp
    type: line
    stroke_width: 2
    color: orange
    data_generator: |
      return entity.attributes.data || [];
  - entity: sensor.nordpool_kwh_se3_sek_3_10_025
    name: Electricity Price
    yaxis_id: price
    type: area
    stroke_width: 1
    color: steelblue
    opacity: 0.3
    data_generator: |
      const today = entity.attributes.today || [];
      const tomorrow = entity.attributes.tomorrow || [];
      const start = new Date();
      start.setHours(0, 0, 0, 0);
      const data = [];
      today.forEach((price, i) => {
        data.push([start.getTime() + i * 15 * 60 * 1000, price]);
      });
      if (tomorrow.length > 0) {
        const tomorrowStart = new Date(start);
        tomorrowStart.setDate(tomorrowStart.getDate() + 1);
        tomorrow.forEach((price, i) => {
          data.push([tomorrowStart.getTime() + i * 15 * 60 * 1000, price]);
        });
      }
      return data;
```

**Note:** Replace `sensor.nordpool_kwh_se3_sek_3_10_025` with your actual Nordpool sensor entity ID.

### Simpler Configuration (Temperature Only)

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Spa Temperature Plan
graph_span: 24h
series:
  - entity: sensor.smart_spa_heating_planned_temperature
    name: Planned Temperature
    type: line
    stroke_width: 2
    data_generator: |
      return entity.attributes.data || [];
```

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `switch.smart_spa_heating_smart_heating` | Switch | Master on/off for automatic heating |
| `sensor.smart_spa_heating_next_heating` | Sensor | Next scheduled heating start time |
| `sensor.smart_spa_heating_heating_schedule` | Sensor | JSON of all scheduled slots |
| `sensor.smart_spa_heating_current_price` | Sensor | Current electricity price |
| `sensor.smart_spa_heating_planned_temperature` | Sensor | For ApexCharts visualization |
| `binary_sensor.smart_spa_heating_heating_active` | Binary Sensor | Whether heating is currently active |
| `binary_sensor.smart_spa_heating_manual_override_active` | Binary Sensor | Whether manual override is active |
| `button.smart_spa_heating_force_heat_on` | Button | Force start heating now |
| `button.smart_spa_heating_force_heat_off` | Button | Force stop heating now |
| `button.smart_spa_heating_clear_manual_override` | Button | Clear manual override early |
| `number.smart_spa_heating_*` | Number | All configurable settings |

## License

MIT License
