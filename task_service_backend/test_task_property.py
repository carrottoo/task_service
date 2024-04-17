from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status
from .models import *
from django.contrib.auth.models import User
from typing import List, Dict


class TaskPropertyTests(APITestCase):

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
        self.test_task_3 = Task.objects.create(name='cooking', description='coke me some riisipiirakka', owner=self.user_employer_1)


        # create property instance
        self.property_1 = Property.objects.create(name='cleaning', creator=self.user_employer_1)
        self.property_2 = Property.objects.create(name='studying', creator=self.user_employee_2)

        # create takk property instance (linking propety to task)
        self.task_property_1 = TaskProperty.objects.create(task=self.test_task_1, property=self.property_1)

    def set_user_profile(self, info: Dict[User, bool]) -> None:
        """
        Set the user profile by giving a dictionary of user object and profile boolean
        """

        for key, value in info.items():
            UserProfile.objects.create(user=key, is_employer=value)

    def test_list_retrieval(self):
        """
        Test GET request for the list retrieval of task properties
        """

        list_url = reverse('task_property-list')
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_retrieval_by_id(self):
        """
        Test GET request to retrieve a task property by its id
        """

        task_property_id = self.task_property_1.pk
        detail_url = reverse('task_property-detail', kwargs={'pk': task_property_id})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], task_property_id)
        self.assertEqual(response.data['task'], self.test_task_1.id)
        self.assertEqual(response.data['property'], self.property_1.id)

    def test_task_property_creation(self):
        """
        Test POST request to create a new task property object (linking one property tag to a task), only the task owner is allowed for such
        action
        """

        create_url = reverse('task_property-list')

        data = {
            'task': self.test_task_2.id,
            'property': self.property_2.id
        }

        # Without login (unauthenticated users)-> should fail
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated user but not the task owner -> should fail
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_count'], 1)
        self.assertTrue('task' in response.data['errors'].keys())
        self.assertEqual(response.data['errors']['task']['message'], 
                         'You can only link properties to your own tasks.')

        self.client.logout

        # Authenticated user and is the task owner -> should pass
        self.client.login(username=self.user_employer_2.username, password='password1234')
        response = self.client.post(create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TaskProperty.objects.count(), 2)

        new_task_property = TaskProperty.objects.latest('id')
        self.assertEqual(new_task_property.task, self.test_task_2)
        self.assertEqual(new_task_property.property, self.property_2)

    def test_task_property_update(self):
        """
        Test PUT request to update the task property object (relink the property to another task or vice versa) by id, only the task owner is allowed to relink the task 
        he/she owns to another property, furthermore, task owners are only allowed to relink a property to another task he/she also owns. You can only manage objects and 
        their relationships when you have the ownerships of those objects
        """

        update_url = reverse('task_property-detail', kwargs={'pk': self.task_property_1.id})

        data = {
            'task': self.test_task_1.id,
            'property': self.property_2.id
        }

        # Unauthenticated users -> should fail
        response = self.client.put(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated users but not the owner of the task, trying to link the task to another property -> should fail
        self.client.login(username=self.user_employer_2.username, password='password1234')
        response_2 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated users and also the owner of the task, trying to link the task to another property -> should pass
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response_3 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_3.status_code, status.HTTP_200_OK)
        
        self.task_property_1.refresh_from_db()
        self.assertEqual(self.task_property_1.property, self.property_2)

        # Authenticated users trying to link the property to another task he/she also owns -> should pass
        data['task'] = self.test_task_3.id
        response_4 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_4.status_code, status.HTTP_200_OK)

        self.task_property_1.refresh_from_db()
        self.assertEqual(self.task_property_1.task, self.test_task_3)

        # Authenticated users trying to link the property to another task he/she doesn't own -> should fail
        data['task'] = self.test_task_2.id
        response_5 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_5.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response_5.data['error_count'], 1)
        self.assertTrue('task' in response_5.data['errors'].keys())
        self.assertEqual(response_5.data['errors']['task']['message'], 
                         'You can only relink properties to tasks you own.')
        
        # Authenticated users trying to null the the task / property
        data['task'] = None
        data['property'] = None
        response_6 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_6.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response_6.data['error_count'], 2)
        self.assertTrue('task' in response_6.data['errors'].keys())
        self.assertTrue('property' in response_6.data['errors'].keys())
        self.assertEqual(response_6.data['errors']['task']['message'], 
                         'This field may not be null.')
        self.assertEqual(response_6.data['errors']['property']['message'], 
                         'This field may not be null.')

    def test_task_property_partial_update(self):
        """
        Test PATCH request to partially update the task property object (relink the property to another task or vice versa) by its id
        """

        update_url = reverse('task_property-detail', kwargs={'pk': self.task_property_1.id})

        data = {
            'property': self.property_2.id
        }

        data_2 ={
            'task': self.test_task_3.id
        }

        # Unauthenticated users -> should fail
        response = self.client.patch(update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated users but not the owner of the task, trying to link the task to another property -> should fail
        self.client.login(username=self.user_employer_2.username, password='password1234')
        response_2 = self.client.patch(update_url, data, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated users and also the owner of the task, trying to link the task to another property -> should pass
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response_3 = self.client.patch(update_url, data, format='json')
        self.assertEqual(response_3.status_code, status.HTTP_200_OK)

        self.task_property_1.refresh_from_db()
        self.assertEqual(self.task_property_1.property, self.property_2)

        # Authenticated users trying to link the property to another task he/she also owns -> should pass
        response_4 = self.client.patch(update_url, data_2, format='json')
        self.assertEqual(response_4.status_code, status.HTTP_200_OK)
        
        self.task_property_1.refresh_from_db()
        self.assertEqual(self.task_property_1.task, self.test_task_3)

        # Authenticated users trying to link the property to another task he/she doesn't own -> should fail
        data_2['task'] = self.test_task_2.id
        response_5 = self.client.patch(update_url, data_2, format='json')
        self.assertEqual(response_5.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response_5.data['error_count'], 1)
        self.assertTrue('task' in response_5.data['errors'].keys())
        self.assertEqual(response_5.data['errors']['task']['message'], 
                         'You can only relink properties to tasks you own.')
        
        # Authenticated users trying to null the the task / property
        data_2['task'] = None
        data['property'] = None
        response_6 = self.client.put(update_url, data, format='json')
        self.assertEqual(response_6.status_code, status.HTTP_400_BAD_REQUEST)
        response_7 = self.client.patch(update_url, data_2, format='json')
        self.assertEqual(response_7.status_code, status.HTTP_400_BAD_REQUEST)

    def test_task_property_deletion(self):
        """
        Test DELETE request to delete a task property by its id, only the task owners are allowed for such an action
        """

        delete_url = reverse('task-detail', kwargs={'pk': self.test_task_1.id})
        
        # Unauthenticated users -> should fail
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticated users but not the owner of task -> should fail
        self.client.login(username=self.user_employer_2.username, password='password1234')
        response_2 = self.client.delete(delete_url)
        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()

        # Authenticated users and also the owner of the task -> should pass
        self.client.login(username=self.user_employer_1.username, password='mysecretpassword')
        response_3 = self.client.delete(delete_url)
        self.assertEqual(response_3.status_code, status.HTTP_204_NO_CONTENT)



