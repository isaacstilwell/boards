import re

months_re = re.compile(
    r"\b(?:"
    r"Jan(?:uary)?|"
    r"Feb(?:ruary)?|"
    r"Mar(?:ch)?|"
    r"Apr(?:il)?|"
    r"May|"
    r"Jun(?:e)?|"
    r"Jul(?:y)?|"
    r"Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|"
    r"Nov(?:ember)?|"
    r"Dec(?:ember)?"
    r")\b\.?",
    re.IGNORECASE,
)

keycap_keywords_re = re.compile(
    r"\b(?:"
    r"GMK|DSA|DSS|DCS|SA|G20|SP|JTK|DMK|EPBT|NicePBT|CYL|"
    r"MT3|KAT|KAM|KAS|DCX|PBT(?:fans)?|MW|CRP|SWG|SW|KKB|"
    r"set|keycaps?|keyset"
    r")\b",
    re.IGNORECASE,
)

keyboard_keywords_re = re.compile(
    r"\b(?:"
    r"(?:key)?board|TKL|full ?size|"
    r"40%?|60%?|65%?|70%?|75%?|80%?|98%?|"
    r"numpad|ergo"
    r")\b",
    re.IGNORECASE,
)

currency_tokens_re = re.compile(r"(\$|€|£)")

price_re = re.compile(r"(\$|€|£)((\d{1,3}(,\d{3})?|\d{1,6})(\.\d{2})?)")

instock_keywords_re = re.compile(r"in(\-| )?stock", re.IGNORECASE)

designed_by_re = re.compile(r"designed by (\w+)", re.IGNORECASE)

dates_re = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?\b")
