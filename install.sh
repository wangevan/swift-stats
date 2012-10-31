#!/bin/bash

rm -rf /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/swift/proxy/server.pyc
mkdir -p  /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/swift/plugins/

rm -rf  /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/swift/common/space.pyc
cp space.py /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/swift/common/
cp server.py /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/swift/proxy/

mkdir -p /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/swift/statistics/
cp statistics-server.py  /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/swift/statistics/server.py

cp stats.conf /etc/swift/
cp statistics.conf /etc/swift/

cp swift-account-stats.sh /usr/bin/swift-account-stats
cp swift-account-stats /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/EGG-INFO/scripts/
cp stats_auth.py /usr/lib/python2.6/site-packages/keystone/middleware/ 

cp entry_points.txt  /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/EGG-INFO/
cp swift-statistics-server /usr/bin/
cp swift-statistics-server.script /usr/lib/python2.6/site-packages/swift-1.4.8-py2.6.egg/EGG-INFO/scripts/swift-statistics-server
