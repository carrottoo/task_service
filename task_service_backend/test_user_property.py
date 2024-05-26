from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status
from .models import *
from django.contrib.auth.models import User
from typing import List, Dict


class UserPropertyTests(APITestCase):

    def setUp(self) -> None:
        """
        Test setup
        """

       # create users with profile 'employer'
        self.user_employer_1 = User.objects.create_user(username='user_1', password='mysecretpassword')
        self.user_employer_2 = User.objects.create_user(username='user_2', password='password1234')

        # create users with profile 'employee'
        self.user_employee_1 = User.objects.create_user(username='user_3', password='myuniquepassword')
        self.user_employee_2 = User.objects.create_user(username='user_4', password='passcode1234')

        self.set_user_profile({self.user_employer_1: True,
                               self.user_employer_2: True,
                               self.user_employee_1: False,
                               self.user_employee_2: False})

        # create property instance
        self.property_1 = Property.objects.create(name='cleaning', creator=self.user_employer_1)
        self.property_2 = Property.objects.create(name='studying', creator=self.user_employee_1)

        # create takk property instance (linking propety to task)
        self.user_property_1 = UserProperty.objects.create(user=self.user_employee_1, property=self.property_1)

    def set_user_profile(self, info: Dict[User, bool]) -> None:
        """
        Set the user profile by giving a dictionary of user object and profile boolean
        """

        for key, value in info.items():
            UserProfile.objects.create(user=key, is_employer=value)

    def test_list_retrieval(self):
        """
        Test GET request for the list retrieval of user property 
        """

        list_url = reverse('user_property-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)  # for non superusers, they cannot see the properties linked to themselves
        self.assertEqual(response.data['results'], [])

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.user_property_1.id)
    
    def test_detail_retrieval_by_id(self):
        """
        Test GET request to retrieve a user property by its id
        """

        user_property_id = self.user_property_1.pk
        detail_url = reverse('user_property-detail', kwargs={'pk': user_property_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['message'], "You do not have access to the requested information")

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], user_property_id)
        self.assertEqual(response.data['user'], self.user_employee_1.id)
        self.assertEqual(response.data['property'], self.user_property_1.id)

        self.client.logout()
        self.client.login(username = self.user_employee_2.username, password='passcode1234')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # A normal user cannot access details of properties likned to other users
        self.assertEqual(response.data['detail']['message'], "You do not have access to the requested information")

    def test_user_property_creation(self):
        """
        Test POST request to create a new user property object (linking one property tag to a user), only authenticated users with employee profile
        are allowed for such action. Moreover, you can only link a property to yourself
        """

        create_url = reverse('user_property-list')

        data = {
            'user': self.user_employee_1.id,
            'property': self.property_2.id
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated user but with profile of employer -> should fail
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user and with profile of employee -> should pass
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserProperty.objects.count(), 2)

        new_user_property = UserProperty.objects.latest('id')
        self.assertEqual(new_user_property.user, self.user_employee_1)
        self.assertEqual(new_user_property.property, self.property_2)

        # Authenticated user and with profile of employee, however the user is trying to set property for others -> should fail
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        data['user'] = self.user_employee_2.id
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('user' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['user']['message'], 
                         'You can only create linkage to a property for yourself.')
        
        data = {
            'property': self.property_2.id
        }
        response = self.client.post(create_url, data, format='json')
        # 'user' is required 
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_property_update(self):
        """
        Test PUT request to update a user property object, you are free to modify the linked property and your interest once you are
        authenticated but you are not allowed to relink your property tag to someone else
        """

        update_url = reverse('user_property-detail', kwargs={'pk': self.user_property_1.id})

        data = {
            'user': self.user_employee_1.id,
            'property': self.property_2.id,
            'is_interested': False
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated user but not the user him/herself -> should fail
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user and also the user him/herself  -> should pass
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user_property_1.refresh_from_db()
        self.assertEqual(self.user_property_1.property, self.property_2)
        self.assertEqual(self.user_property_1.is_interested, False)

        # Authenticated user and also the user him/herself, however the user wants to link the property to another user -> should fail
        data['user'] = self.user_employee_2.id
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('user' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['user']['message'], 
                         'You cannot link the property to someone else.')

        # Authenticated user and also the user him/herself, however the user wants to null the user/property/is_interested or 
        # modified to wrong types -> should fail
        # is_interested is True by default, it can be left null
        data['user'] = ' '
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)

        data = {}
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 2)

    def test_user_property_partial_update(self):
        """
        Test PUT request to update a user property object, you are free to modify the linked property and your interest once you are
        authenticated but you are not allowed to relink your property tag to someone else
        """

        update_url = reverse('user_property-detail', kwargs={'pk': self.user_property_1.id})

        data = {
            'is_interested': False
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated user but not the user him/herself -> should fail
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user and also the user him/herself  -> should pass
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user_property_1.refresh_from_db()
        self.assertEqual(self.user_property_1.is_interested, False)

        # Authenticated user and also the user him/herself, trying to partially null is_interested  -> should fail
        data['is_interested'] = None
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)

        # Authenticated user and also the user him/herself, however the user wants to link the property to another user -> should fail
        data = {
            'user':self.user_employee_2.id
        }
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('user' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['user']['message'], 
                         'You cannot link the property to someone else.')
        
    def test_task_property_deletion(self):
        """
        Test DELETE request to delete a user property by its id, only the user itself are allowed for such an action
        """

        delete_url = reverse('user_property-detail', kwargs={'pk': self.user_property_1.id})

        # Without login (unauthenticated users)-> should fail
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated user but not the user him/herself -> should fail
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user and also the user him/herself  -> should pass
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        



    