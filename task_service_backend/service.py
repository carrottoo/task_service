from .models import *
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class UserService: 
    """
    Implements serveral business logics related to User model
    """

    @staticmethod
    def authenticate_by_name(username: str, password: str) -> tuple:
        """
        Authenticate the user by username and password. It first checks if the username exists and gives error message when the 
        username is not found in the database. Then it authenticates the user with the given password. 
        """

        try:
            user = User.objects.get(username__iexact=username) 
        except User.DoesNotExist:
            return None, "Username does not exist"

        user = authenticate(username=username, password=password)
        if user is not None:
            # Authentication successful
            token, _ = Token.objects.get_or_create(user=user)
            return {
                "token": token.key,
                "user_id": user.id,
                "username": user.username,
                "email": user.email
            }, None
        else:
            # Authentication failed due to incorrect password
            return None, "Invalid credentials"
            
    @staticmethod
    def authenticate_by_email(email: str, password: str) -> tuple:
        """
        Authenticate the user by email address and password. It first checks if the email address exists and gives error message when
        the email address is not found in the database. Then it authenticates the user with the given password. 
        """

        try:
            user = User.objects.get(email=email) 
        except User.DoesNotExist:
            return None, "Email does not exist"

        user = authenticate(username=user.username, password=password)
        if user is not None:
            # Authentication successful
            token, _ = Token.objects.get_or_create(user=user)
            return {
                "token": token.key,
                "user_id": user.id,
                "username": user.username,
                "email": user.email
            }, None
        else:
            return None, "Invalid credentials"


