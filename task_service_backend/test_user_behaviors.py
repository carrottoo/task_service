from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status
from .models import *
from django.contrib.auth.models import User
from typing import List, Dict


class UserBehaviorsTests(APITestCase):

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

        # create task instance samples
        self.test_task_1 = Task.objects.create(name='cleaning', description='clean the bedroom', owner=self.user_employer_1)
        self.test_task_2 = Task.objects.create(name='coding', description='code me a ray tracer', owner=self.user_employer_2)

        self.behavior_1 = UserBehavior.objects.create(user=self.user_employee_1, task=self.test_task_1, is_like=True)


    def set_user_profile(self, info: Dict[User, bool]) -> None:
        """
        Set the user profile by giving a dictionary of user object and profile boolean
        """

        for key, value in info.items():
            UserProfile.objects.create(user=key, is_employer=value)

    def test_list_retrieval(self):
        """
        Test GET request for the list retrieval of user profiles
        """

        list_url = reverse('user_behavior-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)  # for non superusers, they cannot see the properties linked to themselves
        self.assertEqual(response.data['results'], [])

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.behavior_1.id)
    
    def test_detail_retrieval_by_id(self):
        """
        Test GET request to retrieve a user's behavior by its id
        """
        
        detail_url = reverse('user_behavior-detail', kwargs={'pk': self.behavior_1.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['message'], "You do not have access to the requested information")

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.behavior_1.id)
        self.assertEqual(response.data['user'], self.user_employee_1.id)
        self.assertEqual(response.data['task'], self.test_task_1.id)
        self.assertEqual(response.data['is_like'], True)

        self.client.logout()
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['message'], "You do not have access to the requested information")
    
    def test_user_behavior_creation(self):
        """
        Test POST request to create a new user behavior, you can only create behaviors for yourself and you can only have one 
        behavior per task
        """

        create_url = reverse('user_behavior-list')

        data = {
            'user': self.user_employee_2.id,
            'task': self.test_task_2.id,
            'is_like': True
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated user but with profile of employer -> should fail 
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated employee but trying to set behavior for others -> should fail
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('user' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['user']['message'], 
                         'You can only set a behavior for yourself.')

        # If setting behavior for him/herself -> should pass
        data['user'] = self.user_employee_1.id
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserBehavior.objects.count(), 2)

        new_behavior= UserBehavior.objects.latest('id')
        self.assertEqual(new_behavior.user, self.user_employee_1)
        self.assertEqual(new_behavior.task, self.test_task_2)
        self.assertEqual(new_behavior.is_like, True)

        # Trying to set multiple behaviors for one task -> should fail
        data['is_like'] = False
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertEqual(response.data['errors']['non_field_errors']['message'], 
                         'The fields user, task must make a unique set.')

        data = {}
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 2)
        for field in ['user', 'task']:
            self.assertEqual(response.data['errors'][field]['message'],
                             "This field is required.")

        data = {
            'user': self.user_employee_2.id,
        }
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertEqual(response.data['errors']['task']['message'],
                             "This field is required.")
        
        data = {
            'user': self.user_employee_2.id,
            'task': 'wrong data type'
        }
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertEqual(response.data['errors']['task']['message'],
                             "Incorrect type. Expected pk value, received str.")
    
    def test_user_behavior_update(self):
        """
        Test PUT request to update an existing user behavior, you are only allowed to modify behaviors for yourself
        """

        update_url = reverse('user_behavior-detail', kwargs={'pk': self.behavior_1.id})

        data = {
            'user': self.user_employee_1.id,
            'task': self.test_task_1.id,
            'is_like': False
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


        # Authenticated user but not the user him/herself -> should fail
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user and also the user him/herself  -> should pass
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.behavior_1.refresh_from_db()
        self.assertEqual(self.behavior_1.task, self.test_task_1)
        self.assertEqual(self.behavior_1.is_like, False)

        # Remapped your behavior to another task, as long as the new targetted task hasn't been mapped before     
        data['task'] = self.test_task_2.id
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Create a new behavior, mapping it to same user and task 1
        UserBehavior.objects.create(user=self.user_employee_1, task=self.test_task_1, is_like=True)
        self.assertEqual(UserBehavior.objects.count(), 2)

        # Now if we try to modify behavior 1 back to task 1 -> should fail 
        data['task'] = self.test_task_1.id
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors']['non_field_errors']['message'], 
                         'The fields user, task must make a unique set.')

        # Authenticated user and also the user him/herself, however the user wants to link the property to another user -> should fail
        data['user'] = self.user_employee_2.id
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('user' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['user']['message'], 
                         'You cannot remap your behavior to someone else.')
        
        data = {
            'user': self.user_employee_1.id,
            'task': None,
        }
        response = self.client.put(update_url, data, format='json') 
        self.assertEqual(response.data['error_count'], 1)
        self.assertEqual(response.data['errors']['task']['message'], 
                         'This field may not be null.')

    def test_user_behavior_partial_update(self):
        """
        Test PUT request to update an existing user behavior, you are only allowed to modify behaviors for yourself
        """

        update_url = reverse('user_behavior-detail', kwargs={'pk': self.behavior_1.id})

        data = {
            'is_like': False
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated user but not the user him/herself -> should fail
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user and also the user him/herself  -> should pass
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.behavior_1.refresh_from_db()
        self.assertEqual(self.behavior_1.is_like, False)

        # Authenticated user and also the user him/herself, trying to partially null is_like  -> should fail
        data['is_like'] = None
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
                         'You cannot remap your behavior to someone else.')
    
    def test_user_behavior_deletion(self):
        """
        Test DELETE request to delete an existing user behavior, you are only allowed to delete your own behaviors
        """

        delete_url = reverse('user_behavior-detail', kwargs={'pk': self.behavior_1.id})

        # Without login (unauthenticated users)-> should fail
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated user but not the user him/herself -> should fail
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated user and also the user him/herself  -> should pass
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Cascade deletion
        self.user_employee_1.delete()
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    









        






