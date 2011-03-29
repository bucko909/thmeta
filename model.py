from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
Base = declarative_base()

db = create_engine('postgresql+psycopg2:///touhou_meta', echo=True)

class Event(Base):
	__tablename__ = 'event'
	id = Column(Integer, Sequence('event_id_seq'), primary_key=True)
	start_date = Column(Date)
	end_date = Column(Date)

class EventName(Base):
	__tablename__ = 'event_name'
	id = Column(Integer, Sequence('event_name_id_seq'), primary_key=True)
	event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
	event = relationship(Event, backref=backref('event', order_by=id))
	event_name = Column(Text, nullable=False)
	canonical = Column(Boolean, nullable=False)

class Circle(Base):
	__tablename__ = 'circle'
	id = Column(Integer, Sequence('circle_id_seq'), primary_key=True)
	url = Column(Text)

class CircleName(Base):
	__tablename__ = 'circle_name'
	id = Column(Integer, Sequence('circle_name_id_seq'), primary_key=True)
	circle_id = Column(Integer, ForeignKey('circle.id'), nullable=False)
	circle = relationship(Circle, backref=backref('circle', order_by=id))
	circle_name = Column(Text, nullable=False)
	canonincal = Column(Boolean, nullable=False)

class CircleAttendance(Base):
	__tablename__ = 'circle_attendance'
	id = Column(Integer, Sequence('circle_attendance_id_seq'), primary_key=True)
	circle_id = Column(Integer, ForeignKey('circle.id'), nullable=False)
	circle = relationship(Circle, backref=backref('circle', order_by=id))
	event_id = Column(Integer, ForeignKey('event.id')), # Null if they also released without an event
	event = relationship(Event, backref=backref('event', order_by=id))

class Album(Base):
	__tablename__ = 'album'
	id = Column(Integer, Sequence('album_id_seq'), primary_key=True)
	circle_attendance = relationship(CircleAttendance, secondary=

class AlbumName(Base):
	__tablename__ = 'album_name'
	id = Column(Integer, Sequence('album_name_id_seq'), primary_key=True)
	album_id = Column(Integer, ForeignKey('album.id'), nullable=False)
	album = relationship(Album, backref=backref('album', order_by=id))
	album_name = Column(Text, nullable=False)
	canonincal = Column(Boolean, nullable=False)

class AlbumRelease(Base):
	__tablename__ = 'album_release'
	id = Column(Integer, Sequence('album_release_id_seq'), primary_key=True)
	circle_attendance_id = Column(Integer, ForeignKey('circle_attendance.id'), nullable=False)
	circle_attendance = relationship(CircleAttendance, backref=backref('circle_attendance', order_by=id))

class Track(Base):
	__tablename__ = 'track'
	id = Column(Integer, Sequence('track_id_seq'), primary_key=True)
	track_number = Column(Integer, nullable=False)
	album_id = Column(Integer, ForeignKey('album.id'), nullable=False)
	album = relationship(Album, backref=backref('album', order_by=id))

class TrackName(Base):
	__tablename__ = 'track_name'
	id = Column(Integer, Sequence('track_name_id_seq'), primary_key=True)
	track_id = Column(Integer, ForeignKey('track.id'), nullable=False)
	track = relationship(Track, backref=backref('track', order_by=id))
	track_name = Column(Text, nullable=False)
	canonincal = Column(Boolean, nullable=False)

class Atwiki(Base):
	__tablename__ = 'atwiki'
	id = Column(Integer, Sequence('atwiki_id_seq'), primary_key=True)
	page_no = Column(Integer, nullable=False)
	event_id = Column(Integer, ForeignKey('event.id'))
	event = relationship(Event, backref=backref('event', order_by=id))
	circle_id = Column(Integer, ForeignKey('circle.id'))
	circle = relationship(Circle, backref=backref('circle', order_by=id))
	album_id = Column(Integer, ForeignKey('album.id'))
	album = relationship(Album, backref=backref('album', order_by=id))
	other = Column(Text)

Base.metadata.bind = db
Base.metadata.create_all()


