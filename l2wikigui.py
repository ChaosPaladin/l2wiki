# vim: set fileencoding=utf-8
from PySide import QtCore
from PySide import QtGui
from cStringIO import StringIO
import sqlite3 as sql
import sys


# sql constructor
class SqlConstructor():
    def __init__(self):
        self.isDropInfo = False
        self.lvlMin = 1
        self.lvlMax = 75
        self.mobFeatures = None
        self.filterText = ''
        self.__templateSql = (
            """
            SELECT title as mobTitle, location, level, hp, exp, features FROM mobInfo
            WHERE level >= {lvlMin} AND level <= {lvlMax}
            """,
            """
            SELECT isSpoil, images.image as image, dropInfo.title as itemTitle,
            minCount, maxCount, minChance, maxChance,
            mobInfo.title as mobTitle, level, location FROM dropInfo
            INNER JOIN mobInfo ON dropInfo.pageid = mobInfo.pageid
            INNER JOIN images ON dropInfo.imageid = images.id
            WHERE level >= {lvlMin} AND level <= {lvlMax}
            """,
            """
            SELECT image, desc, id FROM features WHERE {features} ORDER BY desc
            """,
            """
            AND (mobTitle LIKE ('%{title}%') OR location LIKE ('%{title}%'))
            """,
            """
            AND (itemTitle LIKE ('%{title}%') OR mobTitle LIKE ('%{title}%') OR
            location LIKE ('%{title}%'))
            """,
        )

    def setDropInfo(self, value):
        self.isDropInfo = value

    def setLvlMin(self, value):
        self.lvlMin = value

    def setLvlMax(self, value):
        self.lvlMax = value

    def setMobFeatures(self, value):
        self.mobFeatures = value

    def setFilterText(self, value):
        self.filterText = value

    # sql for table view
    def getSql(self):
        sql = self.__templateSql[self.isDropInfo].format(
            lvlMin=self.lvlMin,
            lvlMax=self.lvlMax
        )
        if len(self.filterText) > 2:
            sql += ' ' + self.__templateSql[self.isDropInfo + 3].format(
                title=self.filterText.encode('utf-8')
            )
        return sql

    # sql for monster features
    def getMobFeaturesSql(self):
        if len(self.mobFeatures):
            sql = ''
            for feature in self.mobFeatures:
                sql += 'id = {0} OR '.format(feature)
            # cut trailing OR
            sql = sql[:-3]
            return self.__templateSql[2].format(features=sql)

    # sql for features filter panel
    def getFilterSql(self):
        features = (101077397, 701526354, 728503386, 2439934659, 2612649169,
                    3063148529, 3195934303, 2342948171, 4167006689, 574520354,
                    1006112502, 1050875716, 1072529798, 1789908831, 2739281397,
                    3667020493)
        sql = ''
        for feature in features:
            sql += 'id = {0} OR '.format(feature)
        # cut trailing OR
        sql = sql[:-3]
        return self.__templateSql[2].format(features=sql)


