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
app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}])

# Expose the server
server = app.server

# Fetch Username and Password for Whoop API from environment variables
USERNAME = os.getenv("WHOOP_USERNAME")
PASSWORD = os.getenv("WHOOP_PASSWORD")

# App Layout
app.layout = html.Div(style={'display': 'flex', 'flexDirection': 'column', 'minHeight': '100vh', 'backgroundColor': '#f7f7f7'}, children=[

    # Header Section
    html.Div(style={
        'backgroundColor': '#2c3e50', 'padding': '10px 20px', 'color': 'white', 
        'textAlign': 'center', 'fontSize': '24px', 'fontWeight': 'bold'}, 
        children="Whoop Dashboard"),

    # Content Wrapper
    html.Div(style={'display': 'flex', 'flexDirection': 'row', 'flex': 1}, children=[

        # Sidebar (Collapsible for mobile)
        html.Div(id="sidebar", style={
            'width': '250px', 'backgroundColor': '#34495e', 'padding': '20px', 'color': 'white', 
            'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'start', 'height': '100%', 'flexShrink': 0
        }, children=[
            html.H2("Menu", style={'color': 'white', 'textAlign': 'center', 'marginBottom': '20px'}),
            
            # Time range buttons
            html.Button('7 Days', id='7-days-btn', n_clicks=0, className='sidebar-button'),
            html.Button('14 Days', id='14-days-btn', n_clicks=0, className='sidebar-button'),
            html.Button('30 Days', id='30-days-btn', n_clicks=0, className='sidebar-button'),
            html.Button('3 Months', id='3-months-btn', n_clicks=0, className='sidebar-button'),
            html.Button('6 Months', id='6-months-btn', n_clicks=0, className='sidebar-button'),
            html.Button('All Time', id='all-time-btn', n_clicks=0, className='sidebar-button'),
            
            # Date range picker
            html.Label('Custom Date Range:', style={'marginTop': '20px'}),
            dcc.DatePickerRange(
                id='date-picker-range',
                min_date_allowed=datetime.date(2020, 1, 1),
                max_date_allowed=datetime.date.today(),
                start_date=datetime.date(2022, 1, 1),
                end_date=datetime.date.today(),
                style={'marginBottom': '20px'}
            ),
            
            # Submit button
            html.Button(id="submit-btn", children="Fetch Workouts", style={
                'padding': '10px 20px',
                'backgroundColor': '#e74c3c',
                'color': 'white',
                'border': 'none',
                'borderRadius': '5px',
                'cursor': 'pointer',
                'width': '100%'
            }),
        ]),

        # Main Content Area
        html.Div(style={'flexGrow': 1, 'padding': '20px', 'overflowY': 'scroll'}, children=[
            html.H1("Workout Data", style={'textAlign': 'center', 'color': '#34495e', 'marginBottom': '30px'}),

            dcc.Loading(
                id="loading",
                type="default",
                children=[
                    html.Div(id="output-workouts", style={'textAlign': 'center', 'marginBottom': '20px'}),
                    DataTable(
                        id="workouts-table",
                        columns=[],
                        data=[],
                        style_table={
                            'overflowX': 'auto',
                            'overflowY': 'auto',
                            'height': '300px',
                            'border': 'thin lightgrey solid',
                            'borderRadius': '5px',
                            'boxShadow': '0 2px 5px rgba(0, 0, 0, 0.1)',
                            'marginBottom': '20px',
                        },
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px',
                            'border': '1px solid lightgrey',
                        },
                        style_header={
                            'backgroundColor': '#34495e',
                            'color': 'white',
                            'fontWeight': 'bold',
                        },
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': '#f9f9f9',
                            },
                        ],
                        page_size=10,
                        style_as_list_view=True,
                    ),
                    dcc.Graph(id="strain-chart", style={'border': 'thin lightgrey solid', 'borderRadius': '5px'}),
                ]
            ),
        ]),
    ]),
])

# Callback to fetch workouts based on start date and prepare data for the table and chart
@app.callback(
    Output("output-workouts", "children"),
    Output("workouts-table", "data"),
    Output("workouts-table", "columns"),
    Output("strain-chart", "figure"),
    Input("7-days-btn", "n_clicks"),
    Input("14-days-btn", "n_clicks"),
    Input("30-days-btn", "n_clicks"),
    Input("3-months-btn", "n_clicks"),
    Input("6-months-btn", "n_clicks"),
    Input("all-time-btn", "n_clicks"),
    Input("submit-btn", "n_clicks"),
    State("date-picker-range", "start_date"),
    State("date-picker-range", "end_date"),
)
def fetch_workouts(n7, n14, n30, n3m, n6m, n_all, n_custom, start_date, end_date):
    # Determine which button was clicked
    ctx = dash.callback_context

    if not ctx.triggered:
        return "", [], [], go.Figure()

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Calculate the start date based on the button clicked
    if button_id == '7-days-btn':
        start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    elif button_id == '14-days-btn':
        start_date = (datetime.date.today() - datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    elif button_id == '30-days-btn':
        start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    elif button_id == '3-months-btn':
        start_date = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    elif button_id == '6-months-btn':
        start_date = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    elif button_id == 'all-time-btn':
        start_date = "2020-01-01"
    elif button_id == 'submit-btn':
        # Use the custom date range from the DatePicker
        start_date = start_date
        end_date = end_date

    # Fetch workouts and create table and chart (same logic as before)
    try:
        with WhoopClient(USERNAME, PASSWORD) as client:
            workouts = client.get_cycle_collection(start_date=start_date)
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
            "Score State": workout.get("score_state"),
            "Strain": strain,
            "Average Heart Rate": score.get("average_heart_rate") if score else None,
            "Max Heart Rate": score.get("max_heart_rate") if score else None,
            "Kilojoules": score.get("kilojoule") if score else None,
    })
        strain_scores.append(strain)
        dates.append(workout.get("start"))

    columns = [{"name": i, "id": i} for i in workout_data[0].keys()] if workout_data else []
    
    # Prepare strain chart
    strain_chart = go.Figure(
        data=[go.Scatter(x=dates, y=strain_scores, mode='lines+markers')],
        layout=go.Layout(title="Strain Scores Over Time", xaxis={'title': 'Date'}, yaxis={'title': 'Strain Score'})
    )

    return f"Fetched {len(workouts)} workouts.", workout_data, columns, strain_chart

# Run the Dash app with Waitress if this script is run directly
serve(app.server, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
