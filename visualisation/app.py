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


def chat_interface(df):
    st.header("💬 Chat with Your Travel Data")

    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set your OpenAI API key in the environment variables")
        return

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    chat_container = st.container()
    prompt = st.chat_input(
        "Ask about your travel history or search for flights..."
    )

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

        # Determine if this is a flight query or a travel history query
        if any(
            word in prompt.lower() for word in ["flight", "fly", "travel from"]
        ):
            # FLIGHT SEARCH MODE
            cities = extract_cities(prompt.lower())
            if cities:
                departure, arrival = cities

                # First response from AI
                initial_response = f"I'll check available flights from {departure.title()} to {arrival.title()}. Let me fetch the real-time schedule..."

                with chat_container:
                    with st.chat_message("assistant"):
                        st.markdown(initial_response)
                st.session_state["messages"].append(
                    {"role": "assistant", "content": initial_response}
                )

                # Fetch flight data
                with st.spinner("Fetching flights..."):
                    flight_data = get_flight_info(departure, arrival)
                    if flight_data and flight_data.get("formatted_message"):
                        with chat_container:
                            with st.chat_message("assistant"):
                                st.markdown(flight_data["formatted_message"])
                        st.session_state["messages"].append(
                            {
                                "role": "assistant",
                                "content": flight_data["formatted_message"],
                            }
                        )
        else:
            # TRAVEL HISTORY ANALYSIS MODE
            try:
                travel_context = f"""
                You are analyzing travel data with the following information:
                - Total destinations visited: {len(df[df['response'] == 'yes'])}
                - Bucket list destinations: {len(df[df['response'] == 'bucket_list'])}
                - Countries visited: {len(df[df['response'] == 'yes']['country'].unique())}

                The data includes:
                - Destination names
                - Cities and countries
                - Visit status (yes/no/bucket_list)
                - Dates visited (when available)

                Please provide concise, data-driven answers.
                Use bullet points for lists.
                Include specific numbers when relevant.
                """

                messages = [
                    {"role": "system", "content": travel_context},
                    {"role": "user", "content": prompt},
                ]

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

                st.session_state["messages"].append(
                    {"role": "assistant", "content": full_response}
                )

            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
                logging.error(f"OpenAI API error: {str(e)}")


def extract_cities(text):
    """Helper function to extract departure and arrival cities"""
    if "from" in text and "to" in text:
        from_idx = text.find("from") + 4
        to_idx = text.find("to") + 2
        departure = text[from_idx : text.find("to")].strip()
        arrival = text[to_idx:].strip()
        return departure, arrival
    return None


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
    logger.debug(
        f"Starting flight info request for {departure_city} to {arrival_city}"
    )

    # Common airport IATA codes
    airport_codes = {
        "paris": "CDG",
        "london": "LHR",
        "new york": "JFK",
        "tokyo": "HND",
        "dubai": "DXB",
    }

    # Convert city names to IATA codes
    dep_code = (
        departure_city.upper()
        if len(departure_city) == 3
        else airport_codes.get(departure_city.lower(), departure_city)
    )
    arr_code = (
        arrival_city.upper()
        if len(arrival_city) == 3
        else airport_codes.get(arrival_city.lower(), arrival_city)
    )

    api_key = os.getenv("AVIATION_STACK_KEY")
    base_url = "http://api.aviationstack.com/v1/flights"

    params = {
        "access_key": api_key,
        "dep_iata": dep_code.upper(),
        "arr_iata": arr_code.upper(),
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
