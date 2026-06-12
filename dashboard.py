import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

from analysis import get_relative_frequencies

import os



DB = "cell-count.db"
CSV = 'cell-count.csv'
CELL_COLS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


from load_data import create_db, load_csv
@st.cache_data
def load_data():
    if not os.path.isfile(DB):
        create_db(DB)
        load_csv(CSV, DB)

load_data()

st.set_page_config(page_title="Teiko Cytometry Dashboard", layout="wide")
st.title("Teiko Cytometry Dashboard")

st.header("1. Cell Population Relative Frequencies")

# for now just make a table of the get relative frequencies
df = get_relative_frequencies(DB)

# let's get the metadata as well
con = sqlite3.connect(DB)
meta_df = pd.read_sql_query("""
    SELECT sam.sample, sam.sample_type, sam.time_from_treatment_start, sub.condition, sub.treatment, sub.response
    FROM samples sam
    JOIN subjects sub ON sub.subject = sam.subject
""", con)
con.close()

merged = df.merge(meta_df, on="sample", how="left")

# choose the grouping options
group_options = {
    "Overall Average": None,
    "Sample type": "sample_type",
    "Condition": "condition",
    "Treatment": "treatment",
    "Response": "response"
}
group_choice = st.selectbox("Group by", list(group_options.keys()))
group_col = group_options[group_choice]

# get the average percentage for each cell
if group_col is None:
    avg_df = merged.groupby("population")["percentage"].mean().reset_index()
    fig = px.bar(
        avg_df, x="population", y="percentage",
        title="Average Relative Frequency by Population (All Samples)",
        labels={"percentage": "Mean relative frequency (%)"},
    )
else:
    avg_df = merged.groupby([group_col, "population"])["percentage"].mean().reset_index()
    fig = px.bar(
        avg_df, x=group_col, y="percentage", color="population", barmode="group",
        title=f"Average Relative Frequency by Population, grouped by {group_choice}",
        labels={"percentage": "Mean relative frequency (%)"},
    )
st.plotly_chart(fig, width='stretch')

# get the full data table
st.subheader("Full data table")

wide_df = df.pivot(index=["sample", "total_count"], columns="population", values="percentage")
wide_df = wide_df.reset_index()
wide_df.columns.name = None
# st.write(wide_df.columns.tolist())
st.dataframe(wide_df, width='stretch', hide_index=True)


st.header("2. Responder vs Non-Responder Frequencies")

from analysis import freq_on_response



# make the boxplots
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# get the distinct values for the dropdowns
con = sqlite3.connect(DB)
conditions = pd.read_sql_query("SELECT DISTINCT condition FROM subjects", con)["condition"].tolist()
treatments = pd.read_sql_query("SELECT DISTINCT treatment FROM subjects", con)["treatment"].tolist()
sample_types = pd.read_sql_query("SELECT DISTINCT sample_type FROM samples", con)["sample_type"].tolist()
time_treatments = pd.read_sql_query("SELECT DISTINCT time_from_treatment_start FROM samples ORDER BY time_from_treatment_start", con)["time_from_treatment_start"].tolist()
con.close()

ANY_VAL = "All"

with st.sidebar:
    st.header("Filters")
    st.warning("Not All Insights will be Affected")
    selected_condition = st.selectbox("Condition", [ANY_VAL] + conditions, key="condition")
    selected_treatment = st.selectbox("Treatment", [ANY_VAL] + treatments, key="treatment")
    selected_sample_type = st.selectbox("Sample Type", [ANY_VAL] + sample_types, key="sample_type")
    selected_time = st.selectbox("Time From Treatment Start", [ANY_VAL] + time_treatments, key="time_from_treatment_start")

selected_condition = None if selected_condition == ANY_VAL else selected_condition
selected_treatment = None if selected_treatment == ANY_VAL else selected_treatment
selected_sample_type = None if selected_sample_type == ANY_VAL else selected_sample_type
selected_time = None if selected_time == ANY_VAL else selected_time

