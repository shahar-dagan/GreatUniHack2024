import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv
from PIL import Image
import io
import base64
import requests
import logging

load_dotenv()

# Add this near the top of your file
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.set_page_config(layout="wide", page_title="Travel History Visualization")

# Initialize OpenAI client at the top of the file, after imports
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@st.cache_data(ttl=0)
def load_travel_data():
    data_file = Path("frontend/data/travel_history.json")
    if not data_file.exists():
        st.error(f"File not found at {data_file.absolute()}")
        return pd.DataFrame()

    with open(data_file) as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    if "date_visited" not in df.columns:
        df["date_visited"] = None
    if "photo_url" not in df.columns:
        df["photo_url"] = None

    return df


def create_map(df):
    # Create separate dataframes for each response type
    visited = df[df["response"] == "yes"]
    bucket_list = df[df["response"] == "bucket_list"]
    not_visited = df[df["response"] == "no"]

    layers = []

    # Visited locations (green)
    if not visited.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                visited,
                get_position="[coordinates[1], coordinates[0]]",
                get_color=[0, 255, 0, 160],
                get_radius=50000,
                pickable=True,
                opacity=0.8,
                stroked=True,
                filled=True,
            )
        )

    # Bucket list locations (orange)
    if not bucket_list.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                bucket_list,
                get_position="[coordinates[1], coordinates[0]]",
                get_color=[255, 165, 0, 160],
                get_radius=50000,
                pickable=True,
                opacity=0.8,
                stroked=True,
                filled=True,
            )
        )

    # Not visited locations (red)
    if not not_visited.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                not_visited,
                get_position="[coordinates[1], coordinates[0]]",
                get_color=[255, 0, 0, 160],
                get_radius=50000,
                pickable=True,
                opacity=0.8,
                stroked=True,
                filled=True,
            )
        )

    # Before creating the Deck, prepare the tooltip data
    df["photo_link"] = df["photo_url"].apply(
        lambda x: (
            f"<a href='{x}' target='_blank' style='color: white;'>📸 Photos</a>"
            if pd.notna(x)
            else ""
        )
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=20,
            longitude=0,
            zoom=1.5,
            pitch=0,
        ),
        tooltip={
            "html": "<b>{destination_name}</b><br/>"
            "{city}, {country}<br/>"
            "Status: {response}<br/>"
            "{date_info}<br/>"
            "{photo_link}",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white",
                "fontSize": "0.8em",
                "padding": "8px",
            },
        },
    )


