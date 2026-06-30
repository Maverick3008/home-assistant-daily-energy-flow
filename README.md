# Daily Energy Flow for Home Assistant

[Deutsche Dokumentation](README.de.md)

Daily Energy Flow is a Home Assistant custom integration for household consumption, solar production, grid import/export and battery storage.

The integration now separates **power** and **energy** on purpose:

- Current values in **W** are still calculated live from power sensors.
- Daily values in **kWh**, self-sufficiency, PV self-consumption and grid import costs are calculated from existing energy sensors in **kWh or Wh**.

This lets you use existing `utility_meter`, inverter, Shelly, myenergi or Hoymiles daily energy sensors instead of integrating W values again inside the integration.

## Deutsche Kurzfassung

Daily Energy Flow nutzt Live-Leistungssensoren in W nur für aktuelle Anzeigen. Tages-kWh, Hausverbrauch heute, Autarkie, PV-Eigenverbrauch und variable Netzbezugskosten werden ab Version 0.2.0 aus vorhandenen Energie-Sensoren in kWh/Wh berechnet. Die vollständige deutsche Anleitung findest du in [`README.de.md`](README.de.md).

## Features

- House consumption power excluding battery storage charging
- House consumption today in kWh from existing energy sensors
- Grid import power and grid import today in kWh
- Grid export power and grid export today in kWh
- Grid import cost rate and grid import cost today
- Solar production power and solar production today in kWh
- Battery storage charging/discharging power and energy today
- PV self-consumption power, kWh and percentage
- Self-sufficiency percentage for today
- Combined or separate grid import/export sensors for live power
- Combined or separate battery charge/discharge sensors for live power
- Multiple source entities for solar and battery storage systems
- German and English translations
- Local brand icons and logos

## Important change in version 0.2.0

Earlier versions integrated daily kWh internally from W values. Starting with **0.2.0**:

- **Power sensors** are used only for live current values.
- **Energy sensors in kWh/Wh** are used for daily kWh, house consumption today, self-sufficiency, PV self-consumption and variable grid import costs.

The energy sensors should be daily counters, for example `..._today`, `..._heute` or `utility_meter` sensors with a daily cycle.

## Calculation

### Live power in W

House consumption excluding battery storage charging:

```text
house_consumption_power = solar_production_power + grid_import_power - grid_export_power + battery_discharge_power - battery_charge_power
```

PV self-consumption power:

```text
pv_self_consumption_power = solar_production_power - grid_export_power
```

### Daily values in kWh

The following values are read from existing energy sensors:

- Solar production today
- Grid import today
- Grid export today
- Battery storage charge today
- Battery storage discharge today

House consumption today excluding battery storage charging:

```text
house_consumption_today = solar_production_today + grid_import_today - grid_export_today + battery_discharge_today - battery_charge_today
```

PV self-consumption today:

```text
pv_self_consumption_today = solar_production_today - grid_export_today
```

Self-sufficiency today:

```text
self_sufficiency = 100 * (1 - grid_import_today / house_consumption_today)
```

PV self-consumption today:

```text
pv_self_consumption_percent = 100 * pv_self_consumption_today / solar_production_today
```

### Variable grid import costs

Grid import costs are accumulated over the day using the delta of the existing grid import energy sensor:

```text
new_cost = delta_grid_import_kwh * electricity_price_at_that_time
```

This means changing electricity prices during the day do not retroactively recalculate earlier kWh with the new price.

## Recommended setup for a Shelly / Hoymiles setup

For a setup like this:

### Live power

- Electricity price: `input_number.aktueller_strompreis`
- Solar production power: `sensor.shellyplusplugs_e465b8b31a7c_switch_0_power`
- Grid power: `sensor.shellypro3em_a0dd6ca00d0c_total_active_power`
- Grid mode: `Combined grid power: positive import, negative export`
- Battery power mode for Hoymiles `bat_p`: `Combined battery power: positive discharging, negative charging`
- Battery power sensors: select both Hoymiles battery power sensors, or one combined helper if you already have one

### Daily energy

Select existing daily counters, for example:

- Solar production energy today: your PV / balcony solar yield today sensor
- Grid import energy today: your grid import today sensor
- Grid export energy today: your grid export today sensor
- Battery storage charge today: your battery charge today sensor
- Battery storage discharge today: your battery discharge today sensor

Energy sources in `kWh`, `Wh` and `MWh` are supported. `Wh` is converted to `kWh` automatically.

## Installation

### Manual installation

1. Copy the folder `custom_components/daily_energy_flow` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**.
4. Search for **Daily Energy Flow**.
5. Select your source entities.

### HACS custom repository

1. Open HACS.
2. Add this repository as a custom repository.
3. Category: **Integration**.
4. Install the integration and restart Home Assistant.

## Created sensors

The integration creates these sensors:

- House consumption power
- House consumption today
- Solar production power
- Solar production today
- Grid import power
- Grid import today
- Grid export power
- Grid export today
- Battery storage charging power
- Battery storage charge today
- Battery storage discharging power
- Battery storage discharge today
- PV self-consumption power
- PV self-consumption today
- Self-sufficiency today
- PV self-consumption today
- Grid import cost rate
- Grid import cost today

## Notes

- Power sources should provide W.
- Energy sources should provide daily values in kWh or Wh.
- The electricity price entity should provide either currency/kWh, for example `0.29`, or minor units/kWh, for example `29` ct/kWh.
- Daily kWh values are not integrated internally from W; they are read from the selected energy sensors.
- The integration stores only the ongoing variable-price grid import cost state.

## Troubleshooting: Integration does not appear

If **Daily Energy Flow** does not appear under **Settings → Devices & services → Add integration** after installation, check the following:

1. The folder must be located exactly here:

```text
/config/custom_components/daily_energy_flow/
```

This would be wrong, for example:

```text
/config/custom_components/home-assistant-daily-energy-flow/custom_components/daily_energy_flow/
```

2. These files must be directly inside the integration folder:

```text
__init__.py
manifest.json
config_flow.py
sensor.py
manager.py
const.py
strings.json
translations/
brand/
```

3. Restart Home Assistant completely. Reloading YAML is not enough.
4. If necessary, clear the browser cache or hard-refresh the Home Assistant page with `Ctrl + F5`.
5. Search for **Daily Energy Flow**. In the German UI it may also appear as **Täglicher Energiefluss**.
6. If it still does not appear, check **Settings → System → Logs** for errors related to `daily_energy_flow`.

## Brand assets

The repository includes local Home Assistant brand assets in:

```text
custom_components/daily_energy_flow/brand/
```

Included files:

- `icon.png` and `icon@2x.png`
- `dark_icon.png` and `dark_icon@2x.png`
- `logo.png` and `logo@2x.png`
- `dark_logo.png` and `dark_logo@2x.png`

## License

MIT License