yes_freq, no_freq, null_freq = freq_on_response(DB, selected_condition, selected_treatment, selected_sample_type)

st.write(f"Responders: {yes_freq['sample'].nunique()} samples")
st.write(f"Non-responders: {no_freq['sample'].nunique()} samples")
st.write(f"No response data: {null_freq['sample'].nunique()} samples")

fig_box = make_subplots(rows=1, cols=len(CELL_COLS), subplot_titles=CELL_COLS, shared_yaxes=True)

for i, cell in enumerate(CELL_COLS, start=1):
    # responder box
    fig_box.add_trace(
        go.Box(
            y=yes_freq[yes_freq['population'] == cell]["percentage"],
            name="Responder",
            marker_color="#2E86AB",
            legendgroup="Responder",
            showlegend=(i==1)
        ),
        row=1, col=i
    )
    # non-responder box
    fig_box.add_trace(
        go.Box(
            y=no_freq[no_freq["population"] == cell]["percentage"],
            name="Non-responder",
            marker_color="#E76F51",
            legendgroup="Non-responder",
            showlegend=(i == 1),
        ),
        row=1, col=i,
    )
y_max = pd.concat([yes_freq["percentage"], no_freq["percentage"]]).max() * 1.05

fig_box.update_layout(
    height=450,
    title_text="Relative Frequency by Population: Responders VS Non-Responders",
    yaxis={"title": "Relative Frequency (%)", "range": [0, y_max]}
)
#fig_box.update_yaxes(title_text="Relative Frequency (%)")
st.plotly_chart(fig_box, width='stretch')


# compute the significant populations
from analysis import compute_statistics, get_sig_pops

st.subheader("Statistical Significance Tests")

if yes_freq.empty or no_freq.empty:
    st.warning("Not enough data to perform statistical analysis.")
else:
    stat_dict = compute_statistics(yes_freq, no_freq)
    alpha = st.slider("Significance Threshold (alpha)", min_value=0.001, max_value=0.2)

    stats_table = pd.DataFrame({
        "population": CELL_COLS,
        "mann_whitney_p": [stat_dict["mwutest"][c] for c in CELL_COLS],
        "t_test_p": [stat_dict["ttest"][c] for c in CELL_COLS]
    })
    stats_table["significant"] = ((stats_table["mann_whitney_p"] < alpha) & (stats_table["t_test_p"] < alpha))
    significant = get_sig_pops(stat_dict, alpha=alpha, require_both=True)

    def highlight_significant(row):
        color = "background-color: #2E7D3220" if row["significant"] else ""
        return [color] * len(row)
    
    styled = (
        stats_table.style
        .apply(highlight_significant, axis=1)
        .format({"mann_whitney_p": "{:.4f}", "t_test_p":"{:.4f}"})
    )

    st.dataframe(
        styled,
        width='stretch',
        hide_index=True
    )
    if significant:
        st.success(f"Significant difference (alpha={alpha}) between Responders and Non-Responders: " + ", ".join(significant))
    else:
        st.info(f"No population show a significant difference (alpha={alpha})")


st.header("3. Subset Analysis")


from analysis import subset_analysis

subset_stats = subset_analysis(DB, selected_condition, selected_treatment, selected_sample_type, selected_time)

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Samples Per Project")
    st.dataframe(subset_stats["samples_in_project"].rename("sample_count"), width='stretch')
with col2:
    st.subheader("Responder Status")
    st.dataframe(subset_stats["response_status"].rename("subject_count"), width='stretch')
with col3:
    st.subheader("Sex Distribution")
    st.dataframe(subset_stats["sex_status"].rename("subject_count"), width='stretch')

avg_b = subset_stats["avg_b_cells_male_responders"]
st.metric(
    f"Average B cell count for male responders at {selected_time or "any"} days after treatment",
    f"{avg_b:.2f}" if pd.notna(avg_b) else "N/A"
)