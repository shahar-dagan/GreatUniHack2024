import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from pathlib import Path

st.set_page_config(layout="wide", page_title="Travel History Visualization")


def load_travel_data():
    data_file = Path("data/travel_history.json")
    if not data_file.exists():
        return pd.DataFrame()

    with open(data_file) as f:
        data = json.load(f)
    return pd.DataFrame(data)


def create_map(df):
    visited = df[df["response"] == "yes"]
    bucket_list = df[df["response"] == "bucket_list"]

    # Create layers for different types of locations
    visited_layer = pdk.Layer(
        "ScatterplotLayer",
        visited,
        get_position=["coordinates[1]", "coordinates[0]"],
        get_color=[0, 255, 0, 160],  # Green for visited
        get_radius=50000,
        pickable=True,
    )

    bucket_list_layer = pdk.Layer(
        "ScatterplotLayer",
        bucket_list,
        get_position=["coordinates[1]", "coordinates[0]"],
        get_color=[255, 165, 0, 160],  # Orange for bucket list
        get_radius=50000,
        pickable=True,
    )

    return pdk.Deck(
        layers=[visited_layer, bucket_list_layer],
        initial_view_state=pdk.ViewState(
            latitude=20,
            longitude=0,
            zoom=1,
            pitch=0,
        ),
        tooltip={
            "html": "{destination_name}<br/>{city}, {country}",
            "style": {"color": "white"},
        },
    )


def main():
    st.title("My Travel History")

    # Load data
    df = load_travel_data()

    if df.empty:
        st.warning("No travel data found!")
        return

    # Create statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Places Visited", len(df[df["response"] == "yes"]))
    with col2:
        st.metric("Bucket List Items", len(df[df["response"] == "bucket_list"]))
    with col3:
        st.metric("Total Countries", len(df["country"].unique()))

    # Display map
    st.pydeck_chart(create_map(df))

    # Display detailed tables
    st.subheader("Visited Places")
    st.dataframe(
        df[df["response"] == "yes"][
            ["destination_name", "city", "country", "timestamp"]
        ]
    )

    st.subheader("Bucket List")
    st.dataframe(
        df[df["response"] == "bucket_list"][
            ["destination_name", "city", "country", "timestamp"]
        ]
    )


if __name__ == "__main__":
    main()
