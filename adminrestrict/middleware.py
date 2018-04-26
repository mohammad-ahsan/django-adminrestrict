"""
adminrestrict middleware
"""

__author__ = "Robert Romano (rromano@gmail.com)"
__copyright__ = "Copyright 2014 Robert C. Romano"


import socket
import re

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied

from adminrestrict.models import AllowedIP


def is_valid_ip(ip_address):
    """
    Check Validity of an IP address
    """
    valid = True
    try:
        socket.inet_aton(ip_address.strip())
    except:
        valid = False
    return valid


def get_ip_address_from_request(request):
    """
    Makes the best attempt to get the client's real IP or return the loopback
    """
    PRIVATE_IPS_PREFIX = ('10.', '172.', '192.', '127.')
    ip_address = ''
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for and ',' not in x_forwarded_for:
        if not x_forwarded_for.startswith(PRIVATE_IPS_PREFIX) and is_valid_ip(x_forwarded_for):
            ip_address = x_forwarded_for.strip()
    else:
        ips = [ip.strip() for ip in x_forwarded_for.split(',')]
        for ip in ips:
            if ip.startswith(PRIVATE_IPS_PREFIX):
                continue
            elif not is_valid_ip(ip):
                continue
            else:
                ip_address = ip
                break
    if not ip_address:
        x_real_ip = request.META.get('HTTP_X_REAL_IP', '')
        if x_real_ip:
            if not x_real_ip.startswith(PRIVATE_IPS_PREFIX) and is_valid_ip(x_real_ip):
                ip_address = x_real_ip.strip()
    if not ip_address:
        remote_addr = request.META.get('REMOTE_ADDR', '')
        if remote_addr:
            if not remote_addr.startswith(PRIVATE_IPS_PREFIX) and is_valid_ip(remote_addr):
                ip_address = remote_addr.strip()
            if remote_addr.startswith(PRIVATE_IPS_PREFIX) and is_valid_ip(remote_addr):
                ip_address = remote_addr.strip()
    if not ip_address:
            ip_address = '127.0.0.1'
    return ip_address


class AdminPagesRestrictMiddleware(object):
    """
    A middleware that restricts admin pages access to
    restricted IP addresses only. Everyone else gets PermissionDenied exception.
    """
    def __init__(self, get_response):
        self.get_response = get_response 
        # One-time configuration and initialization.

    def __call__(self, request):
        # Section adjusted to restrict login to ? edit (sing cms-toolbar-login)into DjangoCMS login.
        if request.path.startswith(reverse('admin:index') or "cms-toolbar-login" in request.build_absolute_uri()) and \
                        request.method == 'GET':

            # if there aren't allowed ips defined it will not check anything
            if AllowedIP.objects.count() <= 0:
                return self.get_response(request)

            # If any entry as "*" then we open access (as if this middleware wasn't installed)
            if AllowedIP.objects.filter(ip_address="*").count() > 0:
                return self.get_response(request)

            request_ip = get_ip_address_from_request(request)

            for filt in AllowedIP.objects.filter(ip_address__endswith="*"):
                if re.match(filt.ip_address.replace("*", ".*"), request_ip):
                    return self.get_response(request)

            # Otherwise check if the IP address is in the table. If not, deny access
            if AllowedIP.objects.filter(ip_address=request_ip).count() == 0:
                raise PermissionDenied

        return self.get_response(request)
