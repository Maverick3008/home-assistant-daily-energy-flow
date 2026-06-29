# Daily Energy Flow for Home Assistant

[Deutsche Dokumentation](README.de.md)


Daily Energy Flow is a Home Assistant custom integration that calculates daily energy and cost values from live power sensors.

It is designed for setups with solar production, a grid meter and an optional battery storage system. The integration creates current power sensors in W and daily energy sensors in kWh. Grid import costs are accumulated over the day using the current electricity price at each update, so changing prices during the day are handled correctly.

## German summary

Daily Energy Flow berechnet den heutigen Hausverbrauch ohne Akkuspeicher-Ladung, Netzbezug/Netzeinspeisung, Solarproduktion, Akkuspeicher-Ladung/-Entladung, Autarkie, PV-Eigenverbrauch und variable Netzbezugskosten aus aktuellen Leistungssensoren. Die vollständige deutsche Anleitung findest du in [`README.de.md`](README.de.md).

## Features

- House consumption power without battery storage charging
- House consumption today in kWh
- Grid import power and grid import today in kWh
- Grid export power and grid export today in kWh
- Grid import cost rate and grid import cost today
- Solar production power and solar production today in kWh
- Battery storage charging/discharging power and energy today
- PV self-consumption power, kWh and percentage
- Autarky percentage for today
- Combined or separate grid import/export sensors
- Combined or separate battery charge/discharge sensors
- Multiple source entities for solar and battery storage systems
- German and English translations

## Calculation

The integration assumes all source values are power values in W.

House consumption without battery charging:

```text
house_consumption = solar_production + grid_import - grid_export + battery_discharge - battery_charge
```

PV self-consumption:

```text
pv_self_consumption = solar_production - grid_export
```

Autarky today:

```text
autarky = 100 * (1 - grid_import_today / house_consumption_today)
```

PV self-consumption today:

```text
pv_self_consumption_percent = 100 * pv_self_consumption_today / solar_production_today
```

Grid import costs:

```text
grid_import_cost_rate = grid_import_power / 1000 * current_electricity_price
```

The cost rate is integrated over time, so a changing electricity price is accumulated correctly.

## Recommended setup for a Shelly / Hoymiles setup

For a setup like this:

- Electricity price: `input_number.aktueller_strompreis`
- Solar production power: `sensor.shellyplusplugs_e465b8b31a7c_switch_0_power`
- Grid power: `sensor.shellypro3em_a0dd6ca00d0c_total_active_power`
- Grid mode: `Combined grid power: positive import, negative export`
- Battery power mode for Hoymiles `bat_p`: `Combined battery power: positive discharging, negative charging`
- Battery power sensors: select both Hoymiles battery power sensors, or one combined helper if you already have one

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
- Autarky today
- PV self-consumption today
- Grid import cost rate
- Grid import cost today

## Notes

- Source sensors should provide W.
- The electricity price entity should provide either currency/kWh, for example `0.29`, or minor units/kWh, for example `29` ct/kWh.
- Daily totals reset at midnight.
- The integration stores today's totals periodically and restores them after a Home Assistant restart.

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

Home Assistant 2026.3 or newer can use these files directly for the integration tile and configuration pages.

## License

MIT License
