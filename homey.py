import streamlit as st

# Configure the page - MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="AquaVision AI",
    page_icon="🌊",
    layout="wide"
)

import folium
from streamlit_folium import folium_static
import importlib.util
import sys
import os

# Locations with their coordinates (latitude, longitude)
LOCATIONS = {
    "Devprayag": (30.1407, 78.5936),
    "Kannauj": (27.0648, 79.9120),
    "Allahabad": (25.4358, 81.8463),
    "Ghazipur": (25.5799, 83.5963),
    "Patna": (25.5941, 85.1376),
    "Kolkata":(22.5744, 88.3629)
}

def create_ganga_river_map():
    """
    Create an interactive map of the Ganga River basin
    
    Returns:
        folium.Map: Configured map object
    """
    # Create a map centered on the middle of the Ganga basin
    m = folium.Map(
        location=[25.5, 80], 
        zoom_start=6,
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite'
    )

    # Add markers for each location
    for name, (lat, lon) in LOCATIONS.items():
        # Custom HTML popup with styled content
        popup_html = f"""
        <div style="font-family: 'Poppins', sans-serif; color: #333; padding: 12px; border-radius: 8px; background: rgba(255, 255, 255, 0.9);">
            <h3 style="color: #0077be; margin-bottom: 8px; font-weight: 600;">{name}</h3>
            <p style="margin: 0; font-size: 14px;">Latitude: {lat:.4f}</p>
            <p style="margin: 0; font-size: 14px;">Longitude: {lon:.4f}</p>
        </div>
        """
        
        # Add marker with popup
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=name,
            icon=folium.Icon(color='blue', icon='tint')
        ).add_to(m)

    # Draw river path (simplified approximation)
    river_path = list(LOCATIONS.values())
    
    # Add river path with animated dash
    folium.PolyLine(
        locations=river_path, 
        color='#0099ff', 
        weight=4, 
        opacity=0.8,
        dash_array='10'
    ).add_to(m)

    return m

# Helper function to safely import module content without executing st.set_page_config()
def import_module_content(file_path):
    try:
        # Read the file content
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            
        # Remove or comment out st.set_page_config lines
        import re
        # Pattern to match st.set_page_config() calls with various whitespace and parameters
        pattern = r"st\.set_page_config\s*\(.*?\)"
        # Use re.DOTALL to match across multiple lines if the function call spans lines
        modified_content = re.sub(pattern, "# Removed st.set_page_config", content, flags=re.DOTALL)
            
        # Execute the modified content
        exec(modified_content, globals())
        return True
    except FileNotFoundError:
        st.error(f"File not found at path: {file_path}")
        st.info("Please update the file path in the code to point to your file.")
        return False
    except Exception as e:
        st.error(f"Error executing file: {str(e)}")
        return False

