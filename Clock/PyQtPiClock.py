# -*- coding: utf-8 -*-                 # NOQA

import sys
import os
import platform
import signal
import datetime
import time
import json
import locale
import random
import re
import logging
import logging.handlers


from PyQt5 import QtGui, QtNetwork, QtWidgets
from PyQt5.QtGui import QPixmap, QMovie, QBrush, QColor, QPainter
from PyQt5.QtCore import Qt, QUrl, QTimer, QSize, QRect, QBuffer, QIODevice, QByteArray
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkProxy
from subprocess import Popen

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QEventLoop,QUrl


sys.dont_write_bytecode = True
from GoogleMercatorProjection import getCorners             # NOQA
import ApiKeys                                              # NOQA


def tick():
    global clockrect, clockface, lastday
    global datex, datex2, datey2, pdy

    if Config.DateLocale != "":
        try:
            locale.setlocale(locale.LC_TIME, Config.DateLocale)
        except:
            pass

    now = datetime.datetime.now()
    # Update the clock
    clockface.update(now)
    dy = "{0:%I:%M %p}".format(now)
    if dy != pdy:
        pdy = dy
        datey2.setText(dy)

    if now.day != lastday:
        lastday = now.day
        # date
        sup = 'th'
        if (now.day == 1 or now.day == 21 or now.day == 31):
            sup = 'st'
        if (now.day == 2 or now.day == 22):
            sup = 'nd'
        if (now.day == 3 or now.day == 23):
            sup = 'rd'
        if Config.DateLocale != "":
            sup = ""
        ds = "{0:%A %B} {0.day}<sup>{1}</sup> {0.year}".format(now, sup)
        datex.setText(ds)
        datex2.setText(ds)


def tempfinished():
    global tempreply, temp
    if tempreply.error() != QNetworkReply.NoError:
        return
    tempstr = bytes(tempreply.readAll()).decode("utf-8")
    tempdata = json.loads(tempstr)
    if tempdata['temp'] == '':
        return
    if Config.metric:
        s = Config.LInsideTemp + \
            "%3.1f" % ((float(tempdata['temp']) - 32.0) * 5.0 / 9.0)
        if tempdata['temps']:
            if len(tempdata['temps']) > 1:
                s = ''
                for tk in tempdata['temps']:
                    s += ' ' + tk + ':' + \
                        "%3.1f" % (
                            (float(tempdata['temps'][tk]) - 32.0) * 5.0 / 9.0)
    else:
        s = Config.LInsideTemp + tempdata['temp']
        if tempdata['temps']:
            if len(tempdata['temps']) > 1:
                s = ''
                for tk in tempdata['temps']:
                    s += ' ' + tk + ':' + tempdata['temps'][tk]
    temp.setText(s)


def gettemp():
    global tempreply
    host = 'localhost'
    if platform.uname()[1] == 'KW81':
        host = 'piclock.local'  # this is here just for testing
    r = QUrl('http://' + host + ':48213/temp')
    r = QNetworkRequest(r)
    tempreply = manager.get(r)
    tempreply.finished.connect(tempfinished)


