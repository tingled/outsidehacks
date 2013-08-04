from flask import Flask,jsonify
from pymongo import MongoClient
from random import shuffle, random
import utils
import cPickle as pickle

app = Flask(__name__)

sim_dicts = pickle.load(open('all_sim_dicts.pkl','r'))

db = utils.get_mongo_db()

@app.route('/get_schedule',methods=['GET','POST'])
def get_schedule():
  if request.method == 'POST':
    data = json.loads(request.data)
    
    outside_artists = utils.get_all_artists()
    scores = []
    for oa in outside_artists:
      oa_dict = sim_dicts[oa]
      cur_oa_score = 0
      for (artist,score) in data:
        artist=artist.lower()
        cur_oa_score += score * oa_dict.get(artist,0)
      scores.append(oa,cur_oa_score)
    
    scores.sort(key=lambda x:x[1],reverse=True)
    sets = make_schedule_from_scores(scores)
    # save this somewhere
  else:
    pass
    # lookup

  #TODO return json

def check_overlap(set_d1,set_d2):
  if set_d1['day'] != set_d2['day']:
    return False

  if set_d1['start'] >= set_d2['start'] and set_d1['start'] < set_d2['end']:
    return True
  if set_d2['start'] >= set_d1['start'] and set_d2['start'] < set_d1['end']:
    return True

  return False

def get_artist_set(artist):
  return db.sets.find_one({'artist_name_lower':artist.lower()})

def clean_sort_sets(sets):
  sets.sort(key = lambda x: (x['day'],x['start']))
  for aset in sets:
    del aset['_id']
  return sets

def make_schedule_from_scores(scores):
  """ scores is a list of (outside_artist,score) tuples """
  user_sets = []
  scores.sort(key=lambda x:x[1],reverse=True)
  for (artist,score) in scores:
    the_set = get_artist_set(artist)
    to_add = True
    for booked_set in user_sets:
      if check_overlap(booked_set,the_set):
        to_add = False
        break
    if to_add:
      user_sets.append(the_set)
  #TODO save this
  clean_sort_sets(user_sets)
  return user_sets

@app.route('/debug')
@utils.crossdomain(origin='*')
def debug():
  sets = list(db.sets.find())
  shuffle(sets)
  sets = sets[:10]
  sets.sort(key = lambda x: (x['day'],x['start']))
  setlist = []
  
  setlist = clean_sort_sets(sets[:10])
  return jsonify({"setlist":setlist})

@app.route('/debug2')
@utils.crossdomain(origin='*')
def debug2():
  oa = utils.get_all_artists()
  shuffle(oa)
  scores =[]
  for artist in oa[:40]:
    scores.append((artist,random()))
    
  setlist=make_schedule_from_scores(scores)

  return jsonify({"setlist":setlist})

if __name__=="__main__":
  app.run(host='0.0.0.0',port=8080,debug=True)