# Set session state for page navigation
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# Main content rendering
def render_home_page():
    # Enhanced CSS with more beautiful design elements
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        
        .stApp { 
            background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 50%, #e3f2fd 100%); 
            background-size: 400% 400%; 
            animation: gradientBG 20s ease infinite; 
            font-family: 'Poppins', sans-serif;
        }

        @keyframes gradientBG { 
            0% { background-position: 0% 50%; } 
            50% { background-position: 100% 50%; } 
            100% { background-position: 0% 50%; } 
        }

        .big-title { 
            font-family: 'Poppins', sans-serif; 
            color: #0288d1; 
            font-size: 6rem !important; 
            font-weight: 800 !important; 
            margin-bottom: 0 !important; 
            line-height: 1.1 !important; 
            text-align: center !important; 
            letter-spacing: -2px; 
            text-shadow: 0 10px 30px rgba(2, 136, 209, 0.4); 
            animation: float 6s ease-in-out infinite;
        }
        
        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
            100% { transform: translateY(0px); }
        }

        .subtitle { 
            font-family: 'Poppins', sans-serif; 
            background: linear-gradient(to right, #0288d1, #26c6da); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
            font-size: 1.8rem !important; 
            text-align: center !important; 
            margin: 1rem 0 3rem 0 !important; 
            font-weight: 500 !important; 
            letter-spacing: -0.5px; 
        }

        .button-card { 
            cursor: pointer; 
            border-radius: 24px; 
            padding: 3rem 2rem; 
            background: rgba(255, 255, 255, 0.7); 
            backdrop-filter: blur(15px); 
            border: 2px solid rgba(2, 136, 209, 0.2); 
            margin: 1.5rem; 
            transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
            overflow: hidden; 
            position: relative;
            box-shadow: 0 10px 30px rgba(2, 136, 209, 0.1);
        }
        
        .button-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
            transition: 0.5s;
        }

        .button-card:hover { 
            transform: translateY(-12px) scale(1.03); 
            border: 2px solid rgba(2, 136, 209, 0.5); 
            box-shadow: 0 20px 40px rgba(2, 136, 209, 0.2), 0 0 40px rgba(2, 136, 209, 0.2);
        }
        
        .button-card:hover::before {
            left: 100%;
        }

        .emoji-icon { 
            font-size: 4rem !important; 
            margin-bottom: 1.5rem !important; 
            text-align: center; 
            display: block; 
            animation: bounce 3s infinite; 
            filter: drop-shadow(0 5px 15px rgba(2, 136, 209, 0.3));
        }

        @keyframes bounce { 
            0%, 100% { transform: translateY(0); } 
            50% { transform: translateY(-15px); } 
        }

        .card-title { 
            color: #0288d1 !important; 
            font-size: 2.2rem !important; 
            font-weight: 700 !important; 
            margin-bottom: 1.2rem !important; 
            text-align: center; 
            letter-spacing: -0.5px; 
        }

        .card-description { 
            color: #546e7a !important; 
            font-size: 1.2rem !important; 
            margin-bottom: 1.8rem !important; 
            text-align: center; 
            line-height: 1.7 !important;
            font-weight: 400;
        }

        .map-container {
            border-radius: 24px;
            overflow: hidden;
            box-shadow: 0 20px 50px rgba(2, 136, 209, 0.25);
            margin: 2rem 0 3rem 0;
            position: relative;
            border: 4px solid rgba(255, 255, 255, 0.7);
        }
        
        .map-container::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            box-shadow: inset 0 0 30px rgba(2, 136, 209, 0.2);
            border-radius: 20px;
        }
        
        .stButton>button {
            background-color: #0288d1 !important;
            color: white !important;
            font-family: 'Poppins', sans-serif !important;
            font-weight: 600 !important;
            padding: 0.8rem 2rem !important;
            border-radius: 50px !important;
            border: none !important;
            box-shadow: 0 10px 20px rgba(2, 136, 209, 0.3) !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
            font-size: 1.1rem !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
        }
        
        .stButton>button:hover {
            transform: translateY(-5px) !important;
            box-shadow: 0 15px 25px rgba(2, 136, 209, 0.4) !important;
            background-color: #039be5 !important;
        }
        
        /* Footer Style */
        .footer {
            text-align: center;
            padding: 2rem 0;
            margin-top: 3rem;
            color: #546e7a;
            font-size: 1rem;
            border-top: 1px solid rgba(2, 136, 209, 0.1);
        }
        
        /* Water wave animation for map container */
        .water-wave {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 15px;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 320'%3E%3Cpath fill='%230288d1' fill-opacity='0.3' d='M0,224L48,213.3C96,203,192,181,288,181.3C384,181,480,203,576,202.7C672,203,768,181,864,181.3C960,181,1056,203,1152,208C1248,213,1344,203,1392,197.3L1440,192L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z'%3E%3C/path%3E%3C/svg%3E");
            background-size: 100% 100%;
            animation: wave 10s linear infinite;
        }
        
        @keyframes wave {
            0% { background-position-x: 0; }
            100% { background-position-x: 1440px; }
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="big-title">AquaVision AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced Ganga Riverwater Monitoring & Analysis</p>', unsafe_allow_html=True)

    # Satellite Map Section with wave animation
    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    ganga_map = create_ganga_river_map()
    folium_static(ganga_map, width=1200, height=600)
    st.markdown('<div class="water-wave"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Create two columns for the buttons (keeping only 2 as requested)
    col1, col2 = st.columns(2)

    # Feature 1: Water Quality Analysis
    with col1:
        st.markdown("""
            <div class="button-card">
                <span class="emoji-icon">🌊</span>
                <h3 class="card-title">Water Quality Analysis</h3>
                <p class="card-description">
                    Advanced real-time monitoring and AI-powered forecasting of Ganga river water quality 
                    with comprehensive environmental impact assessment.
                </p>
            </div>
        """, unsafe_allow_html=True)

        if st.button('Analyze Water Quality', key='water-quality-btn'):
            st.session_state.page = 'water_quality'

    # Feature 2: Submit Feedback
    with col2:
        st.markdown("""
            <div class="button-card">
                <span class="emoji-icon">💬</span>
                <h3 class="card-title">Submit Feedback</h3>
                <p class="card-description">
                    Help us improve AquaVision AI by sharing your thoughts, experiences, and suggestions 
                    for future enhancements to our water monitoring system.
                </p>
            </div>
        """, unsafe_allow_html=True)

        if st.button('Submit Feedback', key='feedback-btn'):
            st.session_state.page = 'feedback'
    
    # Footer
    st.markdown("""
        <div class="footer">
            <p>© 2025 AquaVision AI | Protecting India's Sacred Waters | Powered by Advanced AI Technology</p>
        </div>
    """, unsafe_allow_html=True)

# Navigation logic (simplified)
if st.session_state.page == 'home':
    render_home_page()
else:
    if st.session_state.page == 'water_quality':
        st.header("Water Quality Analysis")
        
        # Path to your water quality analysis file
        analysis_file_path = "River check.py"  # Replace with your actual file path
        
        # Use the safe import function instead of direct execution
        import_module_content(analysis_file_path)
        
        if st.button('Back to Home'):
            st.session_state.page = 'home'

    elif st.session_state.page == 'feedback':
        st.header("Submit Your Feedback")
        
        # Path to your feedback form file
        feedback_file_path = "feedback.py"  # Replace with your actual file path
        
        # Use the safe import function instead of direct execution
        import_module_content(feedback_file_path)
        
        if st.button('Back to Home'):
            st.session_state.page = 'home'
