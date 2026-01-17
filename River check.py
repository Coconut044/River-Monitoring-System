import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model
from datetime import datetime, timedelta
import os
from sklearn.preprocessing import MinMaxScaler
import altair as alt
import matplotlib.dates as mdates
import folium
from streamlit_folium import folium_static
import google.generativeai as genai
from matplotlib import gridspec
from matplotlib.patches import Arc

st.set_page_config(layout="wide")

# Configuration
GOOGLE_MAPS_API_KEY = 'AIzaSyAPrWcu3ZI4jr5hKinGTgXmdMqlubKfOzg'
LOCATIONS = {
    'ALAKNANDA A/C WITH BHAGIRATHI AT DEVPRAYAG': {
        'file_path': r"Devprayag_NEW.csv",
        'lat': 30.140504,
        'lon': 78.597358
    },
    'GANGA AT HARIDWAR D/S, UPPER GANGA CANAL D/S BALKUMARI MANDIR, AJEETPUR, HARIDWAR ': {
        'file_path': r"Haridwar_NEW.csv",
        'lat': 29.945254,
        'lon': 78.164675
    },
    'GANGA AT KANNAUJ U/S (RAJGHAT), U.P': {
        'file_path': r"Kannauj_NEW.csv",
        'lat': 27.010953,
        'lon': 79.986442
    },
    'GANGA AT ALLAHABAD D/S (SANGAM), U.P': {
        'file_path': r"GHAZIPUR_NEW.csv",
        'lat': 25.419206,
        'lon': 81.900522
    },
    'GANGA AT TRIGHAT (GHAZIPUR), U.P': {
        'file_path': r"Prayagraj_NEW.csv",
        'lat': 25.578175,
        'lon': 83.609594
    },
    'GANGA AT GULABI GHAT, PATNA': {
        'file_path': r"Patna_NEW.csv",
        'lat': 25.620356,
        'lon': 85.179995
    },
    'KOLKATA, WEST BENGAL ': {
        'file_path': r"Howrah_NEW.csv",
        'lat': 22.632682,
        'lon': 88.355369
    }  
}

WEATHER_API_KEY = '5f25b8309c72e6259b8b47115ea3f47c'

