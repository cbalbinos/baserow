from django.conf.urls import url

from .views import (
    UserView, SendResetPasswordEmailView, ResetPasswordView, ChangePasswordView,
    ObtainJSONWebToken, RefreshJSONWebToken, VerifyJSONWebToken
)


app_name = 'baserow.api.v0.user'

urlpatterns = [
    url(r'^token-auth/$', ObtainJSONWebToken.as_view(), name='token_auth'),
    url(r'^token-refresh/$', RefreshJSONWebToken.as_view(), name='token_refresh'),
    url(r'^token-verify/$', VerifyJSONWebToken.as_view(), name='token_verify'),
    url(
        r'^send-reset-password-email/$',
        SendResetPasswordEmailView.as_view(),
        name='send_reset_password_email'
    ),
    url(
        r'^reset-password/$',
        ResetPasswordView.as_view(),
        name='reset_password'
    ),
    url(
        r'^change-password/$',
        ChangePasswordView.as_view(),
        name='change_password'
    ),
    url(r'^$', UserView.as_view(), name='index')
]
