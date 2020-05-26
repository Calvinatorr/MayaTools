__author__  = 'Calvin Simpson'
__company__ = 'The Multiplayer Guys'


###########################################################################################################################################################################


import maya.cmds as cmds
import pymel.all as pm
import maya.mel as mel
import maya.OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import json, os, sys

# Import Qt libraries
try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from shiboken2 import wrapInstance
except ImportError:
    try:
        from PySide.QtCore import *
        from PySide.QtGui import *
        from PySide.QtWidgets import *
        from shiboken import wrapInstance
        assert("Failed to import PySide2, falling back to PySide")
    except ImportError:
        assert("Failed to import PySide & PySide2")


###########################################################################################################################################################################


def MayaMainWindow():
    """get maya main window as pyside object"""
    try:
        mayaWindowPtn = omui.MQtUtil.mainWindow()
        return wrapInstance(long(mayaWindowPtn), QWidget)
    except:
        return None



fileInfo = cmds.fileInfo(query=True)
data = {}
try:
    data = fileInfo["AnimationExporterData"]
except:
    pass


###########################################################################################################################################################################


class ToolButton(QPushButton):
    """ Icon-only """

    _size = 25

    def __init__(self, icon=QIcon(), tooltip=""):
        super(ToolButton, self).__init__()
        self.setIcon(icon)
        self.setIconSize(QSize(self._size, self._size))
        self.setToolTip(tooltip)
        self.setFixedSize(self._size, self._size)


############################################################################### EXPORT NODES #############################################################################


class ExportNodesTree(QTreeWidget):
    """ Widget to contain interface with skeleton data """

    def __init__(self):
        super(ExportNodesTree, self).__init__()

        # Headers
        _headers = ["Node", "Long Name"]
        self.setColumnCount(len(_headers))
        self.setHeaderLabels(_headers)
        #self.setHeaderHidden(True)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.hideColumn(1)

        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.OpenContextMenu)

        # Selection mode
        self.setSelectionMode(QAbstractItemView.MultiSelection)

        # Sort mode
        self.setSortingEnabled(True)


    def OpenContextMenu(self, position):
        self.cursorPosition = position
        self.menu = QMenu(self)
        self.menu = QMenu()
        itemIndices = self.selectedIndexes()

        action = QAction("Add Selected Nodes", self)
        action.triggered.connect(self.AddSelectedObjects)
        self.menu.addAction(action)
        action = QAction("Remove", self)
        action.triggered.connect(self.Remove)
        self.menu.addAction(action)
        action = QAction("Toggle Long Names", self)
        action.triggered.connect(lambda : self.setColumnHidden(1, not self.isColumnHidden(1)))
        self.menu.addAction(action)
        # Add other actions
        self.menu.popup(self.viewport().mapToGlobal(self.cursorPosition))


    def AddSelectedObjects(self):
        selection = pm.ls(selection=True)
        for s in selection:
            self.AddNode(s)


    def AddNodeFromLongName(self, longName=""):
        assert(len(longName) > 0)

        # Check unique, return if not
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            itemLongName = item.text(1)
            if longName == itemLongName:
                return

        pyNode = pm.PyNode(longName)
        nodeName = longName.rsplit("|", 1)[-1]

        # Return node type
        try:
            shape = pm.listRelatives(pyNode, children=True, s=True)[0]
            nodeType = pm.nodeType(shape, q=True)
        except:
            nodeType = pm.nodeType(pyNode, q=True)

        # Construct item widget
        item = QTreeWidgetItem()
        item.setText(0, nodeName)
        item.setText(1, longName)

        # Set icon
        icon = QIcon()
        if nodeType == u'mesh':
            icon = QIcon(":/mesh.svg")
        elif nodeType == u'transform':
            icon = QIcon(":/transform.svg")
        elif nodeType == u'joint':
            icon = QIcon(":/kinJoint.png")
        elif nodeType == u'locator':
            icon = QIcon(":/locator.svg")
        item.setIcon(0, icon)

        self.addTopLevelItem(item)


    def AddNode(self, object=None):
        assert(object != None)
        self.AddNodeFromLongName(object.longName())


    def AddNodesFromData(self, data):
        for longName in data:
            self.AddNodeFromLongName(longName)


    def Remove(self):
        for item in self.selectedItems():
            (item.parent() or self.invisibleRootItem()).removeChild(item)


    def GetData(self):
        data = []
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data.append(item.text(1))
        return data


