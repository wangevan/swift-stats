# Copyright (c) 2010-2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
import shutil
import hashlib
import urllib
import sqlite3

from swift.account.server import DATADIR as account_server_data_dir
from swift.container.server import DATADIR as container_server_data_dir
from swift.common.db import AccountBroker, ContainerBroker
from swift.common.utils import renamer, get_logger, readconf, mkdirs,  TRUE_VALUES, remove_file
from swift.common.constraints import check_mount
from swift.common.daemon import Daemon
from time import sleep
import MySQLdb
from datetime import timedelta
from datetime import datetime

class DatabaseStatsCollector(Daemon):
    """
    Extract storage stats from account databases on the account
    storage nodes

    Any subclasses must define the function get_data.
    """

    def __init__(self, stats_conf):
        super(DatabaseStatsCollector, self).__init__(stats_conf)
        self.stats_type = stats_conf.get('stats_type','account')
        self.data_dir = stats_conf.get('data_dir','/data/swift/data/accounts')
        self.filename_format = stats_conf.get('filename_format','stats-%Y%m%d%H_')
        self.devices = stats_conf.get('devices', '/data/swift')
        self.mount_check = stats_conf.get('mount_check',
                                           'true').lower() in TRUE_VALUES
        self.logger = get_logger(stats_conf, log_route='%s-stats' % self.stats_type) 

        self.server_ID = int(stats_conf.get('server_ID',100) )
        self.interval = int (stats_conf.get('interval',20) )
        self.db_host = stats_conf.get('db_host', '10.12.28.100')
        self.db_user = stats_conf.get('db_user', 'root')
        self.db_passwd = stats_conf.get('db_passwd', '123456')

    def run_once(self, *args, **kwargs):
        self.logger.info(_("Gathering %s stats" % self.stats_type))
        start = time.time()
        self.find_and_process()
        self.logger.info(_("Gathering %s stats complete (%0.2f minutes)") %
                         (self.stats_type, (time.time() - start) / 60))

    def run_forever(self, *args, **kwargs):
        """
         Replicate dbs under the given root in an infinite loop.
        """
        while True:
            begin = time.time()
            try:
                self.run_once()
            except (Exception):
                self.logger.exception('ERROR trying to run_forever()')

            elapsed = time.time() - begin
            if elapsed < self.interval:
               sleep(self.interval - elapsed)

    def get_data(self):
        raise NotImplementedError('Subclasses must override')

    def get_header(self):
        raise NotImplementedError('Subclasses must override')

    def find_and_process(self):

        mysql_conn = None

        # connect the database
        try:
            mysql_conn = MySQLdb.connect(host='%s' % self.db_host,user='%s' % self.db_user,passwd='%s' % self.db_passwd,db='statistics')
        except Exception, e:
            self.logger.error("---" *20)
            self.logger.error("connection mysql exception : %r" % e )
            self.logger.error("+++" *20)
            return
        ##  get the whole point of hour string
        t = datetime.now() 
        if t.minute > 50:
            t += timedelta(hours=1)
        t=t.replace(minute=0, second=0, microsecond=0)
        strt = t.strftime('%Y-%m-%d %H:%M:%S')


        

        try:
                for device in os.listdir(self.devices):
                    if self.mount_check and not check_mount(self.devices, device):
                        self.logger.error("Device %s is not mounted, skipping." % device)
                        continue
                    db_dir = os.path.join(self.devices, device, self.data_dir)

                    if not os.path.exists(db_dir):
                        self.logger.debug("Path %s does not exist, skipping." % db_dir)
                        continue

                    for root, dirs, files in os.walk(db_dir, topdown=False):
                        for filename in files:
                            if filename.endswith('.db'):
                                db_path = os.path.join(root, filename)
                                try:
                                    line_data = self.get_data(db_path)
                                except sqlite3.Error, err:
                                    self.logger.info(
                                        _("Error accessing db %s: %s") %
                                          (db_path, err))
                                    continue
                                if line_data:
                                    accountID, AccountContainerCount,AccountObjectCount,AccountBytesUsed = line_data.split(',')
                                    cursor = mysql_conn.cursor()
                                    sql = "insert into  swift_space_stats(\
                                        ServerID, AddTime,AccountID,AccountContainerCount,AccountObjectCount,AccountBytesUsed) \
                                        values(%d,'%s','%s',%d,%d,%d)" \
                                        % (self.server_ID,strt,accountID.replace('AUTH_',''), int(AccountContainerCount),int(AccountObjectCount),int(AccountBytesUsed)/1024 )
                                    self.logger.error("---" *20)
                                    self.logger.error("sql = %r" % sql )
                                    self.logger.error("+++" *20)
                                    try:
                                        cursor.execute(sql)
                                    except Exception, e:
                                        continue

                    cursor.close()
                    mysql_conn.commit()
                    mysql_conn.close()


        finally:
            self.logger.error("---" *20)
            self.logger.error("finally" )
            self.logger.error("+++" *20)


class AccountStatsCollector(DatabaseStatsCollector):
    """
    Extract storage stats from account databases on the account
    storage nodes
    """

    def __init__(self, stats_conf):
        super(AccountStatsCollector, self).__init__(stats_conf )

    def get_data(self, db_path):
        """
        Data for generated csv has the following columns:
        Account Hash, Container Count, Object Count, Bytes Used

        :raises sqlite3.Error: does not catch errors connecting to db
        """
        line_data = None
        broker = AccountBroker(db_path)
        if not broker.is_deleted():
            info = broker.get_info()
            line_data = '%s,%d,%d,%d\n' % (info['account'],
                                             info['container_count'],
                                             info['object_count'],
                                             info['bytes_used'])
        return line_data

    def get_header(self):
        return ''


class ContainerStatsCollector(DatabaseStatsCollector):
    """
    Extract storage stats from container databases on the container
    storage nodes
    """

    def __init__(self, stats_conf):
        super(ContainerStatsCollector, self).__init__(stats_conf, 'container',
                                                   container_server_data_dir,
                                                   'container-stats-%Y%m%d%H_')
        # webob calls title on all the header keys
        self.metadata_keys = ['X-Container-Meta-%s' % mkey.strip().title()
                for mkey in stats_conf.get('metadata_keys', '').split(',')
                if mkey.strip()]

    def get_header(self):
        header = 'Account Hash,Container Name,Object Count,Bytes Used'
        if self.metadata_keys:
            xtra_headers = ','.join(self.metadata_keys)
            header += ',%s' % xtra_headers
        header += '\n'
        return header

    def get_data(self, db_path):
        """
        Data for generated csv has the following columns:
        Account Hash, Container Name, Object Count, Bytes Used
        This will just collect whether or not the metadata is set
        using a 1 or ''.

        :raises sqlite3.Error: does not catch errors connecting to db
        """
        line_data = None
        broker = ContainerBroker(db_path)
        if not broker.is_deleted():
            info = broker.get_info(include_metadata=bool(self.metadata_keys))
            encoded_container_name = urllib.quote(info['container'])
            line_data = '"%s","%s",%d,%d' % (
                info['account'], encoded_container_name,
                info['object_count'], info['bytes_used'])
            if self.metadata_keys:
                metadata_results = ','.join(
                    [info['metadata'].get(mkey) and '1' or ''
                     for mkey in self.metadata_keys])
                line_data += ',%s' % metadata_results
            line_data += '\n'
        return line_data


