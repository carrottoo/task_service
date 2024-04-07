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
        Test GET request for retrieving the details of a task by its id, no authentication is required
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
        Test POST request to create a task with an authenticated user who has a profile of employee -> should fail
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
        Test POST request with an unauthenticated user -> should fail
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
        Test PUT request to update task details (name, description, outout) with an authenticated user who is the owner 
        of the task. Only authenticated task owner is allowed to update task details
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'studying',
            'description': 'study physics for 2 hours and write a paper review',
            'output': 'a paper review'
        }

        # only task owner can update the task
        self.assertEqual(self.test_task_1.owner, self.user_employer_1)
        self.client.login(username=self.user_employer_1, password='mysecretpassword')
        response = self.client.put(update_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # refresh task_1 and see if the changes are made as we want
        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.name, 'studying')
        self.assertEqual(self.test_task_1.description, 'study physics for 2 hours and write a paper review')
        self.assertEqual(self.test_task_1.output, 'a paper review')

    def test_task_update_auth_non_owner(self):
        """
        Test PUT request to update task details (name, description, output) with an authenticated user whose is not the task 
        owner -> should fail
        """

        put_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'studying',
            'description': 'study physics for 2 hours and write a paper review',
            'output': 'a paper review'
        }

        # Authenticated users who are not the owner of the task are banned from updating the task
        self.assertNotEqual(self.test_task_1.owner, self.user_employer_2)
        self.client.login(username=self.user_employer_2.username, password='password1234')
        response = self.client.put(put_url, data, format='json')

        # For put, patch, we check if the person who is making the request are allowed to update the fields he / she is trying to
        # modify in validation, so respond 400 if fails 
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_task_update_unauthenticated(self):
        """
        Test PUT request to update task details (name, description, output) with an unauthenticated user -> should fail
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'studying',
            'description': 'study physics for 2 hours and write a paper review',
            'output': 'a paper review'
        }

        response_1 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_1.status_code, status.HTTP_403_FORBIDDEN)

        self.client.login(username=self.user_employer_1.username, password='wrongpassword') 
        response_2 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_patch_auth_owner(self):
        """
        Test Patch request to partially update task details with an authenticated user who is the task owner. Only authenticated
        task owner is allow to modify the task details
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})

        data = {
            'name': 'bedroom cleaning'
        }

        self.assertEqual(self.test_task_1.owner, self.user_employer_1)
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response = self.client.patch(update_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.name, 'bedroom cleaning')   
    
    def test_task_patch_non_owner(self):
        """
        Test PATCH request to partically update task details with an authenticated user who is not the task owner -> should fail
        """
        
        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'bedroom cleaning'
        }

        # Authenticated users who are not the owner of the task are banned from updating the task
        self.assertNotEqual(self.test_task_1.owner, self.user_employer_2)
        self.client.login(username=self.user_employer_2.username, password='password1234')
        response = self.client.patch(update_url, data, format='json')

        # We check if he/she edit certain fields in validtion based on their role,  so return bad request when it is failed 
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 

    def test_task_patch_unauthenticated(self):
        """
        Test PATCH request to partically update task details (name, description, output) with unauthenticated users -> should fail
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        data = {
            'name': 'bedroom cleaning'
        }

        response_1 = self.client.patch(update_url, data, format='json')
        self.assertEqual(response_1.status_code, status.HTTP_403_FORBIDDEN)

        self.client.login(username=self.user_employer_1.username, password='wrongpassword') 
        response_2 = self.client.patch(update_url, data, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_deletion_auth_task_owner(self):
        """
        Test DELETE request to delete a task with an authenticated user who is the task owner. Only authenticated task owner
        is allowed to delete the task
        """
        
        delete_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})

        self.assertEqual(self.test_task_1.owner, self.user_employer_1)
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')

        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)     

    def test_task_deletion_auth_non_owner(self):
        """
        Test DELETE request to delete a task with an authenticated user who is not the task owner -> should fail
        """

        delete_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})

        self.assertNotEqual(self.test_task_1.owner, self.user_employer_2)
        self.client.login(username=self.user_employer_2.username, password='password1234')

        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)   

    def test_task_deletion_unauthenticated(self):
        """
        Test DELETE request to delete a task with unauthenticated users -> should fail
        """

        delete_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  

    def test_task_deletion_auth_employee(self):
        """
        Test DELETE request to delete a task with authenticated user whose profile is employee -> should fail
        """

        delete_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  
    
    def test_task_self_assignation_auth_employee(self):
        """
        Test assigning a task to themselves by an authenticated user whose profile is employee. Only employees can access
        this fielf and an employee can only assign a task to themselves
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})

        data = {
            'assignee': self.user_employee_1.id
        }

        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.assignee, self.user_employee_1)
        self.assertEqual(self.test_task_1.status, Task.Status.IN_PROGRESS)

    def test_task_assignation_other_auth_employee(self):
        """
        Test assigning a task to someone else by an authenticated user whose profile is employee -> should fail
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')

        data = {
            'assignee': self.user_employee_2.id
        }

        response = self.client.patch(update_url, data, format='json')

        # We customized validation to check if a user can modify a protected field based on their role and how he/she is allowed
        # to modify. User cannot assign the tasks to someone else except for themselves
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_task_assignation_auth_employer(self):
        """
        Test assigning a task by an authenticated user whose profile is employer -> should fail
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')

        data = {
            'assignee': self.user_employer_1.id
        }

        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_task_assignation_unauthenticated(self):
        """
        Test assigning a task by an unauthenticated user -> should fail
        """
        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        data = {
            'assignee': self.user_employer_1.id
        }

        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_dismission(self):
        """
        Test PATCH request to reassign and unassign the task assignee, the task assignee can only unassign themselves 
        from a task and they are prevented to reassign the task to someone else
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')

        data = {
            'assignee': self.user_employee_1.id
        }
        
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.test_task_1.refresh_from_db()

        data_2 = {
            'assignee': self.user_employee_2.id
    
        }
        response_2 = self.client.patch(update_url, data_2, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_400_BAD_REQUEST)

        data_3 = {
            'assignee': None
        }
        response_3 = self.client.patch(update_url, data_3, format='json')
        self.assertEqual(response_3.status_code, status.HTTP_200_OK)

        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.assignee, None)
        self.assertEqual(self.test_task_1.status, Task.Status.NOT_STARTED)

    def test_task_submission(self):
        """
        Test PATCH request to submit a task, only the task assignee can submit a task and the status will be changed to 
        'In Review' automatically 
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})

        data = {
            'assignee': self.user_employee_1.id
        }

        data_submit = {
            'is_submitted': True
        }

        # Assign the task
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.test_task_1.refresh_from_db()

        # Log out
        self.client.logout()

        # Log in another account who is not the assignee for this task
        self.client.login(username=self.user_employee_2.username, password='passcode1234')
        response_2 = self.client.patch(update_url, data_submit, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_400_BAD_REQUEST)

        # Log out
        self.client.logout()

        # Log in with the account who is the assignee of the task
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')

        # Submit the task
        response_3 = self.client.patch(update_url, data_submit, format='json')
        self.assertEqual(response_3.status_code, status.HTTP_200_OK)
        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.assignee, self.user_employee_1)
        self.assertEqual(self.test_task_1.status, Task.Status.IN_REVIEW)

    def test_task_approval(self):
        """
        """

        update_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})

        data = {
            'assignee': self.user_employee_1.id
        }

        data_submit = {
            'is_submitted': True
        }

        data_approve = {
            'is_approved': True
        }

        # Assign the task
        self.client.login(username=self.user_employee_1.username, password='myuniquepassword')
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.assignee, self.user_employee_1)
        self.assertEqual(self.test_task_1.status, Task.Status.IN_PROGRESS)

        # Submit the task
        response_2 = self.client.patch(update_url, data_submit, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.assignee, self.user_employee_1)
        self.assertEqual(self.test_task_1.status, Task.Status.IN_REVIEW)

        # Approve the task
        response_3 = self.client.patch(update_url, data_approve, format='json')
        self.assertEqual(response_3.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.logout()
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response_4 = self.client.patch(update_url, data_approve, format='json')
        self.assertEqual(response_4.status_code, status.HTTP_200_OK)
        self.test_task_1.refresh_from_db()
        self.assertEqual(self.test_task_1.status, Task.Status.DONE)
        self.assertEqual(self.test_task_1.is_active, False)

        # Try to change the task details when task is inactive 
        data_update ={
            'name': 'trying to change name when task is inactive'
        }
        response_5 = self.client.patch(update_url, data_update, format='json')
        self.assertEqual(response_5.status_code, status.HTTP_400_BAD_REQUEST)
    
    







    
    

