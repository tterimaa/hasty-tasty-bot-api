from flask import Flask
from flask import request
from flask import jsonify, make_response
from aito.client import RecommendRequest, GenericQueryRequest
from aito.schema import AitoStringType, AitoTextType, AitoDelimiterAnalyzerSchema, AitoTableSchema, AitoColumnLinkSchema, AitoDatabaseSchema
from aito.client import AitoClient
import pandas as pd
import aito.api as aito_api
import os

# Fill in your Aito instance credentials
AITO_INSTANCE_URL = 'https://artsyjunction2020.aito.app'
AITO_API_KEY = os.environ.get('AITO_API_KEY', None)

client = AitoClient(instance_url=AITO_INSTANCE_URL, api_key=AITO_API_KEY)

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello world!"

@app.route("/json", methods=["POST"])
def json_example():
    # Validate the request body contains JSON
    if request.is_json:

        # Parse the JSON into a Python dictionary
        
        user_list = request.get_json()
        users={}
        for user in user_list["users"]: 
            users[user["id"]] = {
                "cuisine" : {"$has":user["cuisine"][0]},
                "payment" : {"$has":user["payment"]},
            }

        #res = make_response(jsonify(users), 200)
        #return res
        queries = [
            {
            "from": "ratings",
            "where": {
                "placeID": {"payment": pref["payment"]},
                "userID": {"cuisine": pref["cuisine"]}
            },
            "recommend": "placeID",
            "goal": {"rating": 2},
            "select":["$p", "placeID"],
            "limit": 100
            } for usr, pref in users.items()]
        res = [aito_api.recommend(client=client, query=query).to_json_serializable() for query in queries]
        results = {usr: res[idx]["hits"] for idx, usr in enumerate(users)}
        
        recom = pd.concat([pd.DataFrame(value).set_index("placeID") for key,value in results.items()], axis=1).dropna(thresh=2, axis=1)
        recom["Total"] = recom.fillna(0).mean(axis=1)
        #top_recom = list(recom.nlargest(10, ['Total']).index)
        top_recom = recom.nlargest(5,"Total")["Total"].to_dict()
        print(top_recom)

        queries = [
            {"from": "places",
            "where": {
                "placeID": place
                },
            "select": ["name", "cuisine","latitude", "longitude", "payment"]
            }
            for place in top_recom.keys()]
        responses = [aito_api.generic_query(client=client, query=query).to_json_serializable()["hits"][0] for query in queries]
        print(responses)
        responses = {value: responses[idx] for idx,value in enumerate(top_recom.values())}
        #responses = {prob: res[idx]["hits"] for idx, usr in enumerate(users)}
        res = make_response(jsonify(responses), 200)        
        return res

    else:

        # The request body wasn't JSON so return a 400 HTTP status code
        return "Request was not JSON", 400

if __name__ == "__main__":
    app.run(threaded=True, port=5000)