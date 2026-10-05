# --- ROZŠÍŘENÝ A ROBUSTNÍ PŘEVODNÍK FORMÁTU ---
def parse_user_ticker(user_input: str) -> str:
  """Univerzální převodník pro mapování burz na Yahoo Finance formát."""
  if not user_input:
    return ""

  text = user_input.strip().upper()

  # Oprava případných překlepů se zdvojenými tečkami (např. AT..L -> AT.L)
  while ".." in text:
    text = text.replace("..", ".")

  # Slovník přímého mapování uživatelských koncovek na Yahoo přípony
  exchange_map = {
      ".LSE": ".L",
      ".L": ".L",
      ".AMEX": "",
      ".NYSE": "",
      ".NASDAQ.NMS": "",
      ".NASDAQ.SCM": "",
      ".NASDQ.NMS": "",
      ".SEHK": ".HK",
      ".HK": ".HK",
      ".SGX": ".SI",
      ".SI": ".SI",
      ".PSE": ".PR",
      ".PR": ".PR",
      ".XETRA": ".DE",
      ".IBIS2": ".DE",
      ".IBIS": ".DE",
      ".DE": ".DE",
      ".FRANKFURT": ".F",
      ".F": ".F",
      ".SIX": ".SW",
      ".SW": ".SW",
      ".TSX": ".TO",
      ".TO": ".TO",
      ".T": ".TO",  # Oprava: Kanadská burza .T -> .TO pro Yahoo Finance
      ".ASX": ".AX",
      ".AX": ".AX",
      ".TSE": ".T",
      ".EPA": ".PA",
      ".PA": ".PA",
      ".PARIS": ".PA",
      ".MIL": ".MI",
      ".MI": ".MI",
      ".BVME": ".MI",
      ".MADRID": ".MC",
      ".STHLM": ".ST",
      ".HELSINKI": ".HE",
      ".COPENHAGEN": ".CO",
      ".EB": ".EB",
      ".EBS": ".EB",  # Bernská burza mapovaná na Yahoo ekvivalent
      ".VALUE": "",
      ".IIS": "",
      ".SFB": ".ST",
      ".PINK.OTCQB": ".PK",
      ".OTCQB": ".PK",
      ".PK": ".PK",
  }

  # 1. Zkusíme aplikovat známé mapování koncovek
  for user_suffix, yf_suffix in exchange_map.items():
    if text.endswith(user_suffix):
      base_ticker = text[: -len(user_suffix)].strip()
      base_ticker = base_ticker.replace(" ", "-")
      if yf_suffix == ".HK" and base_ticker.isdigit():
        base_ticker = base_ticker.zfill(4)
      return f"{base_ticker}{yf_suffix}"

  # 2. Pokud končí na mezeru a burzu (např. "PXT T")
  parts = text.split(" ")
  if len(parts) >= 2:
    potential_suffix = "." + parts[-1]
    if potential_suffix in exchange_map:
      base_ticker = "".join(parts[:-1]).replace(" ", "-")
      yf_suffix = exchange_map[potential_suffix]
      return f"{base_ticker}{yf_suffix}"

  # 3. Speciální fallback pro tickery zadané bez burzy, ale známé z Xetry (např. C3R -> C3R.DE)
  # Pokud ticker neobsahuje tečku a je to čistě text, zkusíme ho nechat nebo ošetřit,
  # popř. pokud víte, že jde o Xetru, můžete zde vynutit .DE, ale raději nechejme standard.
  return text.replace(" ", "-")