def wxfinished(read_cache=False):
    global wxreply, wxdata, cache_dir
    global wxicon, temper, wxdesc, press, humidity
    global wind, wind2, wdate, bottom, forecast
    global wxicon2, temper2, wxdesc

    wxcache = os.path.join(cache_dir, 'wxdata.json')
    wxstr = ''
    if read_cache:
        wxstr = open(wxcache, 'r').read()
    else:
        wxstr = bytes(wxreply.readAll()).decode("utf-8")
        with open(wxcache, 'w') as f:
            f.write(wxstr)

    # logging.info(wxstr)
    wxdata = json.loads(wxstr)
    f = wxdata['current_observation']
    iconurl = f['icon_url']
    icp = ''
    if (re.search('/nt_', iconurl)):
        icp = 'n_'
    wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + icp + f['icon'] + ".png")
    wxicon.setPixmap(wxiconpixmap.scaled(
        wxicon.width(), wxicon.height(), Qt.IgnoreAspectRatio,
        Qt.SmoothTransformation))
    wxicon2.setPixmap(wxiconpixmap.scaled(
        wxicon.width(),
        wxicon.height(),
        Qt.IgnoreAspectRatio,
        Qt.SmoothTransformation))
    wxdesc.setText(f['weather'])
    wxdesc2.setText(f['weather'])

    if Config.metric:
        temper.setText(str(f['temp_c']) + u'°C')
        temper2.setText(str(f['temp_c']) + u'°C')
        press.setText(Config.LPressure +
                      f['pressure_mb'] + ' ' + f['pressure_trend'])
        humidity.setText(Config.LHumidity + f['relative_humidity'])
        wd = f['wind_dir']
        if Config.wind_degrees:
            wd = str(f['wind_degrees']) + u'°'
        wind.setText(Config.LWind +
                     wd + ' ' +
                     str(f['wind_kph']) +
                     Config.Lgusting +
                     str(f['wind_gust_kph']))
        wind2.setText(Config.LFeelslike + str(f['feelslike_c']))
        wdate.setText("{0:%H:%M}".format(datetime.datetime.fromtimestamp(
            int(f['local_epoch']))) +
            Config.LPrecip1hr + f['precip_1hr_metric'] + 'mm ' +
            Config.LToday + f['precip_today_metric'] + 'mm')
    else:
        temper.setText(str(f['temp_f']) + u'°F')
        temper2.setText(str(f['temp_f']) + u'°F')
        press.setText(Config.LPressure +
                      f['pressure_in'] + ' ' + f['pressure_trend'])
        humidity.setText(Config.LHumidity + f['relative_humidity'])
        wd = f['wind_dir']
        if Config.wind_degrees:
            wd = str(f['wind_degrees']) + u'°'
        wind.setText(Config.LWind + wd + ' ' +
                     str(f['wind_mph']) + Config.Lgusting +
                     str(f['wind_gust_mph']))
        wind2.setText(Config.LFeelslike + str(f['feelslike_f']))
        wdate.setText("{0:%H:%M}".format(datetime.datetime.fromtimestamp(
            int(f['local_epoch']))) +
            Config.LPrecip1hr + f['precip_1hr_in'] + 'in ' +
            Config.LToday + f['precip_today_in'] + 'in')

    bottom.setText(Config.LSunRise +
                   wxdata['sun_phase']['sunrise']['hour'] + ':' +
                   wxdata['sun_phase']['sunrise']['minute'] +
                   Config.LSet +
                   wxdata['sun_phase']['sunset']['hour'] + ':' +
                   wxdata['sun_phase']['sunset']['minute'] +
                   Config.LMoonPhase +
                   wxdata['moon_phase']['phaseofMoon']
                   )

    for i in range(0, 3):
        f = wxdata['hourly_forecast'][i * 3 + 2]
        fl = forecast[i]
        iconurl = f['icon_url']
        icp = ''
        if (re.search('/nt_', iconurl)):
            icp = 'n_'
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(
            Config.icons + "/" + icp + f['icon'] + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        wx.setText(f['condition'])
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText(f['FCTTIME']['weekday_name'] + ' ' + f['FCTTIME']['civil'])
        wx2 = fl.findChild(QtWidgets.QLabel, "wx2")
        s = ''
        if float(f['pop']) > 0.0:
            s += f['pop'] + '% '
        if Config.metric:
            if float(f['snow']['metric']) > 0.0:
                s += Config.LSnow + f['snow']['metric'] + 'mm '
            else:
                if float(f['qpf']['metric']) > 0.0:
                    s += Config.LRain + f['qpf']['metric'] + 'mm '
            s += f['temp']['metric'] + u'°C'
        else:
            if float(f['snow']['english']) > 0.0:
                s += Config.LSnow + f['snow']['english'] + 'in '
            else:
                if float(f['qpf']['english']) > 0.0:
                    s += Config.LRain + f['qpf']['english'] + 'in '
            s += f['temp']['english'] + u'°F'

        wx2.setText(s)

    for i in range(3, 9):
        f = wxdata['forecast']['simpleforecast']['forecastday'][i - 3]
        fl = forecast[i]
        icon = fl.findChild(QtWidgets.QLabel, "icon")
        wxiconpixmap = QtGui.QPixmap(Config.icons + "/" + f['icon'] + ".png")
        icon.setPixmap(wxiconpixmap.scaled(
            icon.width(),
            icon.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation))
        wx = fl.findChild(QtWidgets.QLabel, "wx")
        wx.setText(f['conditions'])
        day = fl.findChild(QtWidgets.QLabel, "day")
        day.setText(f['date']['weekday'])
        wx2 = fl.findChild(QtWidgets.QLabel, "wx2")
        s = ''
        if float(f['pop']) > 0.0:
            s += str(f['pop']) + '% '
        if Config.metric:
            if float(f['snow_allday']['cm']) > 0.0:
                s += Config.LSnow + str(f['snow_allday']['cm']) + 'cm '
            else:
                if float(f['qpf_allday']['mm']) > 0.0:
                    s += Config.LRain + str(f['qpf_allday']['mm']) + 'mm '
            s += str(f['high']['celsius']) + '/' + \
                str(f['low']['celsius']) + u'°C'
        else:
            if float(f['snow_allday']['in']) > 0.0:
                s += Config.LSnow + str(f['snow_allday']['in']) + 'in '
            else:
                if float(f['qpf_allday']['in']) > 0.0:
                    s += Config.LRain + str(f['qpf_allday']['in']) + 'in '
            s += str(f['high']['fahrenheit']) + '/' + \
                str(f['low']['fahrenheit']) + u'°F'
        wx2.setText(s)


def getwx():
    global wxurl
    global wxreply
    global cache_dir

    logging.info("getting current and forecast:" + time.ctime())
    wxcache = os.path.join(cache_dir, 'wxdata.json')
    if os.path.exists(wxcache):
        mtime = os.stat(wxcache).st_mtime
        cur_time = time.time()
        refresh_time = (Config.weather_refresh - 1) * 60
        # if this was written within the current refresh minus 1 minute
        if mtime > (cur_time - refresh_time):
            logging.info("using wxcache weather data")
            wxfinished(read_cache=True)
        else:
            # cache is out of range
            wxurl = Config.wuprefix + ApiKeys.wuapi + \
                    '/conditions/astronomy/hourly10day/forecast10day/lang:' + \
                    Config.wuLanguage + '/q/'
            wxurl += str(Config.wulocation.lat) + ',' + \
                     str(Config.wulocation.lng) + '.json'
            wxurl += '?r=' + str(random.random())
            logging.info(wxurl)
            r = QUrl(wxurl)
            r = QNetworkRequest(r)
            wxreply = manager.get(r)
            wxreply.finished.connect(wxfinished)
    else:
        # used when required to create cache file
        wxurl = Config.wuprefix + ApiKeys.wuapi + \
            '/conditions/astronomy/hourly10day/forecast10day/lang:' + \
            Config.wuLanguage + '/q/'
        wxurl += str(Config.wulocation.lat) + ',' + \
            str(Config.wulocation.lng) + '.json'
        wxurl += '?r=' + str(random.random())
        logging.info(wxurl)
        r = QUrl(wxurl)
        r = QNetworkRequest(r)
        wxreply = manager.get(r)
        wxreply.finished.connect(wxfinished)


def getallwx():
    getwx()


def qtstart():
    global ctimer, wxtimer, temptimer, frametimer
    global manager
    global objradar1
    global objradar2
    global objradar3
    global objradar4
    global objtraffic

    getallwx()

    gettemp()

    objradar1.start(Config.radar_refresh * 60)
    objradar1.wxstart()
    objradar2.start(Config.radar_refresh * 60)
    objradar2.wxstart()
    objradar3.start(Config.radar_refresh * 60)
    objradar4.start(Config.radar_refresh * 60)
    objtraffic.start(Config.traffic_refresh * 60)

    ctimer = QTimer()
    ctimer.timeout.connect(tick)
    ctimer.start(1000)

    wxtimer = QTimer()
    wxtimer.timeout.connect(getallwx)
    wxtimer.start(1000 * Config.weather_refresh *
                  60 + random.uniform(1000, 10000))

    temptimer = QTimer()
    temptimer.timeout.connect(gettemp)
    temptimer.start(1000 * 10 * 60 + random.uniform(1000, 10000))

    frametimer = QTimer()
    frametimer.timeout.connect(nextframe)
    frametimer.timeout.connect(resetframetimer)
    frametimer.start(10000)


class Radar(QtWidgets.QLabel):

    def __init__(self, parent, radar, rect, myname):
        global xscale, yscale
        self.myname = myname
        self.rect = rect
        self.satellite = Config.satellite
        try:
            if radar["satellite"]:
                self.satellite = 1
        except KeyError:
            pass
        self.baseurl = self.mapurl(radar, rect, False)
        logging.info("google map base url: " + self.baseurl)
        self.mkurl = self.mapurl(radar, rect, True)
        self.wxurl = self.radarurl(radar, rect)
        logging.info("radar url: " + self.wxurl)
        QtWidgets.QLabel.__init__(self, parent)
        self.interval = Config.radar_refresh * 60
        self.lastwx = 0
        self.retries = 0

        self.setObjectName("radar")
        self.setGeometry(rect)
        self.setStyleSheet("#radar { background-color: grey; }")
        self.setAlignment(Qt.AlignCenter)

        self.wwx = QtWidgets.QLabel(self)
        self.wwx.setObjectName("wx")
        self.wwx.setStyleSheet("#wx { background-color: transparent; }")
        self.wwx.setGeometry(0, 0, rect.width(), rect.height())

        self.wmk = QtWidgets.QLabel(self)
        self.wmk.setObjectName("mk")
        self.wmk.setStyleSheet("#mk { background-color: transparent; }")
        self.wmk.setGeometry(0, 0, rect.width(), rect.height())

        self.wxmovie = QMovie()

        piclock_dir = os.path.dirname(os.path.abspath(__file__))
        cache_dir = os.path.join(piclock_dir, '.cache')
        cache_filename = "{}.gif".format(self.myname)
        self.cache_file = os.path.join(cache_dir, cache_filename)


    def mapurl(self, radar, rect, markersonly):
        # 'https://maps.googleapis.com/maps/api/staticmap?maptype=hybrid&center='+rcenter.lat+','+rcenter.lng+'&zoom='+rzoom+'&size=300x275'+markersr;
        urlp = []

        if len(ApiKeys.googleapi) > 0:
            urlp.append('key=' + ApiKeys.googleapi)
        urlp.append(
            'center=' + str(radar['center'].lat) +
            ',' + str(radar['center'].lng))
        zoom = radar['zoom']
        rsize = rect.size()
        if rsize.width() > 640 or rsize.height() > 640:
            rsize = QSize(rsize.width() / 2, rsize.height() / 2)
            zoom -= 1
        urlp.append('zoom=' + str(zoom))
        urlp.append('size=' + str(rsize.width()) + 'x' + str(rsize.height()))
        if markersonly:
            urlp.append('style=visibility:off')
        else:
            urlp.append('maptype=hybrid')
        for marker in radar['markers']:
            marks = []
            for opts in marker:
                if opts != 'location':
                    marks.append(opts + ':' + marker[opts])
            marks.append(str(marker['location'].lat) +
                         ',' + str(marker['location'].lng))
            urlp.append('markers=' + '|'.join(marks))

        return 'http://maps.googleapis.com/maps/api/staticmap?' + \
            '&'.join(urlp)

    def radarurl(self, radar, rect):
        # wuprefix = 'http://api.wunderground.com/api/';
        # wuprefix+wuapi+'/animatedradar/image.gif?maxlat='+rNE.lat+'&maxlon='+
        #       rNE.lng+'&minlat='+rSW.lat+'&minlon='+rSW.lng+wuoptionsr;
        # wuoptionsr = '&width=300&height=275&newmaps=0&reproj.automerc=1&num=5
        #       &delay=25&timelabel=1&timelabel.y=10&rainsnow=1&smooth=1';
        rr = getCorners(radar['center'], radar['zoom'],
                        rect.width(), rect.height())
        if self.satellite:
            return (Config.wuprefix + ApiKeys.wuapi +
                    '/animatedsatellite/lang:' +
                    Config.wuLanguage +
                    '/image.gif' +
                    '?maxlat=' + str(rr['N']) +
                    '&maxlon=' + str(rr['E']) +
                    '&minlat=' + str(rr['S']) +
                    '&minlon=' + str(rr['W']) +
                    '&width=' + str(rect.width()) +
                    '&height=' + str(rect.height()) +
                    '&newmaps=0&reproj.automerc=1&num=5&delay=25' +
                    '&timelabel=1&timelabel.y=10&smooth=1&key=sat_ir4_bottom'
                    )
        else:
            return (Config.wuprefix +
                    ApiKeys.wuapi +
                    '/animatedradar/lang:' +
                    Config.wuLanguage + '/image.gif' +
                    '?maxlat=' + str(rr['N']) +
                    '&maxlon=' + str(rr['E']) +
                    '&minlat=' + str(rr['S']) +
                    '&minlon=' + str(rr['W']) +
                    '&width=' + str(rect.width()) +
                    '&height=' + str(rect.height()) +
                    '&newmaps=0&reproj.automerc=1&num=5&delay=25' +
                    '&timelabel=1&timelabel.y=10&rainsnow=1&smooth=1' +
                    '&radar_bitmap=1&xnoclutter=1&xnoclutter_mask=1&cors=1'
                    )

    def basefinished(self):
        if self.basereply.error() != QNetworkReply.NoError:
            return
        self.basepixmap = QPixmap()
        self.basepixmap.loadFromData(self.basereply.readAll())
        if self.basepixmap.size() != self.rect.size():
            self.basepixmap = self.basepixmap.scaled(self.rect.size(),
                                                     Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation)
        if self.satellite:
            p = QPixmap(self.basepixmap.size())
            p.fill(Qt.transparent)
            painter = QPainter()
            painter.begin(p)
            painter.setOpacity(0.6)
            painter.drawPixmap(0, 0, self.basepixmap)
            painter.end()
            self.basepixmap = p
            self.wwx.setPixmap(self.basepixmap)
        else:
            self.setPixmap(self.basepixmap)

    def mkfinished(self):
        if self.mkreply.error() != QNetworkReply.NoError:
            return
        self.mkpixmap = QPixmap()
        self.mkpixmap.loadFromData(self.mkreply.readAll())
        if self.mkpixmap.size() != self.rect.size():
            self.mkpixmap = self.mkpixmap.scaled(
                self.rect.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation)
        br = QBrush(QColor(Config.dimcolor))
        painter = QPainter()
        painter.begin(self.mkpixmap)
        painter.fillRect(0, 0, self.mkpixmap.width(),
                         self.mkpixmap.height(), br)
        painter.end()
        self.wmk.setPixmap(self.mkpixmap)

    def wxfinished(self, read_cache=False):

        if not read_cache:
            if self.wxreply.error() != QNetworkReply.NoError:
                logging.info("get radar error " + self.myname + ":" +
                            str(self.wxreply.error()))
                self.lastwx = 0
                return
            logging.info("radar map received:" + self.myname + ":" + time.ctime())

        self.wxmovie.stop()
        # read cache if called for, else write to cache
        if read_cache:
            cache_data = open(self.cache_file, 'rb').read()
            self.wxdata = QByteArray(cache_data)
        else:
            self.wxdata = self.wxreply.readAll()
            with open(self.cache_file, 'wb') as f:
                f.write(self.wxdata)

        self.wxbuff = QBuffer(self.wxdata)
        self.wxbuff.open(QIODevice.ReadOnly)
        mov = QMovie(self.wxbuff, b'GIF')
        logging.info("radar map frame count:" + self.myname + ":" +
                     str(mov.frameCount()) + ":r" + str(self.retries))
        if mov.frameCount() > 2:
            self.lastwx = time.time()
            self.retries = 0
        else:
            # radar image retreval failed
            if self.retries > 3:
                # give up, last successful animation stays.
                # the next normal radar_refresh time (default 10min) will apply
                self.lastwx = time.time()
                return

            self.lastwx = 0
            # count retries
            self.retries = self.retries + 1
            # retry in 5 seconds
            QTimer.singleShot(5 * 1000, self.getwx)
            return
        self.wxmovie = mov
        if self.satellite:
            self.setMovie(self.wxmovie)
        else:
            self.wwx.setMovie(self.wxmovie)
        if self.parent().isVisible():
            self.wxmovie.start()

    def getwx(self):
        global lastapiget
        i = 0.1
        # making sure there is at least 2 seconds between radar api calls
        lastapiget += 2
        if time.time() > lastapiget:
            lastapiget = time.time()
        else:
            i = lastapiget - time.time()
        logging.info("get radar api call spacing oneshot get i=" + str(i))
        QTimer.singleShot(i * 1000, self.getwx2)

    def getwx2(self):
        global manager
        try:
            if self.wxreply.isRunning():
                return
        except Exception:
            pass
        logging.info("getting radar map " + self.myname + ":" + time.ctime())

        if os.path.exists(self.cache_file):
            mtime = os.stat(self.cache_file).st_mtime
            cur_time = time.time()
            refresh_time = (Config.radar_refresh - 1) * 60
            # if this was written within the current refresh minus 1 minute
            if mtime > (cur_time - refresh_time):
                logging.info("using cached radar images")
                self.wxfinished(read_cache=True)
            else:
                self.wxreq = QNetworkRequest(
                    QUrl(self.wxurl + '&rrrand=' + str(time.time())))
                self.wxreply = manager.get(self.wxreq)
                self.wxreply.finished.connect(self.wxfinished)
        else:
            self.wxreq = QNetworkRequest(
                QUrl(self.wxurl + '&rrrand=' + str(time.time())))
            self.wxreply = manager.get(self.wxreq)
            self.wxreply.finished.connect(self.wxfinished)

    def getbase(self):
        global manager
        self.basereq = QNetworkRequest(QUrl(self.baseurl))
        self.basereply = manager.get(self.basereq)
        self.basereply.finished.connect(self.basefinished)

    def getmk(self):
        global manager
        self.mkreq = QNetworkRequest(QUrl(self.mkurl))
        self.mkreply = manager.get(self.mkreq)
        self.mkreply.finished.connect(self.mkfinished)

    def start(self, interval=0):
        if interval > 0:
            self.interval = interval
        self.getbase()
        self.getmk()
        self.timer = QTimer()
        self.timer.timeout.connect(self.getwx)

    def wxstart(self):
        logging.info("wxstart for " + self.myname)
        if (self.lastwx == 0 or (self.lastwx + self.interval) < time.time()):
            self.getwx()
        # random 1 to 10 seconds added to refresh interval to spread the
        # queries over time
        i = (self.interval + random.uniform(1, 10)) * 1000
        self.timer.start(i)
        self.wxmovie.start()
        QTimer.singleShot(1000, self.wxmovie.start)

    def wxstop(self):
        logging.info("wxstop for " + self.myname)
        self.timer.stop()
        self.wxmovie.stop()

    def stop(self):
        try:
            self.timer.stop()
            self.timer = None
            if self.wxmovie:
                self.wxmovie.stop()
        except Exception:
            pass

class Traffic(QWebEngineView):

    def __init__(self, parent, radar, rect, myname):
        global xscale, yscale
        self.myname = myname
        self.rect = rect
        self.satellite = Config.satellite
        try:
            if radar["satellite"]:
                self.satellite = 1
        except KeyError:
            pass
        self.baseurl = self.trafficurl(radar, rect, False)
        logging.info("google traffic map base url: " + self.baseurl)
        super().__init__(parent)

        self.interval = Config.traffic_refresh * 60

        self.lastwx = 0
        self.retries = 0

        self.setObjectName(self.myname)
        self.setGeometry(rect)
        self.setStyleSheet("#radar { background-color: grey; }")

        self.page = self.page()

    def trafficurl(self, radar, rect, markersonly):
        urlp = []
        urlp.append( (str(radar['center'].lat) + ',' + str(radar['center'].lng) + ','))
        zoom = radar['zoom']
        urlp.append( str(zoom) + 'z' + '/data=!5')
        urlp.append('m')
        urlp.append('1!1e1')
        return 'https://www.google.com/maps/@' + ''.join(urlp)

    def gettraffic(self):
        logging.info("get traffic api call" )
        self.page.triggerAction(QWebEnginePage.Reload)

    def getbase(self):
        # Apparently QnetworkReply and QwebEngineView are incompatible
        logging.info("getbase for " + self.myname)
        self.page.load(QUrl(self.baseurl))

    def start(self, interval=0):
        if interval > 0:
            self.interval = interval
        self.getbase()
        self.timer = QTimer()
        self.timer.start(self.interval * 1000)
        self.timer.timeout.connect(self.gettraffic)

    def stop(self):
        try:
            self.timer.stop()
            self.timer = None
        except Exception:
            pass

def realquit():
    w.close()


def myquit(a=0, b=0):
    global objradar1, objradar2, objradar3, objradar4, objtraffic
    global ctimer, wtimer, temptimer

    objradar1.stop()
    objradar2.stop()
    objradar3.stop()
    objradar4.stop()
    objtraffic.stop()
    ctimer.stop()
    wxtimer.stop()
    temptimer.stop()

    QTimer.singleShot(200, realquit)


def fixupframe(frame, onoff):
    for child in frame.children():
        if isinstance(child, Radar):
            if onoff:
                # logging.info("calling wxstart on radar on ",
                #    frame.objectName())
                child.wxstart()
            else:
                # logging.info "calling wxstop on radar on ",frame.objectName()
                child.wxstop()


def nextframe(plusminus=1):
    global frames, framep
    frames[framep].setVisible(False)
    fixupframe(frames[framep], False)
    framep += plusminus
    if framep >= len(frames):
        framep = 0
    if framep < 0:
        framep = len(frames) - 1
    frames[framep].setVisible(True)
    fixupframe(frames[framep], True)

"""
 When a mouse/key event occurs, frametimer is set to 20 seconds
 Post 20 secons timeout, frametimer is reset to 10 seconds here
"""
def resetframetimer():
    frametimer.setInterval(10000)

class myMain(QtWidgets.QWidget):

    def keyPressEvent(self, event):
        global weatherplayer, lastkeytime
        if isinstance(event, QtGui.QKeyEvent):
            # logging.info(event.key(), format(event.key(), '08x'))
            if event.key() == Qt.Key_F4:
                myquit()
            if event.key() == Qt.Key_F2:
                if time.time() > lastkeytime:
                    if weatherplayer is None:
                        weatherplayer = Popen(
                            ["mpg123", "-q", Config.noaastream])
                    else:
                        weatherplayer.kill()
                        weatherplayer = None
                lastkeytime = time.time() + 2
            if event.key() == Qt.Key_Space:
                nextframe(1)
            if event.key() == Qt.Key_Left:
                nextframe(-1)
            if event.key() == Qt.Key_Right:
                nextframe(1)
        frametimer.setInterval(20000)

    def mousePressEvent(self, event):
        if type(event) == QtGui.QMouseEvent:
            nextframe(1)
        frametimer.setInterval(20000)


class LogHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # this is just a standard rotaing handler,
        # but forced to start a new file on each program startup
        self.doRollover()


if __name__ == '__main__':
    fmt = logging.Formatter('%(asctime)s %(message)s')
    logger = logging.getLogger()
    fileh = LogHandler(filename='PyQtPiClock.log', backupCount=7)
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)
    errh = logging.StreamHandler(sys.stderr)
    fileh.setFormatter(fmt)
    logger.addHandler(errh)
    logger.setLevel(logging.DEBUG)

    # setup cache
    piclock_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(piclock_dir, '.cache')
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)

    try:
        configname = 'Config'

        if len(sys.argv) > 1:
            configname = sys.argv[1]

        if not os.path.isfile(configname + ".py"):
            logging.logging.info("Config file not found %s" %
                                 configname + ".py")
            exit(1)

        Config = __import__(configname)

        # define default values for new/optional config variables.

        try:
            Config.metric
        except AttributeError:
            Config.metric = 0

        try:
            Config.weather_refresh
        except AttributeError:
            Config.weather_refresh = 30   # minutes

        try:
            Config.radar_refresh
        except AttributeError:
            Config.radar_refresh = 10    # minutes

        try:
            Config.fontattr
        except AttributeError:
            Config.fontattr = ''

        try:
            Config.dimcolor
        except AttributeError:
            Config.dimcolor = QColor('#000000')
            Config.dimcolor.setAlpha(0)

        try:
            Config.DateLocale
        except AttributeError:
            Config.DateLocale = ''

        try:
            Config.wind_degrees
        except AttributeError:
            Config.wind_degrees = 0

        try:
            Config.satellite
        except AttributeError:
            Config.satellite = 0

        try:
            Config.digital
        except AttributeError:
            Config.digital = 0

        try:
            Config.LPressure
        except AttributeError:
            Config.wuLanguage = "EN"
            Config.LPressure = "Pressure "
            Config.LHumidity = "Humidity "
            Config.LWind = "Wind "
            Config.Lgusting = " gusting "
            Config.LFeelslike = "Feels like "
            Config.LPrecip1hr = " Precip 1hr:"
            Config.LToday = "Today: "
            Config.LSunRise = "Sun Rise:"
            Config.LSet = " Set: "
            Config.LMoonPhase = " Moon Phase:"
            Config.LInsideTemp = "Inside Temp "
            Config.LRain = " Rain: "
            Config.LSnow = " Snow: "

        lastday = -1
        pdy = ""
        weatherplayer = None
        lastkeytime = 0
        lastapiget = time.time()

        app = QtWidgets.QApplication(sys.argv)
        desktop = app.desktop()
        rec = desktop.screenGeometry()
        height = rec.height()
        width = rec.width()

        signal.signal(signal.SIGINT, myquit)

        w = myMain()
        w.setWindowTitle(os.path.basename(__file__))

        w.setStyleSheet("QWidget { background-color: black;}")

        # fullbgpixmap = QtGui.QPixmap(Config.background)
        # fullbgrect = fullbgpixmap.rect()
        # xscale = float(width)/fullbgpixmap.width()
        # yscale = float(height)/fullbgpixmap.height()

        xscale = float(width) / 1440.0
        yscale = float(height) / 900.0

        frames = []
        framep = 2

        frame1 = QtWidgets.QFrame(w)
        frame1.setObjectName("frame1")
        frame1.setGeometry(0, 0, width, height)
        frame1.setStyleSheet(
            "#frame1 { background-color: black; border-image: url(" +
            Config.background + ") 0 0 0 0 stretch stretch;}")
        #frame1.setVisible(False)
        frames.append(frame1)

        frame2 = QtWidgets.QFrame(w)
        frame2.setObjectName("frame2")
        frame2.setGeometry(0, 0, width, height)
        frame2.setStyleSheet(
            "#frame2 { background-color: blue; border-image: url(" +
            Config.background + ") 0 0 0 0 stretch stretch;}")
        frame2.setVisible(False)
        frames.append(frame2)

        frame3 = QtWidgets.QFrame(w)
        frame3.setObjectName("frame3")
        frame3.setGeometry(0,0,width,height)
        frame3.setStyleSheet(
            "#frame3 { background-color: blue; border-image: url(" +
            Config.background + ") 0 0 0 0 stretch stretch;}")
        frame3.setVisible(False)
        frames.append(frame3)

        squares1 = QtWidgets.QFrame(frame1)
        squares1.setObjectName("squares1")
        squares1.setGeometry(0, height - yscale * 600,
                             xscale * 340, yscale * 600)
        squares1.setStyleSheet(
            "#squares1 { background-color: transparent; border-image: url(" +
            Config.squares1 +
            ") 0 0 0 0 stretch stretch;}")

        squares2 = QtWidgets.QFrame(frame1)
        squares2.setObjectName("squares2")
        squares2.setGeometry(width - xscale * 340, 0,
                             xscale * 340, yscale * 900)
        squares2.setStyleSheet(
            "#squares2 { background-color: transparent; border-image: url(" +
            Config.squares2 +
            ") 0 0 0 0 stretch stretch;}")

        # Set the clock type
        if not Config.digital:
            from clockfaces.Analog import Analog
            clockface = Analog(Config, frame1)

        else:
            from clockfaces.Digital import Digital
            clockface = Digital(Config, frame1)


        radar1rect = QRect(3 * xscale, 344 * yscale,
                           300 * xscale, 275 * yscale)
        objradar1 = Radar(frame1, Config.radar1, radar1rect, "radar1")

        radar2rect = QRect(3 * xscale, 622 * yscale,
                           300 * xscale, 275 * yscale)
        objradar2 = Radar(frame1, Config.radar2, radar2rect, "radar2")

        radar3rect = QRect(13 * xscale, 50 * yscale,
                           700 * xscale, 700 * yscale)
        objradar3 = Radar(frame2, Config.radar3, radar3rect, "radar3")

        radar4rect = QRect(726 * xscale, 50 * yscale,
                           700 * xscale, 700 * yscale)
        objradar4 = Radar(frame2, Config.radar4, radar4rect, "radar4")

        trafficrect = QRect(13 * xscale, 50 * yscale,
                           1400 * xscale, 800 * yscale)
        objtraffic = Traffic(frame3, Config.traffic, trafficrect, "traffic")


        datex = QtWidgets.QLabel(frame1)
        datex.setObjectName("datex")
        datex.setStyleSheet("#datex { font-family:sans-serif; color: " +
                            Config.textcolor +
                            "; background-color: transparent; font-size: " +
                            str(int(50 * xscale)) +
                            "px; " +
                            Config.fontattr +
                            "}")
        datex.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        datex.setGeometry(0, 0, width, 100)

        datex2 = QtWidgets.QLabel(frame2)
        datex2.setObjectName("datex2")
        datex2.setStyleSheet("#datex2 { font-family:sans-serif; color: " +
                             Config.textcolor +
                             "; background-color: transparent; font-size: " +
                             str(int(50 * xscale)) + "px; " +
                             Config.fontattr +
                             "}")
        datex2.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        datex2.setGeometry(800 * xscale, 780 * yscale, 640 * xscale, 100)
        datey2 = QtWidgets.QLabel(frame2)
        datey2.setObjectName("datey2")
        datey2.setStyleSheet("#datey2 { font-family:sans-serif; color: " +
                             Config.textcolor +
                             "; background-color: transparent; font-size: " +
                             str(int(50 * xscale)) +
                             "px; " +
                             Config.fontattr +
                             "}")
        datey2.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        datey2.setGeometry(800 * xscale, 840 * yscale, 640 * xscale, 100)

        ypos = -25
        wxicon = QtWidgets.QLabel(frame1)
        wxicon.setObjectName("wxicon")
        wxicon.setStyleSheet("#wxicon { background-color: transparent; }")
        wxicon.setGeometry(75 * xscale, ypos * yscale,
                           150 * xscale, 150 * yscale)

        wxicon2 = QtWidgets.QLabel(frame2)
        wxicon2.setObjectName("wxicon2")
        wxicon2.setStyleSheet("#wxicon2 { background-color: transparent; }")
        wxicon2.setGeometry(0 * xscale, 750 * yscale,
                            150 * xscale, 150 * yscale)

        ypos += 130
        wxdesc = QtWidgets.QLabel(frame1)
        wxdesc.setObjectName("wxdesc")
        wxdesc.setStyleSheet(
            "#wxdesc { background-color: transparent; color: " +
            Config.textcolor +
            "; font-size: " +
            str(int(30 * xscale)) +
            "px; " +
            Config.fontattr +
            "}")
        wxdesc.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        wxdesc.setGeometry(3 * xscale, ypos * yscale, 300 * xscale, 100)

        wxdesc2 = QtWidgets.QLabel(frame2)
        wxdesc2.setObjectName("wxdesc2")
        wxdesc2.setStyleSheet(
            "#wxdesc2 { background-color: transparent; color: " +
            Config.textcolor +
            "; font-size: " +
            str(int(50 * xscale)) +
            "px; " +
            Config.fontattr +
            "}")
        wxdesc2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        wxdesc2.setGeometry(400 * xscale, 800 * yscale, 400 * xscale, 100)

        ypos += 25
        temper = QtWidgets.QLabel(frame1)
        temper.setObjectName("temper")
        temper.setStyleSheet(
            "#temper { background-color: transparent; color: " +
            Config.textcolor + "; font-size: " +
            str(int(70 * xscale)) + "px; " +
            Config.fontattr + "}")
        temper.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        temper.setGeometry(3 * xscale, ypos * yscale, 300 * xscale, 100)

        temper2 = QtWidgets.QLabel(frame2)
        temper2.setObjectName("temper2")
        temper2.setStyleSheet(
            "#temper2 { background-color: transparent; color: " +
            Config.textcolor + "; font-size: " +
            str(int(70 * xscale)) + "px; " +
            Config.fontattr + "}")
        temper2.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        temper2.setGeometry(125 * xscale, 780 * yscale, 300 * xscale, 100)

        ypos += 80
        press = QtWidgets.QLabel(frame1)
        press.setObjectName("press")
        press.setStyleSheet("#press { background-color: transparent; color: " +
                            Config.textcolor + "; font-size: " +
                            str(int(25 * xscale)) + "px; " +
                            Config.fontattr + "}")
        press.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        press.setGeometry(3 * xscale, ypos * yscale, 300 * xscale, 100)

        ypos += 30
        humidity = QtWidgets.QLabel(frame1)
        humidity.setObjectName("humidity")
        humidity.setStyleSheet(
            "#humidity { background-color: transparent; color: " +
            Config.textcolor + "; font-size: " +
            str(int(25 * xscale)) + "px; " +
            Config.fontattr + "}")
        humidity.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        humidity.setGeometry(3 * xscale, ypos * yscale, 300 * xscale, 100)

        ypos += 30
        wind = QtWidgets.QLabel(frame1)
        wind.setObjectName("wind")
        wind.setStyleSheet("#wind { background-color: transparent; color: " +
                           Config.textcolor + "; font-size: " +
                           str(int(20 * xscale)) + "px; " +
                           Config.fontattr + "}")
        wind.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        wind.setGeometry(3 * xscale, ypos * yscale, 300 * xscale, 100)

        ypos += 20
        wind2 = QtWidgets.QLabel(frame1)
        wind2.setObjectName("wind2")
        wind2.setStyleSheet("#wind2 { background-color: transparent; color: " +
                            Config.textcolor + "; font-size: " +
                            str(int(20 * xscale)) + "px; " +
                            Config.fontattr + "}")
        wind2.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        wind2.setGeometry(3 * xscale, ypos * yscale, 300 * xscale, 100)

        ypos += 20
        wdate = QtWidgets.QLabel(frame1)
        wdate.setObjectName("wdate")
        wdate.setStyleSheet("#wdate { background-color: transparent; color: " +
                            Config.textcolor + "; font-size: " +
                            str(int(15 * xscale)) + "px; " +
                            Config.fontattr + "}")
        wdate.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        wdate.setGeometry(3 * xscale, ypos * yscale, 300 * xscale, 100)

        bottom = QtWidgets.QLabel(frame1)
        bottom.setObjectName("bottom")
        bottom.setStyleSheet("#bottom { font-family:sans-serif; color: " +
                             Config.textcolor +
                             "; background-color: transparent; font-size: " +
                             str(int(30 * xscale)) +
                             "px; " +
                             Config.fontattr +
                             "}")
        bottom.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        bottom.setGeometry(0, height - 50, width, 50)

        temp = QtWidgets.QLabel(frame1)
        temp.setObjectName("temp")
        temp.setStyleSheet("#temp { font-family:sans-serif; color: " +
                           Config.textcolor +
                           "; background-color: transparent; font-size: " +
                           str(int(30 * xscale)) +
                           "px; " +
                           Config.fontattr +
                           "}")
        temp.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        temp.setGeometry(0, height - 100, width, 50)

        forecast = []
        for i in range(0, 9):
            lab = QtWidgets.QLabel(frame1)
            lab.setObjectName("forecast" + str(i))
            lab.setStyleSheet(
                "QWidget { background-color: transparent; color: " +
                Config.textcolor + "; font-size: " +
                str(int(20 * xscale)) + "px; " +
                Config.fontattr + "}")
            lab.setGeometry(1137 * xscale, i * 100 * yscale,
                            300 * xscale, 100 * yscale)

            icon = QtWidgets.QLabel(lab)
            icon.setStyleSheet("#icon { background-color: transparent; }")
            icon.setGeometry(0, 0, 100 * xscale, 100 * yscale)
            icon.setObjectName("icon")

            wx = QtWidgets.QLabel(lab)
            wx.setStyleSheet("#wx { background-color: transparent; }")
            wx.setGeometry(100 * xscale, 10 * yscale,
                           200 * xscale, 20 * yscale)
            wx.setObjectName("wx")

            wx2 = QtWidgets.QLabel(lab)
            wx2.setStyleSheet("#wx2 { background-color: transparent; }")
            wx2.setGeometry(100 * xscale, 30 * yscale,
                            200 * xscale, 100 * yscale)
            wx2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            wx2.setWordWrap(True)
            wx2.setObjectName("wx2")

            day = QtWidgets.QLabel(lab)
            day.setStyleSheet("#day { background-color: transparent; }")
            day.setGeometry(100 * xscale, 75 * yscale,
                            200 * xscale, 25 * yscale)
            day.setAlignment(Qt.AlignRight | Qt.AlignBottom)
            day.setObjectName("day")

            forecast.append(lab)

        manager = QtNetwork.QNetworkAccessManager()

        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.NoProxy)
        QNetworkProxy.setApplicationProxy(proxy)

        # proxy = QNetworkProxy()
        # proxy.setType(QNetworkProxy.HttpProxy)
        # proxy.setHostName("localhost")
        # proxy.setPort(8888)
        # QNetworkProxy.setApplicationProxy(proxy)

        stimer = QTimer()
        stimer.singleShot(10, qtstart)

        # logging.info(radarurl(Config.radar1,radar1rect))

        w.show()
        #w.windowHandle().setScreen(app.screens()[2])
        w.showFullScreen()

        sys.exit(app.exec_())
    except SystemExit:
        pass
    except Exception as e:
        logging.exception("Unhandled Exception:")
        QtWidgets.QMessageBox.critical(
            None, "Unhandled Error, details in log file",
            str(e), QtWidgets.QMessageBox.Ok)
