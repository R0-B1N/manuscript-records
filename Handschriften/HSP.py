# Author: Leonie Giessler
# Created: 2026-08-26
# Version: 1.1

# benoetigte Bibliotheken importieren
import xml.etree.ElementTree as ET
import requests
import json
import re
import unicodedata

# Konfiguration
OAI_URL = "https://erfassung.handschriftenportal.de/rest/oai-pmh"

SET_SPEC = "NORM-8e9cc754-fce9-3ba3-bc04-434459e60505"

METADATA_PREFIX = "oai_tei"

# XML-Namespaces
NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "tei": "http://www.tei-c.org/ns/1.0"
}

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

# Sprachcodes

# Sprachbezeichnungen aus dem HSP
# -> ISO 639-2/B fuer PICA 010@
SPRACHCODES = {

    # Deutsch
    "deutsch": "ger",
    "german": "ger",
    "ger": "ger",
    "deu": "ger",

    # historische deutsche Sprachstufen
    "mittelhochdeutsch": "gmh",
    "althochdeutsch": "goh",
    "mittelniederdeutsch": "gml",
    "niederdeutsch": "nds",

    # Latein
    "latein": "lat",
    "lateinisch": "lat",
    "latin": "lat",
    "lat": "lat",

    # Franzoesisch
    "franzosisch": "fre",
    "french": "fre",
    "fre": "fre",
    "fra": "fre",
    "altfranzosisch": "fro",
    "mittelfranzosisch": "frm",

    # Englisch
    "englisch": "eng",
    "english": "eng",
    "eng": "eng",
    "altenglisch": "ang",
    "mittelenglisch": "enm",

    # Italienisch
    "italienisch": "ita",
    "italian": "ita",
    "ita": "ita",

    # Spanisch
    "spanisch": "spa",
    "spanish": "spa",
    "spa": "spa",

    # Portugiesisch
    "portugiesisch": "por",
    "portuguese": "por",
    "por": "por",

    # Niederlaendisch
    "niederlandisch": "dut",
    "hollandisch": "dut",
    "dutch": "dut",
    "dut": "dut",
    "nld": "dut",

    # Griechisch
    "griechisch": "gre",
    "neugriechisch": "gre",
    "gre": "gre",
    "ell": "gre",
    "altgriechisch": "grc",

    # Hebraeisch
    "hebraisch": "heb",
    "hebrew": "heb",
    "heb": "heb",

    # Jiddisch
    "jiddisch": "yid",
    "yiddisch": "yid",
    "yiddish": "yid",
    "yid": "yid",

    # Arabisch
    "arabisch": "ara",
    "arabic": "ara",
    "ara": "ara",

    # Russisch
    "russisch": "rus",
    "russian": "rus",
    "rus": "rus",

    # Polnisch
    "polnisch": "pol",
    "polish": "pol",
    "pol": "pol",

    # Tschechisch
    "tschechisch": "cze",
    "czech": "cze",
    "cze": "cze",
    "ces": "cze",

    # Slowakisch
    "slowakisch": "slo",
    "slovak": "slo",
    "slo": "slo",
    "slk": "slo",

    # Slowenisch
    "slowenisch": "slv",
    "slovenian": "slv",
    "slv": "slv",

    # Kroatisch
    "kroatisch": "hrv",
    "croatian": "hrv",
    "hrv": "hrv",

    # Serbisch
    "serbisch": "srp",
    "serbian": "srp",
    "srp": "srp",

    # Ungarisch
    "ungarisch": "hun",
    "hungarian": "hun",
    "hun": "hun",

    # Daenisch
    "danisch": "dan",
    "danish": "dan",
    "dan": "dan",

    # Schwedisch
    "schwedisch": "swe",
    "swedish": "swe",
    "swe": "swe",

    # Norwegisch
    "norwegisch": "nor",
    "norwegian": "nor",
    "nor": "nor",

    # Rumaenisch
    "rumanisch": "rum",
    "romanian": "rum",
    "rum": "rum",
    "ron": "rum",

    # Tuerkisch
    "turkisch": "tur",
    "turkish": "tur",
    "tur": "tur",

    # Persisch
    "persisch": "per",
    "persian": "per",
    "per": "per",
    "fas": "per",

    # Chinesisch
    "chinesisch": "chi",
    "chinese": "chi",
    "chi": "chi",
    "zho": "chi",

    # Ukrainisch
    "ukrainisch": "ukr",
    "ukrainian": "ukr",
    "ukr": "ukr",

    # Katalanisch
    "katalanisch": "cat",
    "catalan": "cat",
    "cat": "cat",

    # Kirchenslawisch
    "kirchenslawisch": "chu",
    "kirchenslavisch": "chu",
    "church slavonic": "chu",
    "chu": "chu"
}

