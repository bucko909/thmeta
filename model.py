from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker


Base = declarative_base()

class Event(Base):
	__tablename__ = 'event'
	id = Column(Integer, Sequence('event_id_seq'), primary_key=True)
	start_date = Column(Date)
	end_date = Column(Date)
	def __repr__(self):
		c = [ n.name for n in self.names if n.canonical ]
		if c:
			n = c[0]
		elif self.names:
			n = self.names[0].name
		else:
			n = "UNKNOWN"
		return u"<Event %s>" % n

class EventName(Base):
	__tablename__ = 'event_name'
	id = Column(Integer, Sequence('event_name_id_seq'), primary_key=True)
	event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
	event = relationship(Event, backref=backref('names', order_by=id))
	name = Column(UnicodeText, nullable=False)
	canonical = Column(Boolean, nullable=False)
	def __init__(self, name, canonical=False):
		self.name = name
		self.canonical = canonical
	def __repr__(self):
		return unicode(self.name)
Index('event_name_name_key', EventName.name, EventName.id, unique=True)

class Circle(Base):
	__tablename__ = 'circle'
	id = Column(Integer, Sequence('circle_id_seq'), primary_key=True)
	events = None
	def page_nos(self):
		return [ page.page_no for page in self.pages ]
	def __repr__(self):
		c = [ n.name for n in self.names if n.canonical ]
		if c:
			n = c[0]
		elif self.names:
			n = self.names[0].name
		else:
			n = "UNKNOWN"
		return u"<Circle %s>" % n

class CircleName(Base):
	__tablename__ = 'circle_name'
	id = Column(Integer, Sequence('circle_name_id_seq'), primary_key=True)
	circle_id = Column(Integer, ForeignKey('circle.id'), nullable=False)
	circle = relationship(Circle, backref=backref('names', order_by=id))
	canonical = Column(Boolean, nullable=False)
	name = Column(UnicodeText, nullable=False)
	def __init__(self, name, canonical=False, circle=None):
		self.name = name
		self.canonical = canonical
		self.circle = circle
	def __repr__(self):
		return unicode(self.name)
Index('circle_name_name_key', CircleName.name, CircleName.circle_id, unique=True)

class Album(Base):
	__tablename__ = 'album'
	id = Column(Integer, Sequence('album_id_seq'), primary_key=True)
	def __repr__(self):
		c = [ n.name for n in self.names if n.canonical ]
		if c:
			n = c[0]
		elif self.names:
			n = self.names[0].name
		else:
			n = "UNKNOWN"
		return u"<Album %s>" % n

class AlbumName(Base):
	__tablename__ = 'album_name'
	id = Column(Integer, Sequence('album_name_id_seq'), primary_key=True)
	album_id = Column(Integer, ForeignKey('album.id'), nullable=False)
	album = relationship(Album, backref=backref('names', order_by=id))
	name = Column(UnicodeText, nullable=False)
	canonical = Column(Boolean, nullable=False)
	def __init__(self, name, canonical=False):
		self.name = name
		self.canonical = canonical
	def __repr__(self):
		return unicode(self.name)
Index('album_name_name_key', AlbumName.name, AlbumName.id, unique=True)

class CircleAttendance(Base):
	__tablename__ = 'circle_attendance'
	id = Column(Integer, Sequence('circle_attendance_id_seq'), primary_key=True)
	circle_id = Column(Integer, ForeignKey('circle.id'), nullable=False)
	circle = relationship(Circle, backref='attendances')
	event_id = Column(Integer, ForeignKey(Event.id))
	event = relationship(Event, backref='attendances')
Index('circle_attendance_key', CircleAttendance.circle_id, CircleAttendance.event_id, unique=True)
Circle.events = relationship(Event, secondary=CircleAttendance.__table__, backref='circles')

class AlbumRelease(Base):
	__tablename__ = 'album_release'
	id = Column(Integer, Sequence('album_release_id_seq'), primary_key=True)
	circle_attendance_id = Column(Integer, ForeignKey('circle_attendance.id'), nullable=False)
	circle_attendance = relationship(CircleAttendance, backref=backref('releases', order_by=id))
	album_id = Column(Integer, ForeignKey('album.id'), nullable=False)
	album = relationship(Album, backref=backref('releases', order_by=id))
	def __init__(self, circle_attendance, album):
		self.circle_attendance = circle_attendance
		self.album = album
Index('album_release_key', AlbumRelease.circle_attendance_id, AlbumRelease.album_id, unique=True)

class Track(Base):
	__tablename__ = 'track'
	id = Column(Integer, Sequence('track_id_seq'), primary_key=True)
	track_number = Column(Integer, nullable=False)
	album_id = Column(Integer, ForeignKey('album.id'), nullable=False)
	album = relationship(Album, backref=backref('tracks', order_by=id))
	def __init__(self, track_number, album):
		self.track_number = track_number
		self.album = album
Index('track_key', Track.track_number, Track.album_id, unique=True)

class TrackName(Base):
	__tablename__ = 'track_name'
	id = Column(Integer, Sequence('track_name_id_seq'), primary_key=True)
	track_id = Column(Integer, ForeignKey('track.id'), nullable=False)
	track = relationship(Track, backref=backref('names', order_by=id))
	name = Column(UnicodeText, nullable=False)
	canonical = Column(Boolean, nullable=False)
	def __init__(self, name, canonical=False):
		self.name = name
		self.canonical = canonical
	def __repr__(self):
		return self.name
Index('track_name_name_key', TrackName.name, TrackName.id, unique=True)

class TrackProperty(Base):
	__tablename__ = 'track_property'
	id = Column(Integer, Sequence('track_property_id_seq'), primary_key=True)
	track_id = Column(Integer, ForeignKey('track.id'), nullable=False)
	track = relationship(Track, backref=backref('properties', order_by=id))
	name = Column(UnicodeText, nullable=False)
	value = Column(UnicodeText, nullable=False)
	def __init__(self, name, value):
		self.name = name
		self.value = value
	def __repr__(self):
		return u"%s=%s" % (self.name, self.value)
Index('track_property_name_key', TrackProperty.name, TrackProperty.id, unique=True)

class Atwiki(Base):
	__tablename__ = 'atwiki'
	id = Column(Integer, Sequence('atwiki_id_seq'), primary_key=True)
	page_no = Column(Integer, nullable=False)
	event_id = Column(Integer, ForeignKey('event.id'))
	event = relationship(Event, backref=backref('pages', order_by=id))
	circle_id = Column(Integer, ForeignKey('circle.id'))
	circle = relationship(Circle, backref=backref('pages', order_by=id))
	album_id = Column(Integer, ForeignKey('album.id'))
	album = relationship(Album, backref=backref('pages', order_by=id))
	other = Column(UnicodeText)
	def __init__(self, page_no):
		self.page_no = page_no
	def __repr__(self):
		return u"<Atwiki %i>" % self.page_no
Index('atwiki_page_no_key', Atwiki.page_no, unique=True)

Base.metadata.bind = create_engine('postgresql+psycopg2:///touhou_meta', echo=False)
Base.metadata.create_all()
Session = sessionmaker(bind=Base.metadata.bind)

if __name__ == '__main__':
	c = Circle()
	sess = Session()
	c.names.append(CircleName(u'foo'))
	sess.add(c)
	sess.flush()
	e = Event()
	sess.add(e)
	e.circles = [c]
	print sess.query(Event).filter(Event.circles.contains(c) ).all()
	sess.rollback()
