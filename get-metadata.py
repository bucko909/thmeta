#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import os.path
import re
import urllib2
import sys
import entities
reload(sys)
sys.setdefaultencoding('utf-8')

import sqlalchemy

from model import *

PAGES = "pages"
DATA = "data"

class NotAPage(Exception):
	pass

class ParseException(Exception):
	pass

class MaybeBadType(ParseException):
	pass

class logger:
	stack = []
	def __init__(self, f):
		self.__f__ = f
	def __call__(self, *args, **kwargs):
		logger.stack += [ u"%s(%s)" % (self.__f__.__name__, u", ".join([u"%s" % v for v in args] + [u"%s=%s" % (k, v) for (k, v) in kwargs.items() ])) ]
		try:
			return self.__f__(*args, **kwargs)
		except NotAPage, e:
			raise
		except Exception, e:
			stack()
			print u"exception:%r" % e
			import traceback
			print traceback.format_exc()
		finally:
			logger.stack.pop()

class fallback:
	fallback_fns = list()
	read_urls = dict()
	def __init__(self, f):
		self.__f__ = f
	def __call__(self, *args, **kwargs):
		if args[0] in fallback.read_urls:
			return
		ret = None
		try:
			ret = self.__f__(*args, **kwargs)
		except NotAPage, e:
			pass
		except Exception, e:
			print stack(),
			print u"exception:%r" % e
			for other_f in fallback_fns:
				if other_f.__f__ == f:
					continue
				try:
					ret = other_f.__orig__(*args, **kwargs)
					break
				except Exception, e:
					pass
				else:
					break
		if ret:
			fallback.read_urls[args[0]] = True
			return ret



def stack():
	t = ''
	for s in logger.stack:
		print t + u"stack:%s" % s
		t += u'    '
	return t
def err(msg):
	print stack(),
	print u"error:%s" % msg
def warn(msg):
	print stack(),
	print u"warn:%s" % msg
def log(msg):
	print stack(),
	print u"log:%s" % msg

def get_page(page_no):
	candidates = session.query(Atwiki).filter(Atwiki.page_no == page_no).all()
	if candidates:
		return candidates[0]
	page = Atwiki(page_no)
	session.add(page)
	return page

names_cls = { Circle: CircleName, Album: AlbumName, Event: EventName }
def get(cls, name=None, page_no=None, url=None):
	name_cls = names_cls[cls]
	if url:
		page_no = url_page_no(url)
	if page_no:
		page = get_page(page_no)

	if page_no and name:
		candidates = session.query(cls).join(Atwiki).filter(or_(cls.names.any(name_cls.name == name), cls.pages.any(Atwiki.id == page.id))).all()
	elif page_no:
		candidates = session.query(cls).filter(cls.pages.contains(page)).all()
	else:
		candidates = session.query(cls).filter(cls.names.any(name_cls.name == name)).all()

	if len(candidates) == 1:
		obj = candidates[0]
	elif candidates:
		err(u"%s / %s does not uniquely define a obj" % (name, page_no))
		return
	else:
		obj = cls()
		session.add(obj)
	
	if page_no and page not in obj.pages:
		if obj.pages:
			warn(obj.names)
			warn(u"Adding page %s to %s with pages %s" % (page, obj, [(o, o.circle, o.album, o.event) for o in obj.pages]))
		obj.pages.append(page)
	add_name(obj, name)
	return obj

def add_name(obj, name):
	if not filter(lambda x: x.name == name, obj.names):
		if obj.names:
			log(u"Adding name %s to %s" % (name, obj))
		obj.names.append(names_cls[obj.__class__](name))

def url_page_no(url):
	m = re.match("http://www16.atwiki.jp/toho/pages/(\d+).html", url)
	if m:
		return int(m.group(1))
	else:
		return None

@logger
def fetch_page(givenurl):
	if 'cmd=edit' in givenurl or '?page=' in givenurl:
		raise NotAPage("Non-existent URL: %s" % givenurl)
	elif givenurl[0] == '/':
		warn("Local URL: %s" % givenurl)
		url = "http://www16.atwiki.jp" + givenurl
	elif givenurl[:7] == 'http://':
		url = givenurl
	else:
		raise NotAPage("Bad URL: %s" % givenurl)
	filename = url.replace("/", "_")
	full_path = "%s/%s" % (PAGES, filename)
	if not os.path.exists(full_path):
		log("Get page: " + url + " -> " + full_path)
		r = urllib2.Request(url, None, {'User-Agent': 'Mozilla'})
		d = urllib2.urlopen(r).read()
		f = open(full_path, "w")
		f.write(d)
		return unicode(d, 'utf8', errors='replace')
	else:
		f = open(full_path, "r")
		return unicode(f.read(), 'utf8', errors='replace')

