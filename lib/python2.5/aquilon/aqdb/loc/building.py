""" Building is a subclass of Location """
from sqlalchemy import Column, Integer, ForeignKey

from aquilon.aqdb.loc.location import Location, location


class Building(Location):
    """ Building is a subtype of location """
    __tablename__ = 'building'
    __mapper_args__ = {'polymorphic_identity' : 'building'}

    id = Column(Integer,
                ForeignKey('location.id', name = 'building_loc_fk',
                           ondelete = 'CASCADE'),
                primary_key=True)

building = Building.__table__
building.primary_key.name = 'building_pk'

table = building

def populate(sess, *args, **kw):

    if len(sess.query(Building).all()) > 0:
        return

    from aquilon.aqdb.loc.city import City
    import aquilon.aqdb.dsdb as dsdb_
    dsdb = dsdb_.DsdbConnection()

    city = {}
    for c in sess.query(City).all():
        city[c.name] = c

    for row in dsdb.dump('building'):
        try:
            p = city[str(row[2])]
        except KeyError,e :
            print >> sys.stderr, e
            continue

        a = Building(name = str(row[0]),
                    fullname = str(row[1]),
                    parent = city[str(row[2])])
        sess.add(a)
    sess.commit()
    print 'created %s buildings'%(len(sess.query(Building).all()))


# Copyright (C) 2008 Morgan Stanley
# This module is part of Aquilon

# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
