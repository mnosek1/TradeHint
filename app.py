import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Panic Dip Analyzer", page_icon="📈", layout="wide")

st.title("📈 Stock Panic Dip Analyzer")
st.caption("Nástroj pro analýzu panických poklesů akcií a odlišení dočasných výprodejů od fundamentálních problémů.")

# Vstupní pole
ticker_input = st.text_input("Zadejte ticker akcie (např. AAPL, NVDA, TSLA, CEZ.PR):", value="NVDA").strip().upper()

# Definice záložek
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Analýza poklesu", 
    "📰 Aktuální zprávy (News)", 
    "🧠 Jak poznat paniku (Manuál)", 
    "🛠️ Další nástroje & Tipy"
])

# --- TAB 1: ANALÝZA POKLESU ---
with tab1:
    if ticker_input:
        with st.spinner(f"Načítám a analyzuji data pro {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                hist = stock.history(period="60d")

                if hist.empty:
                    st.error(f"Pro ticker **{ticker_input}** nebyla nalezena žádná tržní data. Zkontrolujte jeho správnost.")
                else:
                    info = {}
                    try:
                        info = stock.info or {}
                    except Exception:
                        info = {}

                    current_price = float(hist['Close'].iloc[-1])
                    prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                    day_change_pct = ((current_price - prev_close) / prev_close) * 100

                    fifty_two_high = info.get('fiftyTwoWeekHigh', float(hist['High'].max()))
                    drop_from_high = ((current_price - fifty_two_high) / fifty_two_high) * 100 if fifty_two_high else 0.0

                    avg_vol = float(hist['Volume'].tail(20).mean())
                    today_vol = float(hist['Volume'].iloc[-1])
                    vol_ratio = today_vol / avg_vol if avg_vol > 0 else 1.0

                    # Výpočet RSI (14 dní)
                    delta = hist['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi_series = 100 - (100 / (1 + rs))
                    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

                    # Fundamentální ukazatele
                    debt_to_equity = info.get('debtToEquity', 'N/A')
                    forward_pe = info.get('forwardPE', 'N/A')
                    profit_margins = info.get('profitMargins', 'N/A')

                    # Metriky v přehledných sloupcích
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Aktuální cena", f"${current_price:.2f}", f"{day_change_pct:+.2f}%")
                    col2.metric("Pokles od 52w Maxima", f"{drop_from_high:.2f}%")
                    col3.metric("RSI (14 dní)", f"{rsi:.1f}", delta_color="inverse")
                    col4.metric("Relativní objem (vs 20d)", f"{vol_ratio:.2f}x")

                    st.markdown("---")

                    # Logika detekce paniky
                    panic_points = 0
                    signals = []

                    if rsi < 35:
                        panic_points += 3
                        signals.append(f"**RSI pod 35 ({rsi:.1f})**: Akcie je v silně přeprodaném pásmu.")
                    if day_change_pct < -3.0:
                        panic_points += 2
                        signals.append(f"**Prudký denní pokles ({day_change_pct:.2f}%)**: Indikuje zvýšenou nervozitu.")
                    if vol_ratio > 1.5:
                        panic_points += 2
                        signals.append(f"**Vysoký objem obchodů ({vol_ratio:.1f}x průměru)**: Typický znak kapitulace prodávajících.")

                    fund_risk = "Nízké"
                    if isinstance(debt_to_equity, (int, float)) and debt_to_equity > 150:
                        fund_risk = "VYSOKÉ (Firma má vysoké zadlužení / D/E > 1.5)"
                        panic_points -= 2
                    if isinstance(profit_margins, (int, float)) and profit_margins < 0:
                        fund_risk = "STŘEDNÍ/VYSOKÉ (Společnost vykazuje čistou ztrátu)"
                        panic_points -= 1

                    # Verdikt
                    st.subheader("📋 Vyhodnocení příležitosti")
                    if panic_points >= 4:
                        st.success("🔥 **PRAVDĚPODOBNÁ TRŽNÍ PANIKA**: Algoritmus detekuje přeprodanost a vysoký objem při relativně stabilním fundamentu. Zkontrolujte zprávy pro finální ověření.")
                    elif panic_points >= 2:
                        st.warning("⚠️ **BĚŽNÁ KOREKCE / MÍRNÁ PANIKA**: Pokles vykazuje známky nervozity, ale chybí silná kapitulace.")
                    else:
                        st.info("ℹ️ **STANDARDNÍ POHYB**: Nebyly zachyceny známky panického výprodeje.")

                    # Detaily a fundament
                    col_left, col_right = st.columns(2)
                    with col_left:
                        st.markdown("### 📊 Zachycené signály")
                        if signals:
                            for sig in signals:
                                st.markdown(f"- {sig}")
                        else:
                            st.write("Žádné extrémní signály nebyly zachyceny.")

                    with col_right:
                        st.markdown("### 🏦 Fundamentální zdraví")
                        margin_fmt = f"{profit_margins*100:.1f}%" if isinstance(profit_margins, (int, float)) else str(profit_margins)
                        st.write(f"- **Debt to Equity (Dluh):** {debt_to_equity}")
                        st.write(f"- **Forward P/E:** {forward_pe}")
                        st.write(f"- **Zisková marže:** {margin_fmt}")
                        st.write(f"- **Fundamentální riziko:** {fund_risk}")

            except Exception as e:
                st.error(f"Došlo k chybě při zpracování dat: {str(e)}")

# --- TAB 2: ZPRÁVY ---
with tab2:
    st.subheader(f"📰 Aktuální zprávy pro {ticker_input}")
    if ticker_input:
        try:
            stock = yf.Ticker(ticker_input)
            news_items = stock.news if hasattr(stock, 'news') and stock.news else []

            if not news_items:
                st.info("Pro tento ticker nebyly nalezeny žádné aktuální zprávy.")
            else:
                for item in news_items[:10]:
                    title = item.get('title') or item.get('content', {}).get('title', 'Bez názvu')
                    publisher = item.get('publisher') or item.get('content', {}).get('provider', {}).get('displayName', 'Zdroj')
                    link = item.get('link') or item.get('url') or item.get('content', {}).get('canonicalUrl', {}).get('url', '')

                    st.markdown(f"-[**{title}**]({link}) *({publisher})*")
        except Exception as e:
            st.error(f"Nelze načíst zprávy: {str(e)}")

# --- TAB 3: EDUKACE ---
with tab3:
    st.subheader("🧠 Jak odlišit paniku od reálného problému")
    
    st.markdown("""
    | Kritérium | 🟢 Panický pokles (Nákupní příležitost) | 🔴 Fundamentální problém (Riziko) |
    | :--- | :--- | :--- |
    | **Druh zprávy** | Makroekonomické obavy (inflace, úroky), snížení cílové ceny analytikem, dočasný výpadek v dodávkách. | Účetní podvody, vyšetřování úřady, ztráta klíčového zákazníka, permanentní ztráta trhu. |
    | **RSI (14 dní)** | **Pod 30** (Extrémně přeprodaný trh na denním grafu). | RSI se drží mezi 40-50, cena pozvolna klesá celé měsíce. |
    | **Objem (Volume)** | **Masivní nárůst objemu** (Spike) - Znak kapitulace prodávajících. | Průměrný nebo nízký objem při neustálém poklesu. |
    | **Zadlužení (D/E)** | Nízký dluh ($D/E < 1.0$), silná hotovost na rozvaze. | Vysoký dluh ($D/E > 2.0$), riziko neschopnosti splácet. |
    | **Zisková marže** | Stabilní, společnost vytváří kladný volný cash flow (FCF). | Záporné marže, společnost pálí hotovost. |
    """)

# --- TAB 4: NÁSTROJE ---
with tab4:
    st.subheader("🛠️ Doporučené externí nástroje")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.markdown("### 1. Finviz Screener")
        st.write("Filtrujte akcie přímo v panice pomocí parametrů:")
        st.code("Technical: RSI(14) < 30\nPerformance: Week Down -10%\nFundamental: Debt/Equity < 0.5", language="text")
        
    with col_b:
        st.markdown("### 2. TradingView")
        st.write("Sledujte **Volume Profile (VRVP)** a vyhledávejte úroveň **POC (Point of Control)** pro přesný čas vstupu do pozice.")
        
    with col_c:
        st.markdown("### 3. Simply Wall St")
        st.write("Použijte vizuální diagram **Snowflake** k rychlému ověření, zda má firma dostatečné FCF na pokrytí závazků.")
