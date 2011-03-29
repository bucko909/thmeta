#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import os.path
import re
import urllib2

import sqlalchemy

PAGES = "pages"
DATA = "data"

class NotAPage(Exception):
	pass

class ParseException(Exception):
	pass

class MaybeBadType(ParseException):
	pass

def get_circle(name=None, url=None):
	if name and url:
		if url in Circle.cache_url and name not in Circle.cache_url[url].names:
			warn(u"Circle url %s, points to names %s and %s" % (url, Circle.cache_url[url].names, name))
		if name in Circle.cache_name and url not in Circle.cache_name[name].urls:
			warn(u"Circle name %s from urls %s and %s" % (name, Circle.cache_name[name].urls, url))
	if name in Circle.cache_name:
		self = Circle.cache_name[name]
	elif url in Circle.cache_url:
		self = Circle.cache_url[url]
	else:
		self = Circle()
		Circle.cache_list.append(self)
	if name and name not in self.names:
		self.names.append(name)
		Circle.cache_name[name] = self
	if url and url not in self.urls:
		self.urls.append(url)
		Circle.cache_url[url] = self
class Circle:
	cache_name = dict()
	cache_url = dict()
	cache_list = list()
	def __init__(self):
		self.names = list()
		self.urls = list()


class logger:
	stack = []
	def __init__(self, f):
		self.__f__ = f
	def __call__(self, *args, **kwargs):
		logger.stack += [ "%s(%s)" % (self.__f__.__name__, ", ".join(["%r" % v for v in args] + ["%s=%r" % (k, v) for (k, v) in kwargs.items() ])) ]
		try:
			return self.__f__(*args, **kwargs)
		except NotAPage, e:
			raise
		except Exception, e:
			stack()
			print "exception:%r" % e
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
def read_circle(url, name=None):
	#log("Circle: %s (%s)" % (name, url))
	dirname = "%s/%s" % (DATA, name.replace("/", "__"))
	if not os.path.exists(dirname):
		#os.path.mkdir(dirname)
		pass
	album_cache = dirname + "/albums.txt"
	if os.path.exists(album_cache) and False:
		albums = [ album.split("|||") for album in open(album_cache, "r").read().split("\n") ]
	else:
		title, to_parse = get_main(fetch_page(url))
		albums = []
		for (li, url, album_name, alternative) in album_url_re.findall(to_parse):
			if li:
				t = 'album'
			else:
				t = 'maybe_album'
			albums += [(t, url, album_name, alternative)]
		if not albums:
			raise MaybeBadType("Empty circle")
		if not name:
			name = title
		elif name != title:
			warn("Circle has name %s, but page has title %s" % (name, title))
		#open(album_cache, "w").write("\n".join(["|||".join(album) for album in albums]))
	
	for (t, url, album_name, alternative) in albums:
		read_album(url, name=album_name, circle_name=name)

get_tables_re = re.compile("<table>(.*?)</table>", re.DOTALL)
get_album_title_re = re.compile('<h2 id="id_.*?">(.*?)</h2>')
get_album_circle_re = re.compile(u'(?:サ[ー－]クル名?|ｻｰｸﾙ)[：:] ?<a href="(.*?)".*?>(.*?)</a>')
@fallback
@logger
def read_album(url, name=None, circle_name=None):
	#log("Album: %s (%s)" % (name, url))
	title, to_parse = get_main(fetch_page(url))
	match = get_album_title_re.search(to_parse)
	if match and name and name != match.group(1):
		warn(u"Album name was %s, but page said %s" % (name, match.group(1)))
		names = [name, match.group(1)]
	elif match:
		names = [match.group(1)]
	else:
		raise MaybeBadType("No title for this album (though handed %s)" % name)

	match = get_album_circle_re.search(to_parse)
	if match and circle_name and circle_name != match.group(2):
		warn(u"Album circle was %s, but page said %s" %(circle_name, match.group(2)))
		circle = get_circle(name=circle_name, url=match.group(1))
	elif not match:
		raise MaybeBadType("No circle for this album (though handed %s)" % circle_name)
	else:
		circle = get_circle(name=match.group(2), url=match.group(1))

	found_track = False
	for table in get_tables_re.findall(to_parse):
		# Now merge tracks
		names, data = parse_table(table)
		if names[0] != 'Number':
			raise MaybeBadType("First column of album is not track number")
		if names[1] != 'Track Name':
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
		print "Album", names, circle, tracks
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

@fallback
@logger
def read_event(url, name=None):
	pass


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
def read_event(url, name=None):
	title, page = get_main(fetch_page(url))
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
					#print "circle", circle_name
					#read_circle(url, name=circle_name)
				else:
					pass
				res = event_url_re.match(row[1])
				if res:
					url, album_name = res.groups()
					#print "album", album_name
					#read_album(url, name=album_name, circle_name=circle_name)
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

db = sqlalchemy.create_engine('postgresql+psycopg2://touhou_meta')
#read_circle_list_list("http://www16.atwiki.jp/toho/pages/11.html")
read_event_list("http://www16.atwiki.jp/toho/pages/490.html")
