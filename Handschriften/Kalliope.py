# Author: Leonie Giessler
# Created: 2026-08-26
# Version: 1.0

# benoetigte Bibliotheken importieren
import xml.etree.ElementTree as ET
import requests
import json
import re

# MODS-Namespace, wie er von Kalliope tatsaechlich zurueckgegeben wird
NS = {"mods": "http://www.loc.gov/mods/v3"}

# Regex fuer gueltige Signaturen wie "Chart. A 553" oder "Chart B 12a"
SIGNATUR_PATTERN = re.compile(r"^chart\.?\s*[a-z]\s*\d+[a-z]?$", re.IGNORECASE)

# Hilfsfunktionen
def ist_gueltige_signatur(signatur):
    return bool(SIGNATUR_PATTERN.match(signatur.strip()))

def _verfasser_aufteilen(name):
  """
  Zerlegt einen MODS-Namen wie "Brentano, Clemens (1778-1842)"
  in Nachname, Vorname und Lebensdaten.
  """
  match = re.match(r"^(?P<nachname>[^,]+),\s*(?P<rest>.+)$", name)
  if not match:
    return name.strip(), "", ""

  nachname = match["nachname"].strip()
  rest = match["rest"].strip()

  datum_match = re.search(r"\(([^)]*)\)\s*$", rest)
  if datum_match:
    lebensdaten = datum_match.group(1).strip()
    vorname = rest[:datum_match.start()].strip()
  else:
    lebensdaten = ""
    vorname = rest

  return nachname, vorname, lebensdaten

def Suche_SRU(MaxErg):
    Antwort = requests.get(
        "https://kalliope-verbund.info/sru"
        f"?version=1.2&operation=searchRetrieve&query=ead.repository.isil%3DDE-39"
        f"&maximumRecords={MaxErg}&recordSchema=mods37"
    )

    Wurzel = ET.fromstring(Antwort.content)
    Ergebnisse = []

    for datensatz in Wurzel.findall(".//mods:mods", NS):
        # Signatur zuerst pruefen, um ungueltige Datensaetze
        # so frueh wie moeglich zu verwerfen
        signatur_element = datensatz.find("mods:location/mods:shelfLocator", NS)
        signatur_text = signatur_element.text if signatur_element is not None and signatur_element.text else ""

        if not ist_gueltige_signatur(signatur_text):
            continue

        data = {
            "ID": "",
            "Titel": "",
            "Hauptverfasser_Name": "",
            "Hauptverfasser_GND_ID": "",
            "Jahr": "",
            "Signatur": signatur_text,
            "Sprache_Code": "",
            "Sprache_Text": ""
        }

        # ID (Kalliope-Identifikator, kein PICA-PPN)
        rec_id = datensatz.find("mods:recordInfo/mods:recordIdentifier", NS)
        if rec_id is not None and rec_id.text:
            data["ID"] = rec_id.text
        else:
            ident = datensatz.find("mods:identifier[@type='uri']", NS)
            if ident is not None and ident.text:
                data["ID"] = ident.text.rstrip("/").split("/")[-1]

        # Titel
        titel = datensatz.find("mods:titleInfo/mods:title", NS)
        if titel is not None and titel.text:
            data["Titel"] = titel.text

        # Hauptverfasser ermitteln: bevorzugt Person mit Rollencode "cre",
        # sonst Rolle mit Text "Verfasser", sonst erste Person als Fallback
        namen = datensatz.findall("mods:name[@type='personal']", NS)
        hauptverfasser = None
        for name in namen:
            code = name.find("mods:role/mods:roleTerm[@type='code']", NS)
            if code is not None and code.text == "cre":
                hauptverfasser = name
                break
        if hauptverfasser is None:
            for name in namen:
                text = name.find("mods:role/mods:roleTerm[@type='text']", NS)
                if text is not None and text.text and "verfasser" in text.text.lower():
                    hauptverfasser = name
                    break
        if hauptverfasser is None and namen:
            hauptverfasser = namen[0]

        if hauptverfasser is not None:
            namePart = hauptverfasser.find("mods:namePart", NS)
            if namePart is not None and namePart.text:
                data["Hauptverfasser_Name"] = namePart.text
            valueURI = hauptverfasser.get("valueURI")
            if valueURI:
                data["Hauptverfasser_GND_ID"] = valueURI.rstrip("/").split("/")[-1]

        # Datum
        for datum in datensatz.findall("mods:originInfo/mods:dateCreated", NS):
            if datum.get("keyDate") == "yes" and datum.text:
                data["Jahr"] = datum.text[:4]

        # Sprache: Code (fuer 1500/010@) und Klartext (fuer das lokale Feld)
        sprache_code = datensatz.find("mods:language/mods:languageTerm[@type='code']", NS)
        if sprache_code is not None and sprache_code.text:
            data["Sprache_Code"] = sprache_code.text
        sprache_text = datensatz.find("mods:language/mods:languageTerm[@type='text']", NS)
        if sprache_text is not None and sprache_text.text:
            data["Sprache_Text"] = sprache_text.text

        Ergebnisse.append(data)

    return Ergebnisse


