import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Stock Panic Dip Analyzer", page_icon="📈", layout="wide"
)

st.title("📈 Stock Panic Dip Analyzer")
st.caption(
    "Nástroj pro analýzu panických poklesů akcií a odlišení dočasných"
    " výprodejů od fundamentálních problémů."
)


# --- ROZŠÍŘENÝ A ROBUSTNÍ PŘEVODNÍK FORMÁTU ---
def parse_user_ticker(user_input: str) -> str:
  """Univerzální převodník pro mapování burz na Yahoo Finance formát."""
  if not user_input:
    return ""

  text = user_input.strip().upper()

  while ".." in text:
    text = text.replace("..", ".")

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
      ".T": ".TO",
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
      ".EB": ".SW",
      ".EBS": ".SW",
      ".VALUE": "",
      ".IIS": "",
      ".SFB": ".ST",
      ".PINK.OTCQB": ".PK",
      ".OTCQB": ".PK",
      ".PK": ".PK",
  }

  for user_suffix, yf_suffix in exchange_map.items():
    if text.endswith(user_suffix):
      base_ticker = text[: -len(user_suffix)].strip()
      base_ticker = base_ticker.replace(" ", "-")
      if yf_suffix == ".HK" and base_ticker.isdigit():
        base_ticker = base_ticker.zfill(4)
      return f"{base_ticker}{yf_suffix}"

  parts = text.split(" ")
  if len(parts) >= 2:
    potential_suffix = "." + parts[-1]
    if potential_suffix in exchange_map:
      base_ticker = "".join(parts[:-1]).replace(" ", "-")
      yf_suffix = exchange_map[potential_suffix]
      return f"{base_ticker}{yf_suffix}"

  return text.replace(" ", "-")


# --- SPRÁVA VÍCE WATCHLISTŮ V SESSION STATE ---
if "watchlists" not in st.session_state:
  st.session_state.watchlists = {
      "Hlavní watchlist": [
          "NVDA",
          "CEZ.PR",
          "1846.HK",
          "AT.L",
          "VWCE.DE",
          "UNH",
      ]
  }

if "active_watchlist" not in st.session_state:
  st.session_state.active_watchlist = "Hlavní watchlist"

st.sidebar.header("📁 Správa Watchlistů")

watchlist_names = list(st.session_state.watchlists.keys())
selected_wl = st.sidebar.selectbox(
    "Aktivní watchlist:",
    watchlist_names,
    index=watchlist_names.index(st.session_state.active_watchlist),
)
st.session_state.active_watchlist = selected_wl

with st.sidebar.expander("➕ Vytvořit nový watchlist"):
  new_wl_name = st.text_input("Název watchlistu:")
  if st.button("Vytvořit"):
    if new_wl_name and new_wl_name not in st.session_state.watchlists:
      st.session_state.watchlists[new_wl_name] = []
      st.session_state.active_watchlist = new_wl_name
      st.rerun()
    else:
      st.warning("Zadejte platný a unikátní název.")

current_tickers = st.session_state.watchlists[st.session_state.active_watchlist]

# --- HROMADNÉ PŘIDÁVÁNÍ TICKETŮ ---
st.sidebar.subheader(f"⭐ Položky v: {st.session_state.active_watchlist}")
st.sidebar.write(
    "Vložte více tickerů najednou (oddělené čárkou, mezerou nebo novým řádkem)."
)

bulk_input = st.sidebar.text_area(
    "Hromadné vložení:",
    placeholder="1846.SEHK, AT..LSE, UNH.NYSE, ...",
    key="input_bulk_tickers",
)

if st.sidebar.button("➕ Přidat do seznamu"):
  if bulk_input:
    raw_tokens = []
    for line in bulk_input.split("\n"):
      for token in line.replace(";", ",").split(","):
        clean_token = token.strip()
        if clean_token:
          raw_tokens.append(clean_token)

    added_count = 0
    for token in raw_tokens:
      formatted_symbol = parse_user_ticker(token)
      if formatted_symbol and formatted_symbol not in current_tickers:
        current_tickers.append(formatted_symbol)
        added_count += 1

    st.sidebar.success(f"Úspěšně přidáno {added_count} položek.")
    st.rerun()

# --- ZOBRAZENÍ A ŘAZENÍ POLOŽEK ---
st.sidebar.markdown("---")
st.sidebar.subheader("Správa pořadí a mazání:")

