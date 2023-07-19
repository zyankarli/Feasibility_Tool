#Import libraries
import streamlit as st
import pyam
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


st.set_page_config(
     page_title='Feasibility of climate mitigation scenarios',
     initial_sidebar_state="collapsed",
     layout="wide")

#hide menu and footer
hide_default_format = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       </style>
       """
st.markdown(hide_default_format, unsafe_allow_html=True)

@st.cache_resource
def get_data():
    #get IIASA identification
    #IIASA
    #iiasa_creds = r"C:\Users\scheifinger\Documents\GitHub\Feasibility_Tool\iiasa_credentials.yml" 
    #Home
    #iiasa_creds = r"C:\Users\schei\OneDrive\Dokumente\GitHub\Feasibility_Tool\iiasa_credentials.yml"
    #Online // also comment out creds = iiasa_creds in read_iiasa below
    pyam.iiasa.set_config(st.secrets['iiasa_creds']['username'], st.secrets['iiasa_creds']['password'])
    pyam.iiasa.Connection()

    #connections = list(pyam.iiasa.Connection(creds=iiasa_creds).valid_connections)
    #query for climate scenario data
    df = pyam.read_iiasa(
        name = 'engage_internal',
        #creds = iiasa_creds,
        scenario =[
            "T34_1000_ref",
            "T34_1000_govem",
            "T34_1000_feas_em",
            "T34_1000_bitb_em",
            "T34_1000_bitb_ref",
            "T34_1000_enab_em"
        ],
        variable=["Emissions|CO2", 
                  'Emissions|Kyoto Gases',
                  'Primary Energy|Coal',
                  'Primary Energy|Gas',
                  'Primary Energy',
                  'Capacity|Electricity|Coal',
                  'Capacity|Electricity|Solar',
                  'Capacity|Electricity|Wind',
                  'Carbon Sequestration|CCS',
                  'Carbon Sequestration|Land Use',
                  'Secondary Energy|Electricity|Coal',
                  'Secondary Energy|Electricity|Solar'
                  ],
        region=["World",
                "North America; primarily the United States of America and Canada",
                "Eastern and Western Europe (i.e., the EU28)",
                "Pacific OECD",
                "Countries of centrally-planned Asia; primarily China",
                "Countries of South Asia; primarily India", 
                "Countries of Sub-Saharan Africa",
                "Countries of Latin America and the Caribbean",
                "Countries of the Middle East; Iran, Iraq, Israel, Saudi Arabia, Qatar, etc."]
    )      
#TODO change to secdonary energy from primary
    #return data format of df
    return df

df = get_data().data

#DATA WRANGLING
#get regional groupings
## OECD: "North America; primarily the United States of America and Canada","Eastern and Western Europe (i.e., the EU28)"
#TODO Clarify that countries of Asia and Latin America are missing
## China:  Countries of centrally-planned Asia; primarily China
## Rest of the world: other countries
#get world
world = df[df['region'] == "World"]
world.loc[:, "region"] = "World"
#get OECD*
oecd = df[df["region"].isin(["North America; primarily the United States of America and Canada","Eastern and Western Europe (i.e., the EU28)", "Pacific OECD"])]\
    .groupby(["model", "scenario", "variable", "year", "unit"])\
        .agg({"value": "sum"}).reset_index()
oecd['region'] = "OECD"
#get China
china = df[df['region'] == "Countries of centrally-planned Asia; primarily China"]
china.loc[:, "region"] = "China"
#get RoW
row = df[~df["region"].isin(["World", "North America; primarily the United States of America and Canada","Eastern and Western Europe (i.e., the EU28)", "Pacific OECD", "Countries of centrally-planned Asia; primarily China"])]\
        .groupby(["model", "scenario", "variable", "year", "unit"])\
            .agg({"value": "sum"}).reset_index()
row["region"] = "RoW"
#Concat four regions
df = pd.concat([world, oecd, china, row]).reset_index()

#from long to wide
df = pd.pivot(data=df, index=['model','scenario', 'region', 'year'], columns = 'variable', values = 'value').reset_index()
#get diffeernt scenario narratives from scenario name
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_1000_ref", case=True), "Cost Effective", np.nan) 
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_1000_bitb_ref", case=True), "Tech", df['scenario_narrative']) 
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_1000_govem", case=True), "Instit", df['scenario_narrative'])
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_1000_bitb_em", case=True), "Tech+Inst", df['scenario_narrative'])
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_1000_enab_em", case=True), "Inst+Enab", df['scenario_narrative'])
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_1000_feas_em", case=True), "Tech+Inst+Enab", df['scenario_narrative'])

#caluclate percentages of energymix for coal and gas
df["Share_Coal"] = df["Primary Energy|Coal"] / df["Primary Energy"]
df["Share_Gas"] = df["Primary Energy|Gas"] / df["Primary Energy"]


#GET DATA TO PLOT
#filter
to_plot_df = df[(df['year'].isin([2020, 2030, 2040])) & (df["scenario"].isin(["T34_1000_ref", "T34_1000_govem"])) & (df["region"] == "World")]

#calculate reductions
reductions_df = to_plot_df[["model", "scenario", "scenario_narrative", "region", 'year', "Emissions|CO2"]]
reductions_df = pd.pivot(data=reductions_df, index=reductions_df.drop(['year', "Emissions|CO2"], axis=1).columns, columns = 'year', values = 'Emissions|CO2').reset_index()
reductions_df["2030_CO2_redu"] = ( (reductions_df[2030] - reductions_df[2020]) / reductions_df[2020]) * -1 #multiplied with -1 to have positive values 
reductions_df["2040_CO2_redu"] = ((reductions_df[2040] - reductions_df[2020]) / reductions_df[2020]) * -1 
reductions_df.drop([2020, 2030, 2040], axis=1, inplace=True)

#calculate capacities/usage for 2030
coal_use_2030 = pd.pivot(data=to_plot_df, index=['model','scenario', 'region'], columns = 'year', values = 'Secondary Energy|Electricity|Coal').reset_index()[['model', 'scenario', 'region', 2030]]
coal_use_2030.rename(columns={2030:"coal_use_2030"}, inplace=True)

solar_use_2030 = pd.pivot(data=to_plot_df, index=['model','scenario', 'region'], columns = 'year', values = 'Secondary Energy|Electricity|Solar').reset_index()[['model', 'scenario', 'region', 2030]]
solar_use_2030.rename(columns={2030:"solar_use_2030"}, inplace=True)

#merge
to_plot_df = pd.merge(left=reductions_df, right=coal_use_2030, on=["model", "scenario", "region"])
to_plot_df = pd.merge(left=to_plot_df, right=solar_use_2030, on=["model", "scenario", "region"])

# #make CO2 reduction longer for plotting purposes
#reduce data
to_plot_df = pd.melt(to_plot_df, id_vars=["model", 'scenario', 'region', 'scenario_narrative', 'coal_use_2030','solar_use_2030'],
                    value_vars=["2030_CO2_redu", "2040_CO2_redu"],
                    var_name='reduction_year', value_name='reduction_value')



#STATEMENT
#Until when is it feasible to phase out coal
col_l, col_m, col_r = st.columns(3)
with col_m:
    st.write("## Feasibility concerns")
    st.slider('What is the feasible maximum of global coal use for electricity generation in 2030? (The current global coal use is about ' \
            + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Coal"].median()))) \
            + "EJ)",
            min_value = 1,
            max_value = 25,
            value = 1,
            step = 5, 
            key = "coal_use_2030")
    st.slider('What is the feasible maximium of global solar power use for elecricity generation in 2030? (The current global coal use is about ' \
            + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Solar"].median()))) \
            + "EJ)",
              min_value = 5,
              max_value = 40,
              value = 40,
              step = 5,
              key = 'solar_use_2030')


#filter dataframe
#old below
# filter_df = pd.pivot(data=to_plot_df, index=['model','scenario', 'region', 'scenario_narrative', '2030_CO2_redu', '2040_CO2_redu'],
#                      columns = 'year', values = 'Secondary Energy|Electricity|Coal').reset_index()
# filter_df = filter_df[(filter_df[2030] >= st.session_state['coal_use_2030']) & \
#                       (filter_df[])]
# filter_df = pd.melt(filter_df, id_vars=["model", 'scenario', 'region', 'scenario_narrative', 2030],
#                     value_vars=["2030_CO2_redu", "2040_CO2_redu"],
#                     var_name='reduction_year', value_name='reduction_value')

filter_df = to_plot_df[(to_plot_df['coal_use_2030'] >= st.session_state['coal_use_2030']) &\
                       (to_plot_df['solar_use_2030'] <= st.session_state['solar_use_2030'])]



#METRICS // calculate "consequences" of input
#calculate year that each scenario hit's net zero
netzero_df = df[df["Emissions|CO2"] <= 0].groupby(["model", "scenario", "region"])['year'].min().reset_index()
netzero_df.rename(columns={"year": "year_netzero"}, inplace=True)
#add to filter
filter_df = pd.merge(left=filter_df, right=netzero_df, on=["model", "scenario", "region"])

#required coal reduction compared to 2020 median in percent
required_coal_reduction_2030 = round(
    100 - \
    (float(st.session_state['coal_use_2030']) / \
          round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Coal"].median())) *\
          100))

required_solar_upscale_2030 = round(
    float(st.session_state['solar_use_2030']) / \
          round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Solar"].median())) *\
          100)


earliest_net_zero_year = filter_df["year_netzero"].min()
#PA_aligned = (filter_df["carbon_budget"].str.contains("1.5C").sum() > 0)

if filter_df.empty:
    st.write("Chosen values out of scenario space! Please chose another input combination.")
# else:
#     #OUTPUT
#     col1, col2, col3 = st.columns(3)
#     col1.metric("Earliest possible net-zero year:", earliest_net_zero_year)
#     col2.metric("Is it possible to achieve the 2014 PA? ", PA_aligned)
#only show in case not empty
else:
    #FIGURES
    color_mapping = {
        'AIM/CGE V2.2': "rgb(255, 0, 0)",
        'COFFEE 1.5': "rgb(0, 255, 0)",
        'GEM-E3_V2023': "rgb(0, 0, 255)",
        'IMAGE 3.2': "rgb(255, 255, 0)",
        'MESSAGEix-GLOBIOM_1.1': "rgb(255, 0, 255)",
        'POLES ENGAGE': "rgb(0, 255, 255)",
        'REMIND 3.0': "rgb(128, 0, 0)",
        'WITCH 5.0': "rgb(0, 128, 0)"
    }

    # Map colors based on the "model" column
    filter_df["color"] = filter_df["model"].map(color_mapping)

    fig = make_subplots(rows=1, cols=len(filter_df["reduction_year"].unique()), shared_yaxes=True)

    for i, year in enumerate(filter_df["reduction_year"].unique()):
        box_trace = go.Box(
            x=filter_df[(filter_df["reduction_year"] == year)]["scenario_narrative"],
            y=filter_df[(filter_df["reduction_year"] == year)]["reduction_value"],
            name="Boxplot",
            boxpoints=False,
            marker_color='grey',
            opacity=0.3,
            showlegend=False
        )

        fig.add_trace(box_trace, row=1, col=i + 1)

        # Add subplot titles
        fig.update_layout(
            annotations=[dict(text=str(year), xref="x" + str(i + 1), yref="paper", x=0.5, y=1.1, showarrow=False) for i, year in enumerate(filter_df["reduction_year"].unique())]
        )

        # Create a scatterplot for each model
        for model in filter_df["model"].unique():
            scatter_trace = go.Scatter(
                x=filter_df[(filter_df["reduction_year"] == year) & (filter_df["model"] == model)]["scenario_narrative"],
                y=filter_df[(filter_df["reduction_year"] == year) & (filter_df["model"] == model)]["reduction_value"],
                mode="markers",
                name=model,
                marker=dict(
                    color=color_mapping[model],
                    size=6
                ),
                showlegend=i==0,
                legendgroup=model
            )

            fig.add_trace(scatter_trace, row=1, col=i + 1)

    fig.update_layout(
        title = go.layout.Title(
            text="ENGAGE 2C scenarios <br><sup>Global CO2 reductions by 2030 and 2040</sup>",
            xref="paper",
            x=0),
        xaxis=dict(title="Scenario Narrative", ),
        yaxis=dict(title="Reduction Value", range=[0, 0.6]),
        legend=dict(
            traceorder="normal",
            itemsizing="constant"
        )
    )



    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        st.write('### Implications')
        st.metric("Earliest possible net-zero year:", earliest_net_zero_year)
        st.metric("Required coal reduction since 2020:",
                str(required_coal_reduction_2030) + "%")
        st.metric("Required solar upscale since 2020:",
                str(required_solar_upscale_2030) + "%")
    with col2:
        st.plotly_chart(fig, theme="streamlit")



