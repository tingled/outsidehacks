import requests
import pdb
import re
import os
import json
import codecs
from pymongo import MongoClient

def get_mongo_db():
  client =  MongoClient()
  return client.outsidehacks

def parse_artists():
  url = 'http://lineup.sfoutsidelands.com/?sort=alpha'
  page = requests.get(url)
  search_str='<a href="(http://lineup.sfoutsidelands.com/band/.*?)"'
  artist_urls = re.findall(search_str,page.text)
  return artist_urls

def parse_artist_page(url):
  page = requests.get(url)
  search_name = '>(.*?)</h1>'
  search_time = '<a href="/events/.*?>(.*?)</a>\s*on (.*?)<br>'

  name = re.findall(search_name,page.text)
  if len(name)>1:
    pdb.set_trace()
  name = name[0]

  set_time = re.findall(search_time,page.text)
  if not set_time:
    return None

  return (name,set_time)

def old_get_artist_info():
  """whoops! forgot to get duration of set... now for a different approach"""
  artist_urls = parse_artists()
  artist_info = []
  for artist_url in artist_urls:
    info = parse_artist_page(artist_url)
    if info:
      artist_info.append(info)

  json.dump(artist_info,open('set_data.json','w'))

def parse_day(day):
  sets = []
  stages = {'1':'Lands End','2':'Sutro','3':'Twin Peaks','4':'Panhandle','5':'The Dome','6':'The Barbary'}

  url = 'http://lineup.sfoutsidelands.com/events/2013/08/' + day + '/'
  page = requests.get(url)
  search_str = 'href="/band/.*?">(.*?)</a>.*?>(\d.*? - .*?)</span></div>'
  for line in page.text.split('\n'):
    if line.find('ds-stage') >=0:
      stage = stages[re.findall('ds-stage(\d)',line)[0]]
    match=re.findall(search_str,line)
    if match:
      match=match[0]
      name = match[0]
      (start,end) = match[1].split(' - ')
      curd = {'artist_name':name,'start':start,'end':end,'day':day,'stage':stage}
      sets.append(curd)
  return sets

def parse_festival():
  data_file = 'set_data.json'
  if os.path.isfile(data_file):
    sets = json.load(open(data_file,'r'))
  else:
    days = ['09','10','11']
    sets = []
    for day in days:
      sets+=parse_day(day)

    json.dump(sets,open(data_file,'w'))
  return sets

def insert_into_mongo():
  sets = parse_festival()
  db = get_mongo_db()
  sets_coll = db.sets
  for aset in sets:
    aset['artist_name_lower'] = aset['artist_name'].lower()
    sets_coll.insert(aset) 

if __name__=='__main__':
  insert_into_mongo()
