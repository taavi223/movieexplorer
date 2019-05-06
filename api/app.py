import math
import random
import itertools
import operator
import os
import numpy as np
import pandas as pd
import flask
from flask import request, jsonify


#######################
# CONFIGURE FLASK APP #
#######################

DEBUG = False

app = flask.Flask(__name__)
if DEBUG:
    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config["DEBUG"] = DEBUG
data_path = os.path.join(os.path.dirname(__file__), "../data")


#############
# LOAD DATA #
#############

# Load and normalize the vector for the starting location
STARTING_VECTOR = np.load(os.path.join(data_path, "starting_location.npy"))
STARTING_VECTOR = STARTING_VECTOR / np.linalg.norm(STARTING_VECTOR)

# Load the latent vectors for all movies
MOVIE_VECTORS = np.load(os.path.join(data_path, "movie_vectors.npy"))

# Load metadata for all movies and split fields comma separated fields 
MOVIE_DATA = pd.read_csv(os.path.join(data_path, "movie_data.csv")).fillna("").sort_values("popularityLastYear", ascending=False)
MOVIE_DATA["genres"] = MOVIE_DATA["genres"].str.split(',')
MOVIE_DATA["languages"] = MOVIE_DATA["languages"].str.split(',')
MOVIE_DATA["directors"] = MOVIE_DATA["directors"].str.split(',')
MOVIE_DATA["actors"] = MOVIE_DATA["actors"].str.split(',')
MOVIE_DATA["youtubeTrailerIds"] = MOVIE_DATA["youtubeTrailerIds"].str.split(',')
MOVIE_DATA.set_index("item_index")


###########################
# MOVIEEXPLORER FUNCTIONS #
###########################

def get_item_vector(item_or_items):
    try:
        return MOVIE_VECTORS[item_or_items, :]
    except IndexError:
        return MOVIE_VECTORS[list(item_or_items), :]
        #raise AttributeError(item_or_items)

    
def get_delta_vector(vector, location):
    if len(vector.shape) == 1:
        return (vector / np.dot(vector, location)) - location
    elif len(vector.shape) == 2:
        return (vector / np.dot(vector, location)[:, None]) - location[None, :]
    else:
        raise ValueError("vector argument must be 1d or 2d array")

def update_vector_with_feedback(location, feedback, round_num):
    """
    `location` is an np.array of some number of dimensions
    `feedback` is a dictionary of item-score feedback, with scores of 1, 0, or -1 indicating positive, no, and negative feedback, respectively.
    `round_num` is the round number for the current round
    
    """
    
    delta_vecs_norm = np.linalg.norm(get_delta_vector(get_item_vector(feedback.keys()), location), axis=1)
        
    total_delta_vec_norm = sum(delta_vecs_norm)
    min_delta_vec_norm = min(delta_vecs_norm)
    max_delta_vec_norm = max(delta_vecs_norm)
    
    distance_numerator = 0
    distance_denominator = 0
    direction_numerator = location * 0
    direction_denominator = 0
    selected_delta_vec_norm = 0
    
    #####################
    # POSITIVE FEEDBACK #
    #####################

    pos_vecs = get_item_vector([k for k, v in feedback.items() if v == 1])
    pos_weight = math.sqrt(len(pos_vecs))
    
    # Get the delta vectors and the sum of their magnitudes for the given items
    pos_delta_vecs = get_delta_vector(pos_vecs, location)
    pos_delta_vecs_norm_sum = sum(np.linalg.norm(pos_delta_vecs, axis=1))
    
    ## DIRECTION CALCULATIONS ##
    
    direction_numerator += np.sum(pos_delta_vecs, axis=0) * pos_weight
    direction_denominator += pos_delta_vecs_norm_sum * pos_weight
    
    ## DISTANCE CALCULATIONS ##

    distance_numerator += pos_delta_vecs_norm_sum
    distance_denominator += len(pos_vecs)
    
    ## CONFIDENCE CALCULATIONS ##

    selected_delta_vec_norm += pos_delta_vecs_norm_sum
    
    #####################
    # NEGATIVE FEEDBACK #
    #####################
    
    neg_vecs = get_item_vector([k for k, v in feedback.items() if v == -1])
    neg_weight = 0.5 * math.sqrt(len(neg_vecs))
    
    # Get the delta vectors for the negative items, flip their direction, and
    # swap their relative lengths. Closer items should push us farther away than
    # distant items. 
    
    neg_delta_vecs = get_delta_vector(neg_vecs, location)
    neg_delta_vecs_norm = np.linalg.norm(neg_delta_vecs, axis=1)
    neg_delta_vecs *= ((neg_delta_vecs_norm - max_delta_vec_norm - min_delta_vec_norm) / neg_delta_vecs_norm)[:, None]
    neg_delta_vecs_norm_sum = sum(neg_delta_vecs_norm)
    
    ## DIRECTION CALCULATIONS ##
        
    direction_numerator += np.sum(neg_delta_vecs, axis=0) * neg_weight
    direction_denominator += neg_delta_vecs_norm_sum * neg_weight
    
    ## DISTANCE CALCULATIONS ##

    distance_numerator += neg_delta_vecs_norm_sum
    distance_denominator += len(neg_vecs)
    
    ## CONFIDENCE CALCULATIONS ##

    selected_delta_vec_norm += neg_delta_vecs_norm_sum

    ##########################
    # UPDATE LOCATION VECTOR #    
    ##########################
    
    if not direction_denominator or not distance_denominator:
        return location
    
    direction = direction_numerator / direction_denominator
    distance = distance_numerator / distance_denominator
    confidence = (
        (1 / round_num) +
        (min(1.0, selected_delta_vec_norm / total_delta_vec_norm) ** 0.33) *
        ((round_num - 1) / round_num)
    )
    
    new_location = location + (direction * distance * confidence)
    return new_location / np.linalg.norm(new_location)
    
