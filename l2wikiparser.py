# vim: set fileencoding=utf-8
from simplemediawiki import MediaWiki
from simplemediawiki import build_user_agent
from lxml import html
from urllib2 import urlopen
import sqlite3 as sql
import re
import md5
import sys


# exclude this pageids from parsing
excludeIDS = (
    10474,
    12308,
    15108,
    15016,
)


# check database, if tables exist
def dbCheck(con):
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    rows = cur.fetchall()
    if len(rows):
        return True
    else:
        return False


# init database
def dbCreate(con):
    cur = con.cursor()
    cur.executescript("""
                      DROP TABLE IF EXISTS mobInfo;
                      DROP TABLE IF EXISTS dropInfo;
                      DROP TABLE IF EXISTS features;
                      CREATE TABLE mobInfo(pageid INTEGER PRIMARY KEY, title TEXT,
                      location TEXT, level INT, hp INT, exp INT, features);
                      CREATE TABLE dropInfo(id INTEGER PRIMARY KEY AUTOINCREMENT, pageid INT,
                      imageid INT, title TEXT, isSpoil BOOLEAN, minChance FLOAT,
                      maxChance FLOAT, minCount INT, maxCount INT);
                      CREATE TABLE features(id INTEGER PRIMARY KEY, desc TEXT, image BLOB);
                      CREATE TABLE images(id INTEGER PRIMARY KEY, image BLOB);
                      """)
    con.commit()


# little function to delete any non digital characters and return integer or
# float
def s2i(str):
    # regex for decimal
    d = re.compile(r'[^\d.]+')
    str = d.sub('', str)
    if str.isdigit():
        return int(str)
    else:
        return float(str)


# generate index for feature based on description string
def makeIndex(str):
    idx = md5.new()
    idx.update(str.encode('utf-8'))
    return int(idx.hexdigest()[-8:], 16)


# check if feature image already exist
def isFeatureExists(con, idx):
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM features WHERE id = {0}'.format(idx))
    r = cur.fetchone()
    if r[0] > 0:
        return True
    else:
        return False


# check if item image already exist
def isImageExists(con, idx):
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM images WHERE id = {0}'.format(idx))
    r = cur.fetchone()
    if r[0] > 0:
        return True
    else:
        return False


# save feature images and description to db
def saveFeature(con, idx, desc, url):
    cur = con.cursor()
    f = urlopen(url)
    image = sql.Binary(f.read())
    cur.execute(
        """
        INSERT INTO features(id, desc, image)
        VALUES(?,?,?)
        """, (idx,
              desc,
              image,
              ))
    con.commit()
    f.close()


# save image of item to db
def saveImage(con, idx, url):
    cur = con.cursor()
    f = urlopen(url)
    image = sql.Binary(f.read())
    cur.execute(
        """
        INSERT INTO images(id, image)
        VALUES(?,?)
        """, (idx,
              image,
              ))
    con.commit()
    f.close()


# return features of mob and prepare for save to db
def parseFeatures(con, r):
    items = []
    while len(r) > 1:
        url = 'http://l2central.info' + r.pop()
        desc = r.pop()
        idx = makeIndex(desc)
        items.append(str(idx))
        if not isFeatureExists(con, idx):
            saveFeature(con, idx, desc, url)
    return ','.join(items)


# helper function for parseDrop.
# determine is Raid boss or not
def isRB(parsedText):
    xpath = '//*[@id="npc_brief_info_1"]/tr/th/span[1]/text()'
    r = parsedText.xpath(xpath)
    if len(r):
        return True
    xpath = '//*[@id="npc_brief_info_2"]/tr[10]/td/a/img/@alt | \
        //*[@id="npc_brief_info_2"]/tr[10]/td/a/img/@src'
    r = parsedText.xpath(xpath)
    while len(r) > 1:
        feature = r.pop()
        r.pop()
        feature = feature.split('/')[-1:]
        feature = feature.pop()
        if feature == 'Skill_raid.jpg':
            return True
    return False


# parse mob info from given wiki text
def parseMob(con, parsedText):
    # xpath expressions
    paths = (
        '//*[@id="npc_brief_info_1"]/tr[2]/td/a/text()',
        '//*[@id="npc_brief_info_2"]/tr[4]/td[2]/a/text()',
        '//*[@id="npc_brief_info_2"]/tr[5]/td[2]/text()',
        '//*[@id="npc_brief_info_2"]/tr[7]/td[2]/text()',
        '//*[@id="npc_brief_info_2"]/tr[10]/td/a/img/@alt | \
        //*[@id="npc_brief_info_2"]/tr[10]/td/a/img/@src',
    )
    items = []
    for p in paths:
        items.append(parsedText.xpath(p))
    features = parseFeatures(con, items[4])
    if len(items[0]) > 1:
        items[0] = [', '.join(items[0])]
    return {
        'location': items[0].pop(),
        'level': s2i(items[1].pop()),
        'hp': s2i(items[2].pop()),
        'exp': s2i(items[3].pop()),
        'features': features,
    }