def create_edit_form(selected_destination, df):
    with st.form(f"edit_{selected_destination['destination_name']}"):
        st.subheader(f"Edit {selected_destination['destination_name']}")

        # Convert date_visited to datetime if it exists, otherwise use None
        current_date = None
        if selected_destination.get("date_visited"):
            try:
                current_date = datetime.strptime(
                    selected_destination["date_visited"], "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                current_date = None

        date_visited = st.date_input(
            "Date Visited",
            value=current_date,
            help="When did you visit this location?",
        )

        photo_url = st.text_input(
            "Photo Folder URL",
            value=selected_destination.get("photo_url", ""),
            help="Enter the URL to your photo folder",
        )

        # Add the submit button
        submitted = st.form_submit_button("Save Changes")

        if submitted:
            # Update the dataframe
            idx = df.index[
                df["destination_name"]
                == selected_destination["destination_name"]
            ].item()
            df.at[idx, "date_visited"] = (
                date_visited.strftime("%Y-%m-%d") if date_visited else None
            )
            df.at[idx, "photo_url"] = photo_url if photo_url else None

            # Save updated data
            save_travel_data(df)
            st.success("Changes saved successfully!")
            return True
    return False


def save_travel_data(df):
    data_file = Path("frontend/data/travel_history.json")
    data = df.to_dict("records")
    with open(data_file, "w") as f:
        json.dump(data, f, indent=2)


def get_weather_info(city):
    """Get weather information for a city using WeatherAPI.com"""
    api_key = os.getenv("WEATHER_API_KEY")

    # Better city name extraction
    city = city.lower()
    # Remove common weather-related phrases
    phrases_to_remove = [
        "what's",
        "whats",
        "what is",
        "the",
        "weather",
        "temperature",
        "forecast",
        "conditions",
        "like",
        "in",
        "at",
        "for",
        "?",
        ".",
        "please",
        "show",
        "me",
        "current",
    ]

    for phrase in phrases_to_remove:
        city = city.replace(phrase, "")

    # Clean up extra spaces and get final city name
    city = city.strip()

    if not city:
        return {
            "error": True,
            "formatted_message": "⚠️ I couldn't determine which city you're asking about. Please try again with a city name.",
        }

    logger.debug(f"Extracted city name: {city}")  # Add this for debugging

    if not api_key:
        return {
            "error": True,
            "formatted_message": "⚠️ Weather service is currently unavailable. Please try again later.",
        }

    base_url = f"http://api.weatherapi.com/v1/current.json"

    params = {"key": api_key, "q": city, "aqi": "no"}

    try:
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            weather_info = {
                "temp_c": data["current"]["temp_c"],
                "condition": data["current"]["condition"]["text"],
                "humidity": data["current"]["humidity"],
                "wind_kph": data["current"]["wind_kph"],
                "feels_like": data["current"]["feelslike_c"],
                "location": data["location"]["name"],
                "country": data["location"]["country"],
            }

            message = f"""**Current Weather in {weather_info['location']}, {weather_info['country']}:**

• Temperature: {weather_info['temp_c']}°C

• Feels like: {weather_info['feels_like']}°C

• Conditions: {weather_info['condition']}

• Humidity: {weather_info['humidity']}%

• Wind Speed: {weather_info['wind_kph']} km/h
"""
            return {"error": False, "formatted_message": message}

        elif response.status_code == 401:
            return {
                "error": True,
                "formatted_message": "⚠️ Weather service authentication failed. Please try again later.",
            }
        elif response.status_code == 404:
            return {
                "error": True,
                "formatted_message": f"⚠️ Couldn't find weather data for '{city}'. Please check the city name and try again.",
            }
        else:
            return {
                "error": True,
                "formatted_message": f"⚠️ Weather service error (Status: {response.status_code}). Please try again later.",
            }

    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "formatted_message": "⚠️ Couldn't connect to the weather service. Please check your internet connection.",
        }
    except Exception as e:
        return {
            "error": True,
            "formatted_message": f"⚠️ An error occurred while fetching weather data: {str(e)}",
        }


