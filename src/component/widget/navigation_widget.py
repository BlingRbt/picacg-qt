from PySide6.QtCore import QPropertyAnimation, QRect, QEasingCurve, QFile, QEvent, QSize
from PySide6.QtGui import QPixmap, Qt, QIcon
from PySide6.QtWidgets import QWidget, QScroller

from config import config
from config.setting import Setting
from interface.ui_navigation import Ui_Navigation
from qt_owner import QtOwner
from server import req
from task.qt_task import QtTaskBase
from tools.status import Status
from tools.str import Str
from tools.tool import ToolUtil
from tools.user import User
from view.user.login_view import LoginView


class NavigationWidget(QWidget, Ui_Navigation, QtTaskBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        QtTaskBase.__init__(self)
        self.setupUi(self)
        self.resize(260, 800)
        self.__ani = QPropertyAnimation(self, b"geometry")
        self.__connect = None
        self.pictureData = ""
        f = QFile(u":/png/icon/placeholder_avatar.png")
        f.open(QFile.ReadOnly)
        self.picLabel.SetPicture(f.readAll())
        f.close()
        # if Setting.IsGrabGesture.value:
        #     QScroller.grabGesture(self.scrollArea, QScroller.LeftMouseButtonGesture)
        self.loginButton.clicked.connect(self.OpenLoginView)
        self.signButton.clicked.connect(self.Sign)
        self.picLabel.installEventFilter(self)
        self.picData = None
        self.offlineButton.SetState(False)
        self.offlineButton.Switch.connect(self.SwitchOffline)

    def SwitchOffline(self, state):
        QtOwner().isOfflineModel = state
        return

    def OpenLoginView(self):
        isAutoLogin = Setting.AutoLogin.value
        if User().isLogin:
            self.Logout()
            isAutoLogin = 0

        loginView = LoginView(QtOwner().owner, isAutoLogin)
        loginView.show()
        loginView.closed.connect(self.LoginSucBack)
        return

    def Logout(self):
        User().Logout()
        return

    def LoginSucBack(self):
        self.UpdateProxyName()
        if not User().isLogin:
            self.loginButton.setText(Str.GetStr(Str.Login))
            QtOwner().owner.favorityView.InitFavorite()
            return
        QtOwner().owner.LoginSucBack()
        self.loginButton.setText(Str.GetStr(Str.LoginOut))
        self.AddHttpTask(req.GetUserInfo(), self.UpdateUserBack)

    def UpdateProxyName(self):
        if Setting.ProxySelectIndex.value == 4:
            self.proxyName.setText("CDN_{}".format(Setting.PreferCDNIP.value))
        elif Setting.ProxySelectIndex.value == 5:
            self.proxyName.setText("JP反代分流")
        else:
            self.proxyName.setText("分流{}".format(str(Setting.ProxySelectIndex.value)))

    def UpdateUserBack(self, raw):
        self.levelLabel.setText("LV" + str(User().level))
        self.expLabel.setText("Exp: " + str(User().exp))
        self.titleLabel.setText(str(User().title))
        self.nameLabel.setText(str(User().name))
        if User().isPunched:
            self.signButton.setText(Str.GetStr(Str.AlreadySign))
            self.signButton.setVisible(False)
        if not User().avatar:
            return
        url = User().avatar.get("fileServer")
        path = User().avatar.get("path")
        if url and path and config.IsLoadingPicture:
            url = ToolUtil.GetRealUrl(url, path)
            path = ToolUtil.GetMd5RealPath(url, "user")
            self.AddDownloadTask(url, path, completeCallBack=self.ShowUserImg)

    def ShowUserImg(self, data, st):
        if st == Status.Ok:
            self.picData = data
            self.SetPicture(data)
        return

    def Sign(self):
        QtOwner().ShowLoading()
        self.AddHttpTask(req.PunchIn(), self.SignBack)

        return

    def SignBack(self, raw):
        QtOwner().CloseLoading()
        st = raw["st"]
        if st == Status.Ok:
            self.signButton.setVisible(False)
            self.signButton.setText(Str.GetStr(Str.AlreadySign))
            # self.signButton.setHidden(True)
            self.AddHttpTask(req.GetUserInfo(), self.UpdateUserBack)
        return

    def SetPicture(self, data):
        self.pictureData = data
        self.picLabel.SetPicture(data)
        return

    def UpdatePictureData(self, data):
        if not data:
            return
        self.picLabel.setPixmap(QPixmap())
        self.picLabel.setText(Str.GetStr(Str.HeadUpload))
        self.AddHttpTask(req.SetAvatarInfoReq(data), self.UpdatePictureDataBack)
        return

    def UpdatePictureDataBack(self, data):
        st = data["st"]
        if st == Status.Ok:
            self.AddHttpTask(req.GetUserInfo(), self.UpdateUserBack)
        else:
            QtOwner().ShowError(Str.GetStr(st))

    def aniShow(self):
        """ 动画显示 """
        super().show()
        self.activateWindow()
        self.__ani.setStartValue(QRect(self.x(), self.y(), 30, self.height()))
        self.__ani.setEndValue(QRect(self.x(), self.y(), 260, self.height()))
        self.__ani.setEasingCurve(QEasingCurve.InOutQuad)
        self.__ani.setDuration(85)
        self.__ani.start()

    def aniHide(self):
        """ 动画隐藏 """
        self.__ani.setStartValue(QRect(self.x(), self.y(), 260, self.height()))
        self.__ani.setEndValue(QRect(self.x(), self.y(), 30, self.height()))
        self.__connect = self.__ani.finished.connect(self.__hideAniFinishedSlot)
        self.__ani.setDuration(85)
        self.__ani.start()

    def __hideAniFinishedSlot(self):
        """ 隐藏窗体的动画结束 """
        super().hide()
        self.resize(60, self.height())
        if self.__connect:
            self.__ani.finished.disconnect()
            self.__connect = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                if self.picData and (obj == self.picLabel):
                    QtOwner().OpenWaifu2xTool(self.picData)
                    return True
                return False
            else:
                return False
        else:
            return super(self.__class__, self).eventFilter(obj, event)

    def SetNewUpdate(self):
        icon2 = QIcon()
        icon2.addFile(u":/png/icon/new.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.helpButton.setIcon(icon2)
        return