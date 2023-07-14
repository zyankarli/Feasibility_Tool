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
    #iiasa_creds = r"C:\Users\scheifinger\Documents\GitHub\Feasibility_Tool\iiasa_credentials.yml" 
    #Home
    #iiasa_creds = r"C:\Users\schei\OneDrive\Dokumente\GitHub\Feasibility_Tool\iiasa_credentials.yml"
    #iiasa_creds = st.secrets['iiasa_creds']
    pyam.iiasa.set_config(st.secrets['iiasa_creds']['username'], st.secrets['iiasa_creds']['password'])
    pyam.iiasa.Connection()

    #connections = list(pyam.iiasa.Connection(creds=iiasa_creds).valid_connections)
    #query for climate scenario data
    df = pyam.read_iiasa(
        name = 'engage_internal',
        creds = iiasa_creds,
        scenario =['T34_550_feas_em',
                   'T34_550_feas_pr',
                   'T34_550_feas_ref',
                   'T34_1000_feas_em',
                   'T34_1000_feas_pr',
                   'T34_1000_feas_ref'],
        variable=["Emissions|CO2", "Primary Energy|Coal", "Primary Energy|Coal|w/ CCS", "Final Energy|Transportation", "Carbon Capture"],
        region=['World']
    )   
    #return data format of df
    return df

df = get_data().data

#Data wrangling
#from long to wide
df = pd.pivot(data=df, index=['model','scenario', 'region', 'year'], columns = 'variable', values = 'value').reset_index()
#get different carbon budgets from scenario name
df['carbon_budget'] = np.where(df['scenario'].str.contains("1000", case=False), "2C", "1.5C")
#get diffeernt scenario narratives from scenario name
df['scenario_narrative'] = np.where(df['scenario'].str.contains("_em", case=True), "EM", np.nan) 
df['scenario_narrative'] = np.where(df['scenario'].str.contains("_ref", case=True), "REF", df['scenario_narrative']) 
df['scenario_narrative'] = np.where(df['scenario'].str.contains("_pr", case=True), "PR", df['scenario_narrative'])

#NET ZERO
# calculate year that each scenario hit's net zero
netzero_df = df[df["Emissions|CO2"] <= 0].groupby(["model", "scenario", "carbon_budget"])['year'].min().reset_index()
netzero_df.rename(columns={"year": "year_netzero"}, inplace=True)

#COAL PHASEOUT
# get amounts of unabated coal
#both Coal data are in EJ/yr
unabcoal_df = df[["model", "scenario", "carbon_budget", "region","year", "Primary Energy|Coal", "Primary Energy|Coal|w/ CCS"]] 
unabcoal_df["Unabated Coal"] = unabcoal_df["Primary Energy|Coal"] - unabcoal_df["Primary Energy|Coal|w/ CCS"]
#pick threshold for when coal is supposed to the phased out // now it's 8EJ/y
unabcoal_df = unabcoal_df[unabcoal_df["Unabated Coal"] <= 8].groupby(["model", "scenario", "carbon_budget"])['year'].min().reset_index()
unabcoal_df.rename(columns={"year": "year_netcoal"}, inplace=True)

#TRANSPORT ENERGY REDUCTION
#calculate change in transportation energy from 2020 to 2030
tranred_df = df[["model", "scenario", "carbon_budget", "region","year", "Final Energy|Transportation"]]
#filter for year 2020 & 2030
tranred_df = tranred_df[(tranred_df["year"] == 2020) | (tranred_df["year"] == 2030) ].reset_index().drop("index", axis=1)
#from long to wide
tranred_df = pd.pivot(data=tranred_df, index=["model", "scenario", "carbon_budget", "region"], 
             columns="year", values= "Final Energy|Transportation").reset_index()
#Finale Energy Transportation = (FET)
tranred_df["redu_FET"] = (tranred_df[2030] - tranred_df[2020]) / tranred_df[2020] 


#MERGE
to_plot = pd.merge(left=netzero_df, right=unabcoal_df, on=["model", "scenario", "carbon_budget"])
to_plot = pd.merge(left=to_plot, right=tranred_df.loc[:, ~tranred_df.columns.isin([2020, 2030])],
                   on=["model", "scenario", "carbon_budget"])

#FIRST figure - CO2 trajectories of different scenario narratives
fig1 = px.line(df,
               x = "year",
               y="Emissions|CO2",
               color = "carbon_budget",
               line_dash="model",
               facet_col="scenario_narrative", 
               title = "CO2 reduction trajectories per scenario narrative",
               color_discrete_sequence=px.colors.qualitative.G10,
               hover_data = {'scenario':True, 'model':True})



#SECOND figure

fig2 = px.scatter(
    data_frame=to_plot,
    x = "year_netcoal",
    y="redu_FET", 
    color = "carbon_budget",
    title = "Example of scenario space",
    color_discrete_sequence=px.colors.qualitative.G10
)


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


#Print graphs
st.plotly_chart(fig1, theme="streamlit")
st.plotly_chart(fig2, theme="streamlit")
