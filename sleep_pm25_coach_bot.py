# Import libraries yang dipakai
import streamlit as st  # For creating the web app interface
import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI  # For interacting with Google Gemini via LangChain
from langgraph.prebuilt import create_react_agent  # For creating a ReAct agent
from langchain_core.messages import HumanMessage, AIMessage  # For message formatting
from langchain_core.tools import tool  # For creating tools

#ambil tools db kaya di tutorial
from sleepdb_tools import init_database, add_log, recent_logs, stats_last





#flow yang sama seperti sebelumnya
# --- 1. Page Configuration and Title ---

# Set the title and a caption for the web page
st.title("😴Sleep&PM2.5 Coach")
st.caption("chatbot yang dapat mengukur sleep quality melalui kadar PM2.5 dan untuk mengetahui udara di lingkungan sekitar")
st.info("air quality yang diukur melalui sensor PM2.5, tapi kalau tidak ada bisa di referensi kan dari PM2.5 di lingkungan sekitar" \
"melalui nafas.co.id atau airvisual.com",icon="🍃")

# --- 2. Sidebar for Settings ---

# Create a sidebar section for app settings using 'with st.sidebar:'
with st.sidebar:
    # Add a subheader to organize the settings
    st.subheader("Settings")
    
    # Create a text input field for the Google AI API Key.
    # 'type="password"' hides the key as the user types it.
    google_api_key = st.text_input("Google AI API Key", type="password")
    
    # Create a button to reset the conversation.
    # 'help' provides a tooltip that appears when hovering over the button.
    reset_button = st.button("Reset Conversation", help="Clear all messages and start fresh")
    
    # Add a button to initialize the database
    init_db_button = st.button("Initialize Database", help="Create and populate the database with sample data")
    
    # Initialize database if button is clicked
    if init_db_button:
        with st.spinner("Initializing database..."):
            result = init_database()
            st.success(result)
            
    # Add a subheader to display information
    st.markdown("---")
    st.markdown("**Disclaimer**: Informasi bersifat edukasi, bukan nasihat medis.")
    st.markdown("Target praktis: **PM2.5 < 12 µg/m³** selama tidur.")

# --- 3. cek API KEY dan inisialisasi ---
if not google_api_key:
    st.info("Masukkan Google AI API key di sidebar untuk mulai chatting.", icon="🗝️")
    st.stop()


#---- masukan tools sesuai kebutuhan dari/untuk sleepdb_tools.py ----
# Kategori sederhana berbasis PM2.5 (µg/m³)
def _pm25_category(pm25):
    if pm25 <= 12: return "good"
    if pm25 <= 35: return "moderate"
    return "poor"

@tool
def calc_risk(pm25:float,sleep_dur_h:float):
    """Hitung zona kualitas (good/moderate/poor) dan estimasi risiko relatif non-medis
    berdasarkan PM2.5 (µg/m³) dan durasi tidur (jam). Kembalikan dict dengan
    {zone, risk_rel_pct, durasi_h, tips}.
    """
    aq_level = "good" if pm25 <= 12 else ("moderate" if pm25 <= 35 else "poor")
    risk_rel = max(0.0, (pm25 - 12) / 5.0) * 0.21
    tips = [
        "Target PM2.5 < 12 µg/m³ saat tidur.",
        "Nyalakan air purifier 30–60 menit sebelum tidur.",
        "Tutup rapat pintu/jendela saat tidur.",
        "Cek & ganti filter bila indikator >80%."
    ]
    return {
        "zone": aq_level,
        "risk_rel_pct": round(risk_rel * 100, 1),
        "durasi_h": sleep_dur_h,
        "tips": tips[:3] if aq_level != "good" else ["kualitas udara sudah optiomal, pertahankan untuk tidur yang berkualitas."]
    }

@tool
def analyze_sleep(pm25: float, sleep_dur_h: float):
    """
    Analisis non-medis dampak PM2.5 terhadap tidur.
    Returns: dict {zone, risk_rel_pct, durasi_h, tips}
    """
    return calc_risk(float(pm25), float(sleep_dur_h))

@tool
def log_sleep(pm25: float, sleep_dur_h: float, kualitas: str = "", catatan: str = ""):
    """
    Simpan log tidur & PM2.5 ke SQLite.
    """
    return add_log(float(pm25), float(sleep_dur_h), kualitas, catatan)
@tool
def read_summary(days: int = 7, n_recent: int = 10):
    """
    Ringkas rata-rata PM2.5 & durasi dalam X hari + N entri terbaru.
    Returns: dict {avg_pm, avg_durasi_h, cnt, recent: List[Tuple]}
    """
    summary = stats_last(int(days))
    rows = recent_logs(int(n_recent))
    return {**summary, "recent": rows}


