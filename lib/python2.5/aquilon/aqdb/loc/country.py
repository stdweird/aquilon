#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# $Header$
# $Change$
# $DateTime$
# $Author$
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
""" Country is a subclass of Location """


import sys
import os

if __name__ == '__main__':
    DIR = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.realpath(os.path.join(DIR, '..', '..', '..')))
    import aquilon.aqdb.depends

from sqlalchemy import Column, Integer, ForeignKey

from aquilon.aqdb.loc.location import Location, location


class Country(Location):
    """ Country is a subtype of location """
    __tablename__ = 'country'
    __mapper_args__ = {'polymorphic_identity' : 'country'}
    id = Column(Integer,
                ForeignKey('location.id', name = 'country_loc_fk',
                           ondelete = 'CASCADE'),
                primary_key=True)

country = Country.__table__
country.primary_key.name = 'country_pk'

def populate(*args, **kw):
    from aquilon.aqdb.db_factory import db_factory, Base
    dbf = db_factory()
    Base.metadata.bind = dbf.engine
    #if 'debug' in args:
    Base.metadata.bind.echo = False
    s = dbf.session()

    from aquilon.aqdb.loc.continent import Continent
    from aquilon.aqdb.loc.hub import Hub
    from aquilon.aqdb.utils import dsdb

    country.create(checkfirst = True)

    s=dbf.session()

    if len(s.query(Country).all()) < 1:
        cnts = {}
        for c in s.query(Continent).all():
            cnts[c.name] = c

        for row in dsdb.dump_country():

            if row[0] == 'jp':
                continue #skip japan, it maps directly to the TK hub

            a = Country(name = str(row[0]),
                        fullname = str(row[1]),
                        parent = cnts[str(row[2])])
            s.add(a)

        s.commit()

        #Handle Japan as a special case
        tk_hub = s.query(Hub).filter_by(name = 'tk').one()

        jp = Country(name = 'jp', fullname = 'Japan', parent = tk_hub)
        s.add(jp)
        try:
            s.commit()
        except Exception, e:
            sys.stderr.write(e)

        print 'created %s countries'%(len(s.query(Country).all()))

""" select A.id, A.name, A.fullname, B.type, A.parent_id from location A,
location_type B where a.location_type_id = B.id """