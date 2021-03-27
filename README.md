# Activate

![Icon](activate/resources/icons/icon_cropped.png)

Activate is a free activity log and analysis tool.

The recommended way to install Activate is through PyPI. Just run
`pip install activate-app[app]`.

To install an Activate server, use `pip install activate-app[server]`.

## Basic Usage

When you first open Activate, you will see a mostly empty screen with
your total distance, time, number of activities and climb (which are all
zero). To add your activities, go to File/Import or press Ctrl-I. Select
the activities you wish to import, and wait for the import to finish. If
you switch to the 'Activities' tab, you can see individual activities.
Go to Activity/Analyse to see more detail.

To connect to an Activate server, go to Settings/Servers, press 'Add
Server' and enter the server details. You will need a username and
password given to you by the server admin. You can then access the
'Social' tab to see the activities of members of that server.

## Development Information

Run `make` to build the app.

Then, run `./app` to launch Activate, or `./server` to launch a test
server.

---

Activate, a free activity log and analysis tool.
Copyright © 2020–2021 Tom Fryers

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program. If not, see
<https://www.gnu.org/licenses/>.