@tool
def air_quality_now(location: str):
    """
    Cek kualitas udara saat ini berbasis lokasi (nama area/kota).
    provider: Open-Meteo (gratis tanpa perlu API key).
    Return: dict {location, lat, lon, pm25, category, source}
    """
    # 1) Geocoding (pakai Open-Meteo Geocoding)
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "id", "format": "json"},
        timeout=10
    ).json()
    if not geo.get("results"):
        return {"error": f"Lokasi '{location}' tidak ditemukan."}
    place = geo["results"][0]
    lat, lon = place["latitude"], place["longitude"]
    label = place.get("name", location)
    if "admin1" in place and place["admin1"]:
        label += f", {place['admin1']}"
    if "country" in place and place["country"]:
        label += f", {place['country']}"

    # 2) Query Air Quality (Open-Meteo)
    aq = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "pm2_5",
            "timezone": "auto",
            "current": "pm2_5"
        },
        timeout=10
    ).json()

    current = aq.get("current", {})
    pm25 = None
    # Open-Meteo mengembalikan current->pm2_5
    if "pm2_5" in current:
        pm25 = current["pm2_5"]
    # fallback: ambil jam terakhir dari hourly
    if pm25 is None and aq.get("hourly") and aq["hourly"].get("pm2_5"):
        pm25 = aq["hourly"]["pm2_5"][-1]

    if pm25 is None:
        return {"error": "Data PM2.5 tidak tersedia saat ini."}

    category = _pm25_category(pm25)
    return {
        "location": label,
        "lat": lat,
        "lon": lon,
        "pm25": round(float(pm25), 1),
        "category": category,
        "source": "Open-Meteo (no key)"
    }

# Create agent (cached per API key change)
if ("agent" not in st.session_state) or (getattr(st.session_state, "_last_key", None) != google_api_key):
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=google_api_key,
            temperature=0.2
        )

        st.session_state.agent = create_react_agent(
            model=llm,
            tools=[analyze_sleep, log_sleep, read_summary,air_quality_now],
            prompt="""You are a concise assistant about indoor air quality (PM2.5) and sleep.
- Provide clear, non-medical guidance.
- Prefer calling tools when users ask to analyze, log, or summarize.

When appropriate:
1) Use analyze_sleep(pm25, sleep_dur_h) → zone, relative risk (heuristic), and tips.
2) Use log_sleep(pm25, sleep_dur_h, kualitas?, catatan?) → store logs.
3) Use read_summary(days?, n_recent?) → trends and recent entries.
4) Use air_quality_now(location) when the user asks things like "berapa kualitas udara di [lokasi]" to fetch current PM2.5.

Style:
- Keep answers ≤6 lines unless showing a table.
- Emphasize target PM2.5 < 12 µg/m³ for sleep.
- Add disclaimer: 'Informasi bersifat edukasi, bukan nasihat medis.'"""
        )

        st.session_state._last_key = google_api_key
        st.session_state.pop("messages", None)
    except Exception as e:
        st.error(f"Invalid API Key or configuration error: {e}")
        st.stop()

# --- 4. Chat History Management ---

if "messages" not in st.session_state:
    st.session_state.messages = []

if reset_button:
    st.session_state.pop("agent", None)
    st.session_state.pop("messages", None)
    st.rerun()


# --- 5. Display Past Messages ---

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 6. Handle User Input and Agent Communication ---

prompt = st.chat_input(
    "Tanya seputar tidur & PM2.5… (contoh: 'analisis pm25 28 durasi 7', "
    "'log pm25 35 durasi 6 kualitas buruk catatan AC bocor', 'ringkas 7 hari')"
)

if prompt:
    # 1) Tampilkan prompt user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Siapkan riwayat untuk agent
    messages = []
    for m in st.session_state.messages:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            messages.append(AIMessage(content=m["content"]))

    # 3) Invoke agent
    try:
        with st.spinner("Thinking..."):
            response = st.session_state.agent.invoke({"messages": messages})

            # Ambil jawaban teks terakhir
            if "messages" in response and len(response["messages"]) > 0:
                answer = response["messages"][-1].content
            else:
                answer = "Maaf, aku belum bisa menghasilkan jawaban."

            # Cek apakah ada payload 'recent' dari tool read_summary untuk dirender tabel
            recent_rows = None
            try:
                for m in response.get("messages", []):
                    content = getattr(m, "content", None)
                    # ToolMessage bisa berupa dict
                    if isinstance(content, dict) and "recent" in content:
                        recent_rows = content["recent"]
                        break
            except Exception:
                pass

    except Exception as e:
        answer = f"Terjadi error: {e}"
        recent_rows = None

    # 4) Tampilkan jawaban assistant (+ tabel bila ada)
    with st.chat_message("assistant"):
        st.markdown(answer)
        if recent_rows:
            try:
                df = pd.DataFrame(recent_rows, columns=["ts", "pm25", "durasi_h", "kualitas", "catatan"])
                st.dataframe(df, use_container_width=True)
            except Exception:
                pass

    # 5) Simpan ke riwayat
    st.session_state.messages.append({"role": "assistant", "content": answer})