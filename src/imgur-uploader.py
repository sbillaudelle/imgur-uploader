#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import os
import thread
import optparse
import gobject
import gtk
import mimetypes

import cream

from imgur import Imgur

API_KEY = '97afbe8e4bd793012c847f0f39df8ffe'

class ImgurUploader(cream.Module):

    def __init__(self):

        cream.Module.__init__(self, 'org.sbillaudelle.ImgurUploader')

        parser = optparse.OptionParser()
        (options, args) = parser.parse_args()

        self.imgur = Imgur(API_KEY)

        self.interface = gtk.Builder()
        self.interface.add_from_file(os.path.join(self.context.get_path(), 'data/interface.ui'))

        self.window = self.interface.get_object('window')
        self.treeview = self.interface.get_object('treeview')
        self.filechooser = self.interface.get_object('filechooser')
        self.upload_button = self.interface.get_object('upload_button')
        self.close_button = self.interface.get_object('close_button')
        self.add_image_button = self.interface.get_object('add_image_button')
        self.remove_image_button = self.interface.get_object('remove_image_button')
        self.context_menu = self.interface.get_object('context_menu')
        self.copy_item = self.interface.get_object('copy_item')

        icon_path = os.path.join(self.context.get_path(), 'data/imgur.png')
        self.window.set_icon_from_file(icon_path)
        self.window.set_title(self.context.manifest['name'])

        self.filefilter = gtk.FileFilter()
        self.filefilter.set_name("Alle Bilddateien")
        self.filefilter.add_mime_type('image/bmp')
        self.filefilter.add_mime_type('image/gif')
        self.filefilter.add_mime_type('image/jpeg')
        self.filefilter.add_mime_type('image/jpg')
        self.filefilter.add_mime_type('image/pjpeg')
        self.filefilter.add_mime_type('image/png')
        self.filefilter.add_mime_type('image/tiff')
        self.filefilter.add_mime_type('image/x-bmp')

        self.filechooser.add_filter(self.filefilter)
        self.filechooser.set_current_folder(os.path.expanduser('~'))

        self.window.connect('destroy', lambda *args: self.quit())
        self.add_image_button.connect('clicked', self.add_image_cb)
        self.remove_image_button.connect('clicked', self.remove_image_cb)
        self.upload_button.connect('clicked', lambda *args: self.upload())
        self.close_button.connect('clicked', lambda *args: self.quit())
        self.treeview.connect('button-press-event', self.context_menu_cb)
        self.copy_item.connect('activate', self.copy_url_cb)

        # Initialize drag and drop...
        self.treeview.drag_dest_set(0, [], 0)
        self.treeview.connect('drag_motion', self.drag_motion_cb)
        self.treeview.connect('drag_drop', self.drag_drop_cb)
        self.treeview.connect('drag_data_received', self.drag_data_cb)

        theme = gtk.icon_theme_get_default()
        icon_info = theme.lookup_icon('ok', 16, 0)
        self.icon_done = gtk.gdk.pixbuf_new_from_file(icon_info.get_filename())

        self.liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, gtk.gdk.Pixbuf, bool, bool, int, str, str, bool)

        self.treeview.set_model(self.liststore)
        self.treeview_selection = self.treeview.get_selection()
        self.treeview_selection.set_mode(gtk.SELECTION_MULTIPLE)

        self.column_info = gtk.TreeViewColumn("Image")
        self.column_info.set_property('expand', True)
        self.column_url = gtk.TreeViewColumn("URL")
        self.column_status = gtk.TreeViewColumn("Status")
        self.treeview.append_column(self.column_info)
        self.treeview.append_column(self.column_url)
        self.treeview.append_column(self.column_status)

        cellrenderer_preview = gtk.CellRendererPixbuf()
        cellrenderer_title = gtk.CellRendererText()
        self.column_info.pack_start(cellrenderer_preview, False)
        self.column_info.pack_start(cellrenderer_title, True)
        self.column_info.add_attribute(cellrenderer_preview, 'pixbuf', 0)
        self.column_info.add_attribute(cellrenderer_title, 'text', 1)

        cellrenderer_url = gtk.CellRendererText()
        self.column_url.pack_start(cellrenderer_url, True)
        self.column_url.add_attribute(cellrenderer_url, 'markup', 7)

        cellrenderer_spinner = gtk.CellRendererSpinner()
        self.column_status.pack_end(cellrenderer_spinner, False)
        self.column_status.add_attribute(cellrenderer_spinner, 'visible', 3)
        self.column_status.add_attribute(cellrenderer_spinner, 'active', 3)

        cellrenderer_status = gtk.CellRendererPixbuf()
        self.column_status.pack_end(cellrenderer_status, False)
        self.column_status.add_attribute(cellrenderer_status, 'pixbuf', 2)
        self.column_status.add_attribute(cellrenderer_status, 'visible', 4)

        self.window.show_all()

        self.count = 0
        gobject.timeout_add(100, self.pulse, self.liststore, self.column_status, cellrenderer_spinner)

        for arg in args:
            self.add_image(arg)


    @property
    def selected_images(self):
        return self.treeview.get_selection().get_selected_rows()[1]


    def copy_url_cb(self, source):
        data = ''

        for row in self.selected_images:
            data += '\n' + self.liststore[row[0]][7].replace('<tt>', '').replace('</tt>', '')

        clipboard = gtk.clipboard_get()
        clipboard.set_text(data.strip())


    def context_menu_cb(self, source, event):

        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            path_info = self.treeview.get_path_at_pos(x, y)
            if path_info is not None:
                path, col, cellx, celly = path_info
                if not path in self.selected_images:
                    self.treeview.set_cursor(path, col, 0)
                if self.liststore[path[0]][4]:
                    self.copy_item.set_property('sensitive', True)
                else:
                    self.copy_item.set_property('sensitive', False)
                self.context_menu.popup(None, None, None, event.button, event.time)
            return True
        elif event.button == 1:
            x = int(event.x)
            y = int(event.y)
            path_info = self.treeview.get_path_at_pos(x, y)
            if path_info is not None:
                path, col, cellx, celly = path_info

                if self.liststore[path[0]][4]:
                    if col == self.column_url:
                        pass

    def drag_motion_cb(self, source, context, x, y, time):
        context.drag_status(gtk.gdk.ACTION_MOVE, time)
        return True

    def drag_drop_cb(self, source, context, x, y, time):
        if 'text/uri-list' in context.targets:
            source.drag_get_data(context, 'text/uri-list', time)
        return True

    def drag_data_cb(self, source, context, x, y, data, info, time):
        for uri in data.get_uris():
            path = uri.replace('file://', '')
            filename = os.path.split(path)[0]
            mimetype = mimetypes.guess_type(path)[0]

            if self.filefilter.filter((path, uri, filename, mimetype)):
                self.add_image(path)

        context.finish(True, False, time)



    def upload(self):
        thread.start_new_thread(self._upload, ())


    def _upload(self):

        for image in self.liststore:
            if image[4]:
                continue

            gtk.gdk.threads_enter()
            image[3] = True
            gtk.gdk.threads_leave()

            data = self.imgur.upload(image[6])

            gtk.gdk.threads_enter()
            image[7] = "<tt>{0}</tt>".format(data['rsp']['image']['imgur_page'])
            image[3] = False
            image[4] = True
            gtk.gdk.threads_leave()


    def pulse(self, liststore, column, spinner):

        column.add_attribute(spinner, "pulse", 5)

        self.count+=1

        for item in liststore:
            item[5] = self.count

        return True


    def add_image_cb(self, source):

        res = self.filechooser.run()
        self.filechooser.hide()

        if res == 1:
            filenames = self.filechooser.get_filenames()
            for filename in filenames:
                self.add_image(filename)


    def remove_image_cb(self, source):

        selection = self.treeview_selection.get_selected_rows()[1]

        for row in selection:
            if self.liststore[row[0]][3]:
                self.treeview_selection.unselect_path(row)

        selection = self.treeview_selection.get_selected_rows()[1]

        if not selection:
            return

        while selection:
            row = selection[0]
            self.liststore.remove(self.liststore.get_iter(row))
            selection = self.treeview_selection.get_selected_rows()[1]


    def add_image(self, image_path):
        thread.start_new_thread(self._add_image, (image_path,))


    def _add_image(self, image_path):

        icon = gtk.gdk.pixbuf_new_from_file(image_path)
        width = icon.get_width()
        height = icon.get_height()
        factor = float(width) / float(height)

        icon = icon.scale_simple(int(20 * factor), 20, gtk.gdk.INTERP_BILINEAR)

        gtk.gdk.threads_enter()
        self.liststore.append((icon, os.path.basename(image_path), self.icon_done, False, False, 0, image_path, '', True))
        gtk.gdk.threads_leave()


if __name__ == '__main__':
    ImgurUploader().main()
