from pymongo import MongoClient
from api_config import en_key,clientid,userid
from pyechonest import config as ENconfig
from pyechonest import artist as ENartist
from pyechonest.util import EchoNestAPIError
import time
import json
import pygn
import redis
import pdb
import cPickle as pickle

ENconfig.ECHO_NEST_API_KEY=en_key
redcon = redis.StrictRedis()

def get_mongo_db():
  conn = MongoClient()
  return conn.outsidehacks

def get_all_artists():
  db = get_mongo_db()
  return db.sets.distinct('artist_name')

def get_artist_sim(artist):
  artist = artist.lower()
  key = 'sim_dict:'+artist
  simd = redcon.get(key)

  if simd:
    return json.loads(simd)

  simd = {}

  try_again = True
  scores = []
  while try_again:
    try:
      en_artist = ENartist.Artist(artist)
      similar = en_artist.get_similar(results=100)
      cnt = 0
      for sim in similar:
        score = 100 - cnt
        score += int(get_artist_genre_sim(artist,sim.name))
        scores.append((sim.name,score))
        cnt+=1
      try_again = False
    except EchoNestAPIError as e:
      print '.'
      if e.code == 3:
        print 'rate limit error. sleeping...'
        time.sleep(15)
      else:
        print e
        try_again = False

  for (martist,sim) in scores:
    if not martist:
      pdb.set_trace()

    simd[martist]=sim

  redcon.set(key,json.dumps(simd))
  return simd

def get_genre(artist):
  key = 'genre:' + artist.lower()
  genre = redcon.get(key)
  if not genre:
    try:
      artist = artist.encode('utf-8')
    except Exception as e:
      artist = artist.decode('ascii','ignore')
    start = time.time()
    res = pygn.searchArtist(clientid,userid,artist)
    #print '\t\ttook %0.2f seconds' %(time.time()-start)
    try:
      genre2 = res['genre']['2']['TEXT'].lower()
    except (KeyError,TypeError) as e:
      genre2 = ''
    try:
      genre3 = res['genre']['3']['TEXT'].lower()
    except (KeyError,TypeError) as e:
      genre3 = ''
    genre = json.dumps((genre2,genre3))
    redcon.set(key,genre)
  elif genre == -1:
    return None
  else:
    genre = json.loads(genre)
  return genre

def get_artist_genre_sim(a1,a2):
  try:
    a1=a1.encode('utf-8').lower()
    a2=a2.encode('utf-8').lower()
  except Exception as e:
    print 'fucking encodings...'
    raise e

  arts = sorted([a1,a2])
  key = 'sim:'+'\t'.join(arts)
  sim = redcon.get(key)
  if not sim:
    sim = 0
    g1 = get_genre(arts[0])
    g2 = get_genre(arts[1])

    if g1[0] == g2[0]:
      sim +=10
    if g1[1] == g2[1]:
      sim+=25
    redcon.set(key,sim)
  return sim
  
def get_all_sim_dicts():
  simds_file = 'all_sim_dicts.pkl'
  if False and os.path.isfile(simds_file):
    return pickle.load(open(simds_file,'r'))
  else:
    artist_sims = {}
    artists = get_all_artists()
    for artist in artists:
      start = time.time()
      artist = artist.encode('utf-8')
      sim = get_artist_sim(artist)
      lower_sim = {}
      for aa in sim.keys():
        lower_sim[aa.lower()] = sim[aa]
        
      artist_sims[artist.lower()] = lower_sim
    pickle.dump(artist_sims,open(simds_file,'w'))
    return artist_sims

def augment_sim_dicts(sim_dicts):
  simds_file = 'all_sim_dicts.pkl'
  all_keys = redcon.keys('genre:*')
  oas = sim_dicts.keys()
  for oa in oas:
    print oa
    oag_key = 'genre:' + oa.lower()
    oag = redcon.get(oag_key)
    if not oag:
      continue
    oag = json.loads(oag)[1]
    for gk in all_keys:
      newa = gk.split('genre:')[1]
      if newa == oa:
        continue
      newa_g = redcon.get(gk)
      if not newa_g: 
        continue
      newa_g = json.loads(newa_g)[1]
      if oag == newa_g and sim_dicts[oa].get(newa,-1) == -1:
        sim_dicts[oa][newa]=25
  pickle.dump(sim_dicts,open(simds_file,'w'))
  return sim_dicts

ss= get_all_sim_dicts()
ss= augment_sim_dicts(ss)
