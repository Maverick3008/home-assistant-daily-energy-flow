# Täglicher Energiefluss für Home Assistant

[English documentation](README.md)

Täglicher Energiefluss ist eine Home-Assistant-Custom-Integration für Stromverbrauch, PV-Erzeugung, Netzbezug und Akkuspeicher.

Die Integration trennt jetzt bewusst zwischen **Leistung** und **Energie**:

- Die aktuellen Anzeigen in **W** werden weiterhin live aus Leistungssensoren berechnet.
- Die Tageswerte in **kWh**, Autarkie, PV-Eigenverbrauch und Netzbezugskosten werden aus bereits vorhandenen Energie-Sensoren in **kWh oder Wh** berechnet.

Dadurch werden vorhandene `utility_meter`-, Wechselrichter-, Shelly-, myenergi- oder Hoymiles-Tageszähler genutzt, statt Tages-kWh erneut aus Werten in W zu integrieren.

## Funktionen

- Hausverbrauch als aktuelle Leistung ohne Akkuspeicher-Ladung
- Hausverbrauch heute in kWh aus vorhandenen Energie-Sensoren
- Netzbezug als aktuelle Leistung und heute in kWh
- Netzeinspeisung als aktuelle Leistung und heute in kWh
- Netzbezug Kostenrate und Netzbezug Kosten heute
- Solarproduktion als aktuelle Leistung und heute in kWh
- Akkuspeicher-Ladeleistung und Akkuspeicher-Ladung heute
- Akkuspeicher-Entladeleistung und Akkuspeicher-Entladung heute
- PV-Eigenverbrauch als Leistung, kWh und Prozent
- Autarkie heute in Prozent
- Kombinierte oder getrennte Sensoren für Netzbezug/Netzeinspeisung bei der Live-Leistung
- Kombinierte oder getrennte Sensoren für Akkuspeicher-Ladung/Entladung bei der Live-Leistung
- Mehrere Quell-Entitäten, zum Beispiel für mehrere Hoymiles-Akkus
- Deutsche und englische Übersetzung
- Lokale Icons und Logos im `brand/`-Ordner

## Wichtige Änderung ab Version 0.2.0

Vorher wurden Tages-kWh intern aus W-Werten integriert. Ab Version **0.2.0** gilt:

- **W-Sensoren**: nur für Live-Anzeigen.
- **Energie-Sensoren in kWh/Wh**: Grundlage für Tages-kWh, Hausverbrauch heute, Autarkie, PV-Eigenverbrauch und variable Netzbezugskosten.

Die Energie-Sensoren sollten Tageswerte sein, also zum Beispiel `..._today`, `..._heute` oder `utility_meter`-Sensoren mit täglichem Zyklus.

## Berechnung

### Live-Leistung in W

Hausverbrauch ohne Akkuspeicher-Ladung:

```text
hausverbrauch_leistung = solarproduktion_leistung + netzbezug_leistung - netzeinspeisung_leistung + akku_entladeleistung - akku_ladeleistung
```

PV-Eigenverbrauch Leistung:

```text
pv_eigenverbrauch_leistung = solarproduktion_leistung - netzeinspeisung_leistung
```

### Tageswerte in kWh

Die folgenden Werte werden aus vorhandenen Energie-Sensoren gelesen:

- Solarproduktion heute
- Netzbezug heute
- Netzeinspeisung heute
- Akkuspeicher-Ladung heute
- Akkuspeicher-Entladung heute

Hausverbrauch heute ohne Akkuspeicher-Ladung:

```text
hausverbrauch_heute = solarproduktion_heute + netzbezug_heute - netzeinspeisung_heute + akku_entladung_heute - akku_ladung_heute
```

PV-Eigenverbrauch heute:

```text
pv_eigenverbrauch_heute = solarproduktion_heute - netzeinspeisung_heute
```

Autarkie heute:

```text
autarkie = 100 * (1 - netzbezug_heute / hausverbrauch_heute)
```

PV-Eigenverbrauch heute:

```text
pv_eigenverbrauch_prozent = 100 * pv_eigenverbrauch_heute / solarproduktion_heute
```