def zu_Pica_Feldern(data):
    """
    Wandelt einen extrahierten Datensatz in ein PICA+-JSON-Record um.
    Format: Liste von Feldern, jedes Feld = [Tag, Occurrence, Code, Wert, ...]
    (siehe https://format.gbv.de/pica/json)

    002@/002C/002D/002E sind feste Werte fuer nicht-autoptisch erschlossene
    Einzelhandschriften (Retrokatalogisierung), siehe interne Vorgabe.
    003@ (PPN) wird bewusst NICHT belegt - die PPN vergibt das Zielsystem
    beim Import. Die Kalliope-ID wird stattdessen im lokalen Feld 0600
    mitgegeben, damit der Bezug zum Quelldatensatz erhalten bleibt.
    """
    Felder = []

    # 002@ - Satzart/Status (fest: Handschrift, einzelne Einheit, retrokatalogisiert)
    Felder.append(["002@", None, "0", "Har"])

    # 002C - Inhaltstyp (fest: Text)
    Felder.append(["002C", None, "a", "Text", "b", "txt"])

    # 002D - Medientyp (fest: ohne Hilfsmittel zu benutzen)
    Felder.append(["002D", None, "a", "ohne Hilfsmittel zu benutzen", "b", "n"])

    # 002E - Datentraegertyp (fest: Band)
    Felder.append(["002E", None, "a", "Band", "b", "nc"])

    # 011@ - Erscheinungs-/Entstehungsjahr
    if data["Jahr"]:
      Felder.append(["011@", None, "a", data["Jahr"]])
    else:
      Felder.append(["011@", None, "a", ""])

    # 013D - Art des Inhalts (GND-Verknuepfung zu "Handschrift")
    # bewusst leer gelassen, PPN-Verlinkung muss noch manuell ergaenzt werden
    Felder.append(["013D", None, "a", "Handschrift"])

    # 010@ - Sprachcode (ISO 639-2/B, z.B. "ger", "fre")
    if data["Sprache_Code"]:
      Felder.append(["010@", None, "a", data["Sprache_Code"]])

    # 019@ - Erscheinungsland (codiert)
    # ANNAHME: fest auf "XA-DE" gesetzt, da Abfrage auf Institution DE-39
    # eingeschraenkt ist. Keine echte Ableitung aus dem Entstehungsort!
    Felder.append(["019@", None, "a", "XA-DE"])

    # 028A - Hauptverfasser (nur einer, keine weiteren Personen)
    if data["Hauptverfasser_Name"]:
      nachname, vorname, lebensdaten = _verfasser_aufteilen(
          data["Hauptverfasser_Name"])
      feld = ["028A", None, "a", nachname]
      if vorname:
        feld += ["n", vorname]
      if lebensdaten:
        feld += ["d", lebensdaten]
      if data["Hauptverfasser_GND_ID"]:
        feld += ["9", data["Hauptverfasser_GND_ID"]]
      Felder.append(feld)

    # 022A - hier zweckentfremdet fuer die Signatur (statt Werktitel)
    if data["Signatur"]:
      Felder.append(["022A", None, "a", f"Signatur {data['Signatur']}"])

    # 021A - Haupttitel
    if data["Titel"]:
        Felder.append(["021A", None, "a", data["Titel"]])

    # 017C - lokales Verweis-/Sammelfeld (kein offizieller Pica+-Tag!)
    # enthaelt Kalliope-ID
    sonstige = []
    if data["ID"]:
        sonstige += ["3", data["ID"]]
    if sonstige:
      Felder.append(["017C", None] + sonstige)

    return Felder


def pica_json_dump(records):
    def feld_zu_zeile(feld):
        return "[ " + ", ".join(json.dumps(teil, ensure_ascii=False) for teil in feld) + " ]"

    zeilen = ["["]
    for i, record in enumerate(records):
        zeilen.append("  [")
        for j, feld in enumerate(record):
            komma = "," if j < len(record) - 1 else ""
            zeilen.append(f"    {feld_zu_zeile(feld)}{komma}")
        komma = "," if i < len(records) - 1 else ""
        zeilen.append(f"  ]{komma}")
    zeilen.append("]")
    return "\n".join(zeilen)


# main
Menge = input("Angabe für Anzahl der Datensaetze, 1 bis max. 10 (Enter = 10): ").strip() or "10"
if int(Menge) > 10 or "":
    print("No no no, only 10 Waterbottles")
    Menge = "10"
Dateiname = input("Dateiname fuer Export (Enter = kalliope_pica.json): ").strip() or "kalliope_pica.json"

try:
    Liste = Suche_SRU(Menge)
    Pica_Datensaetze = [zu_Pica_Feldern(eintrag) for eintrag in Liste]

    with open(Dateiname, "w", encoding="utf-8") as f:
        f.write(pica_json_dump(Pica_Datensaetze))

    print(f"{len(Pica_Datensaetze)} Datensaetze nach '{Dateiname}' exportiert.")
    print(f"Auftrag abgeschlossen!")

except Exception as e:
    print(f"Fehler: {e}")