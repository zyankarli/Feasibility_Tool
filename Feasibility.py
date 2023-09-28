#Import libraries
import streamlit as st
import pyam
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from PIL import Image
from shillelagh.backends.apsw.db import connect
from google.oauth2 import service_account
import time

st.set_page_config(
     page_title='Feasibility of climate mitigation scenarios',
     initial_sidebar_state="collapsed",
     layout="wide")

#CCS HACKING
#hide menu and footer
hide_default_format = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       header {visibility: hidden;}
       </style>
       """
#uncomment to hide menu and footer
st.markdown(hide_default_format, unsafe_allow_html=True)

#hide fullscreen button for plots
hide_img_fs = '''
<style>
button[title="View fullscreen"]{
    visibility: hidden;}
</style>
'''
st.markdown(hide_img_fs, unsafe_allow_html=True)

#set font for text body
st.markdown("""
<style>
.body-font {
    font-family:Arial;
    font-size:18px;
    color: black;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

#CCS hack to make arrows of metrics disappear
st.write(
    """
    <style>
    [data-testid="stMetricDelta"] svg {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

#CCS links:
## https://discuss.streamlit.io/t/remove-or-reduce-spaces-between-elements/23283


@st.cache_resource #TODO: uncomment this again. Just so that I can always re-run automatically
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
            "T34_1000_bitb_em", # "feasible" scenarios
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
                "Other countries of Asia",
                "Countries of Sub-Saharan Africa",
                "Countries of Latin America and the Caribbean",
                "Countries of the Middle East; Iran, Iraq, Israel, Saudi Arabia, Qatar, etc.",
                "Countries from the Reforming Economies of Eastern Europe and the Former Soviet Union; primarily Russia"]
    )      
#TODO according to Elina Teams message, RoW is own category. Add?
    #return data format of df
    return df

df = get_data().data


##DATA WRANGLING
#get regional groupings
## OECD90+: "North America; primarily the United States of America and Canada","Eastern and Western Europe (i.e., the EU28)"
#TODO Clarify that countries of Asia and Latin America are missing
## China+:  Countries of centrally-planned Asia; primarily China
## Rest of the world: other countries
#get world
world = df[df['region'] == "World"]
world.loc[:, "region"] = "World"
#get OECD*
oecd = df[df["region"].isin(["North America; primarily the United States of America and Canada","Eastern and Western Europe (i.e., the EU28)", "Pacific OECD"])]\
    .groupby(["model", "scenario", "variable", "year", "unit"])\
        .agg({"value": "sum"}).reset_index()
oecd['region'] = "OECD90+"
#get China
china = df[df['region'] == "Countries of centrally-planned Asia; primarily China"]
china.loc[:, "region"] = "China+"
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
to_plot_df = df[(df['year'].isin([2020, 2030, 2040, 2050])) & (df["scenario"].isin(["T34_1000_ref", "T34_1000_bitb_em"]))] #without world filter




#calculate reductions
reductions_df = to_plot_df[["model", "scenario", "scenario_narrative", "region", 'year', "Emissions|CO2"]]
reductions_df = pd.pivot(data=reductions_df, index=reductions_df.drop(['year', "Emissions|CO2"], axis=1).columns, columns = 'year', values = 'Emissions|CO2').reset_index()
reductions_df["2030_CO2_redu"] = ( (reductions_df[2030] - reductions_df[2020]) / reductions_df[2020])
reductions_df["2040_CO2_redu"] = ((reductions_df[2040] - reductions_df[2020]) / reductions_df[2020]) 
reductions_df.drop([2020, 2030, 2040], axis=1, inplace=True)

#calculate capacities/usage for 2030
coal_use_2030 = pd.pivot(data=to_plot_df, index=['model','scenario', 'region'], columns = 'year', values = 'Secondary Energy|Electricity|Coal').reset_index()[['model', 'scenario', 'region', 2030]]
coal_use_2030.rename(columns={2030:"coal_use_2030"}, inplace=True)

solar_use_2030 = pd.pivot(data=to_plot_df, index=['model','scenario', 'region'], columns = 'year', values = 'Secondary Energy|Electricity|Solar').reset_index()[['model', 'scenario', 'region', 2030]]
solar_use_2030.rename(columns={2030:"solar_use_2030"}, inplace=True)

ccs_use_2030 = pd.pivot(data=to_plot_df, index=['model','scenario', 'region'], columns = 'year', values = 'Carbon Sequestration|CCS').reset_index()[['model', 'scenario', 'region', 2050]]
ccs_use_2030.rename(columns={2050:"ccs_use_2050"}, inplace=True) #unit 	Mt CO2/yr

#calculate year that each scenario hit's net zero
# netzero_df = df[df["Emissions|CO2"] <= 0].groupby(["model", "scenario", "region"])['year'].min().reset_index() #net-zero set to 0 CO2 emissions here
# #get all the scenarios that don't reach net_zero
# no_netzero_df = df[df["scenario"].isin(["T34_1000_ref", "T34_1000_govem", 'T34_NDC2100', 'T34_NPi2100'])][["model", "scenario", "region", "year", "Emissions|CO2"]]
# no_netzero_df["netzero_test"] = no_netzero_df["Emissions|CO2"] <= 0
# no_netzero_df = pd.DataFrame(no_netzero_df.groupby(["model", 'scenario', 'region'])["netzero_test"].sum()).reset_index()
# no_netzero_df = no_netzero_df[no_netzero_df["netzero_test"] == 0]
# no_netzero_df['netzero_test'] = "not within this century"
# no_netzero_df.rename(columns={"netzero_test": "year"}, inplace=True)
# #append no_net_zero to netzero 
# netzero_df = pd.concat([netzero_df, no_netzero_df])
# netzero_df.rename(columns={"year": "year_netzero"}, inplace=True)


#merge
to_plot_df = pd.merge(left=reductions_df, right=coal_use_2030, on=["model", "scenario", "region"])
to_plot_df = pd.merge(left=to_plot_df, right=solar_use_2030, on=["model", "scenario", "region"])
to_plot_df = pd.merge(left=to_plot_df, right=ccs_use_2030, on=["model", "scenario", "region"])
# to_plot_df = pd.merge(left=to_plot_df, right=netzero_df, on=["model", "scenario", "region"])


# #make CO2 reduction longer for plotting purposes
#reduce data
to_plot_df = pd.melt(to_plot_df, id_vars=["model", 'scenario', 'region', 'scenario_narrative', 'coal_use_2030','solar_use_2030', 'ccs_use_2050'],
                    value_vars=["2030_CO2_redu", "2040_CO2_redu"],
                    var_name='reduction_year', value_name='reduction_value')
#POLES ENGAGE model doesn't report CCS; set all it's NA values to 4000 so that it's still displayed in graph
to_plot_df['ccs_use_2050'] = to_plot_df['ccs_use_2050'].fillna(6000)


#NEW TEXT
#Title
st.markdown("""# What do feasibility constraints imply for short-term climate mitiation?""", unsafe_allow_html=True)
#Introduction
coll, colm, colr = st.columns([0.4, 0.6, 0.4])
with colm:
    st.markdown(
        """	
        ## Introduction
    
    <p class="body-font"> Integrated assessment models (IAMs) are a critical tool for climate mitigation planning and are often used to inform political decision making.
    IAMs are especially useful because they identify solutions to achieve a climate target given a wide range of constraints and technological details.
    As the usage of IAMs is mounting, critics point out that some of the reported trajectories, such as the speed of mitigation in certain regions or the scale up of certain technologies might not be feasible. For example, IAMs tend to place a majority
    of climate mitigation actions in regions outside of OECD+ and China+ as those have a large techno-economic mitigation potential. This is shown in the figure below. <br />
    </p>
        """
    , unsafe_allow_html=True)

    engage_image = Image.open("data/ENGAGE_result.png")
    st.image(engage_image,
             caption = "Cost effective scenarios place a large share of global climate mitigation action in world regions outside OECD90+ and China+. \
             Those regions are expected to decrease their CO2 emissions by 68% until 2050 compared to 2020. More information on the regional grouping is provided below.") 

    st.markdown(""" <p class="body-font">
                 How would the results of IAMs change if feasibility constraints were taken into account? 
                Please scroll down to find out!
    </p> """, unsafe_allow_html=True)
st.markdown("""****""")

coll, colm, colr = st.columns([0.4, 0.6, 0.2])
with coll:
    st.markdown(
        """
    ## Regions of specific interest

    <p class="body-font"> The OECD90+ countries and China+ are among the key regions in global mitigation efforts.
    They cover a substantial share of global emissions and have the capacity to develop and deploy novel technologies.
    Therefore, the results below highlight these two regions and compare them to the rest of the world (RoW).
    The table to the right shows the regional grouping that was used to derive those three regions. <br />
    </p>
    """
    , unsafe_allow_html=True)
with colm:
    #import images
    regions_image = Image.open("data/IAM_regions.png")
    st.image(regions_image)
    
    st.markdown(
        """
    <p class="body-font"> 
    """
    , unsafe_allow_html=True)

st.markdown("""****""")

coll, colm, colr = st.columns([0.4, 0.2, 0.2])
with coll:
    st.markdown("""
                ## Feasibility concerns

                <p class="body-font"> 
                On the technical side, feasibility constraints incorporate upper bounds on how fast low carbon and carbon removal technologies can be upscaled.
                On the institutional side, feasibility constraints take into account that certain regions might not have the capacity to implement fast emissions reductions. 
                Regional heterogeneity is introduced by carbon price differentiation and upper bounds on decadal emission reductions.
                8 different IAMs explore global climate mitigation scenarios in a feasibility constrained as well as in a default, cost-effective setting.
                You can adjust the sliders to the right to explore how your personal feasiblity concerns are aligned with the modelled scenarios. 
                The metrics next to the figure provide you with an immediate feedback on your choices. </br>
                </p>
                <font size="3px"> <i> The intial settings of sliders is chosen is such a way, that all model findings are included. <i />            
                """
                , unsafe_allow_html=True)


with colm:
        st.markdown(""" <br /> <br /> """, unsafe_allow_html=True) 
        st.markdown("""What is the feasible **minimum** of coal used globally for electricity generation in 2030?""", unsafe_allow_html=False)
        st.markdown("""What is the feasible **maximium** of global solar power used globally for elecricity generation in 2030?""", unsafe_allow_html=False)
        st.markdown("""What is the feasible **maximium** of global CCS deployment in 2050?""", unsafe_allow_html=False)

with colr:
    st.markdown(""" <br /> <br />""", unsafe_allow_html=True) 
    st.slider(
        label="", 
        min_value = 1,
        max_value = 20,
        value = 1,
        step = 5,
        format="%.0f EJ/yr",
        key = "coal_use_2030_world", 
        label_visibility="collapsed")
    
    st.slider('What is the feasible **maximium** of global solar power used globally for elecricity generation in 2030? (The global coal use in 2020 was about ' \
    + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Solar"].median()))) \
    + "EJ/yr)",
        min_value = 15,
        max_value = 40,
        value = 40,
        step = 5,
        format="%.0f EJ/yr",
        key = 'solar_use_2030_world', 
        label_visibility="collapsed")
    
    st.slider('What is the feasible **maximium** of global CCS deployment in 2050? (The global deployment in 2020 was about ' \
    + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Carbon Sequestration|CCS"].median()))) \
    + "Mt CO2/yr)",
        min_value = 4000,
        max_value = 12100,
        value = 12100,
        step = 2000,
        format="%.0f Mt CO2/yr",
        key = 'ccs_use_2050_world', 
        label_visibility="collapsed")
    

    