class TaskService:
    """
    Implements several business logics related to the Task model

    We do not handle the existence check and authentication of a request / id related to a task or user model in the servce,
    we take valid task and user instance as input parameters
    """

    # def __init__(self, Task: type[models.Model]):
        # """
        # Initializes the task service

        # :param Task: Task model 
        # """

        # a set of task ids of all active tasks in the database
        # self.all_active_task_ids = set(Task.objects.all().filter(
        #     is_active=True).values_list('id', flat=True)) 
        
    @staticmethod
    def get_user_interested_properties(user: User) -> set:
        """
        Retrieves the properties that a user is interested in

        :param user: a user instance from User model 
        """

        interested_properties = set(user.user_properties.filter(
            is_interested=True).values_list('property_id', flat=True))
        return interested_properties
    
    @staticmethod
    def get_user_liked_tasks(user: User) -> set:
        """
        Retrieves the tasks that a user has liked 

        :param user: a user instance from User model 
        """

        liked_tasks = set(user.user_behaviors.filter(
            is_like=True).values_list('task_id', flat=True))
        return liked_tasks
    
    @staticmethod
    def get_user_completed_tasks(user: User) -> set:
        """
        Retrieves the tasks that a user has completed in history

        :param user: a user instance from User model 

        return: a set of task ids that the given user has completed 
        """
           
        completed_tasks = set(user.assigned_tasks.filter(
            status=Task.Status.DONE).values_list('id', flat=True))
        return completed_tasks
    
    @staticmethod
    def get_task_properties(task: Task) -> set:
        """
        Retrieves a task's properties

        :param task: a task instance from Task model 

        return: a set of property ids that the given task object has
        """

        linked_properties = set(task.task_properties.all().values_list(
            'property_id', flat=True))
        
        return linked_properties
    
    @staticmethod
    def calc_task_similarity(task_1: Task, task_2: Task) -> float:
        """
        Calculates task similarity based on the task description. We are interested in the topical similarity and use 
        the TF-IDF vectors and cosine similarity

        :param task_1: a task instance from Task model
        :param task_2: the other task instance from Task model

        return: the value of similarity between the two given tasks
        """

        description_1 = task_1.description
        description_2 = task_2.description

        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([description_1, description_2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        return similarity
    
    def get_interest_based_score(self, user: User, task: Task) -> float:
        """
        Calculates the score of a task based on the task's properties and user's interested properties. It uses the fraction of the task's
        properties that are of interest to the user

        :param user: an instance of the User model
        :param task: an instance of the Task model

        return: the value of the score of a task for the given user based on user's interests 
        """

        # set of property ids that the user is interested
        user_interested_properties = self.get_user_interested_properties(user)

        # set of property ids that the given task has 
        task_properties = self.get_task_properties(task)

        common_properties = task_properties.intersection(user_interested_properties)

        if task_properties:
            score = len(common_properties) / len(task_properties)
        else:
            score = 0
        
        return score
    
    def get_history_based_score(self, user: User, task: Task) -> float:
        """
        Calculates the score of a task based on the user's task history (completed tasks). It calculates the average similarity of the tasks to 
        all completed tasks of the user. If the task is very similar to the completed tasks, its average similarity should be high. 

        :param user: an instance of the User model
        :param task_id: the id of an instance of the Task model

        return: the value of the score of a task for the given user based on user's history of tasks he/she has completed
        """
        
        score_sum = 0

        # set of task ids that the user has completed
        completed_task_ids = self.get_user_completed_tasks(user)

        if not completed_task_ids:
            return 0
        
        # We calculate the average similarity of the tasks to all completed tasks
        # If the task is very similar to the completed tasks, this average similarity should be high. 
        for completed_task_id in completed_task_ids:
            completed_task = get_object_or_404(Task, pk=completed_task_id)
            score_sum += self.calc_task_similarity(task, completed_task)

        return score_sum / len(completed_task_ids)
    
    def get_behavior_based_score(self, user: User, task: Task) -> float:
        """
        Calculates the score of a task based on the user's behavior (what task he/she has liked). We use similar approach as the calculation of histroy
        based task score by calculating the average similarity of tasks to all liked tasks of the user. If the task is very similar to the liked tasks 
        of the user, its average similarity should be high.

        :param user: an instance of the User model
        :param task: an instance of the Task model

        return: the value of the score of a task for the given user based on user's behavior about what tasks he/she has liked
        """

        score_sum = 0
        liked_task_ids = self.get_user_liked_tasks(user)
        if not liked_task_ids:
            return 0
        
        for liked_task_id in liked_task_ids:
            liked_task = get_object_or_404(Task, pk=liked_task_id)
            score_sum += self.calc_task_similarity(task, liked_task)
        
        return score_sum / len(liked_task_ids)

    def get_user_task_rank(self, user: User) -> list:
        """
        Performs ranking to all the tasks for a user based on the user's interests, task completion history and behaviors

        :param user: an instance of the User model
        
        return: a list of ranked tasks for the given user
        """

        # all_active_task_ids = set(Task.objects.all().filter(
        #     is_active=True).values_list('id', flat=True)) 
        
        all_active_task = set(Task.objects.all().filter(is_active=True))

        interest_scores = {}
        history_scores = {}
        behavior_scores = {}
        final_scores = {}

        for task in all_active_task:
            # task = get_object_or_404(Task, pk=task_id)

            interest_scores[task] = self.get_interest_based_score(user, task)
            history_scores[task] = self.get_history_based_score(user, task)
            behavior_scores[task] = self.get_behavior_based_score(user, task)

        # Normalize the scores
        interest_score_max = max(interest_scores.values(), default=0)
        normalized_interest_scores = {
            task_id : score / interest_score_max if interest_score_max else 0 for task_id, score in interest_scores.items()
            }
        
        history_score_values = history_scores.values()
        history_score_mean = np.mean(list(history_score_values))
        history_score_std = np.std(list(history_score_values))
        normalized_history_score = {
            task_id: [(score - history_score_mean)] / history_score_std if history_score_std else 0 for task_id, score in history_scores.items() 
        }

        behavior_score_values = behavior_scores.values()
        behavior_score_mean = np.mean(list(behavior_score_values))
        behavior_score_std = np.std(list(behavior_score_values))
        normalized_behavior_score = {
            task_id: [(score - behavior_score_mean)] / behavior_score_std if behavior_score_std else 0 for task_id, score in history_scores.items() 
        }

        # sum up scores
        for task in all_active_task:
            final_scores[task] = normalized_interest_scores[task] + normalized_history_score[task] + normalized_behavior_score[task]
      
        # sort in descending order to get the rank
        task_ranking = sorted(final_scores, key=final_scores.get, reverse=True)

        return task_ranking

        



            


