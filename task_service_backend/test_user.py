from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status
from .models import *
from django.contrib.auth.models import User
from typing import List, Dict


class UserTests(APITestCase):
    
    def setUp(self) -> None:
        """
        Test setup, prepared several test users and tasks
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
    
    def set_user_profile(self, info: Dict[User, bool]) -> None:
        """
        Set the user profile by giving a dictionary of user object and profile boolean
        """

        for key, value in info.items():
            UserProfile.objects.create(user=key, is_employer=value)

    def test_list_retrieval(self):
        """
        Test GET request for retrieving list of users. For superusers, they can see all the users in the db. However, for normal users
        they can only see themselves
        """

        list_url = reverse('user-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])

        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.user_employer_1.id)
    
    def test_detail_retrieval_by_id(self):
        """
        Test GET request to retrieve a user's detail by its id. Except for superusers, users can only retrieve their own profile by id
        """

        detail_url = reverse('user-detail', kwargs={'pk': self.user_employer_1.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['message'], "You do not have access to this user's information")

        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user_employer_1.id)

        detail_url = reverse('user-detail', kwargs={'pk': self.user_employer_2.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['message'], "You do not have access to this user's information")

    def test_normal_user_creation(self):
        """
        """

        create_url = reverse('user-list')

        data = {
        }

        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 3)
        for field in ['username', 'email', 'password']:
            self.assertEqual(response.data['errors'][field]['message'], 'This field is required.')
        
        data = {
            'username': ' ', 
            'email': '',
            'password': ' '
            
        }

        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 3)
        for field in ['username', 'email', 'password']:
            self.assertEqual(response.data['errors'][field]['message'], 'This field may not be blank.')

        data = {
            'username': 'test name', 
            'email': 'email',
            'password': '12345'
        }

        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 3)
        self.assertEqual(response.data['errors']['username']['code'], 'invalid') # may contain only letters, numbers, and @/./+/-/_ characters
        self.assertEqual(response.data['errors']['email']['code'], 'invalid') 
        self.assertEqual(response.data['errors']['password']['code'], 'min_length') # at least 8 char long

        data['username'] = 'valid' * 31
        data['email'] = 'test@gmail.com'
        data['password'] = '123456789'

        response = self.client.post(create_url, data, format='json')
        # this updated data will trigger model level validators and error of violating default max length will be raised before it goes to the customized logics in validate() in serializer  -> total errors raised should be 1 
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertEqual(response.data['errors']['username']['code'], 'max_length') # default max length of username in Django User model is 150
        
        data['username'] = 'valid_name'
        response = self.client.post(create_url, data, format='json')
        # updated data will pass the model level validators and in customized validate() password doesn't follow the rules of containing at least one letter/  specail symbols, 2 errors will be raised
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 2)
        self.assertEqual(len(response.data['errors']['password']), 2)

        data['password'] = 'abc%$1234'
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertEqual(User.objects.count(), 5)
        newly_created_user = User.objects.latest('id')
        self.assertEqual(newly_created_user.username, 'valid_name')
        self.assertEqual(newly_created_user.is_staff, False)
        self.assertEqual(newly_created_user.is_superuser, False) #by default is_staff and is_superuser are set to false

        # You cannot create a user with existing username
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors']['username']['message'],'A user with that username already exists.') # raised from the validators

        data['username'] = 'another'
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors']['email']['message'],'A user with the provided email already exists.')

        data['email'] = 'another@gmail.com'
        data['is_staff'] = True
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors']['is_staff']['message'],'Creation of staff and superuser is not allowed.')

        data = {
            'first_name': 'Lissa',
            'last_name': 'Mark',
            'username': 'newbee',
            'email': 'newbee@gmail.com',
            'password': 'abcd1234$'
        }
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        newly_created_user = User.objects.latest('id')
        self.assertEqual(newly_created_user.first_name, 'Lissa')
        self.assertEqual(newly_created_user.last_name, 'Mark') 

    def test_user_update(self):
        """
        """
        put_url = reverse('user-detail', kwargs={'pk': self.user_employer_1.id})

        # You can have password in this data json but the password wouldn't be updated. To update password, use the update password endpoint
        data = {
            'username': 'test name', 
            'email': 'email',
            'password': 'abc',
            'first_name': 'some',
            'last_name': 'last'
        }

        response = self.client.put(put_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail']['code'], 'not_authenticated')
        
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.put(put_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['code'], 'permission_denied')

        self.client.logout()
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response = self.client.put(put_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 3)

        data['username'] = 'new_name'
        data['email'] = 'new@gmail.com'
        data['password'] = 'abc%1234'
        response = self.client.put(put_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user_employer_1.refresh_from_db()
        self.assertTrue(self.user_employer_1.check_password('abc%1234'))
        self.assertEqual(self.user_employer_1.username, 'new_name')
        self.assertEqual(self.user_employer_1.email, 'new@gmail.com')
        self.assertEqual(self.user_employer_1.first_name, 'some')
        self.assertEqual(self.user_employer_1.last_name, 'last')

    
    def  test_user_partial_update(self):
        patch_url = reverse('user-detail', kwargs={'pk': self.user_employer_1.id})

        data = {
            'email': 'new@outlook.com'
        }

        response = self.client.patch(patch_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail']['code'], 'not_authenticated')
        
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.patch(patch_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['code'], 'permission_denied')

        self.client.logout()
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')

        response = self.client.patch(patch_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user_employer_1.refresh_from_db()
        self.assertEqual(self.user_employer_1.email, 'new@outlook.com')

        response = self.client.patch(patch_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors']['email']['message'],'A user with the provided email already exists.')
    
    def test_user_deletion(self):
        """
        """
        delete_url = reverse('user-detail', kwargs={'pk': self.user_employer_1.id})

        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail']['code'], 'not_authenticated')

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail']['code'], 'permission_denied')

        self.client.logout()
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')

        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_authentication(self):
        
        url = reverse('user-signin')

        data = {
            'username': self.user_employer_1.username,
            'password': 'mysecretpassword'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data['password'] = 'wrong123%'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Incorrect password.')

        data = {
            'username': 'some one',
            'password': 'abcedf'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Username does not exist.')

        data = {
            'email': 'user@gmail.com',
            'password': 'mysecretpassword'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Email does not exist.')

        self.user_employer_1.email = 'user@gmail.com'
        self.user_employer_1.save()

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data['password'] = 'something1234%'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Incorrect password.')









        

   






