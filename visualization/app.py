import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from pathlib import Path
from datetime import datetime

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

    # Create DataFrame and ensure new columns exist
    df = pd.DataFrame(data)
    if "date_visited" not in df.columns:
        df["date_visited"] = None
    if "photo_url" not in df.columns:
        df["photo_url"] = None

    st.write(f"Loaded data: {data[:2]}")
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
    df["date_info"] = df["date_visited"].apply(
        lambda x: f"Visited: {x}" if pd.notna(x) else ""
    )
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
            "html": "{destination_name}<br/>"
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


def main():
    if st.button("🔄 Refresh Data"):
        st.write("Cache cleared!")
        st.cache_data.clear()
        st.rerun()

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
