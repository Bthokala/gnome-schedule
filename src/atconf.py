# atconf.py - mainWindow of the at configuration tool
# Copyright (C) 2004, 2005 Philip Van Hoof <me at freax dot org>
# Copyright (C) 2004, 2005 Gaute Hope <eg at gaute dot eu dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import gtk
import gnome
import gobject
import string
import os
import re
import gtk.glade
import addWindow
import setuserWindow
import at
import addWindowHelp
import sys
import time

from os import popen

##
## I18N
##
from rhpl.translate import _, N_
import rhpl.translate as translate
domain = 'gnome-schedule'
translate.textdomain (domain)
gtk.glade.bindtextdomain(domain)


##
## Icon for windows
##
iconPixbuf = None
try:
	iconPixbuf = gtk.gdk.pixbuf_new_from_file("/usr/share/gnome-schedule/pixmaps/gnome-schedule.png")
except:
	pass




##
## The MainWindow class
##
class main:
	def __init__(self, debug_flag=None):
		self.debug_flag = debug_flag
		# Setting up the glade stuff
		if os.access("gnome-schedule.glade", os.F_OK):
			self.xml = gtk.glade.XML ("gnome-schedule.glade", domain="gnome-schedule")
		else:
			self.xml = gtk.glade.XML ("/usr/share/gnome-schedule/gnome-schedule.glade", domain="gnome-schedule")




		self.widget = self.xml.get_widget("mainWindow")
		self.treeview = self.xml.get_widget("treeview")
		self.set_user_menu = self.xml.get_widget("self_user_menu")
		self.add_button = self.xml.get_widget ("add_button")
		self.prop_button = self.xml.get_widget ("prop_button")
		self.del_button = self.xml.get_widget ("del_button")
		self.help_button = self.xml.get_widget ("help_button")
		self.btnSetUser = self.xml.get_widget("btnSetUser")

		#set title:
		self.widget.set_title("Configure scheduled tasks: at")
		#read the user
		self.readUser()

		# This will only work with PyGTK 2.4.x
		try:
			# this tries to fix a bug in libglade (the homogeneous propery ain't working)
			self.toolbar = self.xml.get_widget ("toolbar")
			self.toolbar.get_nth_item (0).set_homogeneous (gtk.TRUE)
			self.toolbar.get_nth_item (1).set_homogeneous (gtk.TRUE)
			self.toolbar.get_nth_item (2).set_homogeneous (gtk.TRUE)
			self.toolbar.get_nth_item (3).set_homogeneous (gtk.TRUE)
		except:
			pass

		self.treeview.set_rules_hint(gtk.TRUE)
		self.treeview.columns_autosize()
		self.add_scheduled_task_menu = self.xml.get_widget ("add_scheduled_task_menu")
		self.properties_menu = self.xml.get_widget ("properties_menu")
		self.delete_menu = self.xml.get_widget ("delete_menu")
		self.set_user_menu = self.xml.get_widget ("set_user_menu")
		self.quit_menu = self.xml.get_widget ("quit_menu")
		self.advanced_menu = self.xml.get_widget ("advanced_menu")
		self.about_menu = self.xml.get_widget ("about_menu")

		self.xml.signal_connect("on_advanced_menu_activate", self.on_advanced_menu_activate)
		self.xml.signal_connect("on_about_menu_activate", self.on_about_menu_activate)
		self.xml.signal_connect("on_add_scheduled_task_menu_activate", self.on_add_scheduled_task_menu_activate)
		self.xml.signal_connect("on_properties_menu_activate", self.on_properties_menu_activate)
		self.xml.signal_connect("on_delete_menu_activate", self.on_delete_menu_activate)
		self.xml.signal_connect("on_quit_menu_activate", self.quit)
		self.xml.signal_connect("on_manual_menu_activate", self.on_manual_menu_activate)
		self.xml.signal_connect("on_add_button_clicked", self.on_add_button_clicked)
		self.xml.signal_connect("on_prop_button_clicked", self.on_prop_button_clicked)
		self.xml.signal_connect("on_del_button_clicked", self.on_del_button_clicked)
		self.xml.signal_connect("on_help_button_clicked", self.on_help_button_clicked)
		self.xml.signal_connect("on_btnExit_clicked", self.quit)

		#hiding setuser button if not root
		if self.root == 0:
			self.btnSetUser.hide()
		else:
			self.xml.signal_connect("on_btnSetUser_clicked", self.showSetUser)

		self.widget.connect("delete_event", self.quit)
		self.widget.connect("destroy_event", self.quit)
		# self.widget.connect("close", self.quit)

		#inittializing the treeview
		self.init_treeview()

		#initializing the crontab
		self.at = at.At(self)

		#add window
		self.addwidget = self.xml.get_widget("addWindow")
		self.addwidget.hide()
		self.addWindow = addWindow.AddWindow (self, self.at)

		#add window help
		self.addhelpwidget = self.xml.get_widget("addWindowHelp")
		self.addhelpwidget.hide()
		self.addHelpWindow = addWindowHelp.AddWindowHelp(self, self.addWindow)

		#set user window
		self.setuserwidget = self.xml.get_widget("setuserWindow")
		self.setuserwidget.hide()
		self.setuserWindow = setuserWindow.SetuserWindow (self)

		if self.root == 0:
			#hiding the 'set user' option
			self.btnSetUser.hide()
		else:
			self.xml.signal_connect("on_btnSetUser_clicked", self.showSetUser)

		gtk.mainloop()
		return

	def init_treeview(self, mode = "simple", init = 0):
		# [0 Title, 1 date, 2 time, 3 class, 4 id, 5 user, 6 command preview(?)]
		# ["get file", "2004-06-17", "20:17", "a", 24, "wget http://..."]
		self.treemodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING)
		self.treeview.set_model (self.treemodel)

		self.switchView("simple", 1)


		return
	
	def switchView(self, mode = "simple", init = 0):
		if mode == "simple":
			#cleaning up columns
			if init != 1:
				i = 4
				while i > - 1:
					temp = self.treeview.get_column(i)
					self.treeview.remove_column(temp)
					i = i -1
				
			# Setting up the columns
			self.col = gtk.TreeViewColumn(_("Title"), gtk.CellRendererText(), text=0)
			self.treeview.append_column(self.col)
			self.col = gtk.TreeViewColumn(_("Date"), gtk.CellRendererText(), text=1)
			self.treeview.append_column(self.col)
			self.col = gtk.TreeViewColumn(_("Time"), gtk.CellRendererText(), text=2)
			self.treeview.append_column(self.col)
			self.col = gtk.TreeViewColumn(_("Preview"), gtk.CellRendererText(), text=6)
			self.col.set_spacing(235)
			self.treeview.append_column(self.col)


		elif mode == "advanced":
			#cleaning up columns
			if init != 1:
				i = 3
				while i > - 1:
					temp = self.treeview.get_column(i)
					self.treeview.remove_column(temp)
					i = i -1
			
			# Setting up the columns
			self.col = gtk.TreeViewColumn(_("Date"), gtk.CellRendererText(), text=1)
			self.treeview.append_column(self.col)
			self.col = gtk.TreeViewColumn(_("Time"), gtk.CellRendererText(), text=2)
			self.treeview.append_column(self.col)
			self.col = gtk.TreeViewColumn(_("Id"), gtk.CellRendererText(), text=4)
			self.treeview.append_column(self.col)	
			self.col = gtk.TreeViewColumn(_("Class"), gtk.CellRendererText(), text=3)
			self.treeview.append_column(self.col)	
			self.col = gtk.TreeViewColumn(_("Preview"), gtk.CellRendererText(), text=6)
			self.col.set_spacing(235)
			self.treeview.append_column(self.col)

		self.widget.show_all()

		if self.root == 0:
			self.btnSetUser.hide()
		else:
			self.xml.signal_connect("on_btnSetUser_clicked", self.showSetUser)

		# self.treeview.get_selection().connect("changed", self.onTreeViewSelectRow)
		self.treeview.get_selection().unselect_all()
		self.edit_mode = mode
		return


	def quit (self, *args):
		gtk.mainquit()

	def readUser (self):
		UID = os.geteuid()
		if UID == 0:
			self.root = 1
			self.user = "root"
			if len(sys.argv) == 2:
				self.user = sys.argv[1]
		else:
			self.root = 0
			self.user = os.environ['USER']

			
			
		return


	def on_add_button_clicked (self, *args):
		self.on_add_scheduled_task_menu_activate (self, args)
		pass

	def on_prop_button_clicked (self, *args):
		self.on_properties_menu_activate (self, args)
		pass

	def on_del_button_clicked (self, *args):
		self.on_delete_menu_activate (self, args)
		pass

	def on_help_button_clicked (self, *args):
		self.on_manual_menu_activate (self, args)
		pass


	def on_advanced_menu_activate (self, widget):
		if widget.get_active():
			self.switchView("advanced")
		else:
			self.switchView("simple")
		return

	def on_about_menu_activate (self, *args):
		dlg = gnome.ui.About(_("System Schedule"), "@VERSION@",
			_("Copyright (c) 2004-2005 Gaute Hope."),
			_("This software is distributed under the GPL. "),
			["Philip Van Hoof <me at freax dot org>",
			"Gaute Hope <eg at gaute dot eu dot org>"
			])
		dlg.set_transient_for(self.widget)
		dlg.set_position (gtk.WIN_POS_CENTER_ON_PARENT)
		dlg.show()

	def on_add_scheduled_task_menu_activate (self, *args):
		self.addWindow.showAddWindow (self.edit_mode)
		pass

	def on_properties_menu_activate (self, *args):
		store, iter = self.treeview.get_selection().get_selected()
		if iter != None:
			record = self.treemodel.get_value(iter, 3)
			linenumber = self.treemodel.get_value(iter, 4)
			self.addWindow.showEditWindow (record, linenumber, iter, self.edit_mode)

	def on_delete_menu_activate (self, *args):
		store, iter = self.treeview.get_selection().get_selected()
		if iter != None:
			record = self.treemodel.get_value(iter, 3)
			linenumber = self.treemodel.get_value(iter, 4)
			
			self.at.deleteJob (linenumber)

			self.treemodel.clear ()		
			self.at.readAt ()

		#moving to first
		iter =  self.treemodel.get_iter_first()
		if iter:
			selection = self.treeview.get_selection()
			selection.select_iter(iter)
		return

	def on_quit_menu_activate (self, *args):
		pass

	def on_manual_menu_activate (self, *args):
		help_page = "file:///usr/share/doc/gnome-schedule-" + "@VERSION@" + "/index.html"
		path = "/usr/bin/gnome-help"
		pid = os.fork()
		if not pid:
			os.execv(path, [path, help_page])

	def showSetUser(self, *args):
		self.setuserWindow.ShowSetuserWindow()
		return