#count number of unique models are still in filter_df_world
#filter_df_world[(filter_df_world["reduction_year"] == '2030_CO2_redu')].groupby('scenario')['model'].nunique()

# st.write("The current choice implies a reduction of coal consumption by "+
#         str(round(100 - (float(st.session_state['coal_use_2030_world']) / \
#                                 round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Coal"].median())) *100)))+
#         "%")
# st.slider('What is the feasible **maximium** of global solar power used globally for elecricity generation in 2030? (The global coal use in 2020 was about ' \
#     + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Solar"].median()))) \
#     + "EJ/yr)",
#         min_value = 15,
#         max_value = 40,
#         value = 40,
#         step = 5,
#         format="%.1f EJ/yr",
#         key = 'solar_use_2030_world')
# st.slider('What is the feasible **maximium** of global CCS deployment in 2050? (The global deployment in 2020 was about ' \
#     + str(round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Carbon Sequestration|CCS"].median()))) \
#     + "Mt CO2/yr)",
#         min_value = 2000,
#         max_value = 12100,
#         value = 12100,
#         step = 2000,
#         format="%.1f Mt CO2/yr",
#         key = 'ccs_use_2050_world')

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

#set color mapping for figure to come
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

#set plotly configuarations
config = {'displayModeBar': False}
font_size_title = 22
font_size_axis = 16

