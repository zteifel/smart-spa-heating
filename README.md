# Smart Spa Heating

A Home Assistant custom integration that intelligently schedules spa/hot tub heating based on electricity prices. It optimizes heating times to avoid expensive peak hours while ensuring your spa is always ready when you need it.

<a href="https://www.buymeacoffee.com/zteifel" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

## Table of Contents

- [Features](#features)
- [Dependencies](#dependencies)
- [Algorithm](#algorithm)
- [Settings](#settings)
- [Installation](#installation)
- [ApexCharts Configuration](#apexcharts-configuration)
- [Entities Created](#entities-created)
- [License](#license)

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
| **Heating Frequency** | 1-48 hours | 3 | Maximum time between heating sessions. The algorithm ensures heating occurs at least this often. |
| **Heating Duration** | 15-240 minutes | 45 | Duration of each scheduled heating session. |
| **Price Threshold** | any | 1.5 | Always heat when price is below this value. Uses same unit as your price entity. |
| **High Price Threshold** | any | 3.0 | Never heat when price is above this value. Uses same unit as your price entity. |
| **Heating Temperature** | 20-42°C | 37.5 | Target temperature when actively heating. |
| **Idle Temperature** | 5-42°C | 35 | Target temperature when not heating (maintains minimal heating). |
| **Manual Override Duration** | 1-12 hours | 3 | How long to respect manual temperature changes before resuming automatic control. |

## Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click the **3 dots** menu (top right) → **Custom repositories**
3. Add the repository:
   - **Repository:** `https://github.com/zteifel/smart-spa-heating`
   - **Category:** `Integration`
   - Click **Add**
4. Search for "Smart Spa Heating" in HACS and click **Download**
5. **Restart Home Assistant**
6. Go to **Settings → Devices & Services → Add Integration**
7. Search for "Smart Spa Heating" and configure with your Nordpool and climate entities

### Manual

1. Download or clone this repository
2. Copy the `smart_spa_heating` folder to your `config/custom_components` directory
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration**
5. Search for "Smart Spa Heating" and configure

## ApexCharts Configuration

You can visualize the heating schedule using [ApexCharts Card](https://github.com/RomRider/apexcharts-card).

The integration provides a `sensor.smart_spa_heating_planned_temperature` entity with a `data` attribute containing timestamp/temperature pairs for graphing.

### Example Card Configuration

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Spa Heating Schedule
graph_span: 48h
span:
  start: minute
now:
  show: false
  label: Now
yaxis:
  - id: price
    opposite: false
    decimals: 2
    apex_config:
      forceNiceScale: true
  - id: temp
    opposite: true
    min: 30
    max: 40
    align_to: 100
    apex_config:
      tickAmount: 4
series:
  - entity: sensor.nordpool_kwh_se3_sek_3_10_025
    type: line
    yaxis_id: price
    name: Price
    float_precision: 2
    color_threshold:
      - value: -1
        color: cyan
      - value: 1.5
        color: green
      - value: 2.5
        color: orange
      - value: 3.5
        color: red
      - value: 5
        color: black
    data_generator: >
      let td = entity.attributes.raw_today; let tm =
      entity.attributes.raw_tomorrow; const repeatLast = (x) => [new
      Date(x.at(-1)[0]).getTime()+3600000, x.at(-1)[1]]; let dataset = [
        ...td.map((data, index) => {
          return [data["start"], data["value"]];
        }),
        ...tm.map((data, index) => { 
          return [data["start"], data["value"]];
        })
      ]; return [...dataset, repeatLast(dataset)];
  - entity: sensor.smart_spa_heating_planned_temperature
    yaxis_id: temp
    data_generator: |
      return entity.attributes.data;
    curve: stepline
    stroke_width: 2
    color_threshold:
      - value: -2
        color: white
      - value: 35
        color: blue
      - value: 37
        color: red
    name: Planned Temperature
apex_config:
  chart:
    height: 250
  xaxis:
    type: datetime
    labels:
      datetimeFormatter:
        hour: HH:mm
experimental:
  color_threshold: true
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
