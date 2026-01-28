import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Classroom Trading Lab (Humans vs Bots)", layout="wide")

# =====================================================
# INIT STATE
# =====================================================
if "market" not in st.session_state:

    market = {
        "round": 1,

        "assets": {
            "ABC": {"price": 100.0, "history": [], "halted": False, "cb_ref": 100.0},
            "XYZ": {"price": 200.0, "history": [], "halted": False, "cb_ref": 200.0},
        },

        "humans": {},
        "bots": {},

        "trade_log": [],
        "pnl_history": {},

        # Regulations
        "short_selling_ban": False,
        "circuit_breaker_pct": 0.10
    }

    # 10 human teams
    for i in range(1, 11):
        name = f"Team_{i}"
        market["humans"][name] = {
            "cash": 100000.0,
            "pos": {"ABC": 0, "XYZ": 0}
        }
        market["pnl_history"][name] = [100000.0]

    # Normal bots
    bot_names = ["Momentum Bot", "MeanReversion Bot", "Panic Bot", "Random Bot"]
    for b in bot_names:
        market["bots"][b] = {
            "cash": 200000.0,
            "pos": {"ABC": 0, "XYZ": 0}
        }
        market["pnl_history"][b] = [200000.0]

    # Reckless hedge fund 😈
    market["bots"]["😈 Reckless Hedge Fund"] = {
        "cash": 1000000.0,
        "pos": {"ABC": 0, "XYZ": 0}
    }
    market["pnl_history"]["😈 Reckless Hedge Fund"] = [1000000.0]

    st.session_state.market = market

market = st.session_state.market

# =====================================================
# HELPERS
# =====================================================
def net_worth(agent):
    return (
        agent["cash"]
        + agent["pos"]["ABC"] * market["assets"]["ABC"]["price"]
        + agent["pos"]["XYZ"] * market["assets"]["XYZ"]["price"]
    )

# =====================================================
# TITLE
# =====================================================
st.title("🤖📈 Classroom Trading Lab — Humans vs Bots (+ Regulation)")
st.caption("📰 News moves prices immediately. ▶️ Run Round = humans + bots trade.")

# =====================================================
# SIDEBAR — NEWS & REGULATION
# =====================================================
st.sidebar.header("📰 News Shocks (Immediate)")

selected_asset = st.sidebar.selectbox(
    "Select Asset",
    ["ABC", "XYZ"],
    key="news_asset"
)

