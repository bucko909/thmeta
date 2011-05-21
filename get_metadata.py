#!/usr/bin/python -u
# -*- coding: utf-8 -*-

import os
import os.path
import re
import urllib2
import sys
import entities
import pickle
import datetime
reload(sys)
sys.setdefaultencoding('utf-8')

import sqlalchemy

from model import *

PAGES = "pages"
DATA = "data"

class MyException(Exception):
	pass

class NotAPage(MyException):
	pass

class ParseException(MyException):
	pass

class MaybeBadType(ParseException):
	pass

class logger:
	stack = []
	def __init__(self, f):
		self.f = f
		self.__name__ = f.__name__
		self.parser = False
	def __call__(self, *args, **kwargs):
		def name(f, args, kwargs):
			if self.parser:
				return (self.parser, [args[0]] + args[2:], kwargs)
			else:
				return (f.__name__, args, kwargs)
		(_name, _args, _kwargs) = name(self.f, list(args), kwargs)
		logger.stack += [ u"%s(%s)" % (_name, u", ".join([u"%s" % v for v in _args] + [u"%s=%s" % (k, v) for (k, v) in _kwargs.items() ])) ]
		try:
			#stack()
			return self.f(*args, **kwargs)
		except NotAPage, e:
			raise
		except MyException, e:
			print stack(),
			print u"exception:%s" % e
			raise
		except Exception, e:
			print stack(),
			print u"exception:%s" % e
			import traceback
			print traceback.format_exc()
			raise
		finally:
			logger.stack.pop()

def get_ut_parse(url, type, status=None):
	try:
		candidate = session.query(UTParse).filter(and_(UTParse.url==url, UTParse.type==type)).one()
	except:
		candidate = UTParse(url, type)
		session.add(candidate)
	if status != None:
		candidate.status = status
	return candidate

def parser(tname):
	def inner(f):
		return parser_impl(f, tname)
	return inner
class parser_impl:
	fns = dict()
	read_uts = dict()
	fail_uts = dict()
	def __init__(self, f, tname):
		self.tname = tname
		self.f = f
		self.__name__ = f.__name__
		parser_impl.fns[tname] = self
		if isinstance(f, logger):
			f.parser = tname
	def __call__(self, url, *args, **kwargs):
		tname = self.tname
		got = None
		ret = None
		ut_parse = get_ut_parse(url, tname)
		if ut_parse.id != None:
			return ut_parse.status
		#if (url, tname) in parser_impl.read_uts:
		#	return parser_impl.read_uts[(url, f)]
		#if (url, tname) in parser_impl.fail_uts:
		#	return None
		try:
			session.begin_nested()
			page = fetch_page(url)
			title, content = get_main(page)
			utn = get_utn(url, tname, title, witness=url)
			ret = self.f(utn, content, *args, **kwargs)
			got = True
		except MaybeBadType, e:
			parser_impl.fail_uts[(url, tname)] = True
		except MyException, e:
			pass
		finally:
			if ret:
				ut_parse.status = True
				session.commit()
			else:
				session.rollback()
				ut_parse.status = False
			parser_impl.read_uts[(url, got)] = ret
		return ret

last_stack = list()
def stack(last=False):
	global last_stack
	t = ''
	for (l, s) in zip(last_stack + [None] * (len(logger.stack) - len(last_stack)), logger.stack):
		if l != s:
			print t + u"stack:%s" % s
		t += u'    '
	last_stack = list(logger.stack)
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

def get_utn(url, type, name, witness=None):
	try:
		candidate = session.query(UTN).filter(and_(UTN.url==url, UTN.type==type, UTN.name==name)).one()
	except:
		candidate = UTN(url, type, name)
		session.add(candidate)
	if witness and not filter(lambda x: x.url == witness, candidate.witnesses):
		candidate.witnesses.append(UTNWitness(witness))
	return candidate

