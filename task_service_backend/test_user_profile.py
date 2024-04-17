from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status
from .models import *
from django.contrib.auth.models import User
from typing import List, Dict


class UserProfileTests(APITestCase):

    def setUp(self) -> None:
        """
        Test setup
        """

        # create users 
        self.user_1 = User.objects.create_user(username='user_1', password='mysecretpassword')
        self.user_2 = User.objects.create_user(username='user_2', password='password1234')

        # create profile
        self.profile_1 = UserProfile.objects.create(user=self.user_1, is_employer=True)


    def test_list_retrieval(self):
        """
        Test GET request for the list retrieval of user profiles
        """

        list_url = reverse('user_profile-list')
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_detail_retrieval_by_id(self):
        """
        Test GET request to retrieve a user's profile by its id
        """
        id = self.profile_1.id
        detail_url = reverse('user_profile-detail', kwargs={'pk': id})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], id)
        self.assertEqual(response.data['user'], self.user_1.id)
        self.assertEqual(response.data['is_employer'], True)

    def test_user_profile_creation(self):
        """
        Test POST request to create a new user profile, you can only create a profile for yourself and you can only have exactly one 
        profile
        """

        create_url = reverse('user_profile-list')

        data = {
            'user': self.user_2.id
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated user trying to set the profile for another user -> should fail
        self.client.login(username=self.user_1.username, password='mysecretpassword')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('user' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['user']['message'], 
                         'You can only set profile for yourself.')

        self.client.logout()

        # Authenticated user setting profile for him/herself -> should pass
        self.client.login(username=self.user_2.username, password='password1234')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserProfile.objects.count(), 2)

        new_user_profile= UserProfile.objects.latest('id')
        self.assertEqual(new_user_profile.user, self.user_2)
        self.assertEqual(new_user_profile.is_employer, False)

        # Authenticated user setting profile twice -> should fail
        # One to one relationship between user and user profile, uniqueness is ensured on the database level 
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('user' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['user']['message'], 
                         'user profile with this user already exists.')
    
    def test_user_profile_update(self):
        """
        Test PUT request to partically update a user profile, this endpoint has been disabled to maintain the data consistency in the database
        """

        update_url = reverse('user_profile-detail', kwargs={'pk': self.profile_1.id})

        data = {
            'user': self.user_1.id,
            'profile': False
        }

        self.client.login(username=self.user_1.username, password='mysecretpassword')
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'UserProfile cannot be modified once set.')

    def test_user_profile_partial_update(self):
        """
        Test PATCH request to partically update a user profile, this endpoint has been disabled to maintain the data consistency in the database
        """

        update_url = reverse('user_profile-detail', kwargs={'pk': self.profile_1.id})

        data = {
            'profile': False
        }

        self.client.login(username=self.user_1.username, password='mysecretpassword')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'UserProfile cannot be modified once set.')


    def test_user_profile_deletion(self):
        """
        Test DELETE request to delete a user profile by its id, only the user itself can delete his/her profile
        """

        delete_url = reverse('user_profile-detail', kwargs={'pk': self.profile_1.id})

        # Authenticated user but not deleting his/her own profile -> should fail
        self.client.login(username=self.user_2.username, password='password1234')
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user deleting his/her own profile but the user still exists -> should fail
        self.client.login(username=self.user_1.username, password='mysecretpassword')
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Cannot delete profile while the user exists.')

        # Deleting the user_1 will also delete its profile 
        self.user_1.delete()

        # Try again -> should not find the user profile 
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        






    








        



        