def create_satellite_map(latitude, longitude):
    """
    Create a Folium map with satellite view for a given location
    """
    # Create a map centered on the location with satellite view
    m = folium.Map(
        location=[latitude, longitude], 
        zoom_start=13,
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&hl=en',
        attr='Google Satellite'
    )
    
    # Add a marker for the exact location
    folium.Marker(
        [latitude, longitude],
        popup='Monitoring Location',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    return m

def parse_date(date_str):
    """
    Flexible date parsing function to handle different date formats
    """
    date_formats = [
        '%d-%m-%Y',   # Day-Month-Year (13-01-2020)
        '%m-%d-%Y',   # Month-Day-Year (01-13-2020)
        '%Y-%m-%d',   # Year-Month-Day (2020-01-13)
        '%d/%m/%Y',   # Day/Month/Year (13/01/2020)
        '%m/%d/%Y',   # Month/Day/Year (01/13/2020)
    ]
    
    for fmt in date_formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue
    
    # If no format works, raise an error
    raise ValueError(f"Unable to parse date: {date_str}")

def prepare_input_data(historical_data, weather_forecast, parameter):
    """
    Prepare input data for model prediction with fixed sequence length
    """
    # Ensure 'Date' column is in datetime format
    historical_data['Date'] = historical_data['Date'].apply(parse_date)
    historical_data = historical_data.dropna(subset=['Date'])
    historical_data.set_index('Date', inplace=True)
    
    # Get the last 10 days of data
    last_10_days = historical_data[parameter].tail(10)
    
    # Ensure we have exactly 5 forecast points
    if len(weather_forecast) < 5:
        # Pad with the last forecast values if not enough
        while len(weather_forecast) < 5:
            last_forecast = weather_forecast[-1]
            weather_forecast.append({
                'date': last_forecast['date'] + timedelta(days=1),
                'temperature': last_forecast['temperature'],
                'rainfall': last_forecast['rainfall']
            })
    elif len(weather_forecast) > 5:
        # Trim to first 5 forecasts
        weather_forecast = weather_forecast[:5]
    
    # Prepare exogenous variables
    temps = [w['temperature'] for w in weather_forecast]
    rainfalls = [w['rainfall'] for w in weather_forecast]
    
    # Scale the time series data
    param_scaler = MinMaxScaler()
    scaled_data = param_scaler.fit_transform(last_10_days.values.reshape(-1, 1))
    
    # Scale exogenous variables separately
    temp_scaler = MinMaxScaler()
    rainfall_scaler = MinMaxScaler()
    
    scaled_temps = temp_scaler.fit_transform(np.array(temps).reshape(-1, 1))
    scaled_rainfalls = rainfall_scaler.fit_transform(np.array(rainfalls).reshape(-1, 1))
    
    # Combine scaled exogenous variables
    scaled_exogenous = np.column_stack([scaled_temps.flatten(), scaled_rainfalls.flatten()])
    
    # Reshape sequences
    X = scaled_data.reshape(1, 10, 1)  # Time series input
    X_exo = scaled_exogenous.reshape(1, 5, 2)  # Exogenous variables
    
    return X, X_exo, param_scaler, last_10_days, temp_scaler, rainfall_scaler

def fetch_weather_forecast(location, start_date):
    location_coords = {
        'ALAKNANDA A/C WITH BHAGIRATHI AT DEVPRAYAG': {'lat': 30.140504,'lon': 78.597358},
        'GANGA AT HARIDWAR D/S, UPPER GANGA CANAL D/S BALKUMARI MANDIR, AJEETPUR, HARIDWAR': {'lat': 29.945254,'lon': 78.164675},
        'GANGA AT KANNAUJ U/S (RAJGHAT), U.P':{'lat': 27.010953,'lon': 79.986442},
        'GANGA AT ALLAHABAD D/S (SANGAM), U.P':{'lat': 25.419206,'lon': 81.900522},
        'GANGA AT TRIGHAT (GHAZIPUR), U.P':{'lat': 25.578175,'lon': 83.609594},
        'GANGA AT GULABI GHAT, PATNA':{'lat': 25.620356,'lon': 85.179995},
        'KOLKATA, WEST BENGAL':{'lat': 22.5726,'lon': 88.3639},
    }
    
    try:
        coords = location_coords[location]
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        # Group forecasts by date and calculate max temperature
        forecasts_by_date = {}
        for forecast in data['list']:
            forecast_date = datetime.fromtimestamp(forecast['dt']).date()
            
            if forecast_date >= start_date.date():
                temp = forecast['main']['temp']
                rainfall = forecast.get('rain', {}).get('3h', 0) or 0

                if forecast_date not in forecasts_by_date:
                    forecasts_by_date[forecast_date] = {
                        'date': datetime.combine(forecast_date, datetime.min.time()),
                        'temperature': temp,
                        'rainfall': rainfall
                    }
                else:
                    # Update max temperature and add rainfall
                    forecasts_by_date[forecast_date]['temperature'] = max(forecasts_by_date[forecast_date]['temperature'], temp)
                    forecasts_by_date[forecast_date]['rainfall'] += rainfall

        # Convert to list and limit to 5 forecasts
        forecasts = list(forecasts_by_date.values())
        
        # Ensure exactly 5 forecasts
        while len(forecasts) < 5:
            last_forecast = forecasts[-1]
            forecasts.append({
                'date': last_forecast['date'] + timedelta(days=1),
                'temperature': last_forecast['temperature'],
                'rainfall': last_forecast['rainfall']
            })
        
        return forecasts[:5]
    except Exception as e:
        st.error(f"Error fetching weather data: {e}")
        # Generate dummy forecasts if API fails
        dummy_forecasts = [
            {
                'date': start_date + timedelta(days=i+1),
                'temperature': 25.0,  # Default temperature
                'rainfall': 0.0  # Default rainfall
            } for i in range(5)
        ]
        return dummy_forecasts


def create_altair_forecast_plot(historical_data, forecast_data, parameter):
    """
    Create an Altair plot showing historical and forecasted data
    """
    # Convert index to datetime if it's not already
    if not isinstance(historical_data.index, pd.DatetimeIndex):
        historical_data.index = pd.to_datetime(historical_data.index)
    
    # Prepare historical data
    historical_df = pd.DataFrame({
        'Date': historical_data.index,
        'Value': historical_data.values,
        'Type': 'Historical'
    })
    
    # Prepare forecast data
    forecast_dates = [historical_data.index[-1] + timedelta(days=i+1) for i in range(len(forecast_data))]
    forecast_df = pd.DataFrame({
        'Date': forecast_dates,
        'Value': forecast_data,
        'Type': 'Forecast'
    })
    
    # Combine historical and forecast data
    combined_df = pd.concat([historical_df, forecast_df])
    
    # Create the Altair chart
    chart = alt.Chart(combined_df).mark_line(point=True).encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('Value:Q', title=parameter),
        color=alt.Color('Type:N', 
            scale=alt.Scale(domain=['Historical', 'Forecast'], 
                            range=['steelblue', 'red']),
            legend=alt.Legend(title='Data Type')
        ),
        tooltip=['Date:T', 'Value:Q', 'Type:N']
    ).properties(
        title=f'{parameter} - Historical and Forecast',
        width=700,
        height=400
    ).interactive()
    
    return chart

