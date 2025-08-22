import streamlit as st
import pandas as pd
import numpy as np
import datetime

st.set_page_config(page_title="Kredi Kartı Hesaplayıcı", layout="wide")

st.title("💳 Kredi Kartı Ekstre Hesaplayıcı")

# --- Genel Ayarlar ---
st.sidebar.header("Ayarlar")
kesim_gunu = st.sidebar.number_input("Hesap kesim günü", min_value=1, max_value=28, value=28)
son_odeme_gun_farki = st.sidebar.number_input("Son ödeme için ek gün", min_value=1, max_value=20, value=10)
kart_limiti = st.sidebar.number_input("Kart Limiti (₺)", min_value=1000, value=267000, step=1000)

# Faiz ve vergi oranları
st.sidebar.subheader("Oranlar (% aylık)")
faiz_alis = st.sidebar.number_input("Akdi faiz (alışveriş)", value=4.50, step=0.01)
faiz_nakit = st.sidebar.number_input("Akdi faiz (nakit avans)", value=4.75, step=0.01)
faiz_gecikme = st.sidebar.number_input("Gecikme faizi", value=5.05, step=0.01)

st.sidebar.subheader("Vergiler")
bs_mv = st.sidebar.number_input("BSMV (%)", value=5.0, step=0.1)
kkdf = st.sidebar.number_input("KKDF (%) (sadece nakit)", value=15.0, step=0.1)

st.sidebar.subheader("Asgari ödeme oranı")
if kart_limiti <= 50000:
    asgari_oran = st.sidebar.number_input("Asgari oran", value=20.0, step=1.0)
else:
    asgari_oran = st.sidebar.number_input("Asgari oran", value=40.0, step=1.0)

# --- Tarih hesaplama ---
bu_gun = datetime.date.today()
kesim_tarihi = datetime.date(bu_gun.year, bu_gun.month, kesim_gunu)
if bu_gun.day > kesim_gunu:
    if bu_gun.month == 12:
        kesim_tarihi = datetime.date(bu_gun.year + 1, 1, kesim_gunu)
    else:
        kesim_tarihi = datetime.date(bu_gun.year, bu_gun.month + 1, kesim_gunu)

son_odeme_tarihi = kesim_tarihi + datetime.timedelta(days=son_odeme_gun_farki)

st.markdown(f"**Hesap Kesim Tarihi:** {kesim_tarihi.strftime('%d.%m.%Y')}  ")
st.markdown(f"**Son Ödeme Tarihi:** {son_odeme_tarihi.strftime('%d.%m.%Y')}  ")

# --- Veri Girişleri ---
st.header("📥 İşlem Girişi")

tabs = st.tabs(["Devreden Borç", "Peşin Harcama", "Taksitli Harcama", "Nakit Avans", "Ödeme"])

with tabs[0]:
    devreden_borc = st.number_input("Önceki aydan devreden borç (₺)", value=0.0, step=100.0)

with tabs[1]:
    st.write("Peşin (tek çekim) alışverişlerinizi ekleyin:")
    pesin_df = st.data_editor(
        pd.DataFrame(columns=["Tarih", "Tutar"]),
        num_rows="dynamic",
        key="pesin",
        column_config={
            "Tarih": st.column_config.DateColumn("Tarih"),
            "Tutar": st.column_config.NumberColumn("Tutar", step=10.0)
        }
    )

with tabs[2]:
    st.write("Taksitli alışverişlerinizi ekleyin:")
    taksit_df = st.data_editor(
        pd.DataFrame(columns=["Tarih", "Toplam Tutar", "Taksit Sayısı"]),
        num_rows="dynamic",
        key="taksit",
        column_config={
            "Tarih": st.column_config.DateColumn("Tarih"),
            "Toplam Tutar": st.column_config.NumberColumn("Toplam Tutar", step=10.0),
            "Taksit Sayısı": st.column_config.NumberColumn("Taksit Sayısı", step=1, min_value=1)
        }
    )

with tabs[3]:
    st.write("Nakit avans işlemlerinizi ekleyin:")
    nakit_df = st.data_editor(
        pd.DataFrame(columns=["Tarih", "Tutar"]),
        num_rows="dynamic",
        key="nakit",
        column_config={
            "Tarih": st.column_config.DateColumn("Tarih"),
            "Tutar": st.column_config.NumberColumn("Tutar", step=10.0)
        }
    )

