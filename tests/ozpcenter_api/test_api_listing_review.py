"""
Tests for listing reviews
"""
import collections
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest import skip

from ozpcenter import model_access as generic_model_access
from ozpcenter.scripts import sample_data_generator as data_gen
from tests.ozpcenter.helper import APITestHelper


@override_settings(ES_ENABLED=False)
class ListingReviewApiTest(APITestCase):

    def setUp(self):
        pass

    @classmethod
    def setUpTestData(cls):
        data_gen.run()

    def test_get_all_review_for_listing(self):
        url = '/api/listing/1/review/'
        response = APITestHelper.request(self, url, 'GET', username='bigbrother', status_code=200)

        self.assertEqual(len(response.data), 3)

    def test_get_listing_review_by_id(self):
        url = '/api/listing/1/review/3/'
        response = APITestHelper.request(self, url, 'GET', username='bigbrother', status_code=200)

        expected_data = {
            "review_parent": None,
            "text": "I love the sound of acoustic guitars",
            "listing": 1,
            "rate": 5
        }

        self.assertEqual(response.data['review_parent'], expected_data['review_parent'])
        self.assertEqual(response.data['text'], expected_data['text'])
        self.assertEqual(response.data['listing'], expected_data['listing'])
        self.assertEqual(response.data['rate'], expected_data['rate'])

    def test_create_listing_review(self):
        url = '/api/listing/2/review/'
        data = {
            "rate": 5,
            "text": "This is a test review"
        }
        response = APITestHelper.request(self, url, 'POST', username='bigbrother', data=data, status_code=201)

    def test_create_listing_review_invalid_rate(self):
        url = '/api/listing/2/review/'
        data = {
            "rate": -1,
            "text": "This is a test review with a invalid rate"
        }
        response = APITestHelper.request(self, url, 'POST', username='bigbrother', data=data, status_code=400)

    def test_edit_listing_review(self):
        url = '/api/listing/1/review/3/'
        data = {
            "rate": 5,
            "text": "This is the updated review text"
        }
        response = APITestHelper.request(self, url, 'PUT', username='syme', data=data, status_code=200)

        expected_data = {
            "review_parent": None,
            "text": "This is the updated review text",
            "listing": 1,
            "rate": 5
        }
        self.assertEqual(response.data['review_parent'], expected_data['review_parent'])
        self.assertEqual(response.data['text'], expected_data['text'])
        self.assertEqual(response.data['listing'], expected_data['listing'])
        self.assertEqual(response.data['rate'], expected_data['rate'])

    @skip("TODO Add validation to review text field")
    def test_edit_listing_review_no_text(self):
        # TODO: Add validation on backend to require 20 characters or more for the text field
        # validation is currently being done on front, but users can just call a curl manually with anything
        url = '/api/listing/1/review/3/'
        data = {
            "rate": 5,
            "text": ""
        }
        response = APITestHelper.request(self, url, 'PUT', username='syme', data=data, status_code=400)

    def test_edit_listing_review_no_rate(self):
        url = '/api/listing/1/review/3/'
        data = {
            "text": "This is the updated review text"
        }
        response = APITestHelper.request(self, url, 'PUT', username='syme', data=data, status_code=400)

    def test_edit_different_user_listing_review(self):
        # Trying to edit 'syme' review as user, jones
        url = '/api/listing/1/review/3/'
        data = {
            "rate": 5,
            "text": "This is the updated review text"
        }
        response = APITestHelper.request(self, url, 'PUT', username='jones', data=data, status_code=403)

    def test_delete_listing_review(self):
        url = '/api/listing/1/review/3/'
        response = APITestHelper.request(self, url, 'DELETE', username='bigbrother', status_code=204)
