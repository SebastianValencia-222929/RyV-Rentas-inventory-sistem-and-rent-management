from django.test import TestCase
from django.urls import reverse


class InicioIntegrationTests(TestCase):
    def test_landing_page_accessible(self):
        response = self.client.get(reverse('inicio:landing'))
        self.assertEqual(response.status_code, 200)

    def test_landing_renders_template(self):
        response = self.client.get(reverse('inicio:landing'))
        self.assertTemplateUsed(response, 'inicio/landing.html')
