from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status
from .models import *
from django.contrib.auth.models import User
from typing import List, Dict

class TaskTests(APITestCase):
    """
    Using reverse() to generate url for TaskViewSet registered with the router 

    List and Create actions: reverse('task-list')

    Retrieve, Update (both patch and put requests) and Destory: reverse('task-detail', kwargs={'pk': task_id})
    """

    def setUp(self) -> None:
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
        for key, value in info.items():
            UserProfile.objects.create(user=key, is_employer=value)

    def test_retrieving_list_of_tasks(self):
        """
        Test GET request for retrieving list of tasks, no authentication is required
        """

        # list_url = f"{reverse('task-list')}?page=1&page_size=10"
        list_url = reverse('task-list')
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2) # in setup, we created two task instance samples
        self.assertEqual(len(response.data['results']), 2)
    
    def test_retrieving_task_by_id(self):
        """
        Test GET request for retrieving the details of a task by its id
        """
    
        task_id = self.test_task_1.pk
        detail_url = reverse('task-detail', kwargs={'pk': task_id})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the response data matches the task details
        self.assertEqual(response.data['id'], task_id)
        self.assertEqual(response.data['name'], self.test_task_1.name)
        self.assertEqual(response.data['description'], self.test_task_1.description)
        self.assertEqual(response.data['owner'], self.test_task_1.owner.id)

    def test_task_creation_auth_user_employer(self):
        """
        Test 'POST' request to create a task, only authenticated users with 'employer' profiles are allowed.
        Task owner will be set automatically as the task creator. 
        """

        create_url = reverse('task-list')

        # True -> log in successfully, do not use hased password 'self.user_employer_1.password' here 
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword') 
      
        data = {
            'name': 'test task',
            'description': 'a test task description'
        }
        response = self.client.post(create_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 3) # in setup, we have two task instances created

        newly_created_task = Task.objects.latest('id')
        self.assertEqual(newly_created_task.owner, self.user_employer_1)
        self.assertEqual(newly_created_task.status, Task.Status.NOT_STARTED)
        self.assertEqual(newly_created_task.is_active, True)
        self.assertEqual(newly_created_task.is_submitted, False)
        self.assertEqual(newly_created_task.is_approved, False)
        #TODO:  more default and auto-set fields
    
    def test_task_creation_auth_user_employee(self):
        """
        
        """

        create_url = reverse('task-list')

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        data = {
            'name': 'test task',
            'description': 'a test task description'
        }
        response = self.client.post(create_url, data, format='json')
        
        # only a employer can create a task
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
       
    def test_task_creation_unauthenticated(self):
        """
        """

        create_url = reverse('task-list')

        data = {
            'name': 'test task',
            'description': 'a test task description'
        }

        # creation of a new task is forbidden without login 
        response_1 = self.client.post(create_url, data, format='json')
        self.assertEqual(response_1.status_code, status.HTTP_403_FORBIDDEN)

        # creation of a new task is forbidden with failed login
        self.client.login(username=self.user_employer_1.username, password='wrongpassword') 
        response_2 = self.client.post(create_url, data, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_update_auth_owner(self):
        """

        """

        put_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'studying',
            'description': 'study physics for 2 hours and write a paper review',
            'output': 'a paper review'
        }

        # only task owner can update the task
        self.assertEqual(self.test_task_1.owner, self.user_employer_1)
        self.client.login(username=self.user_employer_1, password='mysecretpassword')
        response = self.client.put(put_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # refresh task_1 and see if the changes are made as we want
        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.name, 'studying')
        self.assertEqual(self.test_task_1.description, 'study physics for 2 hours and write a paper review')
        self.assertEqual(self.test_task_1.output, 'a paper review')

    def test_task_update_auth_non_owner(self):
        """
        """

        put_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'studying',
            'description': 'study physics for 2 hours and write a paper review',
            'output': 'a paper review'
        }

        # Authenticated users who are not the owner of the task are banned from updating the task
        self.assertNotEqual(self.test_task_1.owner, self.user_employer_2)
        self.client.login(username=self.user_employer_2, password='passcode1234')
        response = self.client.put(put_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_update_unauthenticated(self):
        """
        """

        put_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'studying',
            'description': 'study physics for 2 hours and write a paper review',
            'output': 'a paper review'
        }

        response_1 = self.client.post(put_url, data, format='json')
        self.assertEqual(response_1.status_code, status.HTTP_403_FORBIDDEN)

        self.client.login(username=self.user_employer_1.username, password='wrongpassword') 
        response_2 = self.client.post(put_url, data, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_patch_auth_user(self):
        pass

    def test_task_patch_unauthenticated(self):
        pass

    def test_task_deletion_auth_task_owner(self):
        pass

    def test_task_deletion_auth_non_owner(self):
        pass

    def test_task_deletion_unauthenticated(self):
        pass

    
    # Test authentication and permission for User viewset



    
    







    
    