def load_model_for_parameter(parameter):
    """
    Load the pre-trained model for a specific water quality parameter.
    """
    parameter_model_paths = {
        "Biochemical Oxygen Demand": r"Biochemical_Oxygen_Demand_water_quality_lstm_model.keras",
        "Dissolved Oxygen": r"Dissolved_Oxygen_water_quality_lstm_model.keras",
        "pH": r"pH_water_quality_lstm_model.keras",
        "Turbidity": r"Turbidity_water_quality_lstm_model.keras",
        "Nitrate": r"Nitrate_water_quality_lstm_model.keras",
        "Fecal Coliform": r"Fecal_Coliform_water_quality_lstm_model.keras",
        "Fecal Streptococci": r"Fecal_Streptococci_water_quality_lstm_model.keras",
        "Total Coliform": r"Total_Coliform_water_quality_lstm_model.keras",
        "Conductivity": r"Conductivity_water_quality_lstm_model.keras"
    }
    model_path = parameter_model_paths.get(parameter)
    
    if model_path and os.path.exists(model_path):
        return load_model(model_path)
    else:
        st.error(f"Model for {parameter} not found.")
        return None


def create_altair_historical_plot(df, parameter):
    """
    Create an Altair plot of historical data
    """
    # Create the base chart
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y(f'{parameter}:Q', title=parameter),
        tooltip=['Date:T', f'{parameter}:Q']
    ).properties(
        title=f'Historical {parameter} Data',
        width=700,
        height=400
    ).interactive()
    
    return chart

GEMINI_API_KEY = 'AIzaSyAPrWcu3ZI4jr5hKinGTgXmdMqlubKfOzg'  # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

def generate_gemini_water_quality_report(parameter, forecasted_values, forecast_dates, historical_data):
    """
    Generate a detailed water quality report using Gemini API
    
    Args:
    parameter (str): Water quality parameter
    forecasted_values (list): Predicted values
    forecast_dates (list): Corresponding dates
    historical_data (pd.DataFrame): Historical water quality data
    
    Returns:
    str: Detailed water quality report from Gemini
    """
    # Prepare input context
    historical_stats = f"""
    Historical Data Statistics for {parameter}:
    - Mean: {historical_data[parameter].mean():.4f}
    - Standard Deviation: {historical_data[parameter].std():.4f}
    - Minimum: {historical_data[parameter].min():.4f}
    - Maximum: {historical_data[parameter].max():.4f}
    """
    
    # Format forecasted data
    forecast_details = "\n".join([
        f"Date: {date.strftime('%Y-%m-%d')}, Predicted Value: {value:.4f}"
        for date, value in zip(forecast_dates, forecasted_values)
    ])
    
    # Construct prompt for Gemini
    prompt = f"""
    Provide a comprehensive water quality report for {parameter} with the following details:

    {historical_stats}

    Forecasted Values:
    {forecast_details}

    For each forecast date, please analyze:
    1. Potential water quality implications
    2. Risk assessment
    3. Recommended actions
    4. Ecological impact
    5. Potential sources of variation

    Format the report with clear headings and provide actionable insights.
    """
    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generate report
        response = model.generate_content(prompt)
        
        return response.text
    
    except Exception as e:
        return f"Error generating report: {str(e)}"

# Integration in main Streamlit function
def append_gemini_report_to_streamlit(parameter, forecasted_values, forecast_dates, historical_data):
    """
    Generate and display Gemini-powered water quality report in Streamlit
    """
    st.markdown("## 🌊 AI-Powered Water Quality Insights")
    
    # Generate report
    gemini_report = generate_gemini_water_quality_report(
        parameter, 
        forecasted_values, 
        forecast_dates, 
        historical_data
    )
    
    # Display report
    st.markdown(gemini_report)
    