### Variable Netzbezugskosten

Die Integration berechnet die Kosten nicht einfach mit dem aktuellen Tagespreis neu, sondern summiert sie fortlaufend über den Tag:

```text
neue_kosten = delta_netzbezug_kwh * strompreis_zu_diesem_zeitpunkt
```

Dadurch können sich Strompreise im Laufe des Tages ändern, ohne dass frühere kWh nachträglich mit dem neuen Preis umgerechnet werden.

## Empfohlene Einrichtung für dein Shelly-/Hoymiles-Setup

Für dein Setup kannst du voraussichtlich diese Auswahl verwenden:

### Live-Leistung

- Aktuelle Stromkosten: `input_number.aktueller_strompreis`
- Solarproduktion Leistung: `sensor.shellyplusplugs_e465b8b31a7c_switch_0_power`
- Kombinierte Netzleistung: `sensor.shellypro3em_a0dd6ca00d0c_total_active_power`
- Netzsensor-Modus: `Kombinierte Netzleistung: positiv = Bezug, negativ = Einspeisung`
- Akkuspeicher-Modus für Hoymiles `bat_p`: `Kombinierte Akkuspeicher-Leistung: positiv = Entladung, negativ = Ladung`
- Akkuspeicher-Leistung: beide Hoymiles-`bat_p`-Sensoren oder ein vorhandener kombinierter Helper

### Tages-Energie

Wähle hier bereits vorhandene Tageszähler aus, zum Beispiel:

- Solarproduktion Energie heute: dein Balkonkraftwerk-/PV-Ertrag-heute-Sensor
- Netzbezug Energie heute: dein Netzbezug-heute-Sensor
- Netzeinspeisung Energie heute: dein Einspeisung-heute-Sensor
- Akkuspeicher-Ladung heute: dein Akku-Ladung-heute-Sensor
- Akkuspeicher-Entladung heute: dein Akku-Entladung-heute-Sensor

Die Integration akzeptiert Energiequellen in `kWh`, `Wh` und `MWh`. `Wh` wird automatisch nach `kWh` umgerechnet.

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

- Leistungsquellen sollten Werte in W liefern.
- Energiequellen sollten Tageswerte in kWh oder Wh liefern.
- Die Strompreis-Entität sollte entweder Währung/kWh liefern, zum Beispiel `0.29`, oder ct/kWh, zum Beispiel `29`.
- Die kWh-Tageswerte werden nicht intern aus W integriert, sondern direkt aus deinen ausgewählten Energie-Sensoren gelesen.
- Die Integration speichert nur den fortlaufenden Kostenstand für variable Netzbezugskosten.

## Fehlerbehebung: Integration erscheint nicht

Wenn **Daily Energy Flow** nach der Installation nicht unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** erscheint, prüfe diese Punkte:

1. Der Ordner muss exakt hier liegen:

```text
/config/custom_components/daily_energy_flow/
```

Nicht korrekt wäre zum Beispiel:

```text
/config/custom_components/home-assistant-daily-energy-flow/custom_components/daily_energy_flow/
```

2. In diesem Ordner müssen direkt diese Dateien liegen:

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

3. Starte Home Assistant vollständig neu. Ein reines Neuladen von YAML reicht nicht.
4. Leere danach ggf. den Browser-Cache oder lade die Home-Assistant-Seite mit `Strg + F5` neu.
5. Suche nach **Daily Energy Flow**. In der deutschen Oberfläche kann auch **Täglicher Energiefluss** angezeigt werden.
6. Wenn sie weiterhin fehlt, prüfe **Einstellungen → System → Protokolle** auf Fehler zu `daily_energy_flow`.

## Icons und Logos

Das Repository enthält lokale Home-Assistant-Brand-Assets in:

```text
custom_components/daily_energy_flow/brand/
```

Enthaltene Dateien:

- `icon.png` und `icon@2x.png`
- `dark_icon.png` und `dark_icon@2x.png`
- `logo.png` und `logo@2x.png`
- `dark_logo.png` und `dark_logo@2x.png`

## Lizenz

MIT License