# Allgemeine Hilfsfunktionen
def _element_text(element):
    """
    Gibt den gesamten Textinhalt eines XML-Elements zurueck.
    Verschachtelte Elemente werden ebenfalls beruecksichtigt.
    """
    if element is None:
        return ""

    text = " ".join(element.itertext())

    return " ".join(text.split())

def _normalisiere_sprache(sprache):
    """
    Normalisiert Sprachbezeichnungen.
    Beispiele:
        Französisch -> franzosisch
        Hebräisch    -> hebraisch
        ITALIENISCH  -> italienisch
    """
    if sprache is None:
        return ""

    text = str(sprache).strip().lower()
    text = text.replace("ß", "ss")

    # Akzente/Umlaute entfernen
    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        zeichen
        for zeichen in text
        if not unicodedata.combining(zeichen)
    )

    # unsichere Angaben wie "italienisch (?)"
    text = re.sub(r"\(\s*\?\s*\)", "", text)
    text = text.replace("?", "")
    text = re.sub(r"\s+", " ", text)

    return text.strip(" .")

def _verfasser_aufteilen(name):
    """
    Zerlegt einen Namen wie:
        Brentano, Clemens (1778-1842)
    in:
        Nachname
        Vorname
        Lebensdaten
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

def _jahr_aus_text(text):
    """
    Extrahiert das erste Jahr aus einem Text.
    Beispiele:
        1629                -> 1629
        November 1629       -> 1629
        03. September 1458  -> 1458
        16. Jh.             -> kein direktes Jahr
    Bei Jahrhundertangaben wird deshalb bevorzugt
    origDate_notBefore verwendet.
    """
    if not text:
        return ""

    text = str(text).strip()

    match = re.search(r"(?<!\d)(\d{3,4})(?!\d)", text)

    if not match:
        return ""

    jahr = match.group(1)

    if len(jahr) == 3:
        jahr = jahr.zfill(4)

    return jahr

def _gnd_id_aus_ref(ref):
    """
    Extrahiert eine GND-ID aus einem URI.
    Beispiel:
        http://d-nb.info/gnd/118540238
    wird zu:
        118540238
    """
    if not ref:
        return ""

    match = re.search(r"(?:d-nb\.info/gnd/|gnd:)" r"([0-9Xx-]+)", ref)

    if match:
        return match.group(1)

    return ""

# Titel
def _titel_ermitteln(ms_desc):
    """
    Ermittelt den Titel aus der tatsaechlichen
    HSP-Normaldatenstruktur:
        msDesc
          -> head
            -> index indexName="norm_title"
              -> term type="title"
    Beispiel:
        <index indexName="norm_title">
            <term type="title">Urkunde, franz.</term>
        </index>
    """
    if ms_desc is None:
        return ""

    titel_elemente = ms_desc.findall(
        "tei:head/"
        "tei:index[@indexName='norm_title']/"
        "tei:term[@type='title']",
        NS
    )

    for titel_element in titel_elemente:
        titel = _element_text(titel_element)

        if titel:
            return titel

    # Fallback fuer andere TEI-Datensaetze
    titel_elemente = ms_desc.findall("tei:head/tei:title", NS)

    for titel_element in titel_elemente:
        titel = _element_text(titel_element)

        if titel:
            return titel

    return ""

# Signatur
def _signatur_ermitteln(ms_desc):
    """
    Ermittelt die aktuelle Signatur aus:
        msDesc
          -> msIdentifier
            -> idno
    altIdentifier wird bewusst nicht verwendet.
    """
    if ms_desc is None:
        return ""

    idno = ms_desc.find("tei:msIdentifier/tei:idno", NS)

    return _element_text(idno)

# HSP-ID
def _hsp_id_ermitteln(record, ms_desc):
    """
    Ermittelt die HSP-ID.
    Bevorzugt wird der OAI-Identifier:
        <header>
            <identifier>HSP-...</identifier>
        </header>
    Dieser entspricht in der vorliegenden XML auch
    der xml:id des msDesc.
    """
    # 1. OAI-Identifier
    identifier = record.find("oai:header/oai:identifier", NS)

    hsp_id = _element_text(identifier)

    if hsp_id:
        return hsp_id

    # 2. Fallback: xml:id von msDesc
    if ms_desc is not None:
        hsp_id = ms_desc.get(XML_ID)

        if hsp_id:
            return hsp_id.strip()

    return ""

# Entstehungsjahr
def _entstehungsjahr_ermitteln(ms_desc):
    """
    Ermittelt das Entstehungsjahr aus der HSP-Struktur:
        head
          -> index indexName="norm_origDate"
            -> term type="origDate"
            -> term type="origDate_notBefore"
            -> term type="origDate_notAfter"
    Prioritaet:
        1. origDate_notBefore
        2. origDate
        3. origDate_notAfter
    Beispiel:
        <term type="origDate">16. Jh.</term>
        <term type="origDate_notBefore">1501</term>
        <term type="origDate_notAfter">1600</term>
    ergibt:
        1501
    """
    if ms_desc is None:
        return ""

    datum_indexe = ms_desc.findall(
        "tei:head/"
        "tei:index[@indexName='norm_origDate']",
        NS
    )

    for datum_index in datum_indexe:
        # Beginn des Zeitraums bevorzugen
        for term_typ in ("origDate_notBefore", "origDate", "origDate_notAfter"):
            term = datum_index.find(f"tei:term[@type='{term_typ}']", NS)

            wert = _element_text(term)

            jahr = _jahr_aus_text(wert)

            if jahr:
                return jahr

    # Fallback fuer klassische TEI-origDate-Strukturen
    orig_dates = ms_desc.findall(".//tei:origDate", NS)

    for orig_date in orig_dates:
        for attribut in ("when", "from", "notBefore", "to", "notAfter"):
            wert = orig_date.get(attribut)

            jahr = _jahr_aus_text(wert)

            if jahr:
                return jahr

        jahr = _jahr_aus_text(_element_text(orig_date))

        if jahr:
            return jahr

    return ""

# Sprachen
def _sprachen_ermitteln(ms_desc):
    """
    Ermittelt die Sprache(n) aus der HSP-Normaldatenstruktur:
        head
          -> index indexName="norm_textLang"
            -> term type="textLang"
    Beispiele:
        lateinisch
        deutsch
        lateinisch, deutsch
        deutsch, lateinisch
        französisch
    werden zu:
        ["lat"]
        ["ger"]
        ["lat", "ger"]
        ["ger", "lat"]
        ["fre"]
    Rueckgabe:
        Sprachcodes,
        unbekannte Sprachbezeichnungen
    """
    codes = []
    unbekannt = []

    if ms_desc is None:
        return codes, unbekannt

    # HSP-Normaldaten
    sprach_elemente = ms_desc.findall(
        "tei:head/"
        "tei:index[@indexName='norm_textLang']/"
        "tei:term[@type='textLang']",
        NS
    )

    for sprach_element in sprach_elemente:
        sprach_text = _element_text(sprach_element)

        if not sprach_text:
            continue

        # mehrere Sprachen trennen
        teile = re.split(r"\s*(?:,|;|/|\+|\bund\b|\bu\.\b)\s*", sprach_text, flags=re.IGNORECASE)

        for teil in teile:
            teil = teil.strip()

            if not teil:
                continue

            normalisiert = _normalisiere_sprache(teil)

            code = SPRACHCODES.get(normalisiert)

            if code:
                if code not in codes:
                    codes.append(code)

            else:
                if teil not in unbekannt:
                    unbekannt.append(teil)

    # Falls HSP-Normaldaten vorhanden waren:
    # direkt zurueckgeben
    if codes or unbekannt:
        return codes, unbekannt

    # Fallback fuer klassisches TEI textLang
    text_lang_elemente = ms_desc.findall(".//tei:textLang", NS)

    TEI_CODE_MAPPING = {
        "de": "ger",
        "deu": "ger",
        "ger": "ger",

        "la": "lat",
        "lat": "lat",

        "fr": "fre",
        "fra": "fre",
        "fre": "fre",

        "en": "eng",
        "eng": "eng",

        "it": "ita",
        "ita": "ita",

        "es": "spa",
        "spa": "spa",

        "nl": "dut",
        "nld": "dut",
        "dut": "dut",

        "el": "gre",
        "ell": "gre",
        "gre": "gre",

        "grc": "grc",

        "he": "heb",
        "heb": "heb",

        "ar": "ara",
        "ara": "ara",

        "ru": "rus",
        "rus": "rus",

        "pl": "pol",
        "pol": "pol",

        "cs": "cze",
        "ces": "cze",
        "cze": "cze",

        "chu": "chu"
    }

    for text_lang in text_lang_elemente:
        rohe_codes = []

        main_lang = text_lang.get("mainLang")

        if main_lang:
            rohe_codes.append(main_lang)

        other_langs = text_lang.get("otherLangs")

        if other_langs:
            rohe_codes.extend(other_langs.split())

        for rohcode in rohe_codes:
            grundcode = (rohcode.strip().lower().split("-")[0])

            code = TEI_CODE_MAPPING.get(grundcode)

            if code:
                if code not in codes:
                    codes.append(code)

            else:
                if rohcode not in unbekannt:
                    unbekannt.append(rohcode)

    return codes, unbekannt

# Hauptverfasser
def _hauptverfasser_ermitteln(ms_desc):
    """
    Versucht einen Hauptverfasser aus klassischen
    TEI-Strukturen zu ermitteln.
    WICHTIG:
    Die vorliegende HSP-OAI-Datei enthaelt keine
    <author>-Elemente und kein norm_author-Feld.
    Fuer die aktuell gelieferten Datensaetze bleibt 028A
    deshalb leer.
    Diese Funktion ist als Fallback eingebaut, falls kuenftige
    HSP-Datensaetze author-Elemente enthalten.
    """
    if ms_desc is None:
        return "", ""

    autoren = ms_desc.findall(".//tei:msContents//tei:author", NS)

    for autor in autoren:
        gnd_id = ""

        # GND-ID direkt am author
        ref = autor.get("ref")

        if ref:
            gnd_id = _gnd_id_aus_ref(ref)

        # persName

        pers_name = autor.find(".//tei:persName", NS)

        if pers_name is not None:
            if not gnd_id:
                ref = pers_name.get("ref")

                if ref:
                    gnd_id = _gnd_id_aus_ref(ref)

            nachname_element = pers_name.find("tei:surname", NS)

            vorname_elemente = pers_name.findall("tei:forename", NS)

            nachname = _element_text(nachname_element)

            vornamen = []

            for element in vorname_elemente:
                wert = _element_text(element)

                if wert:
                    vornamen.append(wert)

            vorname = " ".join(vornamen)

            if nachname:
                if vorname:
                    return f"{nachname}, {vorname}", gnd_id

                return nachname, gnd_id

            name = _element_text(pers_name)

            if name:
                return name, gnd_id

        # einfacher author-Text
        name = _element_text(autor)

        if name:
            return name, gnd_id

    return "", ""

# OAI-PMH-Abfrage
def Suche_OAI(MaxErg=None):
    """
    Fragt das Handschriftenportal per OAI-PMH ab.
    Verarbeitet werden nur Datensaetze mit:
        - Signatur
        - nichtleerem norm_title
    Extrahiert werden:
        HSP-ID
        Signatur
        Titel
        Entstehungsjahr
        Sprache(n)
        Hauptverfasser, falls vorhanden
    resumptionToken werden automatisch verarbeitet.
    """
    Ergebnisse = []

    # Erste OAI-Anfrage
    parameter = {
        "verb": "ListRecords",
        "metadataPrefix": METADATA_PREFIX,
        "set": SET_SPEC
    }

    while True:
        Antwort = requests.get(OAI_URL, params=parameter, timeout=60)

        Antwort.raise_for_status()

        Wurzel = ET.fromstring(Antwort.content)

        # OAI-Fehlermeldung
        fehler = Wurzel.find("oai:error", NS)

        if fehler is not None:
            fehlercode = fehler.get("code", "unbekannt")

            fehlertext = _element_text(fehler)

            raise RuntimeError(
                f"OAI-PMH-Fehler '{fehlercode}': "
                f"{fehlertext}"
            )

        # OAI-Records
        records = Wurzel.findall("oai:ListRecords/oai:record", NS)

        for record in records:
            # Header
            header = record.find("oai:header", NS)

            # geloeschte Records ignorieren
            if header is not None and header.get("status") == "deleted":
                continue

            # TEI
            tei = record.find("oai:metadata/tei:TEI", NS)

            if tei is None:
                metadata = record.find("oai:metadata", NS)

                if metadata is not None:
                    tei = metadata.find(".//tei:TEI", NS)

            if tei is None:
                continue

            # msDesc
            ms_desc = tei.find(".//tei:msDesc", NS)

            if ms_desc is None:
                continue

            # Signatur
            signatur = _signatur_ermitteln(ms_desc)

            if not signatur:
                continue

            # Titel
            titel = _titel_ermitteln(ms_desc)

            # Nur Datensaetze mit nichtleerem Haupttitel
            if not titel:
                continue

            # HSP-ID
            hsp_id = _hsp_id_ermitteln(record, ms_desc)

            # Entstehungsjahr
            jahr = _entstehungsjahr_ermitteln(ms_desc)

            # Sprache(n)
            sprache_codes, unbekannte_sprachen = \
                _sprachen_ermitteln(ms_desc)

            if unbekannte_sprachen:
                print(
                    f"Warnung bei Signatur '{signatur}': "
                    f"Folgende Sprachangaben wurden nicht erkannt: "
                    f"{', '.join(unbekannte_sprachen)}"
                )

            # Hauptverfasser
            hauptverfasser, hauptverfasser_gnd = \
                _hauptverfasser_ermitteln(ms_desc)

            # Datensatz
            data = {
                "ID": hsp_id,
                "Titel": titel,
                "Signatur": signatur,
                "Jahr": jahr,
                "Sprache_Codes": sprache_codes,
                "Hauptverfasser_Name": hauptverfasser,
                "Hauptverfasser_GND_ID": hauptverfasser_gnd
            }

            Ergebnisse.append(data)

            # Maximalzahl erreicht?
            if MaxErg is not None and len(Ergebnisse) >= MaxErg:
                return Ergebnisse

        # resumptionToken
        token_element = Wurzel.find("oai:ListRecords/oai:resumptionToken", NS)

        if token_element is None or not token_element.text or not token_element.text.strip():
            break

        token = token_element.text.strip()

        # Bei einer Folgeabfrage duerfen nur
        # verb und resumptionToken uebergeben werden.
        parameter = {
            "verb": "ListRecords",
            "resumptionToken": token
        }

    return Ergebnisse

# PICA+
def zu_Pica_Feldern(data):
    """
    Wandelt einen HSP-Datensatz
    in ein PICA+-JSON-Record um.
    Format:
        [Tag, Occurrence, Code, Wert, ...]
    """

    Felder = []

    # 002@ - Satzart/Status
    Felder.append([ "002@", None, "0", "Har" ])

    # 002C - Inhaltstyp
    Felder.append([ "002C", None, "a", "Text", "b", "txt" ])

    # 002D - Medientyp
    Felder.append([ "002D", None, "a", "ohne Hilfsmittel zu benutzen", "b", "n" ])

    # 002E - Datentraegertyp
    Felder.append([ "002E", None, "a", "Band", "b", "nc" ])

    # 011@ - Entstehungsjahr
    if data["Jahr"]:
        Felder.append([ "011@", None, "a", data["Jahr"] ])

    else:
        Felder.append([ "011@", None, "a", "" ])

    # 013D - Art des Inhalts
    Felder.append([ "013D", None, "a", "Handschrift" ])

    # 010@ - Sprache(n)
    if data["Sprache_Codes"]:
        feld = [ "010@", None ]

        for code in data["Sprache_Codes"]:
            feld += [ "a", code ]

        Felder.append(feld)

    else:
        Felder.append([ "010@", None, "a", "" ])

    # 019@ - Erscheinungsland
    Felder.append([ "019@", None, "a", "XA-DE" ])

    # 028A - Hauptverfasser
    if data["Hauptverfasser_Name"]:
        nachname, vorname, lebensdaten = \
            _verfasser_aufteilen(data["Hauptverfasser_Name"])

        feld = [ "028A", None, "a", nachname ]

        if vorname:
            feld += [ "n", vorname ]

        if lebensdaten:
            feld += [ "d", lebensdaten ]

        if data["Hauptverfasser_GND_ID"]:
            feld += [ "9", data["Hauptverfasser_GND_ID"] ]

        Felder.append(feld)

    else:
        # ist kein Hauptverfasser enthalten.
        Felder.append([ "028A", None, "a", "" ])

    # 022A - Signatur
    if data["Signatur"]:
        Felder.append([ "022A", None, "a", f"Signatur {data['Signatur']}" ])

    # 021A - Haupttitel
    if data["Titel"]:
        Felder.append([ "021A", None, "a", data["Titel"] ])

    # 017C - HSP-ID
    if data["ID"]:
        Felder.append([ "017C", None, "3", data["ID"] ])

    return Felder

# JSON-Ausgabe
def pica_json_dump(records):
    """
    Erzeugt die lesbar formatierte PICA+-JSON-Struktur.
    """
    def feld_zu_zeile(feld):
        return "[ " + ", ".join(json.dumps(teil, ensure_ascii=False) for teil in feld) + " ]"

    zeilen = ["["]
    for i, record in enumerate(records):
        zeilen.append("  [")
        for j, feld in enumerate(record):
            komma = ("," if j < len(record) - 1 else "")
            zeilen.append(f"    {feld_zu_zeile(feld)}{komma}")
        komma = ("," if i < len(records) - 1 else "")
        zeilen.append(f"  ]{komma}")
    zeilen.append("]")
    return "\n".join(zeilen)

# main
MaxEingabe = input("Angabe für Anzahl der Datensaetze, 1 bis max. 10 (Enter = 10): ").strip() or "10"
if int(MaxEingabe) > 10 or "":
    print("No no no, only 10 Waterbottles")
    MaxEingabe = "10"

Dateiname = input("Dateiname fuer Export (Enter = hsp_pica.json): ").strip() or "hsp_pica.json"

try:
    # Maximale Ergebniszahl
    if MaxEingabe:
        MaxErg = int(MaxEingabe)

        if MaxErg <= 0:
            raise ValueError("Die maximale Anzahl muss groesser als 0 sein.")

    else:
        MaxErg = None

    # OAI-Abfrage
    Liste = Suche_OAI(MaxErg)

    # PICA+-Datensaetze erstellen
    Pica_Datensaetze = [zu_Pica_Feldern(eintrag) for eintrag in Liste]

    # JSON schreiben
    with open(Dateiname, "w", encoding="utf-8") as f:
        f.write(pica_json_dump(Pica_Datensaetze))

    print(f"{len(Pica_Datensaetze)} Datensaetze " f"nach '{Dateiname}' exportiert.")
    print("Auftrag abgeschlossen!")

except ValueError as e:
    print(f"Eingabefehler: {e}")

except requests.RequestException as e:
    print(f"Fehler bei der OAI-Abfrage: {e}")

except ET.ParseError as e:
    print(f"Fehler beim Verarbeiten des XML: {e}")

except Exception as e:
    print(f"Fehler: {e}")