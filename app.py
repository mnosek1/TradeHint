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


# --- INTELIGENTNÍ PŘEVODNÍK FORMÁTU ---
def parse_user_ticker(user_input: str) -> str:
  """Převede zápis typu AT..LSE, BKTI.AMEX, 1846.SEHK na Yahoo formát (AT.L, BKTI, 1846.HK)."""
  text = user_input.strip().upper()

  # Mapa uživatelských kódů burz na Yahoo přípony
  # (můžete přidat libovolné další)
  exchange_map = {
      ".LSE": ".L",
      ".AMEX": "",
      ".NYSE": "",
      ".NASDAQ": "",
      ".SEHK": ".HK",
      ".SGX": ".SI",
      ".PSE": ".PR",
      ".XETRA": ".DE",
      ".FRANKFURT": ".F",
      ".SIX": ".SW",
      ".TSX": ".TO",
      ".ASX": ".AX",
      ".TSE": ".T",
  }

  # Hledáme, zda vstup končí některým známi kódem burzy
  for user_suffix, yf_suffix in exchange_map.items():
    if text.endswith(user_suffix):
      base_ticker = text[: -len(user_suffix)].strip()
      # Speciální ošetření pro číselné tickery (např. SEHK vyžaduje 4 číslice)
      if yf_suffix == ".HK" and base_ticker.isdigit():
        base_ticker = base_ticker.zfill(4)
      return f"{base_ticker}{yf_suffix}"

  # Pokud uživatel zadal tečku nebo nic, zkusíme to nechat nebo vrátit čistý text
  return text


# --- SPRÁVA WATCHLISTU ---
st.sidebar.header("⭐ Správa Watchlistu")
st.sidebar.write(
    "Zadejte ticker a burzu (např. `AT..LSE`, `BKTI.AMEX`, `1846.SEHK` nebo"
    " `NVDA`)."
)

if "watchlist" not in st.session_state:
  st.session_state.watchlist = ["NVDA", "CEZ.PR", "1846.HK", "AT.L"]

# Formulář pro přidání nového tickeru
with st.sidebar.form("add_ticker_form"):
  new_ticker_input = st.text_input(
      "Ticker a burza:", placeholder="např. AT..LSE nebo BKTI.AMEX"
  )
  submitted = st.form_submit_button("➕ Přidat do Watchlistu")

  if submitted and new_ticker_input:
    formatted_symbol = parse_user_ticker(new_ticker_input)

    if formatted_symbol not in st.session_state.watchlist:
      st.session_state.watchlist.append(formatted_symbol)
      st.success(f"Přidáno jako: {formatted_symbol}")
    else:
      st.warning("Tento ticker už ve watchlistu je.")

# Zobrazení aktuálního watchlistu s posouváním a mazáním
st.sidebar.subheader("Aktivní Watchlist:")
if st.session_state.watchlist:
  for idx, item in enumerate(list(st.session_state.watchlist)):
    col_name, col_up, col_down, col_del = st.sidebar.columns([2.5, 0.8, 0.8, 0.8])

    col_name.write(f"• **{item}**")

    if idx > 0:
      if col_up.button("▲", key=f"up_{item}"):
        st.session_state.watchlist[idx], st.session_state.watchlist[idx - 1] = (
            st.session_state.watchlist[idx - 1],
            st.session_state.watchlist[idx],
        )
        st.rerun()

    if idx < len(st.session_state.watchlist) - 1:
      if col_down.button("▼", key=f"down_{item}"):
        st.session_state.watchlist[idx], st.session_state.watchlist[idx + 1] = (
            st.session_state.watchlist[idx + 1],
            st.session_state.watchlist[idx],
        )
        st.rerun()

    if col_del.button("❌", key=f"del_{item}"):
      st.session_state.watchlist.remove(item)
      st.rerun()

  if st.sidebar.button("🗑️ Smazat celý watchlist"):
    st.session_state.watchlist = []
    st.rerun()
else:
  st.sidebar.info("Watchlist je prázdný.")

watchlist_tickers = st.session_state.watchlist

# Definice záložek
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Srovnávací přehled Watchlistu",
    "📰 Zprávy pro vybraný ticker",
    "🧠 Jak poznat paniku (Manuál)",
    "🛠️ Další nástroje & Tipy",
])

# --- TAB 1: SROVNÁVACÍ PŘEHLED WATCHLISTU ---
with tab1:
  st.subheader("📊 Hromadná analýza panických poklesů")

  if not watchlist_tickers:
    st.warning("Zadejte prosím alespoň jeden ticker v postranním panelu.")
  else:
    results = []

    with st.spinner(
        "Stahuji data a analyzuji všechny tickery ve watchlistu..."
    ):
      for ticker_symbol in watchlist_tickers:
        try:
          stock = yf.Ticker(ticker_symbol)
          hist = stock.history(period="60d")

          if hist.empty:
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

          # Výpočet RSI (14 dní)
          delta = hist["Close"].diff()
          gain = delta.where(delta > 0, 0).rolling(window=14).mean()
          loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
          rs = gain / loss
          rsi_series = 100 - (100 / (1 + rs))
          rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

          # Fundamentální ukazatele
          debt_to_equity = info.get("debtToEquity", "N/A")
          forward_pe = info.get("forwardPE", "N/A")
          profit_margins = info.get("profitMargins", "N/A")

          # Logika bodování paniky
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
          continue

    if results:
      df_results = pd.DataFrame(results)
      st.dataframe(df_results, use_container_width=True)
    else:
      st.error(
          "Nepodařilo se načíst data pro zadané tickery. Zkontrolujte, zda"
          " existují."
      )

# --- TAB 2: ZPRÁVY ---
with tab2:
  st.subheader("📰 Aktuální zprávy pro vybraný ticker")
  if watchlist_tickers:
    selected_ticker_news = st.selectbox(
        "Vyberte ticker pro zobrazení zpráv:", watchlist_tickers
    )

    if selected_ticker_news:
      try:
        stock = yf.Ticker(selected_ticker_news)
        news_items = (
            stock.news if hasattr(stock, "news") and stock.news else []
        )

        if not news_items:
          st.info(
              f"Pro tento ticker ({selected_ticker_news}) nebyly nalezeny žádné"
              " zprávy."
          )
        else:
          for item in news_items[:10]:
            title = item.get("title") or item.get("content", {}).get(
                "title", "Bez názvu"
            )
            publisher = item.get("publisher") or item.get("content", {}).get(
                "provider", {}
            ).get("displayName", "Zdroj")
            link = (
                item.get("link")
                or item.get("url")
                or item.get("content", {}).get("canonicalUrl", {}).get("url", "")
            )

            st.markdown(f"- [**{title}**]({link}) *({publisher})*")
      except Exception as e:
        st.error(f"Nelze načíst zprávy: {str(e)}")
  else:
    st.info("Nejprve přidejte tickery v postranním panelu.")

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
