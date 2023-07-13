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

def get_data():
    #get IIASA identification
    iiasa_creds = r"C:\Users\scheifinger\Documents\GitHub\Feasibility_Tool\iiasa_credentials.yml" 
    pyam.iiasa.Connection(creds=iiasa_creds)

    connections = list(pyam.iiasa.Connection(creds=iiasa_creds).valid_connections)
    #other variables: 'Emissions|CO2', 'Primary Energy|Coal', 
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
        variable="Emissions|CO2",
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


st.write(df.head(5))

#FIRST figure
fig1 = px.line(df,
               x = "year",
               y="Emissions|CO2",
               color = "carbon_budget",
               facet_col="scenario_narrative")



#SECOND figure
netzero_df = df[df["Emissions|CO2"] <= 0].groupby(["model", "scenario", 'carbon_budget'])['year'].min().reset_index()

fig2 = px.scatter(
    data_frame=netzero_df,
    x = "year",
    y="carbon_budget"
)


#Print graphs
st.plotly_chart(fig1, theme="streamlit")
st.plotly_chart(fig2, theme="streamlit")