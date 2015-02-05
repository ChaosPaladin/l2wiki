# vim: set fileencoding=utf-8
from l2wikiparser import parseWiki, dbCreate, dbCheck
from l2wikigui import MainWindow
from PySide.QtGui import QApplication
import sqlite3 as sql
import sys

con = None

try:
    con = sql.connect('l2wiki.db')
    if not dbCheck(con):
        dbCreate(con)
        parseWiki(con)
    app = QApplication(sys.argv)
    wid = MainWindow(con)
    wid.show()
    sys.exit(app.exec_())

except sql.Error, e:
    print "Error {0}:".format(e.args[0])
    sys.exit(1)

finally:
    if con:
        con.close()
