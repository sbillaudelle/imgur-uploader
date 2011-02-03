#!/usr/bin/env python

import os
from distutils.core import setup
from distutils.command.install_scripts import install_scripts

class post_install(install_scripts):

    def run(self):
        install_scripts.run(self)

        from shutil import move
        for i in self.get_outputs():
            n = i.replace('.py', '')
            move(i, n)
            print "moving '{0}' to '{1}'".format(i, n)


ID = 'org.sbillaudelle.ImgurUploader'

data_files = []
data_files.extend(
    [
    #('share/cream/{0}/configuration'.format(ID),
    #    ['src/configuration/scheme.xml']),
    ('share/cream/{0}/'.format(ID),
        ['src/manifest.xml']),
    ('share/cream/{0}/data'.format(ID),
        ['src/data/interface.ui', 'src/data/imgur.png']),
    ('share/icons',
        ['src/data/imgur.png']),
    ('share/applications',
        ['imgur-uploader.desktop'])
    ])


setup(
    name = 'imgur-uploader',
    version = '0.0.2',
    author = 'The Cream Project (http://cream-project.org)',
    url = 'http://github.com/sbillaudelle/imgur-uploader',
    data_files = data_files,
    package_dir = {'imgur': 'src/imgur'},
    packages = ['imgur'],
    cmdclass={'install_scripts': post_install},
    scripts = ['src/imgur-uploader.py']
)
