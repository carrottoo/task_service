from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status
from .models import *
from django.contrib.auth.models import User
from typing import List, Dict

class PropertyTests(APITestCase):
    
    def setUp(self) -> None:
        """
        Test setup, prepared several test users and tasks
        """

        # create users with profile 'employer'
        self.user_employer = User.objects.create_user(username='user_1', password='mysecretpassword')
        self.user_employee = User.objects.create_user(username='user_2', password='myuniquepassword')

        self.set_user_profile({self.user_employer: True,
                               self.user_employee: False})

        # create property instance
        self.property_1 = Property.objects.create(name='cleaning', creator=self.user_employer)
        self.property_2 = Property.objects.create(name='studying', creator=self.user_employee)
    
    def set_user_profile(self, info: Dict[User, bool]) -> None:
        """
        Set the user profile by giving a dictionary of user object and profile boolean
        """

        for key, value in info.items():
            UserProfile.objects.create(user=key, is_employer=value)

    def test_list_retrieval(self):
        """
        Test GET request for the list retrieval of property 
        """
        list_url = reverse('property-list')
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_retrieval_by_id(self):
        """
        Test GET request to retrieve a property object by its id 
        """

        property_id = self.property_1.pk
        detail_url = reverse('property-detail', kwargs={'pk': property_id})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], property_id)
        self.assertEqual(response.data['name'], 'cleaning')

    def test_property_creation(self):
        """
        Test POST request to create a new property tag, only authenticated users are allowed
        """

        create_url = reverse('property-list')

        data = {
            'name': 'gardening'
        }

        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.login(username=self.user_employer.username, password='mysecretpassword')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Property.objects.count(), 3)

        new_property = Property.objects.latest('id')
        self.assertEqual(new_property.name, 'gardening')

    def test_property_update(self):
        """
        Test PUT request to update a property tag, this endpoint has been disabled to maintain the data consistency in the database
        """

        update_url = reverse('property-detail', kwargs={'pk': self.property_1.id})

        data={
            'name': 'something else'
        }

        self.client.login(username=self.user_employer.username, password='mysecretpassword')
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Property cannot be modified once created')

    def test_property_partial_update(self):
        """
        Test PUT request to partically update a property tag, this endpoint has been disabled to maintain the data consistency in the database
        """

        update_url = reverse('property-detail', kwargs={'pk': self.property_1.id})

        data={
            'name': 'something else'
        }

        self.client.login(username=self.user_employer.username, password='mysecretpassword')
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Property cannot be modified once created')

    def test_property_deletion(self):
        """
        Test DELETE request to delete a property tag by its id, only the creator can delete the property tags created by his/herslef
        """

        property_id = self.property_2.id
        delete_url = reverse('property-detail', kwargs={'pk': property_id})

        self.assertNotEqual(self.property_2.creator, self.user_employer)
        self.client.login(username=self.user_employer.username, password='mysecretpassword')

        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout
        self.assertEqual(self.property_2.creator, self.user_employee)
        self.client.login(username=self.user_employee.username, password='myuniquepassword')
        
        response_2 = self.client.delete(delete_url)
        self.assertEqual(response_2.status_code, status.HTTP_204_NO_CONTENT)