def link_utn(from_, to, witness=None, bidi=False):
	#log(u"Link %s to %s" % (from_, to))
	try:
		candidate = session.query(UTNLink).filter(and_(UTNLink._from==from_, UTNLink._to==to)).one()
	except:
		candidate = UTNLink(from_, to)
		session.add(candidate)
	if witness and not filter(lambda x: x.url == witness, candidate.witnesses):
		candidate.witnesses.append(UTNLinkWitness(witness))
	if bidi:
		link_utn(to, from_, witness=witness, bidi=False)
	return candidate

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
def fetch_page(givenurl, cache=True):
	if 'cmd=edit' in givenurl or '?page=' in givenurl:
		raise NotAPage("Non-existent URL: %s" % givenurl)
	elif givenurl[0] == '/':
		warn("Local URL: %s" % givenurl)
		url = "http://www16.atwiki.jp" + givenurl
	elif givenurl[:7] == 'http://':
		url = givenurl
	else:
		raise NotAPage("Bad URL: %s" % givenurl)
	if '#' in url:
		url = re.sub("#.*", "", url)
	filename = url.replace("/", "_")
	full_path = "%s/%s" % (PAGES, filename)
	if not os.path.exists(full_path) or not cache:
		log("Get page: " + url + " -> " + full_path)
		retries = 3
		while True:
			try:
				r = urllib2.Request(url, None, {'User-Agent': 'Mozilla', 'Accept': '*/*'})
				d = urllib2.urlopen(r).read()
				break
			except Exception, e:
				print stack(),
				print u"EXCEPTION:%s:%s" % (url,e)
				retries -= 1
				if retries > 0:
					continue
				else:
					raise
		f = open(full_path, "w")
		f.write(d)
		return unicode(d, 'utf8', errors='replace')
	else:
		f = open(full_path, "r")
		return unicode(f.read(), 'utf8', errors='replace')

get_page_re = re.compile(u'<title>東方同人CDwiki - (.*?)</title>.*<div id="main">(.*?)<div (?:id|class)="(?:plugin_comment|ad)">', re.DOTALL)
def get_main(page):
	try:
		groups = get_page_re.search(page).groups()
		return entities.unescape(groups[0]), groups[1]
	except:
		print "page", page
		raise

get_tables_re = re.compile("<table>(.*?)</table>", re.DOTALL)
get_album_title_re = re.compile('<h[23] id="id_.*?">(.*?)</h[23]>')
get_album_circle_re = re.compile(u'(?:サ[ー－]クル名?|ｻｰｸﾙ)[：:]+ ?<a href="(.*?)".*?>(.*?)</a>')
@parser('ALBUM')
@logger
def read_album(utn, page):
	match = get_album_circle_re.search(page)
	if match:
		c_url = entities.unescape(match.group(1))
		c_name = entities.unescape(match.group(2))
		c_utn = get_utn(c_url, 'CIRCLE', c_name, witness=utn.url)
		link_utn(utn, c_utn, witness=utn.url)
	else:
		#raise MaybeBadType("No circle for this album")
		c_utn = None
		pass

	match = get_album_title_re.search(page)
	if match:
		my_name = entities.unescape(match.group(1))
		my_utn = get_utn(utn.url, 'ALBUM', my_name, witness=utn.url)
		if c_utn:
			link_utn(my_utn, c_utn, witness=utn.url)
	else:
		raise MaybeBadType("No title for this album")

	found_track = False
	discs = list()
	disc_no = 1
	for table in get_tables_re.findall(page):
		# Now merge tracks
		names, data = parse_table(table)
		if names[0] == 'Disc' and len(discs)+1 == int(data[0][0]):
			names = names[1:]
			data = [ row[1:] for row in data ]
		if names[0] != 'Number' and names[0] != 'No.':
			raise MaybeBadType("First column of album is not track number")
		if names[1] != 'Track Name' and names[1] != 'Track name' and names[1] != 'Trach Name':
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
		discs.append(tracks)
	utn.data = "%r" % pickle.dumps(discs)
	
	if not found_track:
		raise MaybeBadType("Can't find any tracks")
	return True

get_trs_re = re.compile('<tr class="[^"]*?atwiki_tr_([0-9]+)"[^>]*>(.*?)</tr>', re.DOTALL)
get_tds_re = re.compile('<!--([0-9]+)-([0-9]+)--><td (?:rowspan="([0-9]+)")?.*?>(.*?)</td>')
def parse_table(table):
	grid = dict()
	row_idx = 0
	max_col_idx = 0
	for (tr_row_no, row) in get_trs_re.findall(table):
		if int(tr_row_no) != row_idx + 1:
			raise ParseException(u"Dodgy row number %s != %s" % (tr_row_no, row_idx + 1))
		col_idx = 0
		for (td_row_idx, td_col_idx, rowspan, cell) in get_tds_re.findall(row):
			while (row_idx, col_idx) in grid:
				col_idx += 1
			if int(td_row_idx) != row_idx:
				raise ParseException(u"Dodgy row index %s != %s" % (td_row_idx, row_idx))
			if int(td_col_idx) != col_idx:
				raise ParseException(u"Dodgy col index %s != %s" % (td_col_idx, col_idx))
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

@parser('CIRCLE_LIST_LIST')
@logger
def read_circle_list_list(utn, page):
	for (circle_list_url, alphabet) in re.compile('<a[^>]*href="([^"#]*)"[^>]*>(.*?)<').findall(page):
		read_circle_list(circle_list_url)
		circle_list_utn = get_utn(circle_list_url, 'CIRCLE_LIST', alphabet, witness=utn.url)
		link_utn(utn, circle_list_utn, witness=utn.url)

