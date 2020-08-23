from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


class SocialTree(QtWidgets.QTreeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header().setVisible(False)

    def set_servers(self, servers):
        self.servers = servers
        self.clear()
        for server in self.servers:
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, server.name)
            item.setCheckState(0, Qt.Checked)
            self.addTopLevelItem(item)

    def get_enabled_servers(self):
        enabled = []
        for row in range(len(self)):
            item = self.topLevelItem(row)
            if item.checkState(0) == Qt.Checked:
                enabled.append(item.text(0))
        return enabled

    def __len__(self):
        return self.topLevelItemCount()
