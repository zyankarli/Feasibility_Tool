#Import libraries
import streamlit as st
import pyam
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np


st.set_page_config(
     page_title='Feasibility of climate mitigation scenarios',
     initial_sidebar_state="collapsed")

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
    iiasa_creds = r"C:\Users\scheifinger\Documents\GitHub\Feasibility_Tool\iiasa_credentials.yml" 
    #Home
    #iiasa_creds = r"C:\Users\schei\OneDrive\Dokumente\GitHub\Feasibility_Tool\iiasa_credentials.yml"
    #iiasa_creds = st.secrets['iiasa_creds']
    #pyam.iiasa.set_config(st.secrets['iiasa_creds']['username'], st.secrets['iiasa_creds']['password'])
    #pyam.iiasa.Connection()

    #connections = list(pyam.iiasa.Connection(creds=iiasa_creds).valid_connections)
    #query for climate scenario data
    df = pyam.read_iiasa(
        name = 'engage_internal',
        creds = iiasa_creds,
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
                  'Capacity|Electricity|Solar',
                  'Capacity|Electricity|Wind',
                  'Carbon Sequestration|CCS',
                  'Carbon Sequestration|Land Use'
                  ],
        region=["World",
                "North America; primarily the United States of America and Canada",
                "Eastern and Western Europe (i.e., the EU28)",
                "Countries of centrally-planned Asia; primarily China",
                "Countries of South Asia; primarily India", 
                "Countries of Sub-Saharan Africa",
                "Countries of Latin America and the Caribbean",
                "Countries of the Middle East; Iran, Iraq, Israel, Saudi Arabia, Qatar, etc."]
    )      

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
oecd = df[df["region"].isin(["North America; primarily the United States of America and Canada","Eastern and Western Europe (i.e., the EU28)"])]\
    .groupby(["model", "scenario", "variable", "year", "unit"])\
        .agg({"value": "sum"}).reset_index()
oecd['region'] = "OECD"
#get China
china = df[df['region'] == "Countries of centrally-planned Asia; primarily China"]
china.loc[:, "region"] = "China"
#get RoW
row = df[~df["region"].isin(["North America; primarily the United States of America and Canada","Eastern and Western Europe (i.e., the EU28)", "Countries of centrally-planned Asia; primarily China"])]\
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
to_plot_df = df[(df['year'].isin([2020, 2030, 2040])) & (df["scenario"].isin(["T34_1000_ref", "T34_1000_govem"])) & (df["region"] == "World")]

#calculate reductions
reductions_df = to_plot_df[["model", "scenario", "region", 'year', "Emissions|CO2"]]
reductions_df = pd.pivot(data=reductions_df, index=reductions_df.drop(['year', "Emissions|CO2"], axis=1).columns, columns = 'year', values = 'Emissions|CO2').reset_index()
reductions_df["2030_CO2_redu"] = ( (reductions_df[2030] - reductions_df[2020]) / reductions_df[2020]) * -1 #multiplied with -1 to have positive values 
reductions_df["2040_CO2_redu"] = ((reductions_df[2040] - reductions_df[2020]) / reductions_df[2020]) * -1 
reductions_df.drop([2020, 2030, 2040], axis=1, inplace=True)

#merge
to_plot_df = pd.merge(left=to_plot_df, right=reductions_df, on=["model", "scenario", "region"])

#FIGURE 
fig = go.Figure(px.strip(
    to_plot_df[(to_plot_df['year'] == 2030)],
    x='scenario_narrative',
    y='2030_CO2_redu',
    color='model',
    stripmode='overlay'))


fig.add_trace(go.Box(
    y = to_plot_df[(to_plot_df['year'] == 2030) & (to_plot_df["scenario_narrative"] == "Instit")]["2030_CO2_redu"],
    name = "Instit",
    marker_color='grey',
    opacity=0.3,
    boxpoints=False,
    showlegend=False
))

fig.add_trace(go.Box(
    y = to_plot_df[(to_plot_df['year'] == 2030) & (to_plot_df["scenario_narrative"] == "Cost Effective")]["2030_CO2_redu"],
    name = "Cost Effective",
    marker_color='grey',
    opacity=0.3,
    boxpoints=False,
    showlegend=False
))

fig.update_traces({'marker':{'size': 8}})

fig.update_layout(autosize=False,
                  width=600,
                  height=600,
                  title = go.layout.Title(
                    text="ENGAGE 2C scenarios <br><sup>Global CO2 reductions by 2030</sup>",
                    xref="paper",
                    x=0),
                  xaxis_title="Scenario Narrative",
                  yaxis_title = "CO2 reductions",
                  yaxis_tickformat='.0%')
    
st.plotly_chart(fig, theme="streamlit")



#STATEMENT
#Until when is it feasible to phase out coal
st.slider('What is the earliest year that a coal phase-out seems feasible?',
                                2020, 2100, 2030,
                                key = "year_coal_phaseout")
#What change in energy consumption of transport sector is realistic until 2030?
st.number_input('What is the maximum feasible reduction (%) in energy consumption of the transport sector until 2030?',
                                          min_value = -0.2,
                                          max_value = 0.25,
                                          value = 0.0,
                                          step = 0.01,  
                                          key = "change_energy_transport")

#filter dataframe
filter_df = to_plot.loc[(to_plot["year_netcoal"] >= st.session_state['year_coal_phaseout'] ) & (to_plot["redu_FET"] >= st.session_state['change_energy_transport'])]
#calculate "consequences" of input
earliest_net_zero_year = filter_df["year_netzero"].min()
PA_aligned = (filter_df["carbon_budget"].str.contains("1.5C").sum() > 0)


if filter_df.empty:
    st.write("Chosen values out of scenario space! Please chose another input combination.")
else:
    #OUTPUT
    col1, col2, col3 = st.columns(3)
    col1.metric("Earliest possible net-zero year:", earliest_net_zero_year)
    col2.metric("Is it possible to achieve the 2014 PA? ", PA_aligned)