def chat_interface(df):
    st.header("💬 Chat with Your Travel Data")

    # Add brief instructions with proper line spacing
    with st.expander("ℹ️ What can you ask?"):
        st.markdown(
            """
        **Travel History Questions:**
        
        • "How many countries have I visited?"
        
        • "Show me my bucket list"
        
        • "Which cities have I been to?"
        
        **Weather Queries:**
        
        • "What's the weather in Paris?"
        
        • "Show me weather in Tokyo"
        
        • "Current weather in London"
        """
        )

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Define travel context
    travel_context = f"""
    You are analyzing travel data with:
    • {len(df[df['response'] == 'yes'])} visited destinations
    • {len(df[df['response'] == 'bucket_list'])} bucket list items
    • {len(df[df['response'] == 'yes']['country'].unique())} countries visited

    For travel questions: Be brief and specific with numbers.
    For weather queries: Say "Let me check the current weather in [city]"

    Keep responses under 3 sentences unless asked for more detail.
    """

    # Create containers for chat and thinking animation
    chat_container = st.container()
    thinking_container = st.empty()  # For the thinking animation

    # Place the input box below the chat container
    prompt = st.chat_input("Ask about your travel history or check weather...")

    # Display chat history
    with chat_container:
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt:
        # Show user message
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # Check if this is a weather query
        is_weather_query = any(
            word in prompt.lower()
            for word in ["weather", "temperature", "forecast"]
        )

        messages = [
            {"role": "system", "content": travel_context},
            {"role": "user", "content": prompt},
        ]

        # Show thinking animation while processing
        with thinking_container:
            with st.spinner("Thinking..."):
                # Get AI response
                with chat_container:
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        full_response = ""

                        for response in client.chat.completions.create(
                            model="gpt-4",
                            messages=messages,
                            stream=True,
                            temperature=0.5,
                        ):
                            if response.choices[0].delta.content is not None:
                                full_response += response.choices[
                                    0
                                ].delta.content
                                message_placeholder.markdown(
                                    full_response + "▌"
                                )
                        message_placeholder.markdown(full_response)

                # If it's a weather query, add weather data
                if is_weather_query:
                    city = prompt.lower()
                    weather_data = get_weather_info(city)

                    with chat_container:
                        with st.chat_message("assistant"):
                            if weather_data.get("error", False):
                                st.error(weather_data["formatted_message"])
                            else:
                                st.markdown(weather_data["formatted_message"])

                    # Add to chat history
                    st.session_state["messages"].append(
                        {
                            "role": "assistant",
                            "content": weather_data["formatted_message"],
                        }
                    )
                else:
                    # Just add the AI response for travel analysis
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": full_response}
                    )


def generate_travel_image(client, destination):
    try:
        prompt = f"""Create a realistic travel photo of a person at {destination}. 
        Show them in a natural pose at a famous landmark or scenic viewpoint of {destination}. 
        Make sure the lighting and perspective look natural."""

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard",
        )

        return response.data[0].url
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None


