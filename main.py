import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.dash_table import DataTable
import json
from whoop import WhoopClient
import datetime
import plotly.graph_objs as go
import os
from dotenv import load_dotenv
from waitress import serve

# Load environment variables from .env file
load_dotenv()

# Initialize Dash app
app = dash.Dash(__name__)

# Expose the server
server = app.server  # This is important for waitress

# Fetch Username and Password for Whoop API from environment variables
USERNAME = os.getenv("WHOOP_USERNAME")
PASSWORD = os.getenv("WHOOP_PASSWORD")

# App Layout
app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'margin': '20px'}, children=[
    html.H1("Whoop Workouts Fetcher", style={'textAlign': 'center', 'color': '#4A90E2'}),
    
    # Input for Start Date
    html.Div([
        dcc.Input(id="start-date", type="text", placeholder="YYYY-MM-DD", value="2022-10-12",
                   style={'padding': '10px', 'width': '300px', 'marginRight': '10px'}),
        
        # Submit button
        html.Button(id="submit-btn", children="Fetch Workouts", style={
            'padding': '10px 20px',
            'backgroundColor': '#4A90E2',
            'color': 'white',
            'border': 'none',
            'borderRadius': '5px',
            'cursor': 'pointer'
        }),
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # Loading indicator
    dcc.Loading(
        id="loading",
        type="default",
        children=[
            # Output container for messages
            html.Div(id="output-workouts", style={'textAlign': 'center', 'marginBottom': '20px'}),
            # Data table to display fetched workouts
            DataTable(
                id="workouts-table",
                columns=[],
                data=[],
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'height': '400px',
                    'border': 'thin lightgrey solid',
                    'borderRadius': '5px',
                    'boxShadow': '0 2px 5px rgba(0, 0, 0, 0.1)',
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'border': '1px solid lightgrey',
                },
                style_header={
                    'backgroundColor': '#4A90E2',
                    'color': 'white',
                    'fontWeight': 'bold',
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9f9f9',
                    },
                ],
                page_size=10,  # Set the number of rows per page
                style_as_list_view=True,
            ),
            # Graph to show strain score over time
            dcc.Graph(id="strain-chart")
        ],
    ),
])

# Callback to fetch workouts based on start date and prepare data for the table and chart
@app.callback(
    Output("output-workouts", "children"),
    Output("workouts-table", "data"),
    Output("workouts-table", "columns"),
    Output("strain-chart", "figure"),
    Input("submit-btn", "n_clicks"),
    State("start-date", "value")
)
def fetch_workouts(n_clicks, start_date):
    if n_clicks is None:
        return "", [], [], go.Figure()

    # Ensure start date is properly formatted
    try:
        start_date_parsed = datetime.datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d 23:59:59.999999")
    except ValueError:
        return "Invalid date format. Please enter a date in YYYY-MM-DD format.", [], [], go.Figure()

    # Fetch workouts from Whoop API
    try:
        with WhoopClient(USERNAME, PASSWORD) as client:
            workouts = client.get_workout_collection(start_date=start_date_parsed)
    except Exception as e:
        return f"Error fetching workouts: {str(e)}", [], [], go.Figure()

    # Save workouts to a JSON file
    with open("workouts.json", "w") as f:
        json.dump(workouts, f, indent=4)

    # Prepare data for DataTable and strain chart
    workout_data = []
    strain_scores = []
    dates = []

    for workout in workouts:
        score = workout.get("score")  # Get the score dictionary
        strain = score.get("strain") if score else None
        workout_data.append({
            "ID": workout.get("id"),
            "User ID": workout.get("user_id"),
            "Created At": workout.get("created_at"),
            "Updated At": workout.get("updated_at"),
            "Start": workout.get("start"),
            "End": workout.get("end"),
            "Timezone Offset": workout.get("timezone_offset"),
            "Sport ID": workout.get("sport_id"),
            "Score State": workout.get("score_state"),
            "Strain": strain,
            "Average Heart Rate": score.get("average_heart_rate") if score else None,
            "Max Heart Rate": score.get("max_heart_rate") if score else None,
            "Kilojoules": score.get("kilojoule") if score else None,
            "Percent Recorded": score.get("percent_recorded") if score else None,
            "Distance (meters)": score.get("distance_meter") if score else None,
            "Altitude Gain (meters)": score.get("altitude_gain_meter") if score else None,
            "Altitude Change (meters)": score.get("altitude_change_meter") if score else None,
            "Zone Zero Duration (ms)": score["zone_duration"].get("zone_zero_milli") if score else None,
            "Zone One Duration (ms)": score["zone_duration"].get("zone_one_milli") if score else None,
            "Zone Two Duration (ms)": score["zone_duration"].get("zone_two_milli") if score else None,
            "Zone Three Duration (ms)": score["zone_duration"].get("zone_three_milli") if score else None,
            "Zone Four Duration (ms)": score["zone_duration"].get("zone_four_milli") if score else None,
            "Zone Five Duration (ms)": score["zone_duration"].get("zone_five_milli") if score else None,
        })
        if strain is not None:
            strain_scores.append(strain)
            dates.append(datetime.datetime.fromisoformat(workout.get("start")[:-1]))  # Convert to datetime

    # Define columns for the DataTable
    columns = [
        {"name": "ID", "id": "ID"},
        {"name": "User ID", "id": "User ID"},
        {"name": "Created At", "id": "Created At"},
        {"name": "Updated At", "id": "Updated At"},
        {"name": "Start", "id": "Start"},
        {"name": "End", "id": "End"},
        {"name": "Timezone Offset", "id": "Timezone Offset"},
        {"name": "Sport ID", "id": "Sport ID"},
        {"name": "Score State", "id": "Score State"},
        {"name": "Strain", "id": "Strain"},
        {"name": "Average Heart Rate", "id": "Average Heart Rate"},
        {"name": "Max Heart Rate", "id": "Max Heart Rate"},
        {"name": "Kilojoules", "id": "Kilojoules"},
        {"name": "Percent Recorded", "id": "Percent Recorded"},
        {"name": "Distance (meters)", "id": "Distance (meters)"},
        {"name": "Altitude Gain (meters)", "id": "Altitude Gain (meters)"},
        {"name": "Altitude Change (meters)", "id": "Altitude Change (meters)"},
        {"name": "Zone Zero Duration (ms)", "id": "Zone Zero Duration (ms)"},
        {"name": "Zone One Duration (ms)", "id": "Zone One Duration (ms)"},
        {"name": "Zone Two Duration (ms)", "id": "Zone Two Duration (ms)"},
        {"name": "Zone Three Duration (ms)", "id": "Zone Three Duration (ms)"},
        {"name": "Zone Four Duration (ms)", "id": "Zone Four Duration (ms)"},
        {"name": "Zone Five Duration (ms)", "id": "Zone Five Duration (ms)"},
    ]

    # Create a figure for the strain chart
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=dates, y=strain_scores, mode='lines+markers', name='Strain Score'))
    figure.update_layout(title='Strain Score Over Time', xaxis_title='Date', yaxis_title='Strain Score',
                         xaxis=dict(showgrid=True, gridcolor='LightGray'),
                         yaxis=dict(showgrid=True, gridcolor='LightGray'))

    # Return the number of workouts found, the data, columns for the table, and the strain chart
    return f"Found {len(workouts)} workouts. Data saved to workouts.json", workout_data, columns, figure

# Run the Dash app with Waitress if this script is run directly
if __name__ == "__main__":
    serve(app.server, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
