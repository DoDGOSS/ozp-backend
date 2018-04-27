"""
PKI Authentication

nginx ssl_module vars in headers:
$ssl_client_s_dn -> HTTP_X_SSL_USER_DN
$ssl_client_i_dn -> HTTP_X_SSL_ISSUER_DN
$ssl_client_verify -> HTTP_X_SSL_AUTHENTICATED
"""
import logging
import re

from django.conf import settings
from rest_framework import authentication

from ozpcenter import models
from ozpcenter import utils

from ozpcenter.pubsub import dispatcher


try:
    from django.contrib.auth import get_user_model

    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

logger = logging.getLogger('ozp-center.' + str(__name__))


class PkiAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        # ensure we're using HTTPS
        if not request.is_secure():
            logger.error('Insecure request (not HTTPS): incompatible with PkiAuthentication')
            return None

        # get status of client authentication
        authentication_status = request.META.get('HTTP_X_SSL_AUTHENTICATED', None)
        if not authentication_status:
            logger.error('Missing header: HTTP_X_SSL_AUTHENTICATED')
            return None

        # this assumes that we're using nginx and that the value of
        # $ssl_client_verify was put into the HTTP_X_SSL_AUTHENTICATED header
        if authentication_status != 'SUCCESS':
            logger.error('Value of HTTP_X_SSL_AUTHENTICATED header not SUCCESS, got {0!s} instead'.format(authentication_status))
            return None

        # TODO: do we need to preprocess/sanitize this in any way?
        # get the user's DN
        dn = request.META.get('HTTP_X_SSL_USER_DN', None)
        if not dn:
            logger.error('HTTP_X_SSL_USER_DN missing from header')
            return None

        # get the issuer DN:
        issuer_dn = request.META.get('HTTP_X_SSL_ISSUER_DN', None)
        if not issuer_dn:
            logger.error('HTTP_X_SSL_ISSUER_DN missing from header')
            return None

        # using test certs generated by openssl, a '/' is used as a separator,
        # which is not url friendly and causes our demo authorization service
        # to choke. Replace these with commas instead
        if settings.OZP['PREPROCESS_DN']:
            dn = _preprocess_dn(dn)
            issuer_dn = _preprocess_dn(issuer_dn)

        logger.info('Attempting to authenticate user with dn: {0!s} and issuer dn: {1!s}'.format(dn, issuer_dn))

        profile = _get_profile_by_dn(dn, issuer_dn)

        if profile:
            logger.info('found user {0!s}, authentication succeeded'.format(profile.user.username))  # , extra={'user', profile.user.username})
            return (profile.user, None)
        else:
            logger.error('Failed to find/create user for dn {0!s}. Authentication failed'.format(dn))
            return None


def _preprocess_dn(original_dn):
    """
    Reverse the DN and replace slashes with commas
    """
    dn = original_dn
    if dn[:1] == '/':
        # remove leading slash
        dn = dn[1:]
    dn = dn.split('/')
    dn = dn[::-1]
    dn = ", ".join(dn)
    dn = re.sub(r'(,)([\w])', r'\1 \2', dn)
    return dn


def _get_profile_by_dn(dn, issuer_dn='default issuer dn'):
    """
    Returns a user profile for a given DN

    If a profile isn't found with the given DN, create one
    """
    # look up the user with this dn. if the user doesn't exist, create them
    profile = models.Profile.objects.filter(dn__iexact=dn).first()
    if profile:
        if not profile.user.is_active:
            logger.warning('User {0!s} tried to login but is inactive'.format(dn))
            return None
        # update the issuer_dn
        if profile.issuer_dn != issuer_dn:
            logger.info('updating issuer dn for user {0!s}'.format(profile.user.username))
            profile.issuer_dn = issuer_dn
            profile.save()
        return profile
    else:
        logger.info('creating new user for dn: {0!s}'.format(dn))
        if 'CN=' in dn:
            cn = utils.find_between(dn, 'CN=', ',')
        else:
            cn = dn

        kwargs = {'display_name': cn, 'dn': dn, 'issuer_dn': issuer_dn}
        # sanitize username
        username = cn[0:30]
        username = username.replace(' ', '_')  # no spaces
        username = username.replace("'", "")  # no apostrophes
        username = username.lower()  # all lowercase
        # make sure this username doesn't exist
        count = User.objects.filter(username=username).count()
        if count != 0:
            new_username = username[0:27]
            count = User.objects.filter(username__startswith=new_username).count()
            new_username = '{0!s}_{1!s}'.format(new_username, count + 1)
            username = new_username

        # now check again - if this username exists, we have a problemce
        count = User.objects.filter(username=username).count()
        if count != 0:
            logger.error('Cannot create new user for dn {0!s}, username {1!s} already exists'.format(dn, username))
            return None

        profile = models.Profile.create_user(username, **kwargs)
        logger.info('created new profile for user {0!s}'.format(profile.user.username))
        dispatcher.publish('profile_created', profile=profile)
        return profile