# main window class
class MainWindow(QtGui.QMainWindow):

    def __init__(self, con, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.__con = con
        self.__con.row_factory = sql.Row
        self.__con.text_factory = sql.OptimizedUnicode
        self.filterFeatures = []
        self.initUI()

    def initUI(self):
        self.formatSql = SqlConstructor()
        # create drop or monster toggles
        self.radioMob = QtGui.QRadioButton(u'Монстры')
        self.radioMob.setToolTip(u'Показывать монстров')
        self.radioDrop = QtGui.QRadioButton(u'Трофеи')
        self.radioDrop.setToolTip(u'Показывать дроп и споил')
        # connect signals
        self.radioMob.released.connect(self.refreshTable)
        self.radioMob.toggled.connect(self.radioChanger)
        self.radioDrop.released.connect(self.refreshTable)
        self.radioDrop.toggled.connect(self.radioChanger)
        # init state
        if self.formatSql.isDropInfo:
            self.radioDrop.setChecked(True)
        else:
            self.radioMob.setChecked(True)
        # compose layout
        radioLayout = QtGui.QVBoxLayout()
        radioLayout.setSpacing(0)
        radioLayout.addWidget(self.radioMob)
        radioLayout.addWidget(self.radioDrop)
        radioGroup = QtGui.QGroupBox()
        radioGroup.setContentsMargins(0, 0, 0, 0)
        radioGroup.setLayout(radioLayout)

        # create level range sliders
        # defaults
        hintMin = u'Минимальный уровень монстра'
        hintMax = u'Максимальный уровень монстра'
        lvlMin = self.formatSql.lvlMin
        lvlMax = self.formatSql.lvlMax
        # init sliders
        self.sliderMin = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.sliderMin.setFocusPolicy(QtCore.Qt.NoFocus)
        self.sliderMin.setToolTip(hintMin)
        self.sliderMin.setMinimum(lvlMin)
        self.sliderMin.setMaximum(lvlMax)
        self.sliderMin.setValue(lvlMin)
        self.sliderMax = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.sliderMax.setFocusPolicy(QtCore.Qt.NoFocus)
        self.sliderMax.setToolTip(hintMax)
        self.sliderMax.setMinimum(lvlMin)
        self.sliderMax.setMaximum(lvlMax)
        self.sliderMax.setValue(lvlMax)
        # connect signals
        self.sliderMin.valueChanged[int].connect(self.sliderMinChanger)
        self.sliderMin.sliderReleased.connect(self.refreshTable)
        self.sliderMax.valueChanged[int].connect(self.sliderMaxChanger)
        self.sliderMax.sliderReleased.connect(self.refreshTable)
        # create labels
        self.labelMin = QtGui.QLabel()
        self.labelMin.setToolTip(hintMin)
        self.labelMin.setAlignment(QtCore.Qt.AlignRight)
        self.sliderMinChanger(lvlMin)
        self.labelMax = QtGui.QLabel()
        self.labelMax.setToolTip(hintMax)
        self.labelMax.setAlignment(QtCore.Qt.AlignRight)
        self.labelMin.setMinimumWidth(16)
        self.labelMax.setMinimumWidth(16)
        self.sliderMaxChanger(lvlMax)
        # compose layout
        sliderLayout = QtGui.QGridLayout()
        sliderLayout.setSpacing(0)
        sliderLayout.addWidget(self.labelMin, 0, 0)
        sliderLayout.addWidget(self.labelMax, 1, 0)
        sliderLayout.addWidget(self.sliderMin, 0, 1)
        sliderLayout.addWidget(self.sliderMax, 1, 1)
        sliderGroup = QtGui.QGroupBox()
        sliderGroup.setContentsMargins(0, 0, 0, 0)
        sliderGroup.setMaximumWidth(196)
        sliderGroup.setLayout(sliderLayout)

        # create filter panel
        filtersWidget = self.initFilterPanel()
        self.lineEditWidget = QtGui.QLineEdit()
        self.lineEditWidget.textChanged[str].connect(self.textFilterChanged)
        filterLayout = QtGui.QVBoxLayout()
        filterLayout.setSpacing(0)
        filterLayout.addWidget(filtersWidget)
        filterLayout.addWidget(self.lineEditWidget)
        filterGroup = QtGui.QWidget()
        filterGroup.setContentsMargins(0, 0, 0, 0)
        filterGroup.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        filterGroup.setLayout(filterLayout)

        # compose toolbar layout
        self.mainToolbar = QtGui.QToolBar()
        self.mainToolbar.setFloatable(False)
        self.mainToolbar.setMovable(False)
        self.mainToolbar.addWidget(radioGroup)
        self.mainToolbar.addSeparator()
        self.mainToolbar.addWidget(sliderGroup)
        self.mainToolbar.addSeparator()
        self.mainToolbar.addWidget(filterGroup)
        self.addToolBar(self.mainToolbar)

        # init main window
        self.statusBar()
        self.setMinimumHeight(600)
        self.setMinimumWidth(1000)
        self.setWindowTitle('l2wiki')
        self.setWindowIcon(QtGui.QIcon('l2wiki.jpg'))

        # init table widget
        self.sortSection = [0, 2]
        self.sortOrder = [
            QtCore.Qt.SortOrder.AscendingOrder,
            QtCore.Qt.SortOrder.AscendingOrder
        ]
        self.refreshTable()

    # slots
    # maybe bad but fastest method to clear table
    def newTable(self):
        self.saveOrder()
        self.tableWidget = QtGui.QTableWidget()
        self.tableWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setObjectName(str(int(self.formatSql.isDropInfo)))
        self.rowDefaultSize = self.tableWidget.verticalHeader().defaultSectionSize()
        self.tableWidget.horizontalHeader().setHighlightSections(False)
        self.setCentralWidget(self.tableWidget)

    # save and restore sort order
    def saveOrder(self):
        if hasattr(self, 'tableWidget'):
            sortSection = self.tableWidget.horizontalHeader().sortIndicatorSection()
            sortOrder = self.tableWidget.horizontalHeader().sortIndicatorOrder()
            slot = int(self.tableWidget.objectName())
            self.sortSection[slot] = sortSection
            self.sortOrder[slot] = sortOrder

    def restoreOrder(self):
        sortSection = self.sortSection[self.formatSql.isDropInfo]
        sortOrder = self.sortOrder[self.formatSql.isDropInfo]
        self.tableWidget.horizontalHeader().setSortIndicator(sortSection, sortOrder)

    # execute sql and refresh table widget
    def refreshTable(self): #NOQA
        # clear table
        self.newTable()
        self.tableWidget.hide()
        self.tableWidget.setSortingEnabled(False)
        # exec sql
        cur = self.__con.cursor()
        sql = self.formatSql.getSql()
        cur.execute(sql)
        row = cur.fetchone()
        # fill table with result
        if row is not None:
            i = 0
            self.tableWidget.setColumnCount(len(row.keys()))
            self.translateHeaders(row.keys())
            self.restoreOrder()
            self.resizeRows()
            while row is not None:
                if self.rowIsFiltered(row):
                    row = cur.fetchone()
                    continue

                # temporary fix
                if not self.formatSql.isDropInfo and not row['exp']:
                    row = cur.fetchone()
                    continue

                self.tableWidget.insertRow(i)
                brush = self.getRowColor(row)
                # fill row with values
                for j, value in enumerate(row):
                    item = QtGui.QTableWidgetItem()
                    header = self.getCurrentHeader(j)
                    if header == u'Особенности':
                        if len(value):
                            imagesWidget = self.getImages(value)
                            self.tableWidget.setCellWidget(i, j, imagesWidget)
                    elif header == u'И':
                        img = QtGui.QPixmap()
                        img.loadFromData(StringIO(value).read())
                        img = img.scaled(24, 24, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
                        imgWidget = QtGui.QLabel()
                        imgWidget.setPixmap(img)
                        imgWidget.setMaximumWidth(24)
                        self.tableWidget.setCellWidget(i, j, imgWidget)
                    else:
                        if header == u'С':
                            item.setText([u'Д', u'С'][value])
                            item.setToolTip([u'Дроп', u'Споил'][value])
                        elif self.colIsNumeric(j):
                            item.setData(QtCore.Qt.DisplayRole, value)
                            item.setToolTip(str(value))
                        else:
                            item.setText(value)
                            item.setToolTip(value)
                        item.setBackground(brush)
                        self.alignItem(j, item)
                        self.tableWidget.setItem(i, j, item)
                self.statusBar().showMessage(u'Найдено: ' + str(i + 1) + u' записей.')
                i += 1
                row = cur.fetchone()
            self.tableWidget.setSortingEnabled(True)
            self.tableWidget.resizeColumnsToContents()
            self.resizeHeaders()
            self.tableWidget.show()
        else:
            self.statusBar().showMessage(u'Нет результатов')

    def radioChanger(self):
        if self.radioMob.isChecked():
            self.formatSql.setDropInfo(False)
        else:
            self.formatSql.setDropInfo(True)

    def sliderMinChanger(self, value):
        self.labelMin.setNum(value)
        self.formatSql.setLvlMin(value)
        if value > self.sliderMax.value():
            self.sliderMax.setValue(value)

    def sliderMaxChanger(self, value):
        self.labelMax.setNum(value)
        self.formatSql.setLvlMax(value)
        if value < self.sliderMin.value():
            self.sliderMin.setValue(value)

    def toggleFeatures(self, pressed):
        feature = self.sender().objectName()
        if pressed:
            self.filterFeatures.append(feature)
        else:
            self.filterFeatures.remove(feature)
        if not self.formatSql.isDropInfo:
            self.refreshTable()

    def textFilterChanged(self, text):
        # capitalize first letter of each word
        self.formatSql.setFilterText(text.title())
        self.lineEditWidget.setText(text.title())
        if not len(text) or len(text) > 2:
            self.refreshTable()

    # other functions
    # filter features (bad design)
    def rowIsFiltered(self, row):
        if len(self.filterFeatures) and not self.formatSql.isDropInfo:
            if len(set(self.filterFeatures) &
                    set(row['features'].split(','))) == 0:
                return True

    # return different colors for drop and spoil rows
    def getRowColor(self, row):
        brush = QtGui.QBrush()
        brush.setStyle(QtCore.Qt.SolidPattern)
        brush.setColor(QtGui.QColor(255, 255, 255))
        if self.formatSql.isDropInfo:
            if row['isSpoil'] == True: # NOQA
                brush.setColor(QtGui.QColor(200, 250, 200))
        return brush

    # format and show header
    def translateHeaders(self, keys):
        # KEY: [TEXT, TOOLTIP]
        strings = {
            'isSpoil': [u'С', u'Дроп/Споил'],
            'mobTitle': [u'Имя', u'Имя монстра'],
            'itemTitle': [u'Предмет', u'Название предмета'],
            'minChance': ['min', u'Минимальный шанс'],
            'maxChance': ['max', u'Максимальный шанс'],
            'minCount': ['min', u'Минимальное количество'],
            'maxCount': ['max', u'Максимальное количество'],
            'level': [u'Ур.', u'Уровень монстра'],
            'location': [u'Локация', u'Местонаходжение монстра'],
            'features': [u'Особенности', u'Особенности'],
            'hp': ['HP', u'Уровень здоровья'],
            'exp': [u'Опыт', u'Очки опыта'],
            'image': [u'И', u'Изображение'],
        }
        self.headerKeys = []
        for j, key in enumerate(keys):
            item = QtGui.QTableWidgetItem()
            item.setText(strings[key][0])
            item.setToolTip(strings[key][1])
            self.tableWidget.setHorizontalHeaderItem(j, item)
            self.headerKeys.append(strings[key][0])

    # get current header label
    def getCurrentHeader(self, col):
        return self.headerKeys[col]

    # return True if col must be numeric
    def colIsNumeric(self, col):
        if self.getCurrentHeader(col) in ('HP', u'Ур.', u'Опыт', 'min', 'max'):
            return True

    def alignItem(self, col, item):
        align = {
            'min': QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            'HP': QtCore.Qt.AlignCenter,
            u'Опыт': QtCore.Qt.AlignCenter,
            u'Ур.': QtCore.Qt.AlignCenter,
            u'С': QtCore.Qt.AlignCenter,
        }
        header = self.getCurrentHeader(col)
        if header in align:
            item.setTextAlignment(align[header])

    def resizeHeaders(self):
        for i in range(self.tableWidget.columnCount()):
            header = self.tableWidget.horizontalHeaderItem(i)
            if header.text() in (
                u'Особенности',
                u'Предмет',
                u'Локация',
                u'Имя',
            ):
                if header.text() == u'Имя' and self.formatSql.isDropInfo:
                    self.tableWidget.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.Fixed)
                else:
                    self.tableWidget.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.Stretch)
            else:
                self.tableWidget.horizontalHeader().setResizeMode(i, QtGui.QHeaderView.Fixed)
            if header.text() == u'С':
                self.tableWidget.setColumnWidth(0, 16)
            if header.text() == u'И':
                self.tableWidget.setColumnWidth(1, 24)

    def resizeRows(self):
        if self.formatSql.isDropInfo:
            self.tableWidget.verticalHeader().setDefaultSectionSize(24)
        else:
            self.tableWidget.verticalHeader().setDefaultSectionSize(self.rowDefaultSize)

    # get images from DB and return widget
    def getImages(self, features):
        rowWidget = QtGui.QWidget()
        hLayout = QtGui.QHBoxLayout(rowWidget)
        cur = self.__con.cursor()
        features = features.split(',')
        self.formatSql.setMobFeatures(features)
        cur.execute(self.formatSql.getMobFeaturesSql())
        row = cur.fetchone()
        while row is not None:
            img = QtGui.QPixmap()
            img.loadFromData(StringIO(row[0]).read())
            img = img.scaled(24, 24, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            imgWidget = QtGui.QLabel()
            imgWidget.setPixmap(img)
            imgWidget.setToolTip('<p>%s</p>' % row[1])
            hLayout.addWidget(imgWidget)
            row = cur.fetchone()
        hLayout.addStretch(1)
        hLayout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hLayout.setContentsMargins(5, 0, 5, 0)
        hLayout.setSpacing(2)
        rowWidget.setLayout(hLayout)
        return rowWidget

    # get features for filter and return widget with buttons
    def initFilterPanel(self):
        rowWidget = QtGui.QWidget()
        hLayout = QtGui.QHBoxLayout(rowWidget)
        cur = self.__con.cursor()
        cur.execute(self.formatSql.getFilterSql())
        row = cur.fetchone()
        while row is not None:
            img = QtGui.QPixmap()
            img.loadFromData(StringIO(row[0]).read())
            img = img.scaled(24, 24, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            btnWidget = QtGui.QPushButton()
            btnWidget.setCheckable(True)
            btnWidget.setObjectName(str(row[2]))
            btnWidget.setIcon(img)
            btnWidget.setIconSize(QtCore.QSize(24, 24))
            btnWidget.setToolTip('<p>%s</p>' % row[1])
            btnWidget.setMaximumWidth(32)
            btnWidget.clicked[bool].connect(self.toggleFeatures)
            hLayout.addWidget(btnWidget)
            row = cur.fetchone()
        hLayout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hLayout.setContentsMargins(0, 0, 0, 0)
        hLayout.setSpacing(0)
        rowWidget.setLayout(hLayout)
        return rowWidget


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    con = None
    con = sql.connect('l2wiki.db')

    wid = MainWindow(con)
    wid.show()
    sys.exit(app.exec_())
