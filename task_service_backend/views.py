from task_service_backend.models import *
from django.contrib.auth.models import User
from task_service_backend.serializers import *
from django.contrib.auth import authenticate
from .service import *
from rest_framework import generics, status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from .permissions import *
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db import IntegrityError
from django.db import DatabaseError
from django.db.models import Q

"""
    Data fields' non-nulless, data type are checked (error raises and return 'bad request' etc if there is an error) before data 
    goes to serializer --> in serializer we validation several customized restrictions (error raises if there is any) -> check in-
    tegrity in data (e.g. duplicated records if uniqueness is required) when saving the instance after performing the action in view 
    (raise error if there is any)
"""


class CustomPageNumberPagination(PageNumberPagination):
    """
    Customized default pagination

    By default, display 15 items per page. However user can override the page size via a query paramter. When user
    wants to override the default page size, a maximum size limit of 100 will apply 
    """
  
    page_size = 15 
    page_size_query_param = 'page_size' 
    max_page_size = 100 


class TaskViewSet(viewsets.ModelViewSet):

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    service = TaskService()
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action == 'create':
            permission_classes = [IsEmployer] 
        elif self.action == 'destroy':
            permission_classes = [IsTaskOwnerOrReadOnly|IsSuperuser]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action == 'recommend':
            permission_classes =[IsEmployee]
        else:
            permission_classes = [IsAuthenticated]
        
        # iterate through all items in permission_classes
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        A superuser can access all tasks, a employee can access all active non-assigned tasks and tasks assigned to themselves, a employer can access tasks he has created 
        """
        user_profile = getattr(request.user, 'profile', None)

        if request.user.is_superuser:
            queryset = Task.objects.all()
        elif user_profile is None:
            queryset = [] # display empty set if the user doesn't have set a profile or not logged in
        elif user_profile.is_employer:
            queryset = Task.objects.filter(owner=request.user.id)
        else:
            queryset = Task.objects.filter(
                Q(assignee=None) | Q(assignee=request.user.id)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        A superuser can retrieve any task by id, a employee can retrieve any task that is assigned to him/her or an unasssigned active task, a employer can 
        retrieve any task that is owned by him/her
        """

        instance = self.get_object()
        user_profile = getattr(request.user, 'profile', None)
   
        if not request.user.is_superuser:
            if user_profile is None:
                raise PermissionDenied("You do not have access to the requested task's information")
            elif user_profile.is_employer and  instance.owner != request.user:
                raise PermissionDenied("You do not have access to the requested task's information")
            elif instance.assignee and instance.assignee != request.user:
                raise PermissionDenied("You do not have access to the requested task's information")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """
        Automatically set the task owner as the user who created the task
        """

        serializer.save(
            owner = self.request.user
        )

    # def perform_update(self, serializer):
    #     serializer.save()
    #     Custom logic after saving (e.g., sending notifications, audit logging)

        
    @action(detail=False, methods=['get'], url_path='recommend', url_name='recommend')
    def recommend(self, request):
        """
        Task recommendation 
        """

        user = request.user
        ranked_tasks = self.service.get_user_task_rank(user)
        page = self.paginator.paginate_queryset(ranked_tasks, request, view=self)

        if page is not None:
            # Serialize the page of tasks
            serializer = TaskSimpleSerializer(page, many=True, context={'request': request})
            # Return the paginated response
            return self.paginator.get_paginated_response(serializer.data)

        # Fallback response if pagination is not applicable
        serializer = TaskSimpleSerializer(ranked_tasks, many=True, context={'request': request})
        return Response(serializer.data)
    

