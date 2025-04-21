import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt

# PRIME logo in top‑right
st.image("logo.png", width=60)

st.title("SMART CVD Risk Reduction Calculator")
st.markdown("**Created by Samuel Panday — 21/04/2025**")

# ----- Intervention data -----
interventions = [
    {"name": "Smoking cessation", "arr_lifetime": 17, "arr_5yr": 5},
    {"name": "Antiplatelet (ASA or clopidogrel)", "arr_lifetime": 6, "arr_5yr": 2},
    {"name": "BP control (ACEi/ARB ± CCB)", "arr_lifetime": 12, "arr_5yr": 4},
    {"name": "Semaglutide 2.4 mg", "arr_lifetime": 4, "arr_5yr": 1},
    {"name": "Weight loss to ideal BMI", "arr_lifetime": 10, "arr_5yr": 3},
    {"name": "Empagliflozin", "arr_lifetime": 6, "arr_5yr": 2},
    {"name": "Icosapent ethyl (TG ≥1.5)", "arr_lifetime": 5, "arr_5yr": 2},
    {"name": "Mediterranean diet", "arr_lifetime": 9, "arr_5yr": 3},
    {"name": "Physical activity", "arr_lifetime": 9, "arr_5yr": 3},
    {"name": "Alcohol moderation", "arr_lifetime": 5, "arr_5yr": 2},
    {"name": "Stress reduction", "arr_lifetime": 3, "arr_5yr": 1}
]

ldl_therapies = {
    "Atorvastatin 20 mg": 40,
    "Atorvastatin 80 mg": 50,
    "Rosuvastatin 10 mg": 40,
    "Rosuvastatin 20–40 mg": 55,
    "Simvastatin 40 mg": 35,
    "Ezetimibe": 20,
    "PCSK9 inhibitor": 60,
    "Bempedoic acid": 18
}

def estimate_smart_risk(a, s, sbp, tc, h, sm, dm, egfr, crp, vb):
    sex_v = 1 if s=="Male" else 0
    sm_v = 1 if sm else 0
    dm_v = 1 if dm else 0
    crp_l = math.log(crp+1)
    lp = (0.064*a + 0.34*sex_v + 0.02*sbp + 0.25*tc
          -0.25*h + 0.44*sm_v + 0.51*dm_v
          -0.2*(egfr/10) + 0.25*crp_l + 0.4*vb)
    r10 = 1 - 0.900**math.exp(lp - 5.8)
    return round(r10*100,1)

def convert_5yr(r10):
    p = r10/100
    return round((1-(1-p)**0.5)*100,1)

with st.sidebar:
    st.header("Inputs")
    a = st.slider("Age", 30, 90, 60)
    s = st.radio("Sex", ["Male","Female"])
    sm = st.checkbox("Smoking")
    dm = st.checkbox("Diabetes")
    egfr = st.slider("eGFR",15,120,80)
    vb = st.multiselect("Vascular disease",["Coronary","Cerebrovascular","Peripheral"])
    vb = len(vb)
    tc = st.number_input("Total Cholesterol",2.0,10.0,5.0,0.1)
    h = st.number_input("HDL‑C",0.5,3.0,1.0,0.1)
    crp = st.number_input("hs‑CRP",0.1,20.0,2.0,0.1)
    baseline_ldl = st.number_input("Baseline LDL‑C",0.5,6.0,3.5,0.1)
    on_tx = st.multiselect("Already on",list(ldl_therapies.keys()))
    add_tx = st.multiselect("Add/intensify", [d for d in ldl_therapies if d not in on_tx])
    sbp_cur = st.number_input("Current SBP",80,220,145)
    sbp_tgt = st.number_input("Target SBP",80,220,120)
    ivs = st.multiselect("Other interventions",[iv["name"] for iv in interventions])
    hz = st.radio("Horizon",["5yr","10yr","lifetime"],index=1)
    pat = st.checkbox("Patient-friendly view")
    export = st.button("Download CSV")

r10 = estimate_smart_risk(a,s,sbp_cur,tc,h,sm,dm,egfr,crp,vb)
r5 = convert_5yr(r10)
base = r5 if hz=="5yr" else r10
caps = {"5yr":80,"10yr":85,"lifetime":90}
base_c = min(base,caps[hz])

adj = baseline_ldl
for d in on_tx: adj *= (1-ldl_therapies[d]/100)
adj = max(adj,1.0)
fin_ldl = adj
for d in add_tx: fin_ldl *= (1-(ldl_therapies[d]/100)*0.5)
fin_ldl = max(fin_ldl,1.0)

rem = base_c/100
for iv in interventions:
    if iv["name"] in ivs:
        arr = iv["arr_5yr"] if hz=="5yr" else iv["arr_lifetime"]
        rem *= (1-arr/100)
if fin_ldl<baseline_ldl:
    drop = baseline_ldl-fin_ldl
    rrr_ldl = min(22*drop,35)
    rem *= (1-rrr_ldl/100)
if sbp_tgt<sbp_cur:
    rrr_bp = min(15*((sbp_cur-sbp_tgt)/10),20)
    rem *= (1-rrr_bp/100)

final = round(rem*100,1)
arr = round(base_c-final,1)
rrr_o = round(arr/base_c*100,1) if base_c else 0
rrr = min(rrr_o,75)

if st.button("Calculate"):
    st.subheader("Results")
    st.write(f"Baseline {hz} risk: {base_c}%")
    st.write(f"Post‑intervention risk: {final}% (ARR {arr} pp, RRR {rrr}%)")
    st.write(f"Expected LDL‑C: {fin_ldl:.2f} mmol/L")

if export:
    df = pd.DataFrame([{"Age":a,"Sex":s,"Smoking":sm,"DM":dm,"eGFR":egfr,
                        "Vascular":vb,"TC":tc,"HDL":h,"hsCRP":crp,
                        "LDL0":baseline_ldl,"OnTx":";".join(on_tx),
                        "AddTx":";".join(add_tx),"SBP0":sbp_cur,
                        "SBPt":sbp_tgt,"Other":";".join(ivs),
                        "Horizon":hz,"Base%":base_c,"Final%":final,"ARR":arr,"RRR":rrr}])
    st.download_button("Download report",df.to_csv(index=False),file_name="cvd_report.csv")

if st.button("Show chart"):
    fig,ax=plt.subplots()
    ax.bar(["Before","After"],[base_c,final],color=["#CC4444","#44CC44"],alpha=0.9)
    ax.set_ylabel(f"{hz} risk (%)")
    st.pyplot(fig)

st.markdown("---")
st.markdown("Created by PRIME team (Prevention Recurrent Ischaemic Myocardial Events)  ")
st.markdown("King's College Hospital, London")
