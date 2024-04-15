from rest_framework import permissions
from django.shortcuts import get_object_or_404
from .models import *
from django.contrib.auth.models import User


class IsEmployer(permissions.BasePermission):
    '''
    Custom permission to only allow user with 'employer' profile to create a task
    '''

    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if the user has a profile and is marked as an employer
        user_profile = getattr(request.user, 'profile', None)

        return user_profile and user_profile.is_employer



class IsEmployee(permissions.BasePermission):
    '''
    Custom permission to only allow user with 'employee' profile to create a user property
    '''

    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if the user has a profile and is marked as an employee
        user_profile = getattr(request.user, 'profile', None)
        return user_profile and not user_profile.is_employer
    

class IsTaskOwnerOrReadOnly(permissions.BasePermission):
    '''
    Custom permission to grant access to the owner of a task to update the taks details
    '''

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if getattr(request.user, 'profile', None) and not request.user.profile.is_employer:
            return False
        
        return obj.owner == request.user
    

class IsTaskAssigneeOrReadOnly(permissions.BasePermission):
    '''
    Custom permission to grant access to the assignee of a task to update some fields
    '''

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if obj.status == Task.Status.IN_REVIEW:
            return False
        
        if getattr(request.user, 'profile', None) and request.user.profile.is_employer:
            return False
        
        return obj.assignee == request.user
    

class IsUserOrReadOnly(permissions.BasePermission):
    '''
    Custom permission to only allow uses to edit their own profile
    '''

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        return obj.user == request.user
    

class IsCreatorOrReadOnly(permissions.BasePermission):
    '''
    Custom permission to only allow uses to edit their own profile
    '''

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False

        return obj.creator == request.user


class IsPropertyLinkedTaskOwnerOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False
        
        # mapped_task = get_object_or_404(Task, pk=obj.task)
        return obj.task.owner == request.user