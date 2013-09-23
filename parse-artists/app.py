from flask import Flask,jsonify,request
import json
from pymongo import MongoClient
from random import shuffle, random, sample
import utils
import cPickle as pickle
import redis

app = Flask(__name__)
sim_dicts = pickle.load(open('all_sim_dicts.pkl','r'))
db = utils.get_mongo_db()
redcon = redis.StrictRedis()

distances = {
  ('Lands End','Sutro'):1000,
  ('Lands End','The Barbary'):2000,
  ('Lands End','The Dome'):800,
  ('Lands End','Twin Peaks'):3500,
  ('Lands End','Panhandle'):3000,
  ('Panhandle','Sutro'):3000,
  ('Panhandle','The Barbary'):1200,
  ('Panhandle','The Dome'):2700,
  ('Panhandle','Twin Peaks'):500,
  ('Sutro','The Barbary'):1700,
  ('Sutro','The Dome'):1000,
  ('Sutro','Twin Peaks'):3000,
  ('The Barbary','The Dome'):1300,
  ('The Barbary','Twin Peaks'):1400,
  ('The Dome','Twin Peaks'):2700 }

def get_distance(s1,s2):
  if s1 == s2:
    return 0
  ss = [s1,s2]
  ss.sort()
  ss = tuple(ss)
  return distances[ss]

def sum_artists(data):
  artist_plays = {}
  max_seen = 0

  for k,v in data.items():
    v = v.lower()
    cur_count = artist_plays.get(v,0)+1
    artist_plays[v] = cur_count
    max_seen = max(max_seen,cur_count)

  for k,v in artist_plays.items():
    artist_plays[k] = artist_plays[k]/float(max_seen)

  artist_plays = artist_plays.items()
  artist_plays.sort(key=lambda x: x[1],reverse=True)
  return artist_plays

def calc_ua_scores(listen_scores):
  """ calculates user to artist scores. takes artist plays
  and mulitplies them by artist to artist sim scores """
  outside_artists = utils.get_all_artists()
  scores = []
  for oa in outside_artists:
    oa = oa.lower()
    if oa not in sim_dicts:
      continue
    oa_dict = sim_dicts[oa]
    cur_oa_score = 0
    for (artist,listen_score) in listen_scores:
      artist=artist.lower()
      if oa == artist:
        sim_score = 150
      else:
        sim_score = oa_dict.get(artist,random())
      cur_oa_score += listen_score * sim_score
    scores.append((oa,cur_oa_score))

  scores.sort(key=lambda x:x[1],reverse=True)
  return scores

@app.route('/get_schedule',methods=['GET','POST'])
@utils.crossdomain(origin='*')
def get_schedule():
  if request.method == 'POST':
    data = request.form
    scores = sum_artists(data)
    best_scores = calc_ua_scores(scores)

    shuf_scores1 = list(best_scores)
    shuf_scores1 = sample(shuf_scores1[:10],10) + shuf_scores1[10:]

    shuf_scores2 = list(best_scores)
    shuf_scores2 = sample(shuf_scores2[:10],10) + shuf_scores2[10:]

    shuf_scores3 = list(best_scores)
    shuf_scores3 = sample(shuf_scores3[:10],10) + shuf_scores3[10:]
    
    redcon.set('tmpscores',json.dumps(best_scores))
    best_schedule = make_schedule_from_scores(best_scores)
    #shuf_schedule1 = make_schedule_from_scores(shuf_scores1)
    #shuf_schedule2 = make_schedule_from_scores(shuf_scores2)
    #shuf_schedule3 = make_schedule_from_scores(shuf_scores3)

    redcon.set('tmp',json.dumps(best_schedule))
    #print best_schedule
    return ''
    # save this somewhere
  else:
    setlist = json.loads(redcon.get('tmp'))
    best_scores = json.loads(redcon.get('tmpscores'))

    shuffs = []
    shuff_scores = []
    shuff_scheds = []
    for i in range(7): 
      num_shuf = 15
      shuffs.append(list(best_scores))
      shuff_scores.append(sample(shuffs[i][:num_shuf],num_shuf) + shuffs[i][num_shuf:])
      shuff_scheds.append(make_schedule_from_scores(shuff_scores[i]))
    
    best_schedule = make_schedule_from_scores(best_scores)

    lazy_schedule = make_lazy_schedule_from_scores(best_scores)
    lazy_distance = schedule_to_distance(lazy_schedule)

    min_distance = 100
    mid_sched=None
    for sched in shuff_scheds:
      dist = schedule_to_distance(sched)
      if dist<min_distance:
        mid_sched = sched
        min_distance = dist

    return jsonify({"setlist":setlist,'distance':schedule_to_distance(setlist),'mid_setlist':mid_sched,'mid_distance':min_distance,'lazy_setlist':lazy_schedule,'lazy_distance':lazy_distance})

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
  #scores.sort(key=lambda x:x[1],reverse=True)
  max_score=0
  for (artist,score) in scores:
    max_score = max(max_score,score)

  for (artist,score) in scores:
    the_set = get_artist_set(artist)
    if not the_set:
      continue
    to_add = True
    for booked_set in user_sets:
      if check_overlap(booked_set,the_set):
        to_add = False
        break
    if to_add:
      the_set['score']=score/float(max_score)
      user_sets.append(the_set)
  user_sets = clean_sort_sets(user_sets)
  return user_sets

def make_lazy_schedule_from_scores(scores):
  """ scores is a list of (outside_artist,score) tuples """
  user_sets = []
  #scores.sort(key=lambda x:x[1],reverse=True)
  max_score=0
  for (artist,score) in scores:
    max_score = max(max_score,score)

  day_stage={}
  for (artist,score) in scores:
    the_set = get_artist_set(artist)
    if not the_set:
      continue

    if not day_stage.get(the_set['day']):
      day_stage[the_set['day']] = the_set['stage']
    else:
      if day_stage[the_set['day']] != the_set['stage']:
        continue
    
    to_add = True
    for booked_set in user_sets:
      if check_overlap(booked_set,the_set):
        to_add = False
        break
    if to_add:
      the_set['score']=score/float(max_score)
      user_sets.append(the_set)

  user_sets = clean_sort_sets(user_sets)
  return user_sets

def schedule_to_distance(schedule):
  total_dist = 0
  prev_set = schedule[0]

  for cur_set in schedule[1:]:
    if cur_set['day']==prev_set['day']:
      total_dist += get_distance(prev_set['stage'],cur_set['stage'])
   
  return total_dist/5280.

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

  return jsonify({"setlist":setlist,'distance':schedule_to_distance(setlist)})

if __name__=="__main__":
  app.run(host='0.0.0.0',port=8080,debug=True)
