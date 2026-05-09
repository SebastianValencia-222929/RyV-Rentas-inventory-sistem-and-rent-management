"""
Pruebas para la app `inicio` (vistas públicas).
"""
import pytest
from django.urls import reverse


class TestLandingView:

    def test_landing_anonymous_renders_template(self, client):
        url = reverse('inicio:landing')
        resp = client.get(url)
        assert resp.status_code == 200
        template_names = [t.name for t in resp.templates if t.name]
        assert 'inicio/landing.html' in template_names

    def test_landing_authenticated_redirects_to_rentas(self, client, usuario_empleado):
        client.force_login(usuario_empleado)
        url = reverse('inicio:landing')
        resp = client.get(url)
        assert resp.status_code == 302
        assert resp['Location'].endswith(reverse('rentas:lista'))