# helper function for parseDrop
def getDropItems(con, r, pageid, isSpoil=False):
    # unicode code for em-dash symbol
    emdash = u'\u2014'
    items = []
    while len(r) > 3:
        chance = r.pop()
        count = r.pop()
        title = r.pop()
        url = 'http://l2central.info' + r.pop()
        # 'em-dash' split values
        if emdash in chance:
            minChance, maxChance = chance.split(emdash)
        else:
            minChance, maxChance = [chance] * 2
        if emdash in count:
            minCount, maxCount = count.split(emdash)
        else:
            minCount, maxCount = [count] * 2
        # make index and save image
        idx = url.split('/')[-1:]
        idx = int(s2i(idx.pop()))
        if not isImageExists(con, idx):
            saveImage(con, idx, url)
        items.append({
            'imageid': idx,
            'title': title,
            'pageid': pageid,
            'isSpoil': isSpoil,
            'minChance': s2i(minChance),
            'maxChance': s2i(maxChance),
            'minCount': s2i(minCount),
            'maxCount': s2i(maxCount),
        })
    return items


# parse drop and spoil info from given wiki text
def parseDrop(con, parsedText, pageid):
    # xpath expressions
    p = '//div/table[{0}]/tr[*]/td[1]/a[1]/img/@src | \
        //div/table[{0}]/tr[*]/td[1]/a[2]/text() | \
        //div/table[{0}]/tr[*]/td[position()=2 or position()=3]/text()'
    items = []
    for table in (3, 4, 5):
        if table == 5:
            isSpoil = True
        else:
            isSpoil = False
        r = parsedText.xpath(p.format(table))
        items.extend(getDropItems(con, r, pageid, isSpoil))
    return items


# parse wiki part while cmcontinue returned
def parseWikiPart(con, wiki, cmcontinue=None):
    call = {
        'action': 'query',
        'list': 'categorymembers',
        'cmtitle': 'Категория:Монстры',
        'cmlimit': 20,
    }
    if cmcontinue:
        call['cmcontinue'] = cmcontinue

    root = wiki.call(call)
    cur = con.cursor()
    for row in root['query']['categorymembers']:
        if row['pageid'] not in excludeIDS:
            wikiText = wiki.call({
                'action': 'parse',
                'pageid': row['pageid'],
            })
            wikiText = wikiText['parse']['text']['*']
            parsedText = html.fromstring(wikiText)
            print('Pageid: ' + str(row['pageid']) + ' Title: ' + row['title'])
            if isRB(parsedText):
                continue
            mobInfo = parseMob(con, parsedText)
            if len(mobInfo) and mobInfo['exp'] > 0:
                cur.execute("""
                            INSERT INTO mobInfo
                            (pageid,title,location,level,hp,exp,features)
                            VALUES(?, ?, ?, ?, ?, ?, ?)
                            """, (row['pageid'],
                                  row['title'],
                                  mobInfo['location'],
                                  mobInfo['level'],
                                  mobInfo['hp'],
                                  mobInfo['exp'],
                                  mobInfo['features'],
                                  ))
                con.commit()
            dropInfo = parseDrop(con, parsedText, row['pageid'])
            if len(dropInfo):
                for row in dropInfo:
                    cur.execute("""
                                INSERT INTO dropInfo
                                (pageid,imageid,title,isSpoil,
                                minChance,maxChance,minCount,maxCount)
                                VALUES(?,?,?,?,?,?,?,?)
                                """, (row['pageid'],
                                      row['imageid'],
                                      row['title'],
                                      row['isSpoil'],
                                      row['minChance'],
                                      row['maxChance'],
                                      row['minCount'],
                                      row['maxCount'],
                                      ))
                    con.commit()
    if 'query-continue' in root.keys():
        return root['query-continue']['categorymembers']['cmcontinue']
    else:
        return None


# parse wiki
def parseWiki(con):
    useragent = build_user_agent('l2wiki', 0.1, 'https://github.com/tm-calculate/l2wiki')
    wiki = MediaWiki('http://l2central.info/c/api.php', user_agent=useragent)
    cmcontinue = parseWikiPart(con, wiki)
    while cmcontinue:
        cmcontinue = parseWikiPart(con, wiki, cmcontinue)


if __name__ == '__main__':
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