@parser('CIRCLE_LIST')
@logger
def read_circle_list(utn, page):
	for (li, circle_url, circle_name) in re.compile('(<li>)?<a[^>]*href="([^"#]*)"[^>]*>(.*?)</a').findall(page):
		if not li:
			warn("Spurious URL: %s (from %s)" % (circle_url, circle_name))
		else:
			read_circle(circle_url)
			circle_utn = get_utn(circle_url, 'CIRCLE', circle_name, witness=utn.url)
			link_utn(utn, circle_utn, witness=utn.url)

event_url_re = re.compile(u'<a href="(.*?)".*?>(.*?)</a>')
@parser('EVENT_LIST')
@logger
def read_event_list(utn, page):
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
					ev_url, ev_name = res.groups()
					read_event(ev_url, date=row[1])
					ev_utn = get_utn(ev_url, 'EVENT', ev_name, witness=utn.url)
				else:
					warn("Dodgy row: %s" % row)
					continue
				link_utn(utn, ev_utn, witness=utn.url)
		read = True
	if not read:
		pass

@parser('EVENT')
@logger
def read_event(utn, page, date=None):
	utn.data = date
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
					circle_url, circle_name = res.groups()
					read_circle(circle_url)
					circle_utn = get_utn(circle_url, 'CIRCLE', circle_name, witness=utn.url)
					link_utn(utn, circle_utn, witness=utn.url)
				else:
					circle_utn = None
					pass
				res = event_url_re.match(row[1])
				if res:
					album_url, album_name = res.groups()
					read_album(album_url)
					album_utn = get_utn(album_url, 'ALBUM', album_name, witness=utn.url)
					link_utn(utn, album_utn, witness=utn.url)
					if circle_utn:
						link_utn(circle_utn, album_utn, witness=utn.url, bidi=True)
				else:
					pass
		read = True
	if not read:
		raise MaybeBadType("No releases")

album_url_re = re.compile('(<li>)?.*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>(?:[^\\(<\n]+\\(([^\\)<\n]+)\\)</li>)?')
@parser('CIRCLE')
@logger
def read_circle(utn, to_parse):
	read = False
	for (li, album_url, album_name, alternative) in album_url_re.findall(to_parse):
		if read_album(album_url):
			album_utn = get_utn(album_url, 'ALBUM', album_name, witness=utn.url)
			link_utn(utn, album_utn, witness=utn.url)
			read = True
	if not read:
		raise MaybeBadType("Empty circle")
	return True

recent_changes_interesting_re = re.compile("""<p class="plugin_recent_day">(\d+)-(\d+)-(\d+)</p>|<li><a href="([^"]+)"[^>]*>[^<]*</a></li>""")
@parser('RECENT')
@logger
def read_recent_changes(utn, page):
	changed_at = None
	for (_year, _month, _day, url) in recent_changes_interesting_re.findall(page):
		if _year:
			(year, month, day) = [ int(x) for x in (_year, _month, _day) ]
			changed_at = datetime.datetime(year=int(_year), month=int(_month), day=int(_day), hour=23, minute=59, second=59)
		elif changed_at:
			filename = url.replace("/", "_")
			full_path = "%s/%s" % (PAGES, filename)
			if os.path.exists(full_path) and datetime.datetime.fromtimestamp(os.stat(full_path).st_mtime) < changed_at:
				log(u"%s changed at %s" % (url, changed_at))
				os.remove(full_path)
				session.query(UTNWitness).filter(UTNWitness.url == url).delete()
				session.query(UTNLinkWitness).filter(UTNLinkWitness.url == url).delete()
		else:
			print "Failed to parse date..."

# http://www16.atwiki.jp/toho/pages/911.html <-- vocal summary list
# http://www16.atwiki.jp/toho/pages/951.html <-- genre summary list
# http://www16.atwiki.jp/toho/pages/842.html <-- Original works.
# http://www16.atwiki.jp/toho/pages/1156.html <-- By original work.

if not os.path.exists(PAGES):
	os.path.mkdir(PAGES)
if not os.path.exists(DATA):
	os.path.mkdir(DATA)

session = Session()
if __name__ == '__main__':
	#session.query(UTParse).delete()
	#read_recent_changes("http://www16.atwiki.jp/toho/pages/508.html")
	read_circle_list_list("http://www16.atwiki.jp/toho/pages/11.html")
	read_event_list("http://www16.atwiki.jp/toho/pages/490.html")
	session.commit()