def get_flight_info(departure_city, arrival_city):
    """Get flight information between two cities"""
    logger.debug(
        f"Starting flight info request for {departure_city} to {arrival_city}"
    )

    # Clean up city names and remove quotes
    departure_city = departure_city.strip().strip('"').lower()
    arrival_city = arrival_city.strip().strip('"').lower()

    # Comprehensive airport codes dictionary
    airport_codes = {
        "london": "LHR",
        "paris": "CDG",
        "new york": "JFK",
        "tokyo": "HND",
        "dubai": "DXB",
        "singapore": "SIN",
        "hong kong": "HKG",
        "frankfurt": "FRA",
        "istanbul": "IST",
        "amsterdam": "AMS",
    }

    # Get IATA codes
    dep_code = airport_codes.get(departure_city, departure_city.upper())
    arr_code = airport_codes.get(arrival_city, arrival_city.upper())

    # Validate IATA codes (should be 3 letters)
    if len(dep_code) != 3 or len(arr_code) != 3:
        return {
            "formatted_message": f"Sorry, I couldn't find valid airport codes for {departure_city} or {arrival_city}. "
            f"Please try using major airports or IATA codes (e.g., LHR for London Heathrow)."
        }

    api_key = os.getenv("AVIATION_STACK_KEY")
    base_url = "http://api.aviationstack.com/v1/flights"

    params = {
        "access_key": api_key,
        "dep_iata": dep_code,
        "arr_iata": arr_code,
        "limit": 5,
    }

    try:
        logger.debug(f"Making API request with params: {params}")
        response = requests.get(base_url, params=params)
        logger.debug(f"API response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logger.debug(f"API response data: {data}")

            if data and data.get("data"):
                flights = data["data"]
                if not flights:
                    return {
                        "formatted_message": f"No flights found for route {dep_code} to {arr_code}"
                    }

                formatted_flights = []
                for flight in flights:
                    try:
                        dep_time = datetime.fromisoformat(
                            flight["departure"]["scheduled"]
                        ).strftime("%H:%M")
                        arr_time = datetime.fromisoformat(
                            flight["arrival"]["scheduled"]
                        ).strftime("%H:%M")
                        airline = flight.get("airline", {}).get(
                            "name", "Unknown Airline"
                        )

                        formatted_flights.append(
                            {
                                "flight_number": flight["flight"]["iata"],
                                "airline": airline,
                                "departure": dep_time,
                                "arrival": arr_time,
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error formatting flight: {e}")
                        continue

                message = "**Available Flights:**\n\n"
                for flight in formatted_flights:
                    message += f"• **Flight {flight['flight_number']}** ({flight['airline']})\n"
                    message += f"  Departure: {flight['departure']}\n"
                    message += f"  Arrival: {flight['arrival']}\n\n"

                return {"formatted_message": message, "raw_data": data}

            return {"formatted_message": "No flights found for this route."}

    except Exception as e:
        logger.error(f"Error in get_flight_info: {e}")
        return {"formatted_message": f"Error fetching flight data: {str(e)}"}


def main():
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.title("Travel History")

    # Load data
    df = load_travel_data()

    if df.empty:
        st.warning("No travel data found!")
        return

    # Display metrics before the map
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✈️ Places Visited", len(df[df["response"] == "yes"]))
    with col2:
        st.metric("🎯 Bucket List", len(df[df["response"] == "bucket_list"]))
    with col3:
        st.metric("❌ Not Visited", len(df[df["response"] == "no"]))
    with col4:
        st.metric("🌎 Total Countries", len(df["country"].unique()))

    # Display map
    st.pydeck_chart(create_map(df))

    # Create tabs including the new Badge tab
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "🏆 Badge",
            "✈️ Visited",
            "🎯 Bucket List",
            "❌ Not Visited",
            "📅 Timeline",
            "💬 Chat Analysis",
            "📚 Library",
        ]
    )

    # Show key statistics
    with tab1:
        # Calculate badge based on visited places
        yes_count = len(df[df["response"] == "yes"])
        badge_info = calculate_badge(yes_count)

        # Display badge section
        st.subheader(badge_info["title"])

        # Display badge image with correct path
        badge_images = {
            "Novice Explorer": "frontend/resources/badges/novice_explorer.png",
            "Adventurer": "frontend/resources/badges/adventurer.png",
            "World Master": "frontend/resources/badges/world_master.png",
        }

        badge_image_path = badge_images.get(badge_info["title"])
        if badge_image_path and Path(badge_image_path).exists():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(badge_image_path, width=200)

        st.info(f"🌟 {badge_info['description']}")

    with tab2:
        visited = df[df["response"] == "yes"].sort_values(
            "timestamp", ascending=False
        )
        if not visited.empty:
            # Convert date_visited strings to datetime objects
            visited["date_visited"] = pd.to_datetime(
                visited["date_visited"], errors="coerce"
            )

            # Display each destination in a dataframe with editable columns
            edited_df = st.data_editor(
                visited[
                    [
                        "destination_name",
                        "city",
                        "country",
                        "timestamp",
                        "date_visited",
                        "photo_url",
                    ]
                ],
                hide_index=True,
                column_config={
                    "destination_name": "Destination",
                    "city": st.column_config.TextColumn("City", disabled=True),
                    "country": st.column_config.TextColumn(
                        "Country", disabled=True
                    ),
                    "timestamp": st.column_config.TextColumn(
                        "Added On", disabled=True
                    ),
                    "date_visited": st.column_config.DateColumn(
                        "Date Visited",
                        help="When did you visit this location?",
                        format="YYYY-MM-DD",
                        step=1,  # Show daily intervals
                    ),
                    "photo_url": st.column_config.TextColumn(
                        "Photo URL",
                        help="Link to your photos",
                    ),
                },
                use_container_width=True,
                key="destination_editor",
                num_rows="dynamic",
            )

            # If any changes were made, save them
            if edited_df is not None and st.button("Save Changes"):
                # Convert dates back to string format for saving
                edited_df["date_visited"] = edited_df[
                    "date_visited"
                ].dt.strftime("%Y-%m-%d")

                # Update the main dataframe with edited values
                for idx, row in edited_df.iterrows():
                    df.loc[
                        df["destination_name"] == row["destination_name"],
                        "date_visited",
                    ] = row["date_visited"]
                    df.loc[
                        df["destination_name"] == row["destination_name"],
                        "photo_url",
                    ] = row["photo_url"]

                # Save to file
                save_travel_data(df)
                st.success("Changes saved successfully!")
                st.rerun()
        else:
            st.info("No visited places yet!")

    with tab3:
        bucket = df[df["response"] == "bucket_list"].sort_values(
            "timestamp", ascending=False
        )
        if not bucket.empty:
            st.dataframe(
                bucket[["destination_name", "city", "country", "timestamp"]],
                hide_index=True,
            )
        else:
            st.info("Bucket list is empty!")

    with tab4:
        not_visited = df[df["response"] == "no"].sort_values(
            "timestamp", ascending=False
        )
        if not not_visited.empty:
            st.dataframe(
                not_visited[
                    ["destination_name", "city", "country", "timestamp"]
                ],
                hide_index=True,
            )
        else:
            st.info("No 'not visited' places recorded!")

    with tab5:
        visited_timeline = df[
            (df["response"] == "yes") & (df["date_visited"].notna())
        ].copy()

        if not visited_timeline.empty:
            # Convert date_visited to datetime
            visited_timeline["date_visited"] = pd.to_datetime(
                visited_timeline["date_visited"]
            )
            # Sort by date visited
            visited_timeline = visited_timeline.sort_values("date_visited")

            # Create timeline using streamlit
            st.header("🗓️ Travel Timeline")

            for _, row in visited_timeline.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.write(row["date_visited"].strftime("%B %Y"))
                    with col2:
                        location_text = f"**{row['destination_name']}** - {row['city']}, {row['country']}"
                        if pd.notna(row["photo_url"]):
                            location_text += f" [📸]({row['photo_url']})"
                        st.markdown(location_text)
                st.divider()
        else:
            st.info(
                "No dated visits to display. Add dates to your visited locations to see them on the timeline!"
            )

    with tab6:
        chat_interface(df)

    with tab7:
        st.header("🖼️ Travel Photo Library")

        # Get bucket list destinations
        bucket_list = df[df["response"] == "bucket_list"]

        if bucket_list.empty:
            st.info(
                "Add some destinations to your bucket list to generate travel photos!"
            )
            return

        # Create a dropdown to select destination
        selected_destination = st.selectbox(
            "Select a destination to generate a photo",
            bucket_list["destination_name"].tolist(),
        )

        if st.button("Generate Travel Photo"):
            with st.spinner("Generating your travel photo..."):
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                destination_details = bucket_list[
                    bucket_list["destination_name"] == selected_destination
                ].iloc[0]

                full_destination = f"{destination_details['destination_name']}, {destination_details['city']}, {destination_details['country']}"

                image_url = generate_travel_image(client, full_destination)

                if image_url:
                    st.image(image_url, caption=f"You at {full_destination}")
                    st.markdown(f"[Download Image]({image_url})")


def calculate_badge(yes_count):
    badges = {
        (0, 4): {
            "title": "Novice Explorer",
            "description": "You're just beginning your journey! Keep exploring!",
        },
        (5, 7): {
            "title": "Adventurer",
            "description": "You're getting the hang of traveling! More adventures await!",
        },
        (8, float("inf")): {
            "title": "World Master",
            "description": "You're a true citizen of the world! Incredible journey!",
        },
    }

    for (min_count, max_count), badge in badges.items():
        if min_count <= yes_count <= max_count:
            return badge

    return badges[(0, 4)]  # Default badge


if __name__ == "__main__":
    main()
