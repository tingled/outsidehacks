import requests
import pdb
import re
import json

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