with tabs[4]:
    st.write("Bu dönemde yaptığınız ödemeler:")
    odeme_df = st.data_editor(
        pd.DataFrame(columns=["Tarih", "Tutar"]),
        num_rows="dynamic",
        key="odeme",
        column_config={
            "Tarih": st.column_config.DateColumn("Tarih"),
            "Tutar": st.column_config.NumberColumn("Tutar", step=10.0)
        }
    )

# --- Hesaplama Fonksiyonları ---
def gun_farki(tarih, kesim_tarihi):
    try:
        if isinstance(tarih, pd.Timestamp):
            t = tarih.date()
        else:
            t = pd.to_datetime(tarih).date()
        return max((kesim_tarihi - t).days, 0)
    except:
        return 0

# Hesaplama
toplam_alis_faiz = 0
toplam_nakit_faiz = 0

# Devreden borç faiz
if devreden_borc > 0:
    gun = max((kesim_tarihi - bu_gun).days, 30)
    faiz = devreden_borc * (faiz_alis/100/30) * gun
    vergi = faiz * (bs_mv/100)
    toplam_alis_faiz += faiz + vergi

# Peşin alışveriş
for _, row in pesin_df.dropna().iterrows():
    if row.get("Tutar") and row.get("Tarih"):
        try:
            tutar = float(row["Tutar"])
        except:
            tutar = 0
        gun = gun_farki(row["Tarih"], kesim_tarihi)
        faiz = tutar * (faiz_alis/100/30) * gun if tutar > 0 else 0
        vergi = faiz * (bs_mv/100)
        toplam_alis_faiz += faiz + vergi

# Taksitli alışveriş (sadece bu dönemin taksiti)
aktif_taksitler = []
for _, row in taksit_df.dropna().iterrows():
    if row.get("Toplam Tutar") and row.get("Tarih") and row.get("Taksit Sayısı"):
        try:
            tutar = float(row["Toplam Tutar"])
            taksit_sayi = int(row["Taksit Sayısı"])
        except:
            tutar = 0
            taksit_sayi = 1
        taksit_tutar = tutar / taksit_sayi
        aktif_taksitler.append(taksit_tutar)

# Nakit avans
for _, row in nakit_df.dropna().iterrows():
    if row.get("Tutar") and row.get("Tarih"):
        try:
            tutar = float(row["Tutar"])
        except:
            tutar = 0
        gun = gun_farki(row["Tarih"], kesim_tarihi)
        faiz = tutar * (faiz_nakit/100/30) * gun
        vergi = faiz * (bs_mv/100 + kkdf/100)
        toplam_nakit_faiz += faiz + vergi

# Ödemeler
odeme_toplam = 0
for _, row in odeme_df.dropna().iterrows():
    try:
        odeme_toplam += float(row["Tutar"])
    except:
        pass

# Dönem borcu
pesin_toplam = sum([float(x) for x in pesin_df["Tutar"].dropna()]) if not pesin_df.empty else 0
taksit_toplam = sum(aktif_taksitler)
nakit_toplam = sum([float(x) for x in nakit_df["Tutar"].dropna()]) if not nakit_df.empty else 0

statement_amount = devreden_borc + pesin_toplam + taksit_toplam + nakit_toplam + toplam_alis_faiz + toplam_nakit_faiz - odeme_toplam
statement_amount = max(statement_amount, 0)
asgari_tutar = statement_amount * (asgari_oran/100)

# --- Sonuç ---
st.header("📊 Ekstre Özeti")
c1, c2 = st.columns(2)
c1.metric("Dönem borcu (toplam)", f"₺{statement_amount:,.2f}".replace(",", "."))
c2.metric("Asgari ödeme", f"₺{asgari_tutar:,.2f}".replace(",", "."))

st.subheader("Detaylar")
st.write(f"Peşin harcama: ₺{pesin_toplam:,.2f}")
st.write(f"Bu dönem taksit tutarı: ₺{taksit_toplam:,.2f}")
st.write(f"Nakit avans: ₺{nakit_toplam:,.2f}")
st.write(f"Faiz+Vergi (alışveriş): ₺{toplam_alis_faiz:,.2f}")
st.write(f"Faiz+Vergi (nakit): ₺{toplam_nakit_faiz:,.2f}")
st.write(f"Ödemeler: ₺{odeme_toplam:,.2f}")