def get_status_details(value, parameter_data, selected_parameter):
    """
    Determine status based on ideal values and acceptable ranges for each parameter
    
    Args:
    value (float): Current forecast value
    parameter_data (pd.DataFrame): Historical data (not used in this implementation)
    selected_parameter (str): Current water quality parameter
    
    Returns:
    tuple: (status, color, risk_percentage)
    """
    # Define ideal ranges for each parameter
    parameter_ranges = {
        "Biochemical Oxygen Demand": {
            "ideal": (0, 3),  # mg/L (lower is better)
            "acceptable": (3, 5),
            "poor": (5, float('inf'))
        },
        "Dissolved Oxygen": {
            "ideal": (6, 8),  # mg/L (higher is better, but not too high)
            "acceptable": (4, 10),
            "poor": (0, 4)  # Also consider values > 10 as potentially problematic
        },
        "pH": {
            "ideal": (6.5, 8.5),
            "acceptable": (6.0, 9.0),
            "poor": (0, 6.0)  # Also consider values > 9.0 as poor
        },
        "Turbidity": {
            "ideal": (0, 5),  # NTU (lower is better)
            "acceptable": (5, 10),
            "poor": (10, float('inf'))
        },
        "Nitrate": {
            "ideal": (0, 10),  # mg/L (lower is better)
            "acceptable": (10, 20),
            "poor": (20, float('inf'))
        },
        "Fecal Coliform": {
            "ideal": (0, 100),  # MPN/100ml (lower is better)
            "acceptable": (100, 500),
            "poor": (500, float('inf'))
        },
        "Fecal Streptococci": {
            "ideal": (0, 100),  # MPN/100ml (lower is better)
            "acceptable": (100, 500),
            "poor": (500, float('inf'))
        },
        "Total Coliform": {
            "ideal": (0, 500),  # MPN/100ml (lower is better)
            "acceptable": (500, 5000),
            "poor": (5000, float('inf'))
        },
        "Conductivity": {
            "ideal": (150, 500),  # μS/cm
            "acceptable": (100, 800),
            "poor": (800, float('inf'))  # Also consider values < 100 as poor
        }
    }
    
    # Get ranges for the selected parameter
    ranges = parameter_ranges.get(selected_parameter, {
        "ideal": (0, 100),
        "acceptable": (0, 100),
        "poor": (0, 100)
    })
    
    # Determine status based on the parameter's ideal range
    if selected_parameter == "pH":
        # Special case for pH since it's not always "lower is better"
        if ranges["ideal"][0] <= value <= ranges["ideal"][1]:
            return "Low Risk", "green", 30
        elif ranges["acceptable"][0] <= value <= ranges["acceptable"][1]:
            return "Moderate Risk", "orange", 60
        else:
            return "High Risk", "red", 90
    elif selected_parameter == "Dissolved Oxygen":
        # Special case for DO since higher is generally better (up to a point)
        if ranges["ideal"][0] <= value <= ranges["ideal"][1]:
            return "Low Risk", "green", 30
        elif ranges["acceptable"][0] <= value <= ranges["acceptable"][1]:
            return "Moderate Risk", "orange", 60
        else:
            return "High Risk", "red", 90
    elif selected_parameter == "Conductivity":
        # Special case for conductivity which has an ideal range
        if ranges["ideal"][0] <= value <= ranges["ideal"][1]:
            return "Low Risk", "green", 30
        elif ranges["acceptable"][0] <= value <= ranges["acceptable"][1]:
            return "Moderate Risk", "orange", 60
        else:
            return "High Risk", "red", 90
    else:
        # For most parameters, lower values are better
        if value <= ranges["ideal"][1]:
            return "Low Risk", "green", 30
        elif value <= ranges["acceptable"][1]:
            return "Moderate Risk", "orange", 60
        else:
            return "High Risk", "red", 90