###########################################################################################################################################################################


class AnimationClipsTable(QTableWidget):
    """ Table of the objects. Filled in with the selection by default. """

    def __init__(self):
        super(AnimationClipsTable, self).__init__()

        # Set-up headers
        self._headers = ["", "Animation Name", "Start", "End"]
        self.setColumnCount(len(self._headers))
        self.setHorizontalHeaderLabels(self._headers)

        #self.setColumnHidden(1, True)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 25)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.setColumnWidth(2, 50)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(3, 50)
        #self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(25)

        self.setStyleSheet("""*:indicator {
                                        width: 18px;
                                        height: 18 px;

                                    }
                                    :indicator:checked {
                                            border-radius: 9px;
                                            margin: 0px 0px 2px 2px;
                                            border: 1px solid rgb(0, 100, 0);
                                            background: qradialgradient(cx:0.6, cy:0.6, radius:1,
                                                        fx:0.6, fy:0.4, stop:0 rgb(100, 255, 100), stop:1 rgb(20, 130, 20 ))
                                    }
                                    :indicator:unchecked {
                                            border-radius: 9px;
                                            margin: 0px 0px 2px 2px;
                                            border: 1px solid rgb(100, 0, 0);
                                            background: qradialgradient(cx:0.6, cy:0.6, radius:1,
                                                        fx:0.6, fy:0.4, stop:0 rgb(255, 100, 100), stop:1 rgb(130, 20, 20))
                                    }""")

        #self.FillTableWithSelected()

        self.setEditTriggers(QTreeWidget.NoEditTriggers)
        #self.setSelectionMode(QTreeWidget.ExtendedSelection)

        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.OpenContextMenu)

    def OpenContextMenu(self, position):
        self.cursorPosition = position
        self.menu = QMenu(self)
        self.menu = QMenu()
        itemIndices = self.selectedIndexes()

        # Actions
        action = QAction("Add New Clip", self)
        action.triggered.connect(self.AddClip)
        self.menu.addAction(action)
        action = QAction("Remove Clip", self)
        action.triggered.connect(self.RemoveClip)
        self.menu.addAction(action)

        # Add other actions
        self.menu.popup(self.viewport().mapToGlobal(self.cursorPosition))


    def GetData(self):
        """ Gather clip data """
        clipData = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            data = {
                "enabled": self.cellWidget(row, 0).isChecked(),
                "animationName": self.cellWidget(row, 1).text(),
                "frameStart": self.cellWidget(row, 2).value(),
                "frameEnd": self.cellWidget(row, 3).value()
            }
            clipData.append(data)
        return clipData


    def AddClip(self):
        """ Add new animation to table """
        # Add row
        rowPosition = self.rowCount()
        self.insertRow(rowPosition)

        # Enabled
        enabledCheck = QCheckBox()
        enabledCheck.setFixedSize(24, 24)
        enabledCheck.setChecked(True)
        enabledCheck.setGeometry(10, 10, 24, 24)
        self.setCellWidget(rowPosition, 0, enabledCheck)

        # Animation name
        name = QLineEdit()
        name.setText("Anim0")
        self.setCellWidget(rowPosition, 1, name)

        # Frame start/end
        def CreateFrameBox():
            spinBox = QSpinBox()
            spinBox.setRange(-9999, 9999)
            return spinBox
        start = CreateFrameBox()
        start.setValue(int(pm.playbackOptions(q=True, min=True)))
        end = CreateFrameBox()
        end.setValue(int(pm.playbackOptions(q=True, max=True)))
        self.setCellWidget(rowPosition, 2, start)
        self.setCellWidget(rowPosition, 3, end)

        # Return row position so we can read data from this row
        return rowPosition


    def AddClipsFromData(self, data):
        # Load in clips from file string
        for clipData in data:
            rowPosition = self.AddClip()
            self.cellWidget(rowPosition, 0).setChecked(clipData["enabled"])
            self.cellWidget(rowPosition, 1).setText(clipData["animationName"])
            self.cellWidget(rowPosition, 2).setValue(clipData["frameStart"])
            self.cellWidget(rowPosition, 3).setValue(clipData["frameEnd"])


    def RemoveClip(self):
        row = self.currentRow()
        if row != None:
            self.removeRow(row)


