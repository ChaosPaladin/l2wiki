# vim: set fileencoding=utf-8
from l2wikiparser import parseWiki, dbCreate, dbCheck
import sqlite3 as sql
import sys

con = None

try:
    con = sql.connect('l2wiki.db')
    if not dbCheck(con):
        dbCreate(con)
        parseWiki(con)


except sql.Error, e:
    print "Error {0}:".format(e.args[0])
    sys.exit(1)

finally:
    if con:
        con.close()
