# Täglicher Energiefluss für Home Assistant

[English documentation](README.md)


Täglicher Energiefluss ist eine Home-Assistant-Custom-Integration, die Tagesenergie und Kosten aus aktuellen Leistungssensoren berechnet.

Die Integration ist für Setups mit Solarproduktion, Netzsensor und optionalem Akkuspeicher gedacht. Sie erstellt aktuelle Leistungssensoren in W und Tagesenergiesensoren in kWh. Die Netzbezugskosten werden über den Tag mit dem jeweils aktuellen Strompreis aufsummiert. Dadurch werden auch Preisänderungen im Laufe des Tages korrekt berücksichtigt.

## Funktionen

- Hausverbrauch als aktuelle Leistung ohne Akkuspeicher-Ladung
- Hausverbrauch heute in kWh
- Netzbezug als aktuelle Leistung und heute in kWh
- Netzeinspeisung als aktuelle Leistung und heute in kWh
- Netzbezug Kostenrate und Netzbezug Kosten heute
- Solarproduktion als aktuelle Leistung und heute in kWh
- Akkuspeicher-Ladeleistung und Akkuspeicher-Ladung heute
- Akkuspeicher-Entladeleistung und Akkuspeicher-Entladung heute
- PV-Eigenverbrauch als Leistung, kWh und Prozent
- Autarkie heute in Prozent
- Kombinierte oder getrennte Sensoren für Netzbezug/Netzeinspeisung
- Kombinierte oder getrennte Sensoren für Akkuspeicher-Ladung/Entladung
- Mehrere Quell-Entitäten, zum Beispiel für mehrere Hoymiles-Akkus
- Deutsche und englische Übersetzung

## Berechnung

Die Integration geht davon aus, dass alle Quellwerte Leistung in W liefern.

Hausverbrauch ohne Akkuspeicher-Ladung:

```text
hausverbrauch = solarproduktion + netzbezug - netzeinspeisung + akku_entladung - akku_ladung
```

PV-Eigenverbrauch:

```text
pv_eigenverbrauch = solarproduktion - netzeinspeisung
```

Autarkie heute:

```text
autarkie = 100 * (1 - netzbezug_heute / hausverbrauch_heute)
```

PV-Eigenverbrauch heute:

```text
pv_eigenverbrauch_prozent = 100 * pv_eigenverbrauch_heute / solarproduktion_heute
```

Netzbezugskosten:

```text
netzbezug_kostenrate = netzbezug_leistung / 1000 * aktueller_strompreis
```

Diese Kostenrate wird über die Zeit integriert. Wenn sich der Strompreis im Laufe des Tages ändert, wird nur der jeweilige Zeitraum mit diesem Preis berechnet.

## Empfohlene Einrichtung für dein Shelly-/Hoymiles-Setup

Für dein Setup kannst du voraussichtlich diese Auswahl verwenden:

- Aktuelle Stromkosten: `input_number.aktueller_strompreis`
- Solarproduktion Leistung: `sensor.shellyplusplugs_e465b8b31a7c_switch_0_power`
- Kombinierte Netzleistung: `sensor.shellypro3em_a0dd6ca00d0c_total_active_power`
- Netzsensor-Modus: `Kombinierte Netzleistung: positiv = Bezug, negativ = Einspeisung`
- Akkuspeicher-Modus für Hoymiles `bat_p`: `Kombinierte Akkuleistung: positiv = Entladung, negativ = Ladung`
- Akkuspeicher-Leistung: entweder beide Hoymiles-`bat_p`-Sensoren auswählen oder deinen bereits vorhandenen kombinierten Helper verwenden

## Installation

### Manuelle Installation

1. Kopiere den Ordner `custom_components/daily_energy_flow` nach `config/custom_components/` in Home Assistant.
2. Starte Home Assistant neu.
3. Öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
4. Suche nach **Daily Energy Flow** oder **Täglicher Energiefluss**.
5. Wähle deine Quell-Entitäten aus.

### HACS Custom Repository

1. Öffne HACS.
2. Füge dieses Repository als benutzerdefiniertes Repository hinzu.
3. Kategorie: **Integration**.
4. Integration installieren und Home Assistant neu starten.

## Erstellte Sensoren

Die Integration erstellt diese Sensoren:

- Hausverbrauch Leistung
- Hausverbrauch heute
- Solarproduktion Leistung
- Solarproduktion heute
- Netzbezug Leistung
- Netzbezug heute
- Netzeinspeisung Leistung
- Netzeinspeisung heute
- Akkuspeicher-Ladeleistung
- Akkuspeicher-Ladung heute
- Akkuspeicher-Entladeleistung
- Akkuspeicher-Entladung heute
- PV-Eigenverbrauch Leistung
- PV-Eigenverbrauch heute
- Autarkie heute
- PV-Eigenverbrauch heute in Prozent
- Netzbezug Kostenrate
- Netzbezug Kosten heute

## Hinweise

- Die Quell-Sensoren sollten Werte in W liefern.
- Die Strompreis-Entität sollte entweder Währung/kWh liefern, zum Beispiel `0.29`, oder ct/kWh, zum Beispiel `29`.
- Die Tageswerte werden um Mitternacht zurückgesetzt.
- Die Integration speichert die heutigen Werte regelmäßig und stellt sie nach einem Home-Assistant-Neustart wieder her.

## Lizenz

MIT License
