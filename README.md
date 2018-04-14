# h4s2018-backend
The backend application for MittMedia DMU's contribution to Hack 4 Sweden 2018

## Purpose
This backend application queries the riksdag.se open data API's and serves all the SOU _(Statlig Offentlig Utredning)_ "topics" on the `/topics` endpoint. Then using graph logic we identify which documents are related to a specific SOU identifier.
```
GET /topics
```

The `/documents`-endpoint then serves all the related documents for a given `doc_id` like `SOU 2016:89`:
```
GET /documents?doc_id=SOU%202016:89
```

## TODO:
- Secure the endpoints.
- Caching?
- Setup a message queue to pass events to the frontend
- Add a background worker that periodically refreshes the latest data from the riksdag.se API.
- Move database credentials into ENV variables.

Pull requests are welcome

## Prerequisits
- Python 3
- neo4j database
- `pip install -r requirements.txt`

## Running the app
- Start neo4j (`bin/neo4j start` from the neo4j folder)
- Configure the database credentials in app.py
- `python app.py`
