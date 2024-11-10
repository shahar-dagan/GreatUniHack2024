function initializeGooglePlaces() {
  const input = document.getElementById("destination-input");
  const options = {
    types: ["tourist_attraction", "point_of_interest"],
  };

  const autocomplete = new google.maps.places.Autocomplete(input, options);
  const seenPlaces = new Set(); // Keep track of places we've already seen

  autocomplete.addListener("place_changed", function () {
    const place = autocomplete.getPlace();

    // Create unique identifier for the place (using place_id or name+location)
    const placeIdentifier =
      place.place_id ||
      `${
        place.name
      }_${place.geometry.location.lat()}_${place.geometry.location.lng()}`;

    // Check if we've already seen this place
    if (!seenPlaces.has(placeIdentifier)) {
      seenPlaces.add(placeIdentifier);

      const placeData = {
        destination_name: place.name,
        city: extractCity(place),
        country: extractCountry(place),
        coordinates: [
          place.geometry.location.lat(),
          place.geometry.location.lng(),
        ],
        place_id: place.place_id,
      };

      // Send to backend
      sendPlaceToBackend(placeData);
    }
  });
}

function extractCity(place) {
  // Improved city extraction
  let city = "";
  if (place.address_components) {
    for (const component of place.address_components) {
      if (
        component.types.includes("locality") ||
        component.types.includes("administrative_area_level_1")
      ) {
        city = component.long_name;
        break;
      }
    }
  }
  return city;
}

function extractCountry(place) {
  // Improved country extraction
  let country = "";
  if (place.address_components) {
    for (const component of place.address_components) {
      if (component.types.includes("country")) {
        country = component.long_name;
        break;
      }
    }
  }
  return country;
}
