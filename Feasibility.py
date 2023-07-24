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

#CCS links:
## https://discuss.streamlit.io/t/remove-or-reduce-spaces-between-elements/23283


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
            "T34_1000_enab_em",
            "T34_NPi2100",
            "T34_NDC2100"
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
                "Other countries of Asia"
                "Countries of Sub-Saharan Africa",
                "Countries of Latin America and the Caribbean",
                "Countries of the Middle East; Iran, Iraq, Israel, Saudi Arabia, Qatar, etc.",
                "Countries from the Reforming Economies of Eastern Europe and the Former Soviet Union; primarily Russia"]
    )      
#TODO according to Elina Teams message, RoW is own category. Add?
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
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_NDC2100", case=True), "NDC", df['scenario_narrative'])
df['scenario_narrative'] = np.where(df['scenario'].str.contains("T34_NPi2100", case=True), "Current Policy", df['scenario_narrative'])

#caluclate percentages of energymix for coal and gas
df["Share_Coal"] = df["Primary Energy|Coal"] / df["Primary Energy"]
df["Share_Gas"] = df["Primary Energy|Gas"] / df["Primary Energy"]



#GET DATA TO PLOT
#filter
#to_plot_df = df[(df['year'].isin([2020, 2030, 2040])) & (df["scenario"].isin(["T34_1000_ref", "T34_1000_govem"])) & (df["region"] == "World")] #old approach
to_plot_df = df[(df['year'].isin([2020, 2030, 2040, 2050])) & (df["scenario"].isin(["T34_1000_ref", "T34_1000_govem", 'T34_NDC2100', 'T34_NPi2100']))] #without world filter




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

ccs_use_2030 = pd.pivot(data=to_plot_df, index=['model','scenario', 'region'], columns = 'year', values = 'Carbon Sequestration|CCS').reset_index()[['model', 'scenario', 'region', 2050]]
ccs_use_2030.rename(columns={2050:"ccs_use_2050"}, inplace=True) #unit 	Mt CO2/yr

#calculate year that each scenario hit's net zero
netzero_df = df[df["Emissions|CO2"] <= 0].groupby(["model", "scenario", "region"])['year'].min().reset_index() #net-zero set to 0 CO2 emissions here
#get all the scenarios that don't reach net_zero
no_netzero_df = df[df["scenario"].isin(["T34_1000_ref", "T34_1000_govem", 'T34_NDC2100', 'T34_NPi2100'])][["model", "scenario", "region", "year", "Emissions|CO2"]]
no_netzero_df["netzero_test"] = no_netzero_df["Emissions|CO2"] <= 0
no_netzero_df = pd.DataFrame(no_netzero_df.groupby(["model", 'scenario', 'region'])["netzero_test"].sum()).reset_index()
no_netzero_df = no_netzero_df[no_netzero_df["netzero_test"] == 0]
no_netzero_df['netzero_test'] = "not within this century"
no_netzero_df.rename(columns={"netzero_test": "year"}, inplace=True)
#append no_net_zero to netzero 
netzero_df = pd.concat([netzero_df, no_netzero_df])
netzero_df.rename(columns={"year": "year_netzero"}, inplace=True)


#merge
to_plot_df = pd.merge(left=reductions_df, right=coal_use_2030, on=["model", "scenario", "region"])
to_plot_df = pd.merge(left=to_plot_df, right=solar_use_2030, on=["model", "scenario", "region"])
to_plot_df = pd.merge(left=to_plot_df, right=ccs_use_2030, on=["model", "scenario", "region"])
to_plot_df = pd.merge(left=to_plot_df, right=netzero_df, on=["model", "scenario", "region"])


# #make CO2 reduction longer for plotting purposes
#reduce data
to_plot_df = pd.melt(to_plot_df, id_vars=["model", 'scenario', 'region', 'scenario_narrative', 'coal_use_2030','solar_use_2030', 'ccs_use_2050', 'year_netzero'],
                    value_vars=["2030_CO2_redu", "2040_CO2_redu"],
                    var_name='reduction_year', value_name='reduction_value')
#POLES ENGAGE model doesn't report CCS; set all it's NA values to 4000 so that it's still displayed in graph
to_plot_df['ccs_use_2050'] = to_plot_df['ccs_use_2050'].fillna(6000)

tab1, tab2 = st.tabs(["Globe", "Regions"])

