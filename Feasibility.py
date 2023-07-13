#Import libraries
import streamlit as st
import pyam
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


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
    #connect to iiasa server 
    conn = pyam.iiasa.Connection('ar6-public')
    #other variables: 'Emissions|CO2', 'Primary Energy|Coal', 
    #query for climate scenario data
    df = conn.query(
        model='REMIND-MAgPIE 2.1-4.2',
        scenario = ['EN_NPi2020_500', 'SusDev_SDP-PkBudg1000'],
        variable="Agricultural Demand|Livestock|Food",
        RRRRRRRRRRRRRRRregion=['Asia', 'Latin America']
    )
    #return data format of df
    return df.data

#df = get_data()