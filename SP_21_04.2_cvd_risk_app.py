import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt

# ----- Page Config & Branding -----
st.set_page_config(layout="wide")
col1, col2, col3 = st.columns([1,6,1])
with col3:
    try:
        st.image("logo.png", width=200)
    except Exception:
        st.warning("Logo not found; please add logo.png to your repo.")

st.title("SMART CVD Risk Reduction Calculator")
st.markdown("**Created by Samuel Panday — 21/04/2025**")

# ----- Intervention Data -----
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

# ----- Risk Functions -----
def estimate_smart_risk(age, sex, sbp, tc, hdl, smoker, diabetes, egfr, crp, vasc):
    sex_v = 1 if sex == "Male" else 0
    smoke_v = 1 if smoker else 0
    dm_v = 1 if diabetes else 0
    crp_log = math.log(crp + 1) if crp else 0
    lp = (0.064 * age + 0.34 * sex_v + 0.02 * sbp + 0.25 * tc
          - 0.25 * hdl + 0.44 * smoke_v + 0.51 * dm_v
          - 0.2 * (egfr / 10) + 0.25 * crp_log + 0.4 * vasc)
    r10 = 1 - 0.900 ** math.exp(lp - 5.8)
    return round(r10 * 100, 1)

def convert_5yr(r10):
    p = r10 / 100
    return round((1 - (1 - p) ** 0.5) * 100, 1)

# ----- Sidebar Inputs -----
with st.sidebar:
    st.header("Inputs")
    # Co-morbidities
    age = st.slider("Age", 30, 90, 60)
    sex = st.radio("Sex", ["Male", "Female"])
    smoker = st.checkbox("Smoking")
    diabetes = st.checkbox("Diabetes")
    egfr = st.slider("eGFR (mL/min/1.73m²)", 15, 120, 80)
    st.markdown("**Vascular disease (please tick all that apply):**")
    vasc_cor = st.checkbox("Coronary artery disease")
    vasc_ce = st.checkbox("Cerebrovascular disease")
    vasc_pad = st.checkbox("Peripheral artery disease")
    vasc_count = sum([vasc_cor, vasc_ce, vasc_pad])

    # Labs
    total_chol = st.number_input("Total Cholesterol (mmol/L)", 2.0, 10.0, 5.0, 0.1)
    hdl = st.number_input("HDL-C (mmol/L)", 0.5, 3.0, 1.0, 0.1)
    crp = st.number_input("hs-CRP (mg/L) (baseline, not during acute MI)", 0.1, 20.0, 2.0, 0.1)
    hbA1c = st.number_input("Latest HbA1c (%)", 4.0, 12.0, 7.0, 0.1)
    baseline_ldl = st.number_input("Pre-admission LDL-C (mmol/L)", 0.5, 6.0, 3.5, 0.1)

    # Lipid-lowering therapy
    pre_tx = st.multiselect("Pre-admission lipid-lowering therapy", list(ldl_therapies.keys()))
    add_tx = st.multiselect("Pre-admission additional lipid-lowering therapy (if appropriate)",
                             [d for d in ldl_therapies if d not in pre_tx])

    # Blood Pressure
    sbp_current = st.number_input("Current SBP (mmHg)", 80, 220, 145)
    sbp_target = st.number_input("Target SBP (mmHg)", 80, 220, 120)

    # Other interventions
    st.markdown("**Additional interventions (tick all that apply):**")
    selected_iv = []
    for iv in interventions:
        if st.checkbox(iv["name"]):
            selected_iv.append(iv["name"])

    # Time horizon
    horizon = st.radio("Select time horizon", ["5yr", "10yr", "lifetime"], index=1)
    patient_mode = st.checkbox("Patient-friendly view")
    export = st.button("Download report as CSV")

# ----- Calculations -----
risk10 = estimate_smart_risk(age, sex, sbp_current, total_chol, hdl,
                               smoker, diabetes, egfr, crp, vasc_count)
risk5 = convert_5yr(risk10)
baseline_risk = risk5 if horizon == "5yr" else risk10
# Cap baseline
caps = {"5yr": 80, "10yr": 85, "lifetime": 90}
baseline_capped = min(baseline_risk, caps[horizon])

# LDL adjustment
adjusted_ldl = baseline_ldl
for d in pre_tx:
    adjusted_ldl *= (1 - ldl_therapies[d] / 100)
adjusted_ldl = max(adjusted_ldl, 1.0)
final_ldl = adjusted_ldl
for d in add_tx:
    final_ldl *= (1 - (ldl_therapies[d] / 100) * 0.5)
final_ldl = max(final_ldl, 1.0)

# Apply interventions
remaining = baseline_capped / 100
# non-lipid
for iv in interventions:
    if iv["name"] in selected_iv:
        arr = iv["arr_5yr"] if horizon == "5yr" else iv["arr_lifetime"]
        remaining *= (1 - arr / 100)
# LDL effect
if final_ldl < baseline_ldl:
    drop = baseline_ldl - final_ldl
    rrr_ldl = min(22 * drop, 35)
    remaining *= (1 - rrr_ldl / 100)
# BP effect
if sbp_target < sbp_current:
    rrr_bp = min(15 * ((sbp_current - sbp_target) / 10), 20)
    remaining *= (1 - rrr_bp / 100)

final_risk = round(remaining * 100, 1)
ARR = round(baseline_capped - final_risk, 1)
RRR = round(min(ARR / baseline_capped * 100 if baseline_capped else 0, 75), 1)

# ----- Display Results -----
if st.button("Calculate"):
    st.subheader("Results")
    st.write(f"Baseline {horizon} risk: {baseline_capped}%")
    st.write(f"Post-intervention risk: {final_risk}% (ARR {ARR} pp, RRR {RRR}%)")
    st.write(f"Expected LDL-C: {final_ldl:.2f} mmol/L — at 3 months following initiated lipid-lowering therapy")

    if export:
        df = pd.DataFrame([{
            "Age": age, "Sex": sex, "Smoking": smoker, "Diabetes": diabetes,
            "eGFR": egfr, "Vascular beds": vasc_count, "Total Chol": total_chol,
            "HDL": hdl, "hsCRP": crp, "HbA1c": hbA1c, "LDL baseline": baseline_ldl,
            "Pre-admission Tx": ";".join(pre_tx), "Add-on Tx": ";".join(add_tx),
            "SBP current": sbp_current, "SBP target": sbp_target,
            "Other interventions": ";".join(selected_iv), "Horizon": horizon,
            "Baseline risk (%)": baseline_capped, "Final risk (%)": final_risk,
            "ARR (pp)": ARR, "RRR (%)": RRR
        }])
        st.download_button("Download report", df.to_csv(index=False), file_name="cvd_report.csv")

# Chart
if st.button("Show Chart"):
    fig, ax = plt.subplots()
    ax.bar(["Baseline", "After"], [baseline_capped, final_risk], color=["#CC4444", "#44CC44"], alpha=0.9)
    ax.set_ylabel(f"{horizon} CVD Risk (%)")
    st.pyplot(fig)

# Footer
st.markdown("---")
st.markdown("Created by PRIME team (Prevention Recurrent Ischaemic Myocardial Events)")
st.markdown("King's College Hospital, London")
'''

# Write files
Path("/mnt/data/cvd_risk_app.py").write_text(app_code)
Path("/mnt/data/requirements.txt").write_text(reqs)

("/mnt/data/cvd_risk_app.py