def make_donut(input_response, input_text, parameter, parameter_data, selected_parameter):
    """
    Create an Altair donut chart for water quality forecast visualization with text labels
    
    Args:
    input_response (float): The actual forecast value
    input_text (str): Label for the chart
    parameter (str): Water quality parameter for color selection
    parameter_data (pd.DataFrame): Historical dataframe
    selected_parameter (str): Current selected parameter
    
    Returns:
    alt.Chart: Altair donut chart
    """
    # Determine risk level and color
    status, risk_color, risk_percentage = get_status_details(
        input_response, parameter_data, selected_parameter
    )
    
    # Map status to user-friendly display text
    if status == "Low Risk":
        display_text = "Good"
    elif status == "Moderate Risk":
        display_text = "Moderate"
    else:  # High Risk
        display_text = "Bad"
    
    # Color mapping based on risk level
    color_map = {
        'Low Risk': ['#27AE60', '#12783D'],  # Green
        'Moderate Risk': ['#F39C12', '#875A12'],  # Orange
        'High Risk': ['#E74C3C', '#FAF9F6']  # Red
    }
    
    chart_color = color_map.get(status, color_map['Moderate Risk'])
    
    # Prepare data for donut chart
    source = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100 - risk_percentage, risk_percentage]
    })
    
    # Background donut (full circle)
    source_bg = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100, 0]
    })
    
    # Create base donut chart
    plot = alt.Chart(source).mark_arc(
        innerRadius=45, 
        cornerRadius=25
    ).encode(
        theta="% value",
        color=alt.Color(
            "Topic:N", 
            scale=alt.Scale(
                domain=[input_text, ''],
                range=chart_color
            ),
            legend=None
        )
    ).properties(width=130, height=130)
    
    # Add text overlay - show quality classification instead of numeric value
    text = alt.Chart(source).mark_text(
        align='center', 
        color=chart_color[0], 
        font="Arial", 
        fontSize=16, 
        fontWeight='bold'
    ).encode(
        text=alt.value(display_text)
    ).properties(width=130, height=130)
    
    # Add small subtitle with actual value
    value_text = alt.Chart(source).mark_text(
        align='center', 
        color=chart_color[0], 
        font="Arial", 
        fontSize=10,
        dy=20  # Position below the main text
    ).encode(
        text=alt.value(f'{input_response:.2f}')
    ).properties(width=130, height=130)
    
    # Background donut chart
    plot_bg = alt.Chart(source_bg).mark_arc(
        innerRadius=45, 
        cornerRadius=20
    ).encode(
        theta="% value",
        color=alt.Color(
            "Topic:N", 
            scale=alt.Scale(
                domain=[input_text, ''],
                range=chart_color
            ),
            legend=None
        )
    ).properties(width=130, height=130)
    
    # Combine charts
    return plot_bg + plot + text + value_text