class AnimationTab(QDialog):
    """ Animation tab - encapsulates metadata, clips, and settings """

    def __init__(self, tabWidget=None):
        super(AnimationTab, self).__init__()

        self.tabWidget = tabWidget
        self.tabIndex = self.tabWidget.count()

        # Layout
        vbox = QVBoxLayout()
        vbox.setAlignment(Qt.AlignTop)
        self.setLayout(vbox)
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

        # Skeleton name
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(QLabel("Name"))
        self.name = QLineEdit("NewSkeletalMesh", toolTip="Skeleton/Rig Name")
        self.name.setFixedHeight(25)
        self.name.textEdited.connect(self.UpdateParentTabWidget)
        hbox.addWidget(self.name)

        # Directory
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(QLabel("Directory"))
        self.exportDirectory = QLineEdit(os.path.dirname(cmds.file(q=True, sn=True)))
        self.exportDirectory.setFixedHeight(25)
        self.exportDirectory.setReadOnly(True)
        hbox.addWidget(self.exportDirectory)
        self.directoryExplorer = QToolButton(toolTip="Find directory")
        self.directoryExplorer.setIcon(QIcon(":/openLoadGeneric.png"))
        self.directoryExplorer.setFixedSize(QSize(25, 25))
        self.directoryExplorer.setIconSize(self.directoryExplorer.size())
        self.directoryExplorer.clicked.connect(self.OpenDirectoryExplorer)
        hbox.addWidget(self.directoryExplorer)

        # FBX settings
        self.bakeAnimation = QCheckBox("Bake Animation", checked=True)
        vbox.addWidget(self.bakeAnimation)

        # Vertical splitter
        splitter = QSplitter(self)
        splitter.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        vbox.addWidget(splitter)

        # Widgets
        self.animationClips = AnimationClipsTable()
        splitter.addWidget(self.animationClips)
        self.exportNodes = ExportNodesTree()
        splitter.addWidget(self.exportNodes)

        splitter.setSizes([300, 25])

        # Buttons layout
        hbox = QHBoxLayout(alignment=Qt.AlignLeft)
        vbox.addLayout(hbox)

        # Export data button
        self.exportDataButton = QPushButton(text="Export Clips", toolTip="Export all clips rom the current tab", icon=QIcon(":/saveToShelf.png"), iconSize=QSize(25, 25))
        self.exportDataButton.setFixedWidth(150)
        self.exportDataButton.clicked.connect(self.ExportClips)
        hbox.addWidget(self.exportDataButton)

        # Export bind
        self.exportBindButton = QPushButton(text="Export Bind", toolTip="Export bind pose from the current tab", icon=QIcon(":/out_character.png"), iconSize=QSize(25, 25))
        self.exportBindButton.setFixedWidth(150)
        self.exportBindButton.clicked.connect(self.ExportBind)
        hbox.addWidget(self.exportBindButton)


    def GetData(self):
        # Gather clip data
        clipData = self.animationClips.GetData()

        # Load in existing file info
        tabData = {
            "name": self.name.text(),
            "exportDirectory": self.exportDirectory.text(),
            "bakeAnimation": self.bakeAnimation.isChecked(),
            "exportNodes": self.exportNodes.GetData(),
            "clips": clipData
        }
        return tabData


    def LoadFromData(self, data):
        self.name.setText(data["name"])
        self.exportDirectory.setText(data["exportDirectory"])
        self.bakeAnimation.setChecked(data["bakeAnimation"])
        self.animationClips.AddClipsFromData(data["clips"])
        self.exportNodes.AddNodesFromData(data["exportNodes"])


    def UpdateParentTabWidget(self):
        assert(self.tabWidget != None or self.tabIndex >= 0)
        self.tabWidget.setTabText(self.tabIndex, self.name.text())


    def OpenDirectoryExplorer(self):
        filename = QFileDialog.getExistingDirectory(self, "Export Directory", self.exportDirectory.text())
        if len(filename) > 0:
            self.exportDirectory.setText(filename)


    def ExportClips(self):
        assert (self.animationClips.rowCount() != 0 or self.exportNodes.invisibleRootItem().childCount() != 0), "No clips to export"
        print("Exporting clips from '{}'..".format(self.name.text()))

        selection = cmds.ls(sl=True) # Cache selection
        pm.select(clear=True) # Clear it
        minTime = cmds.playbackOptions(minTime=True, query=True)
        maxTime = cmds.playbackOptions(maxTime=True, query=True)

        # Select nodes to export
        root = self.exportNodes.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            longname = item.text(1)
            pyNode = pm.PyNode(longname)
            if pyNode.nodeType != u'mesh': # Ignore mesh types
                cmds.select(longname, add=True)

        # Set base FBX settings
        pm.mel.FBXExportTangents(v=False)
        pm.mel.FBXExportInstances(v=False)
        pm.mel.FBXExportInAscii(v=False)
        pm.mel.FBXExportSmoothMesh(v=True)
        pm.mel.FBXExportShapes(v=False)
        pm.mel.FBXExportSkins(v=True)
        pm.mel.FBXExportAnimationOnly(v=False)
        pm.mel.FBXExportInputConnections(v=False)

        # Export each clip
        directory = self.exportDirectory.text()
        for row in range(self.animationClips.rowCount()):
            # If disabled clip, ignore and continue to next clip
            if not self.animationClips.cellWidget(row, 0).isChecked():
                continue

            # Get filename
            name = self.name.text()
            animationName = self.animationClips.cellWidget(row, 1).text()
            filename = os.path.join(directory, "{0}_{1}_ANIM.fbx".format(name, animationName))

            # Set frame range
            frameStart = self.animationClips.cellWidget(row, 2).value()
            frameEnd = self.animationClips.cellWidget(row, 3).value()
            cmds.playbackOptions(minTime=frameStart, maxTime=frameEnd)

            # Set FBX options
            pm.mel.FBXExportBakeComplexStart(v=frameStart)
            pm.mel.FBXExportBakeComplexEnd(v=frameEnd)
            pm.mel.FBXExportBakeComplexAnimation(v=self.bakeAnimation.isChecked())

            # Export
            pm.mel.FBXExport(f=filename, s=True)

            # Success
            print("{}: Exported clip '{}' to '{}' from frame {} to {}".format(name, animationName, filename, frameStart, frameEnd))


        # Restore selection
        pm.select(selection)
        # Restore frame range
        cmds.playbackOptions(minTime=minTime, maxTime=maxTime)


    def ExportBind(self):
        print("Exporting bind from '{}'..".format(self.name.text()))

        selection = cmds.ls(sl=True) # Cache selection
        pm.select(clear=True) # Clear it

        # Select nodes to export
        root = self.exportNodes.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            longname = item.text(1)
            cmds.select(longname, add=True)

        # Set base FBX settings
        try:
            pm.mel.FBXExportSmoothingGroups(v=True)
        except:
            print("FBX export smoothing groups failed")
        try:
            pm.mel.FBXExportHardEdges(v=False)
        except:
            print("FBX export hard edges failed")
        pm.mel.FBXExportTangents(v=False)
        pm.mel.FBXExportInstances(v=False)
        pm.mel.FBXExportInAscii(v=False)
        pm.mel.FBXExportSmoothMesh(v=True)
        pm.mel.FBXExportShapes(v=False)
        pm.mel.FBXExportSkins(v=True)
        pm.mel.FBXExportAnimationOnly(v=False)
        pm.mel.FBXExportInputConnections(v=False)

        # Construct filename
        directory = self.exportDirectory.text()
        name = self.name.text()
        filename = os.path.join(directory, name + "_SK.fbx")

        # Export
        pm.mel.FBXExport(f=filename, s=True)

        # Restore selection
        pm.select(selection)

        # Success
        print("Exported bind from '{}' to '{}'".format(name, filename))