if st.sidebar.button("🚨 Bad News (-10%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 0.90
    a["cb_ref"] = a["price"]
    a["halted"] = False

if st.sidebar.button("✅ Good News (+10%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 1.10
    a["cb_ref"] = a["price"]
    a["halted"] = False

if st.sidebar.button("💣 Crash (-25%)"):
    a = market["assets"][selected_asset]
    a["history"].append(a["price"])
    a["price"] *= 0.75
    a["cb_ref"] = a["price"]
    a["halted"] = False

st.sidebar.divider()

st.sidebar.header("🏛️ Market Regulation")

market["short_selling_ban"] = st.sidebar.checkbox(
    "🚫 Ban Short Selling",
    value=market["short_selling_ban"]
)

market["circuit_breaker_pct"] = st.sidebar.slider(
    "🛑 Circuit Breaker Threshold (%)",
    min_value=0.05,
    max_value=0.50,
    value=market["circuit_breaker_pct"],
    step=0.05
)

if st.sidebar.button("🟢 Resume All Trading"):
    for a in market["assets"]:
        market["assets"][a]["halted"] = False
        market["assets"][a]["cb_ref"] = market["assets"][a]["price"]

st.sidebar.divider()

if st.sidebar.button("🔁 Reset Simulation"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# =====================================================
# MARKET STATUS
# =====================================================
st.subheader("📊 Market Status")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Round", market["round"])
c2.metric("ABC", f"₹ {market['assets']['ABC']['price']:.2f}", "HALTED" if market["assets"]["ABC"]["halted"] else "LIVE")
c3.metric("XYZ", f"₹ {market['assets']['XYZ']['price']:.2f}", "HALTED" if market["assets"]["XYZ"]["halted"] else "LIVE")
c4.metric("Short Ban", "ON" if market["short_selling_ban"] else "OFF")

# =====================================================
# HUMAN DECISIONS
# =====================================================
st.subheader("👩‍🏫 Team Decisions")

human_orders = {}

cols = st.columns(5)
for i, name in enumerate(market["humans"].keys()):
    with cols[i % 5]:
        st.markdown(f"**{name}**")
        asset = st.selectbox("Asset", ["ABC", "XYZ"], key=f"{name}_asset")
        action = st.radio("Action", ["HOLD", "BUY", "SELL"], horizontal=True, key=f"{name}_action")
        qty = st.number_input("Qty", min_value=0, max_value=2000, value=0, step=20, key=f"{name}_qty")
        human_orders[name] = {"asset": asset, "action": action, "qty": qty}

# =====================================================
# RUN ROUND (HUMANS + BOTS)
# =====================================================
if st.button("▶️ Run Next Round"):

    trade_log_round = []

    buy_vol = {"ABC": 0, "XYZ": 0}
    sell_vol = {"ABC": 0, "XYZ": 0}

    # -------------------------------
    # 1. HUMAN TRADES
    # -------------------------------
    for team, order in human_orders.items():
        human = market["humans"][team]
        asset = order["asset"]

        if market["assets"][asset]["halted"]:
            continue

        action = order["action"]
        qty = order["qty"]
        price = market["assets"][asset]["price"]

        if action == "HOLD" or qty <= 0:
            continue

        # Short selling ban
        if market["short_selling_ban"] and action == "SELL":
            if human["pos"][asset] - qty < 0:
                trade_log_round.append([market["round"], team, asset, action, qty, price])
                continue

        if action == "BUY":
            human["pos"][asset] += qty
            human["cash"] -= qty * price
            buy_vol[asset] += qty
        else:
            human["pos"][asset] -= qty
            human["cash"] += qty * price
            sell_vol[asset] += qty

        trade_log_round.append([market["round"], team, asset, action, qty, price])

    # -------------------------------
    # 2. BOT TRADES
    # -------------------------------
    for bname, bot in market["bots"].items():
        for asset in ["ABC", "XYZ"]:

            if market["assets"][asset]["halted"]:
                continue

            price = market["assets"][asset]["price"]
            hist = market["assets"][asset]["history"]

            action = None
            qty = 0

            # 😈 Reckless hedge fund
            if "Reckless" in bname:
                base_qty = 300
                if len(hist) > 0:
                    if price > hist[-1]:
                        action = "BUY"; qty = base_qty
                    else:
                        action = "SELL"; qty = base_qty * 2
                else:
                    action = "BUY"; qty = base_qty
            else:
                # Momentum
                if "Momentum" in bname and len(hist) > 0:
                    action = "BUY" if price > hist[-1] else "SELL"
                    qty = 50

                # Mean reversion
                if "MeanReversion" in bname:
                    ref = 100 if asset == "ABC" else 200
                    if price > 1.1 * ref:
                        action = "SELL"; qty = 40
                    elif price < 0.9 * ref:
                        action = "BUY"; qty = 40

                # Panic
                if "Panic" in bname and len(hist) > 0:
                    if price < 0.95 * hist[-1]:
                        action = "SELL"; qty = 80

                # Random
                if "Random" in bname:
                    action = "BUY" if np.random.rand() > 0.5 else "SELL"
                    qty = 30

            if action is None or qty == 0:
                continue

            # Short selling ban for bots
            if market["short_selling_ban"] and action == "SELL":
                if bot["pos"][asset] - qty < 0:
                    continue

            if action == "BUY":
                bot["pos"][asset] += qty
                bot["cash"] -= qty * price
                buy_vol[asset] += qty
            else:
                bot["pos"][asset] -= qty
                bot["cash"] += qty * price
                sell_vol[asset] += qty

            trade_log_round.append([market["round"], bname, asset, action, qty, price])

    # -------------------------------
    # -------------------------------
# 3. PRICE FORMATION + MARKET-WIDE CIRCUIT BREAKER
# -------------------------------
triggered = False
new_prices = {}

# First compute proposed prices
for asset in ["ABC", "XYZ"]:
    old_price = market["assets"][asset]["price"]
    market["assets"][asset]["history"].append(old_price)

    if market["assets"][asset]["halted"]:
        new_prices[asset] = old_price
        continue

    imbalance = buy_vol[asset] - sell_vol[asset]
    new_price = max(1.0, old_price + imbalance / 40.0)
    new_prices[asset] = new_price

# Check if ANY breaches circuit breaker
for asset in ["ABC", "XYZ"]:
    ref = market["assets"][asset]["cb_ref"]
    if abs(new_prices[asset] - ref) / ref > market["circuit_breaker_pct"]:
        triggered = True

# If triggered → halt ALL
if triggered:
    for asset in ["ABC", "XYZ"]:
        market["assets"][asset]["halted"] = True
else:
    # Otherwise apply prices normally
    for asset in ["ABC", "XYZ"]:
        market["assets"][asset]["price"] = new_prices[asset]
        market["assets"][asset]["cb_ref"] = new_prices[asset]

    # -------------------------------
    # 4. SAVE LOGS & P&L
    # -------------------------------
    market["trade_log"].extend(trade_log_round)

    for name, h in market["humans"].items():
        market["pnl_history"][name].append(net_worth(h))
    for name, b in market["bots"].items():
        market["pnl_history"][name].append(net_worth(b))

    market["round"] += 1

# =====================================================
# CHARTS, LEADERBOARD, P&L, LOG (same as before)
# =====================================================
st.subheader("📈 Price History")

c1, c2 = st.columns(2)
with c1:
    if len(market["assets"]["ABC"]["history"]) > 0:
        st.line_chart(pd.DataFrame({"ABC": market["assets"]["ABC"]["history"]}))
with c2:
    if len(market["assets"]["XYZ"]["history"]) > 0:
        st.line_chart(pd.DataFrame({"XYZ": market["assets"]["XYZ"]["history"]}))

st.subheader("🏆 Leaderboard")

rows = []
for name, h in market["humans"].items():
    rows.append({"Agent": name, "Type": "Human", "Net Worth": round(net_worth(h), 0)})
for name, b in market["bots"].items():
    rows.append({"Agent": name, "Type": "Bot", "Net Worth": round(net_worth(b), 0)})

st.dataframe(pd.DataFrame(rows).sort_values("Net Worth", ascending=False), use_container_width=True)

st.subheader("📈 P&L Summary")

pnl_rows = []
for name, series in market["pnl_history"].items():
    start = series[0]
    current = series[-1]
    pnl_rows.append({
        "Agent": name,
        "Net Worth": round(current, 0),
        "P&L": round(current - start, 0),
        "Return %": round(100 * (current - start) / start, 2)
    })

st.dataframe(pd.DataFrame(pnl_rows), use_container_width=True)

st.subheader("🧾 Trade Log (Last 50)")

if len(market["trade_log"]) > 0:
    log_df = pd.DataFrame(
        market["trade_log"],
        columns=["Round", "Agent", "Asset", "Action", "Qty", "Price"]
    )
    st.dataframe(log_df.tail(50), use_container_width=True)
else:
    st.write("No trades yet.")

st.info("""
Now includes:
• 🛑 Circuit breaker (halts trading after large moves)
• 🚫 Short-selling ban (no negative positions)
• 😈 Reckless fund that amplifies both bubbles and crashes

This is now a proper Market Microstructure + Regulation lab.
""")