def apply_advanced_styling():
    st.markdown("""
    <style>
    /* Advanced Color Palette */
    :root {
        --primary-blue: #0A2342;       /* Deep Navy */
        --secondary-blue: #1F4287;     /* Rich Ocean Blue */
        --accent-blue: #4ECDC4;        /* Vibrant Aqua */
        --soft-background: #F7F9FC;    /* Soft Cloud Background */
        --water-gradient: linear-gradient(135deg, #1F4287, #4ECDC4);
        --card-gradient: linear-gradient(135deg, rgba(31, 66, 135, 0.05), rgba(78, 205, 196, 0.05));
    }

    /* Keyframe Animations */
    @keyframes float-wave {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }

    @keyframes subtle-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }

    /* Global Styling */
    body {
        font-family: 'Inter', 'Helvetica Neue', sans-serif;
        background: var(--soft-background) !important;
        overflow-x: hidden;
    }

    /* Streamlit App Container */
    .stApp {
        max-width: 1600px;
        margin: 0 auto;
        padding: 20px;
        background: transparent;
    }

    /* Elegant Card Design */
    .elegant-card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 
            0 20px 40px rgba(31, 66, 135, 0.08),
            0 10px 20px rgba(78, 205, 196, 0.06);
        transition: all 0.4s ease;
        border: 1px solid rgba(78, 205, 196, 0.1);
        position: relative;
        overflow: hidden;
    }

    .elegant-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 5px;
        background: var(--water-gradient);
        transform: scaleX(0);
        transform-origin: right;
        transition: transform 0.4s ease;
    }

    .elegant-card:hover::before {
        transform: scaleX(1);
        transform-origin: left;
    }

    .elegant-card:hover {
        transform: translateY(-10px);
        box-shadow: 
            0 30px 50px rgba(31, 66, 135, 0.12),
            0 15px 25px rgba(78, 205, 196, 0.08);
    }

    /* Header with Water Wave Animation */
    .water-header {
        background: var(--water-gradient);
        color: white;
        padding: 40px;
        border-radius: 25px;
        text-align: center;
        position: relative;
        overflow: hidden;
        animation: float-wave 5s ease-in-out infinite;
        box-shadow: 0 25px 50px rgba(31, 66, 135, 0.2);
    }

    .water-header::before, 
    .water-header::after {
        content: '';
        position: absolute;
        bottom: -50px;
        left: 0;
        width: 100%;
        height: 100px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
        animation: wave 10s linear infinite;
    }

    .water-header::after {
        bottom: -70px;
        animation-delay: -5s;
        opacity: 0.5;
    }

    @keyframes wave {
        0% { transform: translateX(-50%) rotate(0deg); }
        100% { transform: translateX(-50%) rotate(360deg); }
    }

    /* UPDATED TAB STYLING: Hovering Scrollable Tabs with Bold Black Text */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        overflow-x: auto;
        white-space: nowrap;
        background: white !important;
        border-radius: 10px;
        padding: 8px 4px;
        box-shadow: 0 5px 15px rgba(31, 66, 135, 0.1);
        scrollbar-width: thin;
        scrollbar-color: var(--accent-blue) transparent;
        align-items: center;
        position: sticky;
        top: 0;
        z-index: 999;
    }

    /* Custom scrollbar for webkit browsers */
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        height: 6px;
        width: 6px;
    }

    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-track {
        background: transparent;
    }

    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
        background-color: var(--accent-blue);
        border-radius: 20px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 12px 20px;
        margin: 0 5px;
        font-weight: 700;
        font-size: 16px;
        color: #000000;
        border-radius: 8px;
        transition: all 0.3s ease;
        opacity: 0.7;
        text-align: center;
        min-width: fit-content;
        border: none !important;
        position: relative;
        cursor: pointer;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(78, 205, 196, 0.15);
        opacity: 1;
        transform: translateY(-2px);
        box-shadow: 0 5px 10px rgba(31, 66, 135, 0.1);
    }

    .stTabs [data-baseweb="tab-selected"] {
        font-weight: 800;
        color: #000000;
        opacity: 1;
        background: rgba(78, 205, 196, 0.2);
        border-bottom: none !important;
        box-shadow: 0 5px 10px rgba(31, 66, 135, 0.08);
    }

    .stTabs [data-baseweb="tab-selected"]::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 40px;
        height: 3px;
        background: var(--accent-blue);
        border-radius: 10px;
    }

    /* Animation for active tab indicator */
    @keyframes tab-highlight {
        from { width: 0; opacity: 0; }
        to { width: 40px; opacity: 1; }
    }

    .stTabs [data-baseweb="tab-selected"]::after {
        animation: tab-highlight 0.3s ease;
    }

    /* Content area */
    .stTabs [role="tabpanel"] {
        padding-top: 20px;
    }

    /* Forecast Item Styling */
    .forecast-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 20px;
    }

    .forecast-item {
        background: var(--card-gradient);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        transition: all 0.4s ease;
        box-shadow: 0 15px 30px rgba(31, 66, 135, 0.1);
    }

    .forecast-item:hover {
        transform: scale(1.05);
        box-shadow: 0 20px 40px rgba(31, 66, 135, 0.15);
    }
    </style>
    """, unsafe_allow_html=True)
    