if filter_df_world.empty:
    st.write("Chosen values out of scenario space! Please chose another input combination.")
else:
#FIGURES
    # Map colors based on the "model" column
    filter_df_world["color"] = filter_df_world["model"].map(color_mapping)

    #change values of columns for nicer display
    filter_df_world['scenario_narrative'] = filter_df_world['scenario_narrative'].replace({"Cost Effective": "Cost Effective", "Tech+Inst": "Feasibility Constraint"})
    filter_df_world["reduction_year"] = filter_df_world["reduction_year"].replace({"2030_CO2_redu": "2030", "2040_CO2_redu": "2040"})
    #set order of scenario_narratives for plot
    filter_df_world["scenario_narrative"] = pd.Categorical(filter_df_world["scenario_narrative"], categories=["Cost Effective", "Feasibility Constraint", "NDC", "Current Policy"])
    filter_df_world["reduction_year"] = pd.Categorical(filter_df_world["reduction_year"], categories=["2030", "2040"])
    filter_df_world["model"] = pd.Categorical(filter_df_world["model"], categories=["AIM/CGE V2.2", "COFFEE 1.5", "GEM-E3_V2023", "IMAGE 3.2", "MESSAGEix-GLOBIOM_1.1", "POLES ENGAGE", "REMIND 3.0", "WITCH 5.0"])
    filter_df_world = filter_df_world.sort_values(by=["reduction_year","scenario_narrative", "model"])
    #filter out NDC and Current policy
    filter_df_world = filter_df_world[~filter_df_world["scenario_narrative"].isin(["NDC", "Current Policy"])]

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
            annotations=[dict(text=str(year), xref="x" + str(i + 1), yref="paper", x=0.5, y=1, font= dict(size=22), showarrow=False) for i, year in enumerate(filter_df_world["reduction_year"].unique())]
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
            # Set tickfont for xaxis
            fig_world.update_xaxes(tickfont=dict(size=font_size_axis), row=1, col=i + 1)
            #

    fig_world.update_layout(
        title = go.layout.Title(
            text="ENGAGE 2C scenarios <br><sup>Global CO2 reductions by 2030 and 2040 compared to 2020</sup>",
            xref="paper",
            x=0, 
            font=dict(size=font_size_title)
        ),
        yaxis=dict(title="relative reductions compared to 2020", range=[-0.6, 0], tickfont=dict(size=font_size_axis)),

        legend=dict(
        traceorder="normal",
        itemsizing="constant",
        font = dict(size = 18)
        )
        ,
        height=600,  # Change this value to your desired height in pixels
        width=1000   # Change this value to your desired width in pixels
    )