class UserViewSet(viewsets.ModelViewSet): 
    queryset = User.objects.all()
    serializer_class = UserSerializer
    service = UserService()
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action in ['update', 'partial_update']:
            # PUT and PATCH request to update a user's details: only the user himself/herself is allowed
            permission_classes = [IsUserHimOrHerself]
        elif self.action == 'destroy':
            permission_classes = [IsUserHimOrHerself|IsSuperuser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        Superusers can see all the users in the system but for others they should get a filtered result (
        they can only see themselves if they are a valid user in the system)
        """

        if request.user.is_superuser:
            # Superuser gets all users
            queryset = User.objects.all()
        else:
            # Non-superusers see only their own profile
            queryset = User.objects.filter(id=request.user.id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        If a user is not the superuser, then he/she can only retrieve his/her own profile
        """
        
        instance = self.get_object()
        if not request.user.is_superuser and request.user != instance:
            raise PermissionDenied("You do not have access to this user's information")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    # superuser can be created through "python manage.py createsuperuser" 

    @action(detail=False, methods=['post'], url_path= 'singin', url_name ='signin')
    def signin(self, request):
        username = request.data.get('username', None)
        email = request.data.get('email', None)
        password = request.data.get('password', None)

        if username:
            result, error = self.service.authenticate_by_name(username, password)   
        
        if email:
            result, error = self.service.authenticate_by_email(email, password)

        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
    

class PropertyViewSet(viewsets.ModelViewSet):

    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action == 'destroy':
            permission_classes = [IsCreatorOrReadOnly|IsSuperuser]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        A superuser can see all the properties in DB, however a normal user can only see the propeties he/she has created
        """
        if request.user.is_superuser:
            queryset = Property.objects.all()
        else:
            queryset = Property.objects.filter(creator=request.user.id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        For non superuser, he/she can only retrieve a property created by him/herself by id 
        """

        instance = self.get_object()
        if not request.user.is_superuser and request.user != instance.creator:
            raise PermissionDenied("You do not have access to this property's information")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """
        Automatically set the property creator as the user who created the property
        """

        serializer.save(
            creator = self.request.user
        )

    def update(self, request, *args, **kwargs):
        """
        Override the update method to prevent updating an existing property
        """

        return Response({"error": "Property cannot be modified once created"}, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        """
        Override the update method to prevent partcially updating an existing property
        """
         
        return Response({"error": "Property cannot be modified once created"}, status=status.HTTP_403_FORBIDDEN)
    

class TaskPropertyViewSet(viewsets.ModelViewSet):

    queryset = TaskProperty.objects.all()
    serializer_class = TaskPropertySerializer
    paginator = CustomPageNumberPagination()
    
    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action == 'create':
            permission_classes = [IsEmployer]
        elif self.action == 'destroy':
            permission_classes = [IsPropertyLinkedTaskOwnerOrReadOnly|IsSuperuser]
        else:
            permission_classes = [IsPropertyLinkedTaskOwnerOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        A superuser can see all the properties in DB, however a normal user can only see the propeties of the task he/she has owned
        """
        if request.user.is_superuser:
            queryset = TaskProperty.objects.all()
        else:
            queryset = TaskProperty.objects.filter(task__owner=request.user.id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        For non superuser, he/she can only retrieve a task property of the task owned by him/her
        """

        instance = self.get_object()
        if not request.user.is_superuser and request.user != instance.task.owner:
            raise PermissionDenied("You do not have access to the requested information")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserPropertyViewSet(viewsets.ModelViewSet):

    queryset = UserProperty.objects.all()
    serializer_class = UserPropertySerializer
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action == 'create':
            permission_classes = [IsEmployee]
        elif self.action == 'destroy':
            permission_classes = [IsUserOrReadOnly|IsSuperuser]
        else:
            permission_classes = [IsUserOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        A superuser can see all the user properties in DB, however a normal user can only see the propeties he/she have linked to themselves
        """
        if request.user.is_superuser:
            queryset = UserProperty.objects.all()
        else:
            queryset = UserProperty.objects.filter(user__id=request.user.id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        For non superuser, he/she can only retrieve a property tag that has been linked to him/herself
        """

        instance = self.get_object()
        if not request.user.is_superuser and request.user != instance.user:
            raise PermissionDenied("You do not have access to the requested information")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action == 'destroy':
            permission_classes = [IsUserOrReadOnly|IsSuperuser]
        else:
            permission_classes = [IsUserOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        A superuser can see all the user profiles in DB, however a normal user can only see his/her own profile
        """
        if request.user.is_superuser:
            queryset = UserProfile.objects.all()
        else:
            queryset = UserProfile.objects.filter(user__id=request.user.id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        For non superuser, he/she can only retrieve his/her own profile by id
        """

        instance = self.get_object()
        if not request.user.is_superuser and request.user != instance.user:
            raise PermissionDenied("You do not have access to other user's profile")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    
    def update(self, request, *args, **kwargs):
        """
        Override the update method to prevent updating a user profile
        """

        return Response({"error": "UserProfile cannot be modified once set."}, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        """
        Override the update method to prevent partcially updating a user profile
        """
         
        return Response({"error": "UserProfile cannot be modified once set."}, status=status.HTTP_403_FORBIDDEN)
    
    def destroy(self, request, *args, **kwargs):
        """
        Override the destroy method to prevent deletion of the UserProfile if the associated User exists.
        """

        user_profile = self.get_object()
        user = user_profile.user

        if User.objects.filter(id=user.id).exists():
            # Prevent deletion of UserProfile if User exists
            return Response({"error": "Cannot delete profile while the user exists."},
                            status=status.HTTP_400_BAD_REQUEST)

        # If the User does not exist, proceed with deletion
        return super().destroy(request, *args, **kwargs)


class UserBehaviorViewSet(viewsets.ModelViewSet):

    queryset = UserBehavior.objects.all()
    serializer_class = UserBehaviorSerializer
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action == 'create':
            permission_classes = [IsEmployee]
        elif self.action == 'destroy':
            permission_classes = [IsUserOrReadOnly|IsSuperuser]
        else:
            permission_classes = [IsUserOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """
        A superuser can see all the user behaviors in DB, however normal users can only see their own behaviors
        """
        if request.user.is_superuser:
            queryset = UserBehavior.objects.all()
        else:
            queryset = UserBehavior.objects.filter(user__id=request.user.id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        For normal users, they can only retrieve their own behaviors by id 
        """

        instance = self.get_object()
        if not request.user.is_superuser and request.user != instance.user:
            raise PermissionDenied("You do not have access to the requested information")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    