get_page_re = re.compile(u'<title>東方同人CDwiki - (.*?)</title>.*<div id="main">(.*?)<div (?:id|class)="(?:plugin_comment|ad)">', re.DOTALL)
def get_main(page):
	try:
		return get_page_re.search(page).groups()
	except:
		print "page", page
		raise

album_url_re = re.compile('(<li>).*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>(?:[^\\(<\n]+\\(([^\\)<\n]+)\\)</li>)?')
@fallback
@logger
def read_circle(url, name=None, event=None):
	#log("Circle: %s (%s)" % (name, url))
	title, to_parse = get_main(fetch_page(url))
	albums = []
	if not name:
		name = title
	circle = get(Circle, name=name, url=url)
	if name != title:
		add_name(circle, title)

	for (li, url, album_name, alternative) in album_url_re.findall(to_parse):
		if li:
			t = 'album'
		else:
			t = 'maybe_album'
		albums += [(t, url, album_name, alternative)]
	if not albums:
		raise MaybeBadType("Empty circle")

	if event and not filter(lambda x: x == event, circle.events):
		# We'll get to the albums later
		circle.events.append(event)
	else:
		for (t, url, album_name, alternative) in albums:
			read_album(url, name=album_name, circle=circle)

	return circle

get_tables_re = re.compile("<table>(.*?)</table>", re.DOTALL)
get_album_title_re = re.compile('<h[23] id="id_.*?">(.*?)</h[23]>')
get_album_circle_re = re.compile(u'(?:サ[ー－]クル名?|ｻｰｸﾙ)[：:]+ ?<a href="(.*?)".*?>(.*?)</a>')
@fallback
@logger
def read_album(url, name=None, circle=None, event=None):
	#log("Album: %s (%s)" % (name, url))
	title, to_parse = get_main(fetch_page(url))
	match = get_album_circle_re.search(to_parse)
	if match:
		m_c_url = entities.unescape(match.group(1))
		c_page_no = url_page_no(m_c_url)
		m_c_name = entities.unescape(match.group(2))
		if circle:
			add_name(circle, match.group(2))
			if c_page_no not in circle.page_nos():
				raise ParseException(u"Circle %s has urls %s and %s" % (circle, circle.page_nos(), c_page_no))
				add_url(circle, m_c_url)
		else:
			circle = get(Circle, name=match.group(2), url=match.group(1))
	else:
		raise MaybeBadType("No circle for this album (though handed %s)" % circle)

	match = get_album_title_re.search(to_parse)
	if match and name and name != match.group(1):
		warn(u"Album name was %s, but page said %s" % (name, match.group(1)))
		names = [name, match.group(1)]
	elif match:
		names = [match.group(1)]
	else:
		raise MaybeBadType("No title for this album (though handed %s)" % name)
	album = get(Album, name=names[0], url=url)

	found_track = False
	for table in get_tables_re.findall(to_parse):
		# Now merge tracks
		names, data = parse_table(table)
		if names[0] != 'Number':
			raise MaybeBadType("First column of album is not track number")
		if names[1] != 'Track Name' and names[1] != 'Track name':
			raise MaybeBadType("Second column of album is not track name")
		# Confident, now.
		if not data:
			raise ParseException("Found empty table")

		old_val = None
		tracks = list()
		for row in data:
			row_data = dict()
			for i in range(1,len(names)):
				row_data[names[i]] = row[i]
			if row[0] == old_val:
				if row_data['Track Name'] != tracks[-1][0]['Track Name']:
					raise ParseException(u"Track name mismatch %s vs %s" % (row_data['Track Name'], tracks[-1][0]['Track Name']))
				tracks[-1].append(row_data)
			else:
				tracks.append([row_data])
			old_val = row[0]
		found_track = True
		#print u"Album %s" %((names, circle, tracks),)
	if not found_track:
		raise MaybeBadType("Can't find any tracks in %s - %s" % (circle, name))