if current_tickers:
  for idx, item in enumerate(list(current_tickers)):
    cols = st.sidebar.columns([2.5, 1, 1])
    cols[0].write(f"**{idx+1}. {item}**")

    if idx > 0 and cols[1].button(
        "⬆️", key=f"up_{st.session_state.active_watchlist}_{idx}_{item}"
    ):
      current_tickers[idx], current_tickers[idx - 1] = (
          current_tickers[idx - 1],
          current_tickers[idx],
      )
      st.rerun()

    if cols[2].button(
        "❌", key=f"del_{st.session_state.active_watchlist}_{idx}_{item}"
    ):
      current_tickers.remove(item)
      st.rerun()

  if st.sidebar.button("🗑️ Vyčistit tento watchlist"):
    st.session_state.watchlists[st.session_state.active_watchlist] = []
    st.rerun()
else:
  st.sidebar.info("Tento watchlist je prázdný.")

watchlist_tickers = current_tickers

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Srovnávací přehled Watchlistu",
    "📰 Zprávy & Laická interpretace",
    "🧠 Jak poznat paniku (Manuál)",
    "🛠️ Další nástroje & Tipy",
])

# --- TAB 1: SROVNÁVACÍ PŘEHLED WATCHLISTU ---
with tab1:
  st.subheader(
      f"📊 Hromadná analýza panických poklesů ({st.session_state.active_watchlist})"
  )

  if not watchlist_tickers:
    st.warning("Zadejte prosím alespoň jeden ticker v postranním panelu.")
  else:
    results = []
    failed_tickers = []

    with st.spinner(
        "Stahuji data a analyzuji všechny tickery ve watchlistu..."
    ):
      for ticker_symbol in watchlist_tickers:
        try:
          stock = yf.Ticker(ticker_symbol)
          hist = stock.history(period="60d")

          if hist.empty:
            failed_tickers.append(ticker_symbol)
            continue

          info = {}
          try:
            info = stock.info or {}
          except Exception:
            info = {}

          current_price = float(hist["Close"].iloc[-1])
          prev_close = (
              float(hist["Close"].iloc[-2])
              if len(hist) > 1
              else current_price
          )
          day_change_pct = ((current_price - prev_close) / prev_close) * 100

          fifty_two_high = info.get(
              "fiftyTwoWeekHigh", float(hist["High"].max())
          )
          drop_from_high = (
              ((current_price - fifty_two_high) / fifty_two_high) * 100
              if fifty_two_high
              else 0.0
          )

          avg_vol = float(hist["Volume"].tail(20).mean())
          today_vol = float(hist["Volume"].iloc[-1])
          vol_ratio = today_vol / avg_vol if avg_vol > 0 else 1.0

          delta = hist["Close"].diff()
          gain = delta.where(delta > 0, 0).rolling(window=14).mean()
          loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
          rs = gain / loss
          rsi_series = 100 - (100 / (1 + rs))
          rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

          debt_to_equity = info.get("debtToEquity", "N/A")
          forward_pe = info.get("forwardPE", "N/A")
          profit_margins = info.get("profitMargins", "N/A")

          panic_points = 0
          if rsi < 35:
            panic_points += 3
          if day_change_pct < -3.0:
            panic_points += 2
          if vol_ratio > 1.5:
            panic_points += 2

          if isinstance(debt_to_equity, (int, float)) and debt_to_equity > 150:
            panic_points -= 2
          if isinstance(profit_margins, (int, float)) and profit_margins < 0:
            panic_points -= 1

          if panic_points >= 4:
            status = "🔥 Pravděpodobná panika"
          elif panic_points >= 2:
            status = "⚠️️ Mírná korekce"
          else:
            status = "ℹ️ Standardní pohyb"

          margin_fmt = (
              f"{profit_margins*100:.1f}%"
              if isinstance(profit_margins, (int, float))
              else str(profit_margins)
          )

          results.append({
              "Ticker": ticker_symbol,
              "Cena": round(current_price, 2),
              "Denní změna (%)": round(day_change_pct, 2),
              "Pokles od max (%)": round(drop_from_high, 2),
              "RSI (14)": round(rsi, 1),
              "Objem (x)": round(vol_ratio, 2),
              "D/E Dluh": debt_to_equity,
              "Marže": margin_fmt,
              "P/E": forward_pe,
              "Vyhodnocení": status,
          })
        except Exception:
          failed_tickers.append(ticker_symbol)

    if results:
      df_results = pd.DataFrame(results)
      st.dataframe(df_results, use_container_width=True)

    if failed_tickers:
      st.error(
          "⚠️ **Následující tickery se nepodařilo najít nebo stáhnout jejich"
          f" data:** {', '.join(failed_tickers)}"
      )

