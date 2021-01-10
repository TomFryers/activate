from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


def children(item: QtWidgets.QTreeWidgetItem):
    for index in range(item.childCount()):
        yield item.child(index)


class SocialTree(QtWidgets.QTreeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header().setVisible(False)

    def set_servers(self, servers, activities):
        self.servers = servers
        self.clear()
        structure = {s.name: set() for s in self.servers}
        for activity in activities:
            for server, username in zip(
                activity.server.split("\n"), activity.username.split("\n")
            ):
                structure[server].add(username)

        for server, users in structure.items():
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, server)
            item.setCheckState(0, Qt.Checked)
            for user in users:
                sub_item = QtWidgets.QTreeWidgetItem()
                sub_item.setText(0, user)
                sub_item.setCheckState(0, Qt.Checked)
                item.addChild(sub_item)
            self.addTopLevelItem(item)

    def get_enabled_servers(self):
        enabled = []
        for row in range(len(self)):
            item = self.topLevelItem(row)
            if item.checkState(0) == Qt.Checked:
                for sub_item in children(item):
                    if sub_item.checkState(0) == Qt.Checked:
                        enabled.append((item.text(0), sub_item.text(0)))
        return enabled

    def __len__(self):
        return self.topLevelItemCount()
