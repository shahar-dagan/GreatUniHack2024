from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import os


@dataclass
class TravelResponse:
    destination_name: str
    city: str
    country: str
    coordinates: tuple
    response: str  # 'yes', 'no', or 'bucket_list'
    timestamp: datetime


class TravelHistory:
    def __init__(self, filename="travel_history.json"):
        # Use absolute path from the current file's location
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.filename = self.data_dir / filename
        print(f"Travel history file path: {self.filename}")

        # Create empty JSON file if it doesn't exist
        if not self.filename.exists():
            with open(self.filename, "w") as f:
                json.dump([], f)
                print(f"Created new travel history file at {self.filename}")

    def save_response(self, destination, response):
        print(f"\nSaving response to {self.filename}")

        # Create the response data
        data = {
            "destination_name": destination.name,
            "city": destination.city,
            "country": destination.country,
            "coordinates": destination.coordinates,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Load existing data
            existing_data = self.load_responses()
            print(f"Loaded {len(existing_data)} existing responses")

            # Append new data
            existing_data.append(data)

            # Save back to file
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4, ensure_ascii=False)

            print(
                f"Successfully saved response. Total responses: {len(existing_data)}"
            )

        except Exception as e:
            print(f"Error saving response: {str(e)}")
            import traceback

            traceback.print_exc()

    def load_responses(self):
        try:
            if not self.filename.exists():
                print(f"No existing file found at {self.filename}")
                return []

            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Successfully loaded {len(data)} responses")
                return data

        except Exception as e:
            print(f"Error loading responses: {str(e)}")
            return []

    def print_all_responses(self):
        responses = self.load_responses()
        print(f"\nAll saved responses ({len(responses)} total):")
        for resp in responses:
            print(f"- {resp['destination_name']}: {resp['response']}")

    def verify_file_contents(self):
        """Debug method to verify file contents"""
        print(f"\nVerifying contents of {self.filename}")
        try:
            if self.filename.exists():
                with open(self.filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"File contains {len(data)} responses:")
                    for resp in data:
                        print(
                            f"- {resp['destination_name']}: {resp['response']}"
                        )
            else:
                print("File does not exist!")
        except Exception as e:
            print(f"Error verifying file: {str(e)}")

    def get_response_count(self, response_type: str) -> int:
        """
        Count the number of responses of a specific type
        Args:
            response_type: The type of response to count ('yes', 'no', or 'bucket_list')
        Returns:
            int: The number of responses of the specified type
        """
        return len(
            [r for r in self.responses if r.get("response") == response_type]
        )