# --- TAB 2: ZPRÁVY & LAICKÁ INTERPRETACE ---
with tab2:
  st.subheader("📰 Zprávy a laické shrnutí nálady")
  if watchlist_tickers:
    selected_ticker_news = st.selectbox(
        "Vyberte ticker pro analýzu zpráv:",
        watchlist_tickers,
        key="news_ticker_select",
    )

    if selected_ticker_news:
      try:
        stock = yf.Ticker(selected_ticker_news)
        news_items = []
        if hasattr(stock, "get_news"):
          try:
            news_items = stock.get_news()
          except Exception:
            pass

        if not news_items and hasattr(stock, "news"):
          news_items = stock.news or []

        # --- LAICKÁ INTERPRETACE (ANALÝZA TITULKŮ) ---
        positive_keywords = [
            "beat",
            "surge",
            "jump",
            "higher",
            "growth",
            "profit",
            "upgrade",
            "rally",
            "buy",
            "strong",
            "record",
            "positive",
        ]
        negative_keywords = [
            "drop",
            "fall",
            "plunge",
            "slump",
            "loss",
            "miss",
            "downgrade",
            "cut",
            "warning",
            "risk",
            "lawsuit",
            "investigation",
            "fraud",
            "negative",
        ]

        pos_count = 0
        neg_count = 0

        titles_text = []
        for item in news_items:
          content = item.get("content", item)
          title = (
              content.get("title") or item.get("title") or ""
          ).lower()
          titles_text.append(title)
          for word in positive_keywords:
            if word in title:
              pos_count += 1
          for word in negative_keywords:
            if word in title:
              neg_count += 1

        # Vykreslení laického shrnutí
        st.markdown("### 🤖 Laické shrnutí situace zpráv")
        if not news_items:
          st.info(
              f"Pro {selected_ticker_news} nejsou k dispozici čerstvé zprávy v"
              " API."
          )
        else:
          if neg_count > pos_count + 1:
            st.error(
                "🔴 **Převažují varovné/negativní zprávy:** V titulcích se často"
                " objevují výrazy o poklesech, horších výsledcích nebo rizicích."
                " Pokles ceny může mít reálný fundamentální důvod, buďte"
                " opatrní."
            )
          elif pos_count > neg_count + 1:
            st.success(
                "🟢 **Převažují pozitivní zprávy:** Zprávy hovoří o růstu,"
                " dobrých výsledcích nebo doporučeních k nákupu. Pokud cena"
                " klesá, může jít o klasický krátkodobý výpadek (panika bez"
                " důvodu)."
            )
          else:
            st.info(
                "⚪ **Neutrální/smíšené zprávy:** Zprávy nevykazují žádný"
                " extrémní směr, jde o běžný mediální šum nebo rutinní zprávy."
            )

        st.markdown("---")
        st.subheader("Seznam nejnovějších zpráv:")
        if not news_items:
          yahoo_url = f"https://finance.yahoo.com/quote/{selected_ticker_news}"
          st.markdown(
              f"👉 [Otevřít profil a zprávy pro {selected_ticker_news} přímo"
              f" na Yahoo Finance]({yahoo_url})"
          )
        else:
          for item in news_items[:10]:
            content = item.get("content", item)
            title = (
                content.get("title")
                or item.get("title")
                or "Bez názvu"
            )
            publisher = (
                content.get("provider", {}).get("displayName")
                or content.get("publisher")
                or item.get("publisher")
                or "Zdroj"
            )
            click_url = ""
            click_dict = (
                content.get("clickThroughUrl")
                or content.get("link")
                or item.get("link")
            )
            if isinstance(click_dict, dict):
              click_url = click_dict.get("url", "")
            elif isinstance(click_dict, str):
              click_url = click_dict

            if not click_url:
              click_url = f"https://finance.yahoo.com/quote/{selected_ticker_news}"

            st.markdown(f"- [**{title}**]({click_url}) *({publisher})*")
      except Exception as e:
        st.error(f"Nelze načíst zprávy: {str(e)}")
  else:
    st.info("Nejprve přidejte tickery do aktivního watchlistu.")

# --- TAB 3: EDUKACE ---
with tab3:
  st.subheader("🧠 Jak odlišit paniku od reálného problému")
  st.markdown("""
    | Kritérium | 🟢 Panický pokles (Nákupní příležitost) | 🔴 Fundamentální problém (Riziko) |
    | :--- | :--- | :--- |
    | **Druh zprávy** | Makroekonomické obavy, dočasný výpadek. | Účetní podvody, trvalá ztráta trhu. |
    | **RSI (14 dní)** | **Pod 30** (Přeprodáno). | Drží se 40–50, pozvolný pokles. |
    | **Objem (Volume)** | **Masivní nárůst** (kapitulace). | Nízký nebo průměrný objem. |
    """)

# --- TAB 4: NÁSTROJE ---
with tab4:
  st.subheader("🛠️ Doporučené externí nástroje")
  st.write("Finviz, TradingView, Simply Wall St.")