def create_dynamic_header():
    from datetime import datetime
    current_time = datetime.now()
    
    # Determine greeting based on time of day
    if 5 <= current_time.hour < 12:
        greeting = "Good Morning"
    elif 12 <= current_time.hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"
    
    st.markdown(f"""
    <div class="water-header">
        <div style="
            display: flex; 
            justify-content: space-between; 
            align-items: center;
        ">
            <div style="text-align: left; flex-grow: 1;">
                <h3 style="
                    margin: 0; 
                    color: rgba(255,255,255,0.7); 
                    font-weight: 300;
                    font-size: 1.2em;
                ">
                    {greeting}, Water Quality Analyst
                </h3>
                <h1 style="
                    font-size: 2.5em; 
                    color: white;
                    margin: 10px 0;
                    text-shadow: 0 5px 15px rgba(0,0,0,0.2);
                ">
                    🌊 AquaWatch Intelligence
                </h1>
                <p style="
                    color: rgba(255,255,255,0.8);
                    font-size: 1em;
                    margin: 0;
                ">
                    Advanced River Water Quality Monitoring & Predictive Analytics
                </p>
            </div>
            <div style="
                background: rgba(255,255,255,0.1); 
                border-radius: 50%; 
                width: 100px; 
                height: 100px; 
                display: flex; 
                align-items: center; 
                justify-content: center;
            ">
                <span style="
                    font-size: 2em; 
                    color: white;
                ">
                    📊
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_greeting_card(selected_location):
    st.markdown(f"""
    <div class="elegant-card" style="
        display: flex; 
        align-items: center; 
        justify-content: space-between;
    ">
        <div>
            <h3 style="margin-bottom: 10px; color: var(--primary-blue);">
                Current Monitoring Station
            </h3>
            <p style="
                font-size: 1.2em; 
                color: var(--secondary-blue); 
                font-weight: 600;
            ">
                🏞️ {selected_location}
            </p>
        </div>
        <div style="
            background: var(--water-gradient);
            color: white;
            padding: 15px;
            border-radius: 15px;
        ">
            View Location Details
        </div>
    </div>
    """, unsafe_allow_html=True)
    
def display_forecast_donuts(forecast_dates, predicted_values, parameter, df):
    """
    Display forecast donut charts in a custom grid layout
    """
    # Create columns for forecast display
    cols = st.columns(5)
    
    for idx, (date, value) in enumerate(zip(forecast_dates, predicted_values)):
        with cols[idx]:
            # Create a card-like container
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #f5f7fa, #f5f7fa);
                border-radius: 15px;
                padding: 15px;
                text-align: center;
                margin-bottom: 15px;
                box-shadow: 0 10px 20px rgba(31, 66, 135, 0.1);
                transition: transform 0.3s ease;
            ">
                <h4 style="color: #1F4287; margin-bottom: 10px;">{date.strftime("%Y-%m-%d")}</h4>
            """, unsafe_allow_html=True)
            
            # Create donut chart
            donut = make_donut(
                input_response=value,  
                input_text=date.strftime("%Y-%m-%d"),
                parameter=parameter,
                parameter_data=df,
                selected_parameter=parameter
            )
            st.altair_chart(donut, use_container_width=True)
            
            # Close the card container
            st.markdown("</div>", unsafe_allow_html=True)
            
def get_location_based_wqi_classification(location_name):
    """
    Returns water quality classification based on location name.
    
    Args:
        location_name (str): Name of the monitoring location
        
    Returns:
        tuple: (classification, color, description)
    """
    location_classifications = {
        'ALAKNANDA A/C WITH BHAGIRATHI AT DEVPRAYAG': ('Good', '#27AE60', 'Water quality is excellent and safe for all uses'),
        'GANGA AT HARIDWAR D/S, UPPER GANGA CANAL D/S BALKUMARI MANDIR, AJEETPUR, HARIDWAR ': ('Good', '#27AE60', 'Water quality is good and suitable for most uses'),
        'GANGA AT KANNAUJ U/S (RAJGHAT), U.P': ('Poor', '#F39C12', 'Water quality is concerning, caution advised'),
        'GANGA AT ALLAHABAD D/S (SANGAM), U.P': ('Dangerous', '#E74C3C', 'Water quality is severely degraded, unsafe for most uses'),
        'GANGA AT TRIGHAT (GHAZIPUR), U.P': ('Dangerous', '#E74C3C', 'Water quality is severely degraded, unsafe for most uses'),
        'GANGA AT GULABI GHAT, PATNA': ('Poor', '#F39C12', 'Water quality is concerning, treatment required'),
        'KOLKATA, WEST BENGAL ': ('Poor', '#F39C12', 'Water quality is below standards, caution advised')
    }
    
    # Return default if location is not in the dictionary
    return location_classifications.get(
        location_name, 
        ('Unknown', '#808080', 'Water quality data not available')
    )

def display_wqi_card(selected_location):
    """
    Displays a water quality index card for the selected location.
    
    Args:
        selected_location (str): Name of the selected monitoring location
    """
    # Get classification for this location
    classification, color, description = get_location_based_wqi_classification(selected_location)
    
    # Create icon based on classification
    if classification == 'Good':
        icon = "✅"
    elif classification == 'Poor':
        icon = "⚠️"
    elif classification == 'Dangerous':
        icon = "⛔"
    else:
        icon = "❓"
    
    # Display WQI card with styling
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border-left: 5px solid {color};
    ">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <h3 style="margin-bottom: 10px; color: #333;">Overall Water Quality Index</h3>
                <h2 style="margin: 0; color: {color}; font-size: 28px;">{classification}</h2>
                <p style="color: #666; margin-top: 10px;">{description}</p>
            </div>
            <div style="
                font-size: 42px;
                background: linear-gradient(135deg, {color}22, {color}44);
                width: 80px;
                height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                box-shadow: 0 5px 15px {color}33;
            ">
                {icon}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
