# Canonical mapping: UPPERCASE with spaces (normalized form)
# Keys match model.names after .strip().upper().replace("_", " ")

traffic_signs_kh = {
    "NO OVERTAKING":               "ហាមជែង",
    "NO HORN":                     "ហាមចុចស៊ីប្លេ",
    "40 SPEED LIMIT":              "កំណត់ល្បឿន 40",
    "60 SPEED LIMIT":              "កំណត់ល្បឿន 60",
    "80 SPEED LIMIT":              "កំណត់ល្បឿន 80",
    "END SPEED LIMIT":             "ផុតកំណត់ល្បឿន",
    "KEEP RIGHT":                  "ប្រកាន់ស្តាំ",
    "30 MIN SPEED LIMIT":          "ល្បឿនអប្បបរមា 30",
    "SLOW DOWN":                   "បន្ថយល្បឿន",
    "STOP":                        "ឈប់",
    "GIVE WAY":                    "ផ្តល់សិទ្ធិ",
    "GIVE WAY AT RB":              "ផ្តល់សិទ្ធិនៅរង្វង់មូល",
    "PRIORITY ROAD":               "ផ្លូវអាទិភាព",
    "DANGER":                      "គ្រោះថ្នាក់",
    "RIGHT BEND":                  "ផ្លូវកោងទៅស្តាំ",
    "LEFT BEND":                   "ផ្លូវកោងទៅឆ្វេង",
    "WINDING ROAD":                "ផ្លូវកោងបត់បែន",
    "ROAD JUNCTION ON THE LEFT":   "ផ្លូវប្រសព្វខាងឆ្វេង",
    "ROAD JUNCTION ON THE RIGHT":  "ផ្លូវប្រសព្វខាងស្តាំ",
    "ROUND ABOUT":                 "រង្វង់មូល",
    "CARRIAGE WAY NARROWS":        "ផ្លូវរួមតូច",
    "STEEP ASCENT":                "ផ្លូវឡើងចំណោតខ្លាំង",
    "STEEP DESCENT":               "ផ្លូវចុះចំណោតខ្លាំង",
    "CHILDREN CROSSING":           "កុមារឆ្លងកាត់",
    "PEDESTRIAN CROSSING":         "កន្លែងថ្មើរជើងឆ្លងកាត់",
    "HOSPITAL":                    "មន្ទីរពេទ្យ",
    "PEDESTRIAN CROSSING AREA":    "តំបន់ថ្មើរជើងឆ្លងកាត់",
    "30 SPEED LIMIT":              "កំណត់ល្បឿន 30",
    "ROAD JUNCTION":               "ផ្លូវបំបែក",
    "NO STOPPING":                 "ហាមឈប់",
    "NO PARKING":                  "ហាមចត",
    "NO UTURN":                    "ហាមបត់ត្រឡប់ក្រោយ",
    "END PROHIBIT":                "ផុតបម្រាម",
    "NO ENTRY":                    "ហាមចូល",

    # ── Aliases: underscore variants (some training tools save these)
    "NO OVERTAKING":               "ហាមជែង",
    "NO HORN":                     "ហាមចុចស៊ីប្លេ",
    "END SPEED LIMIT":             "ផុតកំណត់ល្បឿន",
    "KEEP RIGHT":                  "ប្រកាន់ស្តាំ",
    "SLOW DOWN":                   "បន្ថយល្បឿន",
    "GIVE WAY":                    "ផ្តល់សិទ្ធិ",
    "GIVE WAY AT RB":              "ផ្តល់សិទ្ធិនៅរង្វង់មូល",
    "PRIORITY ROAD":               "ផ្លូវអាទិភាព",
    "RIGHT BEND":                  "ផ្លូវកោងទៅស្តាំ",
    "LEFT BEND":                   "ផ្លូវកោងទៅឆ្វេង",
    "WINDING ROAD":                "ផ្លូវកោងបត់បែន",
    "ROUND ABOUT":                 "រង្វង់មូល",
    "STEEP ASCENT":                "ផ្លូវឡើងចំណោតខ្លាំង",
    "STEEP DESCENT":               "ផ្លូវចុះចំណោតខ្លាំង",
    "CHILDREN CROSSING":           "កុមារឆ្លងកាត់",
    "PEDESTRIAN CROSSING":         "កន្លែងថ្មើរជើងឆ្លងកាត់",
    "ROAD JUNCTION":               "ផ្លូវបំបែក",
    "NO STOPPING":                 "ហាមឈប់",
    "NO PARKING":                  "ហាមចត",
    "NO UTURN":                    "ហាមបត់ត្រឡប់ក្រោយ",
    "END PROHIBIT":                "ផុតបម្រាម",
    "NO ENTRY":                    "ហាមចូល",
}


def lookup(class_name: str) -> tuple[str, str]:
    """
    Given a raw model class name (any case, underscores or spaces),
    returns (english_display, khmer_label).

    Normalization pipeline:
      1. strip whitespace
      2. uppercase
      3. replace underscores with spaces
    """
    key = class_name.strip().upper().replace("_", " ")
    kh  = traffic_signs_kh.get(key)

    if kh:
        en = key.title()   # "NO ENTRY" → "No Entry"
        return en, kh

    # Fallback: return something rather than silently drop
    en = class_name.strip().replace("_", " ").title()
    return en, en   # show English in Khmer column so it's visible, not blank