###########################################################################################################################################################################


class AnimationExporterWindow(QMainWindow):
#class AnimationExporterWindow(MayaQWidgetDockableMixin, QMainWindow):
    """ Main window class """

    _filename = ""

    def __CreateVBox__(self):
        vbox = QVBoxLayout()
        vbox.setAlignment(Qt.AlignTop)
        return vbox

    def __init__(self, parent=MayaMainWindow()):
        super(AnimationExporterWindow, self).__init__(parent)

        self.canSaveData = False

        # Window styling
        self.setWindowTitle("Animation Exporter")
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint) # Hide help
        self.setWindowIcon(QIcon(":/animPrefsWndIcon.png"))
        self.setGeometry(600, 300, 650, 350)
        stdIcon = self.style().standardIcon
        #self.show(dockable=True) # Show early
        self.show() # Show early

        self.uiSettingsIni = pm.Path('{}mainWindowStates/AnimationExporter.ini'.format(pm.internalVar(userPrefDir=True)))

        # Central widget
        self.setCentralWidget(QWidget())
        vbox = self.__CreateVBox__()
        self.centralWidget().setLayout(vbox)


        # Toolbar
        toolbar = QToolBar(self)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        toolbar.setIconSize(QSize(35, 35))


        # Add tab button
        def AddTab():
            self.animationTabWidget.addTab(AnimationTab(self.animationTabWidget), "New Tab")
            self.animationTabWidget.setCurrentIndex(self.animationTabWidget.count()-1)
        self.addTabButton = QToolButton(toolTip="Add Tab", icon=QIcon(":/addClip.png"))
        self.addTabButton.clicked.connect(AddTab)
        toolbar.addWidget(self.addTabButton)

        # Remove tab button
        def RemoveTab():
            if self.animationTabWidget.count() == 0:
                return
            widget = self.animationTabWidget.widget(self.animationTabWidget.currentIndex())
            message = QMessageBox.warning(self, "Delete Current Tab", "You are about to delete the current tab '{}'.\nThis is not undoable!\nAre you sure?".format(widget.name.text()), QMessageBox.Ok, QMessageBox.Cancel)
            if message == QMessageBox.Ok:
                widget.deleteLater()
        self.removeTabButton = QToolButton(toolTip="Remove Tab", icon=QIcon(":/delete.png"))
        self.removeTabButton.clicked.connect(RemoveTab)
        toolbar.addWidget(self.removeTabButton)

        # Save data button
        self.saveDataButton = QToolButton(toolTip="Save Data", icon=QIcon(":/save.png"))
        self.saveDataButton.clicked.connect(self.Save)
        toolbar.addWidget(self.saveDataButton)

        # Import data button
        self.importDataButton = QToolButton(toolTip="Import Data", icon=QIcon(":/loadPreset.png"))
        self.importDataButton.clicked.connect(self.ImportData)
        toolbar.addWidget(self.importDataButton)

        # Export data button
        self.exportDataButton = QToolButton(toolTip="Export Data", icon=QIcon(":/saveToShelf.png"))
        self.exportDataButton.clicked.connect(self.ExportData)
        toolbar.addWidget(self.exportDataButton)

        # Export all tab clips button
        self.exportAllTabs = QToolButton(toolTip="Export clips from all tabs", icon=QIcon(":/writeToVectorBuffer.svg"))
        self.exportAllTabs.clicked.connect(self.ExportAllTabs)
        toolbar.addWidget(self.exportAllTabs)

        # Export all tab clips button
        self.exportBindsAllTabs = QToolButton(toolTip="Export bind poses from all tabs", icon=QIcon(":/QR_QuickRigTool.png"))
        self.exportBindsAllTabs.clicked.connect(self.ExportBindsAllTabs)
        toolbar.addWidget(self.exportBindsAllTabs)


        # Animation tabs
        self.animationTabWidget = QTabWidget()
        vbox.addWidget(self.animationTabWidget)


        # Load clips & restore UI
        self.canSaveData = True # We do this in-case the UI fails, the user doesn't overwrite their animation data
        self.Load()
        self.RestoreUI()


    def RestoreUI(self):
        """ Restore window geo """
        if os.path.exists(self.uiSettingsIni):
            uiSettings = QSettings(self.uiSettingsIni, QSettings.IniFormat)
            try:
                self.restoreGeometry(uiSettings.value("windowGeometry"))
            except:
                pass
            try:
                self.resize(uiSettings.value("size"))
            except:
                pass
            try:
                pos = uiSettings.value("pos")
                self.move(pos[0], pos[1])
            except:
                pass


    def closeEvent(self, *args, **kwargs):
        """ Kill jobs, save geo, save clips """
        self.Save()

        # Create ini file if it doesn't exist
        if not os.path.exists(self.uiSettingsIni):
            file = open(self.uiSettingsIni, "w")
            file.close()

        # Save window settings
        uiSettings = QSettings(str(self.uiSettingsIni), QSettings.IniFormat)
        uiSettings.setValue("windowGeometry", self.saveGeometry())
        uiSettings.setValue("size", self.size())
        uiSettings.setValue("pos", self.pos())

        self.deleteLater()


    def _LoadExporterData(self):
        """ Load exporter data from the file info """
        data = {}
        try:
            fileInfo = cmds.fileInfo("AnimationExporterData", query=True)[0]
            fileInfo = fileInfo.replace(u"\\", u"")
            data = json.loads(fileInfo)
        except:
            pass
        return data


    def Save(self):
        assert self.canSaveData, "Cannot save data, UI failed to build"

        # Try to load existing data so we don't overwrite it, as we store all our data in a single encoded json string
        data = self._LoadExporterData()
        data["tabs"] = [] # Initialize/overwrite tabs, we don't care about the previous data here

        # For each tab
        for i in range(self.animationTabWidget.count()):
            item = self.animationTabWidget.widget(i)
            data["tabs"].append(item.GetData())

        # Dump an encoded json string into our file info
        cmds.fileInfo("AnimationExporterData", json.dumps(data))
        print("Saved data")


    def _LoadFromData(self, data=None):
        assert(data != None)

        for tabData in data["tabs"] or []:

            # Find existing tabs and overwrite them to avoid duplicates
            found = False
            for i in range(self.animationTabWidget.count()):
                item = self.animationTabWidget.widget(i)
                if item.name.text() == tabData["name"]:
                    found = True
                    break
            if found:
                continue

            # Else create new tab
            newTab = AnimationTab(self.animationTabWidget)
            self.animationTabWidget.addTab(newTab, tabData["name"])
            newTab.LoadFromData(tabData)

        print("Loaded data")


    def Load(self):
        self._LoadFromData(self._LoadExporterData())


    def ImportData(self):
        """ Import data from json file """
        # construct filename from mb file
        currentFile = cmds.file(q=True, sn=True)
        filename = os.path.basename(currentFile).rsplit(".", 1)[0]
        directory = os.path.dirname(cmds.file(q=True, sn=True))
        file = QFileDialog.getOpenFileName(self, "Import Animation Metadata",
                                           dir=(os.path.join(directory, "{}_Metadata.json".format(filename))),
                                           filter=("JSON (*.json)"))[0]

        # If file exists
        if len(file) > 0 and os.path.exists(file):
            # Read in from json file & decode stringbuffer
            data = []
            with open(file, "r") as inFile:
                data = json.load(inFile)

            self._LoadFromData(data)

            # Display success
            message = QMessageBox(text="Successfully imported animation metadata from disk", buttons=QMessageBox.Ok)
            message.exec_()



    def ExportData(self):
        """ Export data to json file """
        # construct filename from mb file
        currentFile = cmds.file(q=True, sn=True)
        filename = os.path.basename(currentFile).rsplit(".", 1)[0]
        directory = os.path.dirname(cmds.file(q=True, sn=True))
        file = QFileDialog.getSaveFileName(self, "Export Animation Metadata",
                                           dir=(os.path.join(directory, "{}_Metadata.json".format(filename))),
                                           filter=("JSON (*.json)"))[0]

        # If we have a valid file to export, then write to disk
        if len(file) > 0:
            self.Save()
            data = cmds.fileInfo("AnimationExporterData", query=True)[0]
            data = data.replace(u"\\", u"")
            data = json.loads(data)

            with open(file, "w") as outFile:
                json.dump(data, outFile, indent=4)

            # Display success
            print("Exported data")
            message = QMessageBox(text="Successfully exported animation metadata to disk", buttons=QMessageBox.Ok)
            message.exec_()


    def ExportCurrentTab(self):
        index = self.animationTabWidget.currentIndex()
        item = self.animationTabWidget.widget(index)
        item.ExportClips()


    def ExportAllTabs(self):
        # For each tab
        for i in range(self.animationTabWidget.count()):
            item = self.animationTabWidget.widget(i)
            item.ExportClips()


    def ExportBindsAllTabs(self):
        # For each tab
        for i in range(self.animationTabWidget.count()):
            item = self.animationTabWidget.widget(i)
            item.ExportBind()


    def ExportSkinWeights(self):
        """ Export skin weight data to json file """

        # Get objects from table
        selected = self.objectTable.GetObjects()

        # Warning & early-out
        if len(selected) < 1:
            print("No objects to export")
            ret = QMessageBox.warning(self, self.tr("Warning"),
                                      self.tr("No objects to export."),
                                      QMessageBox.Ok)
            return

        # Get directory to save to
        filename = QFileDialog.getSaveFileName(self, "Export Skin Weights Data", dir=self._filename, filter=("JSON (*.json)"))[0]
        # Validate directory
        if len(self._filename) < 1:
            print("File invalid")
            ret = QMessageBox.critical(self, self.tr("Warning"),
                                      self.tr("File invalid."),
                                      QMessageBox.Ok)
            return
        else:
            self._filename = filename

        # Init data
        data = []

        # For each selected object
        for s in selected:
            skin = mel.eval("findRelatedSkinCluster {}".format(s))

            numVertices = cmds.polyEvaluate(v=True)
            d = {"object": s, "numVertices": numVertices, "skinCluster": skin, "vertices": []}
            if skin:
                influences = cmds.skinCluster(skin, query=True, inf=True)
                for i in range(0, numVertices):
                    vtx = (s + ".vtx[{}]").format(i)

                    newData = []
                    joints = cmds.skinPercent(skin, vtx, query=True, transform=None) or []
                    weights = cmds.skinPercent(skin, vtx, query=True, v=True) or []
                    for idx, j in enumerate(joints):
                        newData.append( (j, weights[idx]) )
                    d["vertices"].append(newData)
            data.append(d)


        with open(self._filename, "w") as outFile:
            json.dump(data, outFile, indent=4)

        print("Exported skin weights to '{}'".format(file))
        message = QMessageBox()
        message.setText("Successfully exported skin weights")
        message.setStandardButtons(QMessageBox.Ok)
        message.exec_()


    def ImportSkinWeights(self):
        """ Import skin weight data from json file """

        # Get directory to save to
        filename = QFileDialog.getOpenFileName(self, "Import Skin Weights Data", dir=self._filename, filter=("JSON (*.json)"))[0]
        # Validate directory
        if len(self._filename) < 1:
            print("File invalid")
            ret = QMessageBox.critical(self, self.tr("Warning"),
                                       self.tr("File invalid."),
                                       QMessageBox.Ok)
            return
        else:
            self._filename = filename

        # Init data
        data = []
        # Import data from file
        with open(self._filename) as inFile:
            data = json.load(inFile)

        cmds.undoInfo(openChunk=True)
        cmds.select(cl=True)
        for d in data or []:
            s = d["object"]
            skin = mel.eval("findRelatedSkinCluster {}".format(s))

            if skin != None:
                for idx, vertex in enumerate(d["vertices"] or []):
                    influences = []
                    for inf in vertex:
                        joint = inf[0]
                        weight = inf[1]
                        influences.append( (joint, weight) )

                        #if unicode(joint) not in cmds.skinCluster(skin, query=True, inf=True):
                        #cmds.select(s, replace=True)
                        #cmds.skinCluster(skin, edit=True, addInfluence=unicode(joint))#, normalizeWeights=True, forceNormalizeWeights=True)


                    vtx = s + ".vtx[{}]".format(idx)
                    cmds.skinPercent(skin, vtx, transformValue=influences)

            cmds.select(s)

        cmds.undoInfo(closeChunk=True)

        # Success message
        msgStr = "Imported skin weights from '{}'".format(self._filename)
        print(msgStr)
        message = QMessageBox()
        message.setText(msgStr)
        message.setStandardButtons(QMessageBox.Ok)
        message.exec_()



def ShowUI():
    for win in qApp.allWidgets():
        if type(win).__name__ == 'AnimationExporterWindow':
            win.close()
            win.deleteLater()
    win = AnimationExporterWindow(MayaMainWindow())
    return win


###########################################################################################################################################################################


if __name__ == '__main__':
    win = ShowUI()