get_trs_re = re.compile('<tr class="[^"]*?atwiki_tr_([0-9]+)"[^>]*>(.*?)</tr>', re.DOTALL)
get_tds_re = re.compile('<!--([0-9]+)-([0-9]+)--><td (?:rowspan="([0-9]+)")?.*?>(.*?)</td>')
def parse_table(table):
	grid = dict()
	row_idx = 0
	max_col_idx = 0
	for (tr_row_no, row) in get_trs_re.findall(table):
		if int(tr_row_no) != row_idx + 1:
			raise Exception(u"Dodgy row number %s != %s" % (tr_row_no, row_idx + 1))
		col_idx = 0
		for (td_row_idx, td_col_idx, rowspan, cell) in get_tds_re.findall(row):
			while (row_idx, col_idx) in grid:
				col_idx += 1
			if int(td_row_idx) != row_idx:
				raise Exception(u"Dodgy row index %s != %s" % (td_row_idx, row_idx))
			if int(td_col_idx) != col_idx:
				raise Exception(u"Dodgy col index %s != %s" % (td_col_idx, col_idx))
			if not rowspan:
				rowspan = 1
			fill_row_idx = 0
			while fill_row_idx < int(rowspan):
				grid[(row_idx + fill_row_idx, col_idx)] = cell.strip()
				fill_row_idx += 1
			col_idx += 1
			if col_idx > max_col_idx:
				max_col_idx = col_idx
		row_idx += 1
	data = list()
	for row_idx in range(0, row_idx):
		row = list()
		for col_idx in range(0, max_col_idx):
			if (row_idx, col_idx) in grid:
				row.append(grid[(row_idx, col_idx)])
			else:
				row.append(None)
		data.append(row)
	return data[0], data[1:]

@logger
def read_circle_list_list(url):
	#log("Reading list of lists of circles.")
	title, circle_list_list_page = get_main(fetch_page("http://www16.atwiki.jp/toho/pages/11.html"))
	for (url, alphabet) in re.compile('<a[^>]*href="([^"#]*)"[^>]*>(.*?)<').findall(circle_list_list_page):
		read_circle_list(url, name=alphabet)

@logger
def read_circle_list(url, name=None, list_url=None):
	title, circle_page = get_main(fetch_page(url))
	if list_url:
		page_name = re.compile('<a href="' + list_url + '"[^>]*>サークル一覧</a>(.*?)</h2>').search(circle_page).group(1)
	else:
		page_name = None
	log("Reading list of circles: %s / %s / %s" % (name, page_name, title))
	for (li, circle_url, circle_name) in re.compile('(<li>)?<a[^>]*href="([^"#]*)"[^>]*>(.*?)</a').findall(circle_page):
		if not li:
			warn("Spurious URL: %s (from %s)" % (circle_url, circle_name))
		else:
			read_circle(circle_url, name=circle_name)

event_url_re = re.compile(u'<a href="(.*?)".*?>(.*?)</a>')
@logger
def read_event_list(url):
	title, page = get_main(fetch_page(url))
	read = False
	for table in get_tables_re.findall(page):
		names, data = parse_table(table)
		if names != [u'イベント名', u'開催時期']:
			warn(u"Dodgy table heading; assuming table has no heading: %s" % ", ".join(names))
			data = [names] + data
		else:
			for row in data:
				res = event_url_re.match(row[0])
				if res:
					url, name = res.groups()
					read_event(url, name=name, date=row[1])
				elif '<' not in row[0]:
					pass
				else:
					warn("Dodgy row: %s / %s" % row)
		read = True
	if not read:
		raise MaybeNotType("No events")

@fallback
@logger
def read_event(url, name=None, date=None):
	title, page = get_main(fetch_page(url))
	event = get(Event, name=name, url=url)
	read = False
	for table in get_tables_re.findall(page):
		names, data = parse_table(table)
		if names != [u'サークル名', u'CD名']:
			warn("Dodgy table heading; assuming table has no heading: %s" % ", ".join(names))
			data = [names] + data
		else:
			for row in data:
				circle_name = None
				res = event_url_re.match(row[0])
				if res:
					url, circle_name = res.groups()
					circle = read_circle(url, name=circle_name, event=event)
				else:
					circle = None
					pass
				res = event_url_re.match(row[1])
				if res:
					url, album_name = res.groups()
					read_album(url, name=album_name, circle=circle, event=event)
				else:
					pass
		read = True
	if not read:
		raise MaybeNotType("No releases")

fallback.fallback_fns = [ read_album, read_event, read_circle ]

# http://www16.atwiki.jp/toho/pages/911.html <-- vocal summary list
# http://www16.atwiki.jp/toho/pages/951.html <-- genre summary list
# http://www16.atwiki.jp/toho/pages/842.html <-- Original works.
# http://www16.atwiki.jp/toho/pages/1156.html <-- By original work.
# http://www16.atwiki.jp/toho/pages/490.html <-- event list

if not os.path.exists(PAGES):
	os.path.mkdir(PAGES)
if not os.path.exists(DATA):
	os.path.mkdir(DATA)

session = Session()
#read_circle_list_list("http://www16.atwiki.jp/toho/pages/11.html")
read_event_list("http://www16.atwiki.jp/toho/pages/490.html")