#TAB GLOBAL
with tab1:
    #STATEMENTS
    #Until when is it feasible to phase out coal
    col_l, col_m, col_r = st.columns(3)
    with col_m:
        st.write("### Feasibility concerns")
        st.slider('What is the feasible **minimum** of coal used globally for electricity generation in 2030? (The current global coal use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Coal"].median()))) \
                + "EJ/yr)",
                min_value = 1,
                max_value = 20,
                value = 1,
                step = 5,
                format="%.1f EJ/yr",
                key = "coal_use_2030_world")
        st.slider('What is the feasible **maximium** of global solar power used globally for elecricity generation in 2030? (The current global coal use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Solar"].median()))) \
                + "EJ/yr)",
                    min_value = 15,
                    max_value = 40,
                    value = 40,
                    step = 5,
                    format="%.1f EJ/yr",
                    key = 'solar_use_2030_world')
        st.slider('What is the feasible **maximium** of global CCS deployment in 2050? (The current global deployment is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Carbon Sequestration|CCS"].median()))) \
                + "Mt CO2/yr)",
                    min_value = 2000,
                    max_value = 12100,
                    value = 12100,
                    step = 2000,
                    format="%.1f Mt CO2/yr",
                    key = 'ccs_use_2050_world')

    #filter dataframe
    filter_df_world = to_plot_df[(to_plot_df['coal_use_2030'] >= st.session_state['coal_use_2030_world']) &\
                        (to_plot_df['solar_use_2030'] <= st.session_state['solar_use_2030_world']) &\
                        (to_plot_df['ccs_use_2050'] <= st.session_state['ccs_use_2050_world']) &\
                        (to_plot_df['region'] == "World")]
    #METRICS // calculate "consequences" of input
    #required coal reduction compared to 2020 median in percent
    required_coal_reduction_2030 = round(
    100 - \
    (float(st.session_state['coal_use_2030_world']) / \
            round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Coal"].median())) *\
            100))

    required_solar_upscale_2030 = round(
    float(st.session_state['solar_use_2030_world']) / \
            round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Solar"].median())) *\
            100)

    if pd.to_numeric(filter_df_world["year_netzero"], errors="coerce").notna().sum() != 0: #as long as there are numbers, display the lowest value
        earliest_net_zero_year = filter_df_world[pd.to_numeric(filter_df_world["year_netzero"], errors="coerce").notna()]["year_netzero"].min() #filter only to numeric values
    else: #display disclaimer
        earliest_net_zero_year = "not within this century"

    
    #PA_aligned = (filter_df["carbon_budget"].str.contains("1.5C").sum() > 0)

    if filter_df_world.empty:
        st.write("Chosen values out of scenario space! Please chose another input combination.")
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
        filter_df_world["color"] = filter_df_world["model"].map(color_mapping)

        #set order of scenario_narratives for plot
        filter_df_world["scenario_narrative"] = pd.Categorical(filter_df_world["scenario_narrative"], categories=["Cost Effective", "Instit", "NDC", "Current Policy"])
        filter_df_world = filter_df_world.sort_values(by="scenario_narrative")

        #TODO: test for each scenario, how many models (unique) are still present. When this number drops below 3, set the reduction_value of all respective rows to 0
        #(filter_df_world[(filter_df_world["reduction_year"] == '2030_CO2_redu')].groupby('scenario')['model']))
        
        fig_world = make_subplots(rows=1, cols=len(filter_df_world["reduction_year"].unique()), shared_yaxes=True)

        for i, year in enumerate(filter_df_world["reduction_year"].unique()):            
            box_trace = go.Box(
                x=filter_df_world[(filter_df_world["reduction_year"] == year)]["scenario_narrative"],
                y=filter_df_world[(filter_df_world["reduction_year"] == year)]["reduction_value"],
                name="Boxplot",
                boxpoints=False,
                marker_color='grey',
                opacity=0.3,
                showlegend=False
        )

            fig_world.add_trace(box_trace, row=1, col=i + 1)

            # Add subplot titles
            fig_world.update_layout(
                annotations=[dict(text=str(year), xref="x" + str(i + 1), yref="paper", x=0.5, y=1.1, showarrow=False) for i, year in enumerate(filter_df_world["reduction_year"].unique())]
            )

            # Create a scatterplot for each model
            for model in filter_df_world["model"].unique():
                scatter_trace = go.Scatter(
                    x=filter_df_world[(filter_df_world["reduction_year"] == year) & (filter_df_world["model"] == model)]["scenario_narrative"],
                    y=filter_df_world[(filter_df_world["reduction_year"] == year) & (filter_df_world["model"] == model)]["reduction_value"],
                    mode="markers",
                    name=model,
                    marker=dict(
                        color=color_mapping[model],
                        size=6
                    ),
                    showlegend=i==0,
                    legendgroup=model
                )

                fig_world.add_trace(scatter_trace, row=1, col=i + 1)

        fig_world.update_layout(
            title = go.layout.Title(
                text="ENGAGE 2C scenarios <br><sup>Global CO2 reductions by 2030 and 2040</sup>",
                xref="paper",
                x=0),
            xaxis=dict(title="Scenario Narrative", ),
            yaxis=dict(title="Reduction Value", range=[-0.2, 0.6]),
            legend=dict(
                traceorder="normal",
                itemsizing="constant"
            )
        )
        #print output
        col1, col2 = st.columns([0.3, 0.7])
        with col1:
            st.write('### Global Policy Implications')
            st.metric("Earliest possible net-zero year:", earliest_net_zero_year)
            st.metric("Required coal reduction in the next 10 years:",
                    str(required_coal_reduction_2030) + "%")
            st.metric("Required solar upscale in the next 10 years:",
                    str(required_solar_upscale_2030) + "%")
        with col2:
            st.plotly_chart(fig_world, theme="streamlit")

#TAB REGIONAL
with tab2:
    #STATEMENTS
    #Until when is it feasible to phase out coal
    col_l, col_m, col_r = st.columns(3)
    with col_m:
        st.write("### Feasibility concerns")
    with col_l:
        st.write("#### Feasible **minimum** of coal used for electricity generation in 2030:") # round off min value
        st.slider('In **OECD** (The current coal use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "OECD")]["Secondary Energy|Electricity|Coal"].median()))) \
                + "EJ/yr)",
                min_value = 0.0,
                max_value = 2.0,
                value = 0.0,
                step = 1.0,
                format="%.1f EJ/yr",
                key = "coal_use_2030_OECD")
                
        st.slider('In **China** (The current coal use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "China")]["Secondary Energy|Electricity|Coal"].median()))) \
                + "EJ/yr)",
                min_value=0.0,
                max_value=12.0,
                value=0.0,
                step=4.0,
                format="%.1f EJ/yr",
                key="coal_use_2030_China")
        
        st.slider('In the **rest of the world** (The current coal use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "RoW")]["Secondary Energy|Electricity|Coal"].median()))) \
                + "EJ/yr)",
                min_value=0.0,
                max_value=4.0,
                value=0.0,
                step=1.0,
                format="%.1f EJ/yr",
                key="coal_use_2030_RoW")
    with col_r:
        st.write("#### Feasible **maximum** of solar power used for electricity generation in 2030:")
        st.slider('In **OECD** (The current solar use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "OECD")]["Secondary Energy|Electricity|Solar"].median()))) \
                + "EJ/yr)",
                    min_value = 8.0,
                    max_value = 14.0,
                    value = 14.0,
                    step = 2.0,
                    format="%.1f EJ/yr",
                    key = 'solar_use_2030_OECD')
        st.slider('In **China** (The current solar use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "China")]["Secondary Energy|Electricity|Solar"].median()))) \
                + "EJ/yr)",
                min_value=6.0,
                max_value=12.5,
                value=12.5,
                step=2.0,
                format="%.1f EJ/yr",
                key="solar_use_2030_China")
        
        st.slider('In the **rest of the world** (The current solar use is about ' \
                + str(round(float(df[(df["year"] == 2020) & (df["region"] == "RoW")]["Secondary Energy|Electricity|Solar"].median()))) \
                + "EJ/yr)",
                min_value=8.0,
                max_value=16.0,
                value=16.0,
                step=2.0,
                format="%.1f EJ/yr",
                key="solar_use_2030_RoW")

    #filter dataframe
    ##conditions
    con_1 = to_plot_df.loc[to_plot_df['region'] == "OECD", 'coal_use_2030'] >= st.session_state['coal_use_2030_OECD']
    con_2 = to_plot_df.loc[to_plot_df['region'] == "China", 'coal_use_2030'] >= st.session_state['coal_use_2030_China']
    con_3 = to_plot_df.loc[to_plot_df['region'] == "RoW", 'coal_use_2030'] >= st.session_state['coal_use_2030_RoW']
    condition_coal = pd.concat([con_1, con_2, con_3]).sort_index() #the less coal, the larger scenario space

    con_1 = to_plot_df.loc[to_plot_df['region'] == "OECD", 'solar_use_2030'] <= st.session_state['solar_use_2030_OECD']
    con_2 = to_plot_df.loc[to_plot_df['region'] == "China", 'solar_use_2030'] <= st.session_state['solar_use_2030_China']
    con_3 = to_plot_df.loc[to_plot_df['region'] == "RoW", 'solar_use_2030'] <= st.session_state['solar_use_2030_RoW']
    condition_solar = pd.concat([con_1, con_2, con_3]).sort_index() #the more solar, the larger scenario space

    #filter on conditions
    filter_df_region = to_plot_df[to_plot_df["region"] != "World"].loc[condition_coal & condition_solar]
   
    #METRICS // calculate "consequences" of input
    #required coal reduction compared to 2020 median in percent
    required_coal_reduction_2030_OECD = round(
    100 - \
    (float(st.session_state['coal_use_2030_OECD']) / \
            round(float(df[(df["year"] == 2020) & (df["region"] == "OECD")]["Secondary Energy|Electricity|Coal"].median())) *\
            100))

    required_solar_upscale_2030_OECD = round(
    float(st.session_state['solar_use_2030_OECD']) / \
            round(float(df[(df["year"] == 2020) & (df["region"] == "OECD")]["Secondary Energy|Electricity|Solar"].median())) *\
            100)

    #only report on global net zero 
    #drop year_netzero column
    filter_df_region.drop(columns=["year_netzero"], inplace=True)
    #add global netzero column
    filter_df_region = pd.merge(left=filter_df_region, 
                                right=to_plot_df[to_plot_df['region'] == "World"][['model', 'scenario', 'year_netzero']],
                                on = ["model", "scenario"])
    #rename year_netzero to year_netzero_global
    filter_df_region.rename(columns={"year_netzero": "year_netzero_global"}, inplace=True)
    #Dealing with scenarios that never reach net_zero
    if pd.to_numeric(filter_df_region["year_netzero_global"], errors="coerce").notna().sum() != 0: #as long as there are numbers, display the lowest value
        earliest_net_zero_year = filter_df_region[pd.to_numeric(filter_df_region["year_netzero_global"], errors="coerce").notna()]["year_netzero_global"].min() #filter only to numeric values
    else: #display disclaimer
        earliest_net_zero_year = "not within this century"
    
    if filter_df_region.empty:
        st.write("Chosen values out of scenario space! Please chose another input combination.")
    else:
        #FIGURES
        #filter data on reduction year
        #TODO rename dataframe to filter_df_region
        filter_df = filter_df_region[filter_df_region['reduction_year'] == "2030_CO2_redu"]
        # Define color mapping for models
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
        
        #set order of regions in plot
        region_order = ["OECD", "China", "RoW"]
        #set order of scenario_narratives for plot
        filter_df["scenario_narrative"] = pd.Categorical(filter_df["scenario_narrative"], categories=["Cost Effective", "Instit"])
        filter_df = filter_df.sort_values(by="scenario_narrative")

        fig = make_subplots(rows=1, cols=len(region_order), shared_yaxes=True)

        for i, region_ in enumerate(region_order):
            box_trace = go.Box(
                x=filter_df[(filter_df["region"] == region_)]["scenario_narrative"],
                y=filter_df[(filter_df["region"] == region_)]["reduction_value"],
                name="Boxplot",
                boxpoints=False,
                marker_color='grey',
                opacity=0.3,
                showlegend=False
            )

            fig.add_trace(box_trace, row=1, col=i + 1)

            # Add subplot titles
            fig.update_layout(
                annotations=[dict(text=str(year), 
                                  xref="x" + str(i + 1), yref="paper", x=0.5, y=1.1,
                                  showarrow=False) for i, year in enumerate(region_order)]
            )

            # Create a scatterplot for each model
            for model in filter_df["model"].unique():
                scatter_trace = go.Scatter(
                    x=filter_df[(filter_df["region"] == region_) & (filter_df["model"] == model)]["scenario_narrative"],
                    y=filter_df[(filter_df["region"] == region_) & (filter_df["model"] == model)]["reduction_value"],
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
            text="ENGAGE 2C scenarios <br><sup>Regional CO2 reductions by 2030 </sup>",
            xref="paper",
            x=0),
        #xaxis=dict(title="Scenario Narrative"),
        yaxis=dict(title="Necessary CO2 Reduction (%)", range=[-0.2, 0.6], tickformat="2%"),
        legend=dict(
            traceorder="normal",
            itemsizing="constant"
        )
    )
    fig.update_xaxes(title_text="Scenario Narrative", col=2)

    #print output
    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        st.write('### Regional Policy Implications')
        st.metric("Earliest possible global net-zero year:", earliest_net_zero_year)
    with col2:
        st.plotly_chart(fig, theme="streamlit")