coll, colm, colr = st.columns([0.6, 0.1, 0.25], gap="small")


with colr:
    st.write("")
    st.markdown("""<p class="body-font"> <b>Your current choice implies:<b> </p>""", unsafe_allow_html=True)
    
    #get model count for each scenario // better solution than radio because only scenario count changes
    n_cost_eff = filter_df_world[filter_df_world['scenario_narrative'] == 'Cost Effective']['model'].nunique()
    n_feasi = filter_df_world[filter_df_world['scenario_narrative'] == 'Feasibility Constraint']['model'].nunique()
    st.metric('Number of models finding scenarios to stay below 2C',
            value = filter_df_world['model'].nunique(), 
            delta = '{cost_eff} cost effective / {feasi}  feasibility constrained'.format(cost_eff=n_cost_eff, feasi=n_feasi), 
            delta_color="off")          
    st.metric('Global reduction of coal comsumption by 2030', 
        value = str(round(100 - (float(st.session_state['coal_use_2030_world']) / \
                    round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Coal"].median())) *100))) + "%")
    st.metric('Global solar power increase by 2030', 
            value = str(round(100 - (float(st.session_state['solar_use_2030_world']) / \
                        round(float(df[(df["year"] == 2020) & (df["region"] == "World")]["Secondary Energy|Electricity|Solar"].median())) *-100))) + "%")        
    #According to State of CDR report 2023, in 2020 only 2Mt CO2/yr were sequestered globally using CCS (DACCS and BECCS together)
    st.metric('Global fractional increase of global CCS deployment by 2050', 
                        value = str(str(int(st.session_state['ccs_use_2050_world']/2)) + "x times more")) #TODO median absolute CCS deployment by 2050

with coll:
    #only plot if filter_df_world is not empty
    if filter_df_world.empty != True:
        st.plotly_chart(fig_world, theme="streamlit", config=config)


coll, colm, colr = st.columns([0.4, 0.6, 0.4])
with colm:
    st.markdown("""
    ### Key takeaway for global CO2 reductions

    <p class="body-font">
                \u2714 Considering feasibility constraints reduces the uncertainty of future emission reductions, as indicated by shorter boxplots. </li></p>
    """,
unsafe_allow_html=True) 


st.markdown("""****""")


coll, colm, colr = st.columns([0.4, 0.6, 0.4])
with colm:
    st.markdown(
        """	
        ## Effects on short-term CO2 reduction
    
    <p class="body-font"> Let's now look at the difference between the conventional, cost-effective scenarios and the set of scenarios 
    that consider institutional feasibility. All scenarios aim to limit the increase of average global temperature to around 2C compared to pre-industrial times.
    The figure below shows the difference in CO2 emissions between these two scenarios.
    Colored lines are the delta-values for each model, the black line is the median of all models.
    </p>
        """
    , unsafe_allow_html=True)
#----------------------------#
#  prepare data for plotting #
#----------------------------#
#from df, get the difference between Cost Effective and Instit for all years and each model and call it delta
# filter relevant columns
to_plot = df[(df['scenario'].isin(["T34_1000_bitb_em", "T34_1000_ref"])) & (df['year'] >= 2020) & (df['year'] <= 2050) & (df['region'] != "World")]
# pivot to wide format
to_plot = pd.pivot(data=to_plot, index=['model','region', "year"], columns = 'scenario', values = 'Emissions|CO2').reset_index()
# calculate delta between all years
to_plot['delta'] = to_plot['T34_1000_bitb_em'] - to_plot['T34_1000_ref']

#set order for plot
region_order = ['OECD90+', 'China+', 'RoW']
to_plot['region'] = pd.Categorical(to_plot['region'], categories=region_order)

#drop rows with delta value of zero (only COFFEE)
#to_plot = to_plot[to_plot['delta'] != 0]

#add color mapping to to_plot
to_plot['color'] = to_plot['model'].map(color_mapping)

#add trendline to line_fig that shows median of all models
#calculate median of all models
median_df = to_plot.groupby(['year', 'region'])['delta'].median().reset_index()


color_mapping = {
'OECD90+': "rgb(255, 0, 0)",
'China+': "rgb(0, 255, 0)",
'RoW': "rgb(0, 0, 255)"
}

subplots = make_subplots(rows=1, cols=len(region_order), subplot_titles=region_order)

for i, region in enumerate(region_order, 1):
    region_data = to_plot[to_plot['region'] == region]
    
    for model in region_data['model'].unique():
        model_data = region_data[region_data['model'] == model]
        
        subplot_title = f"Delta - {region} - {model}"
        
        subplots.add_trace(
            go.Scatter(
                x=model_data['year'],
                y=model_data['delta'],
                mode='lines',
                line=dict(color=color_mapping[region], width=2, dash='solid'),
                name=subplot_title,
                showlegend= False,
                hovertemplate = f"{model} <extra></extra>"
            ),
            row=1,
            col=i
        )
    subplots.add_trace(
        go.Scatter(
        x=median_df[median_df['region'] == region]['year'],
        y=median_df[median_df['region'] == region]['delta'],
        mode='lines',
        line=dict(color='black', width=4, dash='solid'),
        showlegend=False, 
        hoverinfo = 'skip'
        ),
    row=1, col=i,
    )

       # Add horizontal line at y=0
    subplots.add_shape(
        type="line",
        x0=2020,
        y0=0,
        x1=2050,
        y1=0,
        line=dict(color="grey", width=2, dash="dash"),
        row=1,
        col=i
    )
    
    # Add text annotation above the line
    subplots.add_annotation(
        xref="paper",
        yref="paper",
        x=0.85,
        y=0.43,
        text="CO2 emission reductions <br> in cost-effective scenarios </br> are the baseline",
        showarrow=True,
        arrowhead=1,
        arrowcolor="grey",
        ax=0,
        ay=40,
        font=dict(size=16)
    )

    #set x-ticks size
    subplots.update_xaxes(tickfont=dict(size = font_size_axis), row=1, col=i)
    #set subtitles size
    subplots.update_annotations(font_size=18)

#ensure that subplots have same y-axis
subplots.update_yaxes(matches='y')
#ensure that only first plot has y-axis labels
subplots.update_yaxes(title_text="CO2 Emissions (Mt CO2/yr)", row=1, col=1)
#delete y-axis labels for second and third plot
subplots.update_yaxes(showticklabels=False, row=1, col=2, #set font size
                      )
subplots.update_yaxes(showticklabels=False, row=1, col=3, 
                      tickfont=dict(size=font_size_axis))
subplots.update_layout(
    title = go.layout.Title(
        text="Difference of CO2 emissions to reach a 2C target <br><sup> between cost effective and feasibility constrained scenarios </sup>",
        x=0, 
        xanchor = 'left',
        yanchor = 'top',
        font = dict(size = font_size_title)),
    yaxis=dict(title="Mt CO2/yr", tickfont=dict(size=font_size_axis)),
    #yaxis=dict(title="", range=[-0.2, 0.6]),
    # legend=dict(
    #     traceorder="normal",
    #     itemsizing="constant"
    # ),
    height=800,  # Change this value to your desired height in pixels
    width=1200   # Change this value to your desired width in pixels
    )



coll, colm, colr = st.columns([0.2, 0.6, 0.2])
with colm:
    st.plotly_chart(subplots, theme="streamlit", config=config, use_container_width=True)

coll, colm, colr = st.columns([0.4, 0.6, 0.4])
with colm:
    st.markdown(""" <p class="body-font"> <b>Feasibility-updated CO2 net-zero years:</b> </p>""", unsafe_allow_html=True)


coll, colm1, colm2, colm3, colr = st.columns([0.4, 0.2, 0.2, 0.2, 0.4])
with colm1:
    st.metric("For OECD90+",
              value="2045",
              delta="5 years earlier",
              delta_color="inverse")
with colm2:
    st.metric("For China+",
                value="2050",
                delta="10 years earlier",
                delta_color="inverse")
with colm3:
    st.metric("For RoW",
                value="2070")

coll, colm, colr = st.columns([0.4, 0.6, 0.4])
with colm: # "&nbsp;" could be used to insert white spaces manually
    st.markdown("""
    ### Key takeaways for regional CO2 emission reductions

    <p class="body-font"> 
        \u2714 OECD90+ countries are required to significantly increase their short term 
        mitigation actions. Compared to the cost-effective scenarios, feasibility constraint scenarios require OECD90+ countries to reduce their
               CO2 emissions by additional 26% by 2040. </br> 
        \u2714 China+'s mitigation effort needs to increase from 2040 onwards.</br>
         The region is expected to reduce around 10% more (median) of its CO2 emissions
         until 2050 compared to a cost-effective scenario. </br>
        \u2714 The Rest of the World is expected to have lower CO2 reductions compared to a cost-effective scenario.
          CO2 emissions reductions in these regions are expected to be around 20% lower (median) when considering feasibility constraints.
        </p>
    """,
unsafe_allow_html=True) 


st.markdown("""****""")

coll, colm, colr = st.columns([0.4, 0.6, 0.4])
with colm:
    st.markdown(""" <br /> <br /> <br />""", unsafe_allow_html=True) 
    st.markdown("""
    <p class = "body-font"> Implications of those findings for temperature/ climate goals will be added soon. </p>
    """,unsafe_allow_html=True)

st.markdown("""****""")

st.markdown(""" <br /> <br /> <br />""", unsafe_allow_html=True) 

coll, colm, colr = st.columns([0.4, 0.6, 0.4])
with colm:
    st.markdown("## Publications")
    st.markdown(""" <p class = "body-font"> 
            The presented results are based on scenario design as described in Bertram et al. (in preparation).
            The regional level figures and feasibility indicators are based on Brutschin et al. (in preparation) and Brutschin et al. (2021). </br>
            These papers as well as this web app are part of the <a href="https://iiasa.ac.at/projects/engage">international ENGAGE project</a> funded by the European Commission’s Horizon 2020 research and innovation programme under grant agreement No 821471. </p>""", unsafe_allow_html=True)

coll, colm, colr = st.columns([0.5, 0.33, 0.33])
with colm:
    ENGAGE_logo = Image.open("data/ENGAGE_logo.png")
    st.image(ENGAGE_logo)


#-------------------------#
# GOOGLE SHEET CONNECTION #
#-------------------------#

#prepare google sheet connection
sheet_url = st.secrets["private_gsheets_url"]

def create_connection():
        credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=["https://www.googleapis.com/auth/spreadsheets",],)
        connection = connect(":memory:", adapter_kwargs={
            "gsheetsapi" : { 
            "service_account_info" : {
                "type" : st.secrets["gcp_service_account"]["type"],
                "project_id" : st.secrets["gcp_service_account"]["project_id"],
                "private_key_id" : st.secrets["gcp_service_account"]["private_key_id"],
                "private_key" : st.secrets["gcp_service_account"]["private_key"],
                "client_email" : st.secrets["gcp_service_account"]["client_email"],
                "client_id" : st.secrets["gcp_service_account"]["client_id"],
                "auth_uri" : st.secrets["gcp_service_account"]["auth_uri"],
                "token_uri" : st.secrets["gcp_service_account"]["token_uri"],
                "auth_provider_x509_cert_url" : st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url" : st.secrets["gcp_service_account"]["client_x509_cert_url"],
                }
            },
        })
        return connection.cursor()
#------------------------------------------------------------------------------#


feedback_question = st.text_input("Feed me feedback", placeholder="Please enter your feedback here", 
                            key=1)
timestamp = time.time()

#Submit button; send data to google sheet
submitted = st.form_submit_button("Click here to submit!")
if submitted:
    cursor = create_connection()
    query = f'INSERT INTO "{sheet_url}" VALUES ("{feedback_question}", "{timestamp}")'
    cursor.execute(query)
    st.write("**:green[Submission successful. Thank you for your input!]**")
    st.toast("**:green[Submission successful!]**", icon=None)