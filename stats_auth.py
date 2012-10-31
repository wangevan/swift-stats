# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Copyright (c) 2012 OpenStack, LLC.
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

import webob

from swift.common import utils as swift_utils
# from swift.common.middleware import acl as swift_acl


class StatsAuth(object):

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = swift_utils.get_logger(conf, log_route='swift_stats_auth')
        self.admin_user_list = conf.get('admin_user_list',
                                       'admin').lower().split(',')

    def __call__(self, environ, start_response):

        #self.logger.info('%r' % environ)
        if environ.get('HTTP_X_IDENTITY_STATUS') != 'Confirmed': 
            return self.denied_response(req)

        roles = [] 
        if 'HTTP_X_ROLE' in environ: 
            roles = environ['HTTP_X_ROLE'].split(',') 
        identity = {'user': environ.get('HTTP_X_USER'), 
                    'tenant': environ.get('HTTP_X_TENANT_ID'), 
                    'roles': roles} 
        environ['keystone.identity'] = identity
        environ['stats.authorize'] = self.authorize

        return self.app(environ, start_response)

    def authorize(self, req):

        env = req.environ
        env_identity = env.get('keystone.identity', {})
        user_roles = env_identity.get('roles', [])

#        self.logger.info('%r' % env)
        for admin_user in self.admin_user_list:
            if admin_user in user_roles:
                return

        tenant_id = env_identity.get('tenant')
        if tenant_id == None:
            return self.denied_response(req)

        account_id = env.get('query_info', {}).get('account_id')

        if tenant_id == account_id:
            return
        return self.denied_response(req)

    def denied_response(self, req):
        """Deny WSGI Response.

        Returns a standard WSGI response callable with the status of 403 or 401
        depending on whether the REMOTE_USER is set or not.
        """
        if req.remote_user:
            return webob.exc.HTTPForbidden(request=req)
        else:
            return webob.exc.HTTPUnauthorized(request=req)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return StatsAuth(app, conf)
    return auth_filter