def main():
    # Apply water-themed styling
    apply_advanced_styling()
    
    # Create elegant header
    create_dynamic_header()
    
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown('<div class="water-card">', unsafe_allow_html=True)
        selected_location = st.selectbox(
            '📍 Select Monitoring Station', 
            list(LOCATIONS.keys()),
            key='location_selector'
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if selected_location:
            st.markdown('<div class="water-card">', unsafe_allow_html=True)
            location_data = LOCATIONS[selected_location]
            satellite_map = create_satellite_map(location_data['lat'], location_data['lon'])
            folium_static(satellite_map, width=600, height=400)
            st.markdown('</div>', unsafe_allow_html=True)
    
    if selected_location:
        # Display WQI card immediately after location is confirmed
        display_wqi_card(selected_location)
        
        # Load location-specific dataset
        df = pd.read_csv(LOCATIONS[selected_location]['file_path'])
        df['Date'] = df['Date'].apply(parse_date)
        
        # Get the last date in the dataset
        last_date = df['Date'].max()

        parameters = [
            param for param in df.columns 
            if param not in ['Date', 'Temperature', 'Rainfall', 'Quality']
        ]
    
        # Custom tab styling to ensure full visibility
        tabs = st.tabs(parameters)
            
        # Iterate through tabs and create content for each parameter
        for idx, parameter in enumerate(parameters):
            with tabs[idx]:
                st.markdown('<div class="card-container">', unsafe_allow_html=True)
                
                # Prediction and Visualization
                try:
                    # Get the last date in the dataset
                    last_date = df['Date'].max()
                    
                    # Fetch Weather Forecast
                    weather_forecasts = fetch_weather_forecast(selected_location, last_date)
                    
                    # Load Appropriate Model
                    model = load_model_for_parameter(parameter)

                    if model and weather_forecasts:
                        # Prepare the input data for prediction
                        historical_features, exogenous_features, scaler, last_10_days, temp_scaler, rainfall_scaler = prepare_input_data(
                            df, weather_forecasts, parameter
                        )

                        # Predict
                        prediction = model.predict([historical_features, exogenous_features])
                        predicted_values = scaler.inverse_transform(prediction.reshape(-1, 1)).flatten()
                        forecast_dates = [last_date + timedelta(days=i+1) for i in range(len(predicted_values))]

                        # Create two side-by-side graphs
                        st.markdown('<div class="graph-container">', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Past Year Data
                            past_year_data = df[df['Date'] > (last_date - timedelta(days=365))]
                            st.subheader('Past Year Data')
                            historical_chart = create_altair_historical_plot(past_year_data, parameter)
                            st.altair_chart(historical_chart, use_container_width=True)
                        
                        with col2:
                            # 10 Day Historical and 5 Day Forecast
                            st.subheader('10 Day Historical and 5 Day Forecast')
                            forecast_chart = create_altair_forecast_plot(last_10_days, predicted_values, parameter)
                            st.altair_chart(forecast_chart, use_container_width=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)

                        # Weather Forecast Table
                        st.subheader('Upcoming Weather Outlook')
                        forecast_df = pd.DataFrame([
                            {
                                'Date': forecast['date'].strftime('%Y-%m-%d'), 
                                'Temperature (°C)': forecast['temperature'], 
                                'Rainfall (mm)': forecast['rainfall']
                            } for forecast in weather_forecasts
                        ])
                        st.table(forecast_df)

                        # Daily Water Quality Forecast
                        st.subheader("Daily Water Quality Forecast")
                        display_forecast_donuts(forecast_dates, predicted_values, parameter, df)

                        # Generate Gemini AI Report
                        try:
                            append_gemini_report_to_streamlit(
                                parameter, 
                                predicted_values, 
                                forecast_dates, 
                                df
                            )
                        except Exception as e:
                            st.error(f"Could not generate AI insights: {e}")

                except Exception as e:
                    st.error(f"Error processing data for {parameter}: {e}")
                
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()