def sort_items(location, items, breadth):
    vectors = get_item_vector(items)
    
    dot = np.dot(vectors, location)
    cos = dot / (np.linalg.norm(vectors, axis=1) * np.linalg.norm(location))
            
    if breadth == "wide":
        scores = dot * cos ** 1
    elif breadth == "medium":
        scores = dot * cos ** 2
    elif breadth == "narrow":
        scores = dot * cos ** 3
    else:
        raise ValueError("breadth must be set to 'wide', 'medium', or 'narrow'")

    # Return item indices in descending order of score
    return np.array(items)[np.argsort(scores)[::-1]]
    
def min_distance(item, otherItems):
    diffs = get_item_vector(otherItems) - get_item_vector(item)[None, :]
    return min(np.sum(np.abs(diffs), axis=1), default=-random.random())

def select_diverse_items(selected, items, n, limit, dropout):
    stop_size = len(selected) + n
    while len(selected) < stop_size:
        candidates = list(itertools.islice((
            (i, min_distance(i, selected)) for i in items
            if i not in selected and random.random() >= dropout
        ), limit))
        s = sorted(candidates, key=operator.itemgetter(1), reverse=True)
        selected.append(s[0][0])

def frac(v):
    return int(v * len(MOVIE_DATA) / 10000)

def get_remaining_items(displayed, limit):
    return list(set(MOVIE_DATA.index[:limit]).difference(displayed))

def get_items_around_location(location, displayed, round_num):
    selected = []
    if round_num == 1:
        print("Round 1, sorting items wide.")
        items = get_remaining_items(displayed, frac(1000))    
        sorted_items = sort_items(location, items, "wide")
        select_diverse_items(selected, sorted_items, 3, frac(20), 0.5)
        select_diverse_items(selected, sorted_items, 3, frac(80), 0.5)
        select_diverse_items(selected, sorted_items, 4, frac(200), 0.5)
    
    elif round_num == 2:
        print("Round 2, sorting items medium.")
        items = get_remaining_items(displayed, frac(2000))   
        sorted_items = sort_items(location, items, "medium")
        select_diverse_items(selected, sorted_items, 3, frac(10), 0.5)
        select_diverse_items(selected, sorted_items, 3, frac(40), 0.5)
        select_diverse_items(selected, sorted_items, 4, frac(100), 0.5)
    
    elif round_num >= 3:
        items = get_remaining_items(displayed, frac(10000))    
        print("Round 3+, sorting items narrow.")
        sorted_items = sort_items(location, items, "narrow")
        select_diverse_items(selected, sorted_items, 3, frac(5), 0.5)
        select_diverse_items(selected, sorted_items, 3, frac(20), 0.5)
        select_diverse_items(selected, sorted_items, 4, frac(50), 0.5)    
    
    else:
        raise ValueError("round_num must be greater than 0")
    
    return selected
    
        
def get_movie_data(item_or_items):
    try:
        return MOVIE_DATA.loc[item_or_items].to_dict("records")
    except TypeError:
        return MOVIE_DATA.loc[list(item_or_items)].to_dict("records")
    
    
#######
# API #
#######
    
@app.route('/api', methods=['POST'])
def home():
    if not request.is_json:
        return "Error: JSON input required."
    
    data = request.get_json()
    
    if "rounds" not in data:
        return "Error: rounds must be specified."
        
    exclude = set(data.get("exclude", []))
    vec = STARTING_VECTOR
    i = 1
    print("Calculating vector...")
    for feedback in data["rounds"]:
        print("Updating vector with round %d feedback" % i)
        feedback = {int(k): v for k, v in feedback.items()}
        exclude.update(feedback.keys())
        vec = update_vector_with_feedback(vec, feedback, i)
        i += 1
    
    selected = get_items_around_location(vec, exclude, i)
    
    return jsonify(candidates=get_movie_data(selected))


if __name__ == "__main__":
    app.run(host='0.0.0.0')