import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from pathlib import Path

st.set_page_config(layout="wide", page_title="Travel History Visualization")


@st.cache_data(ttl=0)
def load_travel_data():
    data_file = Path("frontend/data/travel_history.json")
    st.write(f"Looking for file at: {data_file.absolute()}")

    if not data_file.exists():
        st.error(f"File not found at {data_file.absolute()}")
        return pd.DataFrame()

    with open(data_file) as f:
        data = json.load(f)
    st.write(f"Loaded data: {data[:2]}")
    return pd.DataFrame(data)


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

    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=20,
            longitude=0,
            zoom=1.5,
            pitch=0,
        ),
        tooltip={
            "html": "{destination_name}<br/>{city}, {country}<br/>Status: {response}",
            "style": {"backgroundColor": "steelblue", "color": "white"},
        },
    )


def main():
    if st.button("🔄 Refresh Data"):
        st.write("Cache cleared!")
        st.cache_data.clear()
        st.experimental_rerun()

    st.title("🌍 My Travel History")

    # Load data
    df = load_travel_data()
    st.write(f"DataFrame shape: {df.shape}")

    if df.empty:
        st.warning("No travel data found!")
        return

    # Create statistics
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

    # Create tabs for detailed views
    tab1, tab2, tab3 = st.tabs(
        ["✈️ Visited", "🎯 Bucket List", "❌ Not Visited"]
    )

    with tab1:
        visited = df[df["response"] == "yes"].sort_values(
            "timestamp", ascending=False
        )
        if not visited.empty:
            st.dataframe(
                visited[["destination_name", "city", "country", "timestamp"]],
                hide_index=True,
            )
        else:
            st.info("No visited places yet!")

    with tab2:
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

    with tab3:
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


if __name__ == "__main__":
    main()
