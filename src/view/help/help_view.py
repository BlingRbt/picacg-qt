import base64
import json
import pickle
import time
from datetime import datetime, timedelta
from functools import partial

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, Qt
from PySide6.QtWidgets import QWidget, QMessageBox

from config import config
from config.setting import Setting
from interface.ui_help import Ui_Help
from qt_owner import QtOwner
from server import req
from server.sql_server import SqlServer, DbBook
from task.qt_task import QtTaskBase
from tools.log import Log
from tools.str import Str
from tools.tool import ToolUtil
from view.help.help_log_widget import HelpLogWidget


class HelpView(QWidget, Ui_Help, QtTaskBase):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        Ui_Help.__init__(self)
        QtTaskBase.__init__(self)
        self.setupUi(self)
        self.dbUpdateUrl = [config.DatabaseUpdate2, config.DatabaseUpdate3, config.DatabaseUpdate]
        self.dbUpdateDbUrl = [config.DatabaseDownload2, config.DatabaseDownload3, config.DatabaseDownload]
        self.curIndex = 0
        self.curSubVersion = 0
        self.curUpdateTick = 0
        self.pushButton.clicked.connect(self.OpenUrl)
        self.version.setText(config.UpdateVersion)
        self.isCheckUp = False
        self.logButton.clicked.connect(self.OpenLogDir)

        self.isHaveDb = False
        self.dbCheck.clicked.connect(self.ReUpdateDatabase)
        self.verCheck.clicked.connect(self.InitUpdate)

        self.updateUrl = [config.UpdateUrl, config.UpdateUrl2, config.UpdateUrl3]
        self.updateBackUrl = [config.UpdateUrlBack, config.UpdateUrl2Back, config.UpdateUrl3Back]
        self.checkUpdateIndex = 0
        self.helpLogWidget = HelpLogWidget()
        if Setting.IsShowCmd.value:
            self.helpLogWidget.show()
        else:
            self.helpLogWidget.hide()
        self.openCmd.clicked.connect(self.helpLogWidget.show)
        self.updateWidget.setVisible(False)
        self.selectUrl = ""
        self.updateButton.clicked.connect(self.OpenUpdateUrl)

    def retranslateUi(self, Help):
        Ui_Help.retranslateUi(self, Help)
        self.version.setText(config.RealVersion)
        self.upTimeLabel.setText(config.TimeVersion)
        self.waifu2x.setText(config.Waifu2xVersion)

    def Init(self):
        self.CheckDb()
        # self.UpdateDbInfo()

    def InitUpdate(self):
        self.checkUpdateIndex = 0
        self.UpdateText(self.verCheck, Str.CheckUp, "#7fb80e", False)
        self.StartUpdate()

    def StartUpdate(self):
        if self.checkUpdateIndex > len(self.updateUrl) -1:
            self.UpdateText(self.verCheck, Str.AlreadyUpdate, "#ff4081", True)
            return
        self.AddHttpTask(req.CheckUpdateReq(self.updateUrl[self.checkUpdateIndex]), self.InitUpdateBack)

    def InitUpdateBack(self, raw):
        try:
            data = raw.get("data")
            if not data:
                self.checkUpdateIndex += 1
                self.StartUpdate()
                return
            if data == "no":
                self.UpdateText(self.verCheck, Str.AlreadyUpdate, "#ff4081", True)
                return
            self.SetNewUpdate(self.updateBackUrl[self.checkUpdateIndex], Str.GetStr(Str.CurVersion) + config.UpdateVersion + ", "+ Str.GetStr(Str.CheckUpdateAndUp) + "\n" + data)
            self.UpdateText(self.verCheck, Str.HaveUpdate, "#d71345", True)
        except Exception as es:
            Log.Error(es)

    def CheckDb(self):
        self.AddSqlTask("book", "", SqlServer.TaskCheck, self.CheckDbBack)

    def CheckDbBack(self, data):
        if not data:
            Log.Error("Not found book.db !!!!!!!!!!!!!!!")
            from qt_owner import QtOwner
            QtOwner().SetDbError()
            QtOwner().ShowErrOne("无法加载本地数据库data/book.db")
            return
        self.isHaveDb = True
        self.UpdateDbInfo()
        return

    def SwitchCurrent(self, **kwargs):
        self.UpdateDbInfo()
        return

    def UpdateDbInfo(self):
        if not self.isHaveDb:
            return
        self.AddSqlTask("book", "", SqlServer.TaskTypeSelectUpdate, self.UpdateDbInfoBack)

    def UpdateDbInfoBack(self, data):
        num, timeStr, version = data
        self.curSubVersion = version
        self.curUpdateTick = ToolUtil.GetTimeTickEx(timeStr)

        # curEndTime = datetime.now() - timedelta(7)
        # newTick = int(curEndTime.timestamp())
        # self.curUpdateTick = newTick

        self.localNum.setText(str(num))
        self.localTime.setText(timeStr)
        QtOwner().searchView.UpdateTime(timeStr)
        if not self.isCheckUp:
            self.isCheckUp = True
            self.ReUpdateDatabase()
        return

    def ReUpdateDatabase(self):
        self.curIndex = 0
        self.InitUpdateDatabase()

    def InitUpdateDatabase(self):
        if QtOwner().isOfflineModel:
            return

        if self.curUpdateTick <= 0:
            return
        if self.curIndex >= len(self.dbUpdateUrl):
            return

        self.UpdateText(self.dbCheck, Str.CheckUp, "#7fb80e", False)
        self.dbCheck.setEnabled(False)
        url = self.dbUpdateUrl[self.curIndex]
        self.AddHttpTask(req.CheckUpdateDatabaseReq(url), self.InitUpdateDatabaseBack)

    def InitUpdateDatabaseBack(self, raw):
        try:
            data = raw["data"]
            updateTick = int(data)
            self.CheckLoadNextDayData(updateTick)

        except Exception as es:
            Log.Error(es)
            self.curIndex += 1
            self.InitUpdateDatabase()

            self.UpdateText(self.dbCheck, Str.NetError, "#d71345", True)

    def UpdateText(self, label, text, color, enable):
        label.setStyleSheet("background-color:transparent;color:{}".format(color))
        label.setText("{}".format(Str.GetStr(text)))
        label.setEnabled(enable)
        if enable:
            label.setCursor(Qt.PointingHandCursor)
        else:
            label.setCursor(Qt.ArrowCursor)
        return

    def CheckLoadNextDayData(self, newTick):
        if newTick <= self.curUpdateTick:
            if self.curSubVersion > 0:
                self.UpdateText(self.dbCheck, Str.DailyUpdated, "#7fb80e", True)
            else:
                self.UpdateText(self.dbCheck, Str.Updated, "#7fb80e", True)
            return
        day = ToolUtil.DiffDays(newTick, self.curUpdateTick)
        url = self.dbUpdateDbUrl[self.curIndex]

        curTime = datetime.fromtimestamp(self.curUpdateTick)
        curFirstTime = curTime - timedelta(curTime.weekday())

        nowTime = datetime.now()
        nowFirstTIme = nowTime - timedelta(nowTime.weekday())

        ## 判断是否同一周
        if curFirstTime.date() == nowFirstTIme.date():
            if day <= 0:
                self.AddHttpTask(req.DownloadDatabaseReq(url, newTick), self.DownloadDataBack, backParam=(newTick, newTick))
            else:
                self.curSubVersion = 0
                self.AddHttpTask(req.DownloadDatabaseReq(url, self.curUpdateTick), self.DownloadDataBack, backParam=(ToolUtil.GetCurZeroDatatime(self.curUpdateTick + 24*3600), newTick))
            return
        else:
            curEndTime = curTime + timedelta(7 - curTime.weekday())
            curEndTime = datetime(curEndTime.year, curEndTime.month, curEndTime.day)
            weekTick = int(curEndTime.timestamp())
            self.AddHttpTask(req.DownloadDatabaseWeekReq(url, self.curUpdateTick), self.DownloadWeekDataBack, backParam=(weekTick, newTick))

    def DownloadDataBack(self, raw, v):
        updateTick, newTick = v
        try:
            data = raw["data"]
            if not data:
                return
            Log.Info("db: check update, {}->{}->{}".format(time.strftime('%Y-%m-%d', time.localtime(self.curUpdateTick)), time.strftime('%Y-%m-%d', time.localtime(updateTick)), time.strftime('%Y-%m-%d', time.localtime(newTick))))
            if len(data) <= 200:
                Log.Info("Update code: {}".format(data))
                return
            elif data:
                if ToolUtil.DiffDays(updateTick, self.curUpdateTick) <= 0:
                    # 分割数据
                    dataList = data.split("\r\n")
                    dataList = list(filter(lambda data: data != "", dataList))
                    rawList = dataList[self.curSubVersion:]
                    self.curSubVersion = len(dataList)
                else:
                    # 全部更新
                    rawList = data.split("\r\n")
                addData = self.ParseBookInfo(rawList)
                self.AddSqlTask("book", (addData, updateTick, self.curSubVersion), SqlServer.TaskTypeUpdateBook)
        except Exception as es:
            Log.Error(es)
        finally:
            self.curUpdateTick = updateTick
            self.CheckLoadNextDayData(newTick)

    def DownloadWeekDataBack(self, raw, v):
        updateTick, newTick = v
        try:
            data = raw["data"]
            if not data:
                return
            Log.Info("db: check week update, {}->{}->{}".format(time.strftime('%Y-%m-%d', time.localtime(self.curUpdateTick)), time.strftime('%Y-%m-%d', time.localtime(updateTick)), time.strftime('%Y-%m-%d', time.localtime(newTick))))
            if len(data) <= 200:
                Log.Info("Update code: {}".format(data))
                return
            elif data:
                rawList = data.split("\r\n")
                addData = self.ParseBookInfo(rawList)
                self.AddSqlTask("book", (addData, updateTick, self.curSubVersion), SqlServer.TaskTypeUpdateBook)
        except Exception as es:
            Log.Error(es)
        finally:
            self.curUpdateTick = updateTick
            self.CheckLoadNextDayData(newTick)

    def ParseBookInfo(self, rawList):
        infos = []
        try:
            for raw in rawList:
                if not raw:
                    continue
                data = base64.b64decode(raw.encode('utf-8'))
                # book = pickle.loads(data)
                book = DbBook()
                book.CopyFromJson(json.loads(data))
                infos.append(book)
        except Exception as es:
            Log.Error(es)
        finally:
            return infos

    def OpenUrl(self):
        QDesktopServices.openUrl(QUrl(config.Issues))

    def OpenLogDir(self):
        path = Setting.GetLogPath()
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        return

    def SetNewUpdate(self, updateUrl, updateLog):
        self.updateWidget.setVisible(True)
        self.selectUrl = updateUrl
        self.updateLabel.setText(updateLog)
        QtOwner().owner.navigationWidget.SetNewUpdate()
        return

    def OpenUpdateUrl(self):
        QDesktopServices.openUrl(QUrl(self.selectUrl))
        return