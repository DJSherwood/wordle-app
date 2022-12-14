# import libraries
import pandas as pd
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px

# Data Load Section 
######################################################################
df = pd.read_csv('auto_wordle_scores.csv')
# limit to the puzzle in which we last have words (396)
df = df[ (df['PuzzleNum'] != 420) & 
         (df['PuzzleNum'] != 421) &
         (df['Difficulty'] != 'Undefined')].copy()
# make player list
player_list = ['Da.M','Ka.W','St.S','Ca.W','Da.S','Ka.S']
# focus on puzzles which have all 6 players
df1 = df[ df['Name'].isin(player_list) ].copy()
B = df1.groupby(['PuzzleNum']).agg({'Name':'count'}).reset_index()
C = B[ B['Name'] == 6 ].copy()
df2 = df1[ df1['PuzzleNum'].isin(C['PuzzleNum'].to_list())]
# static ranking data frame
ranking_df = df2.groupby(['Name']).agg({'Fails':'sum'}).reset_index()
ranking_df = ranking_df.sort_values(by=['Fails'], ascending=True)
# static total games data frame
total_games = df2.groupby(['Name','PuzzleNum']).size().reset_index().groupby('Name').count().reset_index()
# static fails by difficulty data frame
avg_fails = df2.groupby(['Name','Difficulty']).agg({'Fails': 'mean'}).reset_index().sort_values(['Name'])
# load predictions
preds = pd.read_csv('predictions.csv')
# load model output
model_output = pd.read_csv('BetaBinomialOut.csv')

# App Definition and Layout
######################################################################
app = dash.Dash(__name__, external_stylesheets= [dbc.themes.CYBORG])
# initialize server for gunicorn, I guess?
server = app.server
# Master Div
app.layout = dbc.Container([
    # this is the header
    dbc.Row([
        dbc.Col(html.H1("Wordle Ranking & Performance", className='text-center my-4 text-success'), width=12)
    ]),
    dbc.Row([
        dbc.Col([
            html.P("Player Selection"),
            dcc.Dropdown(id='crossfilter-xaxis-column', options=[
                {'label': i, 'value': i} for i in player_list
            ],
                className="mr-3",
                value='Da.M'
            ),
            dbc.Card([
                dbc.CardGroup([
                    dbc.Card([
                        dbc.CardHeader([html.P("Number of Wordles Used")]), 
                        dbc.CardBody([html.H2(id="total-games-played")])
                        ])
                ]),
                dbc.CardGroup([
                    dbc.Card([
                        dbc.CardHeader([html.P("Actual Avg. Fails on Easy Wordles")]),
                        dbc.CardBody([html.H2(id='avg-fails-easy')])
                    ]),
                    dbc.Card([
                        dbc.CardHeader([html.P("Actual Avg. Fails on Hard Wordles")]),
                        dbc.CardBody([html.H2(id='avg-fails-hard')])
                    ])
                ]),
                dbc.CardGroup([
                    dbc.Card([
                        dbc.CardHeader([html.P("Predicted Avg. Fails on Easy Wordles")]),
                        dbc.CardBody([html.H2(id='model-preds-easy')])
                    ]),
                    dbc.Card([
                        dbc.CardHeader([html.P("Predicted Avg. Fails on Hard Wordles")]),
                        dbc.CardBody([html.H2(id='model-preds-hard')])
                    ])
                ])
            ])
        ],
        lg=5, className='border border-secondary py-2 mx-3'
        ),
        dbc.Col([
            html.P("Player Ranking"),
            dcc.Graph(
                id='bars-fail-total', 
                figure=px.bar(
                    ranking_df,
                    x="Fails",
                    y="Name",
                    color="Name",
                    text_auto=True
                    ).update_layout(
                        {'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                        'showlegend': False,
                        'font_color': "white"}))
        ],
        lg=5, className='border border-secondary py-2 mx-3'
        )
    ]),
    dbc.Row([
        dbc.Col([
            html.P("Predicted Performance"),
            dcc.Graph(id='model-output',figure={})
        ],
        lg=5, className='border border-secondary py-2 mx-3'
        ),
        dbc.Col([
            html.P("Actual Performance"),
            dcc.Graph(id='bars-fail-distribution', figure={})
        ],
        lg=5, className='border border-secondary py-2 mx-3'
        )
    ], className='mt-lg-5')
],
    className='px-2'
)

# # update bars-fail-distribution
@app.callback(
    Output('bars-fail-distribution', 'figure'),
    Input('crossfilter-xaxis-column', 'value')
)
def update_distplot(value):
    # input filters df onto a single name
    filtered_df = df2[ df2.Name == value ].dropna()
    fig = px.histogram(
        filtered_df, 
        x="Fails",
        color="Difficulty", 
        facet_col="Difficulty",
        text_auto=True
    )
    # now update the figture with a click
    fig.update_layout(
        {'plot_bgcolor': 'rgba(0, 0, 0, 0)',
         'paper_bgcolor': 'rgba(0, 0, 0, 0)',
         'showlegend': False,
         'font_color': "white"
        }
    )
    
    fig.update_yaxes(range=[0.0, 40.0], showgrid=False)
    fig.update_xaxes(showgrid=False)

    return fig

@app.callback(
    Output('model-output', 'figure'),
    Input('crossfilter-xaxis-column', 'value')
)
def update_density(value):
    filtered_df = model_output[ model_output.Name == value ]
    fig = px.area(
        filtered_df, 
        x="Fails", 
        y="Density",
        color="Difficulty",
        facet_col="Difficulty"
    )
    # now update the figure with a click
    fig.update_layout(
        {'plot_bgcolor': 'rgba(0, 0, 0, 0)',
         'paper_bgcolor': 'rgba(0, 0, 0, 0)',
         'showlegend': False,
         'font_color': "white"
        }
    )
    fig.update_yaxes(range=[0.0, 0.5],showgrid=False)
    fig.update_xaxes(showgrid=False)
    
    return fig

# update total-games-played
@app.callback(
    Output('total-games-played', 'children'),
    Input('crossfilter-xaxis-column', 'value')
)
def update_total_games(selected_player):
    filtered_value = total_games[ total_games.Name == selected_player ]['PuzzleNum'].values
    return '{}'.format(filtered_value[0])

# update avg-fails
@app.callback(
    Output('avg-fails-easy', 'children'),
    Input('crossfilter-xaxis-column', 'value')
)
def update_avg_fails(selected_player):
    filtered_value = avg_fails[ avg_fails.Name == selected_player]['Fails'].values
    return '{:.2f}'.format(filtered_value[0])

# update avg-fails
@app.callback(
    Output('avg-fails-hard', 'children'),
    Input('crossfilter-xaxis-column', 'value')
)
def update_avg_fails(selected_player):
    filtered_value = avg_fails[ avg_fails.Name == selected_player]['Fails'].values
    return '{:.2f}'.format(filtered_value[1])

# update model predictions
@app.callback(
    Output('model-preds-easy','children'),
    Input('crossfilter-xaxis-column', 'value')
)
def update_model_preds(selected_player):
    filtered_value = preds[ preds.Name == selected_player]['prediction'].values
    return '{:.2f}'.format(filtered_value[0])

@app.callback(
    Output('model-preds-hard','children'),
    Input('crossfilter-xaxis-column', 'value')
)
def update_model_preds(selected_player):
    filtered_value = preds[ preds.Name == selected_player]['prediction'].values
    return '{:.2f}'.format(filtered_value[1])


if __name__ == '__main__':
    app.run_server(debug=True)