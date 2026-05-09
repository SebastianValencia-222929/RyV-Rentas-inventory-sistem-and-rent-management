"""
Tests for authentication views: login_view and logout_view.
"""
import pytest
from django.urls import reverse
from django.contrib.messages import get_messages


@pytest.mark.django_db
class TestLoginView:

    def test_get_renders_login_form(self, client):
        url = reverse('authentication:login')
        resp = client.get(url)
        assert resp.status_code == 200
        template_names = [t.name for t in resp.templates if t.name]
        assert 'authentication/login.html' in template_names

    def test_post_valid_credentials_redirects(self, client, usuario_admin):
        url = reverse('authentication:login')
        resp = client.post(url, data={'username': 'admin_test', 'password': 'admin1234'})
        assert resp.status_code == 302
        assert resp['Location'].endswith(reverse('rentas:lista'))

    def test_post_valid_with_next_redirects_to_next(self, client, usuario_admin):
        next_path = '/some/protected/'
        url = reverse('authentication:login') + f'?next={next_path}'
        resp = client.post(url, data={'username': 'admin_test', 'password': 'admin1234'})
        assert resp.status_code == 302
        assert resp['Location'] == next_path

    def test_post_invalid_shows_error_message(self, client, db):
        url = reverse('authentication:login')
        resp = client.post(url, data={'username': 'no_user', 'password': 'badpass'})
        # invalid credentials should re-render the form with an error
        assert resp.status_code == 200
        msgs = list(get_messages(resp.wsgi_request))
        assert any('Usuario o contraseña incorrectos.' in str(m) for m in msgs)


@pytest.mark.django_db
class TestLogoutView:

    def test_post_logs_out_and_redirects(self, client, usuario_admin):
        # login first
        client.force_login(usuario_admin)
        url = reverse('authentication:logout')
        resp = client.post(url)
        assert resp.status_code == 302
        # redirects to login
        assert resp['Location'].endswith(reverse('authentication:login'))
        # message present
        msgs = list(get_messages(resp.wsgi_request))
        assert any('Sesión cerrada correctamente.' in str(m) for m in msgs)
        # subsequent access to a protected view should redirect to login
        from django.urls import reverse as _r
        r = client.get(_r('rentas:lista'))
        assert r.status_code == 302

    def test_get_does_not_logout_but_redirects(self, client, usuario_admin):
        client.force_login(usuario_admin)
        url = reverse('authentication:logout')
        resp = client.get(url)
        # GET should redirect to login but not log out the user
        assert resp.status_code == 302
        # user should still be authenticated (access protected view)
        client.force_login(usuario_admin)
        r = client.get(reverse('rentas:lista'))
        assert r.status_code == 200
