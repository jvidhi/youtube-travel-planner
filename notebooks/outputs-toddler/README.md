# AI-Generated Travel Itinerary Flow

This folder contains the generated outputs for a custom Japan travel itinerary. The files are produced sequentially through an automated pipeline defined in the `japan_itinerary_grounded.ipynb` notebook. The pipeline leverages Google Gemini and its Search and Maps Grounding capabilities to combine static prompts with real-time web and location data.

Below is the flow-by-flow structure of how each file was generated, along with an explanation of the underlying logic.

## 0. The Starting Point: User Preferences
* **File:** [preferences.md](preferences.md)
* **Logic:** This file serves as the foundational reference point for the entire pipeline. It defines the core travel persona (e.g., couple trip, young, mid-luxury budget) and interests (e.g., adventure, nature, history). Every subsequent prompt and generation dynamically injects this file to ensure all outputs are strictly tailored to the user's criteria.

## 1. Initial Itinerary Generation
* **File:** [japan_itinerary.md](japan_itinerary.md)
* **Logic:** The generation process begins by reading a base travel prompt and combining it with the user's specific preferences (`preferences.md`). These inputs are sent to the Gemini model with **Google Search Grounding** enabled. The model searches the live web for the best destinations, activities, and current recommendations that match the user's criteria to produce an initial, rich itinerary.

## 2. YouTube Video Recommendations
* **File:** [japan_youtube_recommendations.md](japan_youtube_recommendations.md)
* **Logic:** The pipeline reads the newly generated `japan_itinerary.md` and the user's preferences. It then prompts Gemini (again with **Google Search Grounding**) to act as a travel video curator. The model searches YouTube and the web to find high-quality travel guides, vlogs by authentic travelers, and practical "Know Before You Go" videos that specifically cover the locations mentioned in the itinerary.

## 3. Extracting Actionable Trip Insights
* **File:** [japan_trip_insights.md](japan_trip_insights.md)
* **Logic:** The notebook reads the `japan_youtube_recommendations.md` file and uses a regular expression (`regex`) to extract just the "Know Before You Go" section. This focused snippet is then passed back to Gemini with a prompt asking it to parse out and structure the actionable insights into a concise bulleted list of tips (e.g., luggage forwarding, IC cards).

## 4. Maps-Grounded Detailed Itinerary
* **File:** [japan_itinerary_maps.md](japan_itinerary_maps.md)
* **Logic:** The initial itinerary (`japan_itinerary.md`), the YouTube recommendations (`japan_youtube_recommendations.md`), and the user preferences (`preferences.md`) are fed into Gemini. This time, the model is configured with **Google Maps Grounding** to provide exact locations, confirm logistics, and create a highly detailed, day-by-day structured itinerary with real-world geographical awareness.

## 5. Comprehensive Transportation & Routing
* **File:** [japan_comprehensive_routing.md](japan_comprehensive_routing.md)
* **Logic:** The notebook reads the `japan_itinerary_maps.md` file and uses a flexible regex to extract only the "Itinerary Overview" section (which lists the days and locations). This overview is sent to Gemini (with **Google Maps Grounding**) to generate a comprehensive transportation guide. The model compares the route to the traditional "Golden Route", calculates travel times for public transit and driving, and recommends specific stops, scenic viewpoints, and highly-rated restaurants along the way.

## 6. Deep Dive Place Reviews & Summaries
* **File:** [japan_place_reviews.md](japan_place_reviews.md)
* **Logic:** The notebook scans `japan_itinerary_maps.md` and uses regex to extract the bolded place names (ignoring generic terms). For the top 30 unique places, it makes direct calls to the **Google Maps New Places API**. It first searches for the `placeId`, then fetches detailed metadata including:
  * Generative, Area, and Review summaries
  * EV charging options and amenities (parking, accessibility)
  * The top 10 highest-rated positive reviews and the top 10 lowest-rated negative reviews
  * The top photo for the location, which is downloaded directly to a `temp_images/` folder and linked within the markdown file.
  
All of these dynamic details are formatted into a final, comprehensive Markdown file that provides a deep dive into every location on the itinerary.
