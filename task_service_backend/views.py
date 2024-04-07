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
    """
    Task viewset (task controller)

    GET request to retrieve a signle task by id or to retrieve all the tasks: anyone is allowed
    POST request to create a task: only a authenticated user with a profile of employer is allowed
    DELETE request to delete a task: only the task owner is allowed
    PUT and PATCH request to update a task's details: only a authenticated user is allowed, but they do not
    access to every field. Whether they can modify a field depends on their own role right and field's characteristics
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    service = TaskService(Task)
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action == 'create':
            permission_classes = [IsEmployer] 
        elif self.action == 'destroy':
            permission_classes = [IsTaskOwnerOrReadOnly]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        
        # iterate through all items in permission_classes
        return [permission() for permission in permission_classes]
    
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

        
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def recommendations(self, request):
        """
        Task recommendation 
        """
        user = request.user
        ranked_tasks = self.service.get_user_task_rank(user)
        page = self.paginator.paginate_queryset(ranked_tasks, request, view=self)

        if page is not None:
            # Serialize the page of tasks
            serializer = TaskSerializer(page, many=True, context={'request': request})
            # Return the paginated response
            return self.paginator.get_paginated_response(serializer.data)

        # Fallback response if pagination is not applicable
        serializer = TaskSerializer(ranked_tasks, many=True, context={'request': request})
        return Response(serializer.data)
    

class UserViewSet(viewsets.ModelViewSet):
    """
    User viewset (user controller)

    GET request to retrieve a signle user by id or to retrieve all the user: anyone is allowed
    POST request to create a user: anyone is allowed
    DELETE request to delete a task: only the user himself/herself is allowed
    PUT and PATCH request to update a task's details: only the user himself/herself is allowed
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    service = UserService()

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsUserOrReadOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'])
    def authenticate_by_username(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        result, error = self.service.authenticate_by_name(username, password)

        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def authenticate_by_email(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        result, error = self.service.authenticate_by_email(email, password)

        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_password(self, request):
        password = request.data.get('password')
        user_id = request.data.get('id', None)
        username = request.data.get('username', None)
        email = request.data.get('email', None)

        if not password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = None

        if user_id:
            user = User.objects.filter(id=user_id).first()
        elif username:
            user = User.objects.filter(username=username).first()
        elif email:
            user = User.objects.filter(email=email).first()

        if user is None:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Only the user itself can set up or update the password
        # if not request.user.is_staff and user != request.user:
        if user != request.user:
            return Response({"error": "You do not have permission to change this user's password."}, status=status.HTTP_403_FORBIDDEN)

        user.set_password(password)
        user.save()
        return Response({"status": "Password updated successfully."}, status=status.HTTP_200_OK)


class PropertyViewSet(viewsets.ModelViewSet):
    """
    Property viewset (property controller)

    GET request to retrieve a single property by id or all the properties: Anyone is allowed
    POST request to create a new property: only authenticated user is allowed
    DELETE request to delete a property: only the creater of this property is allowed

    PUT, PATCH are disabled for this viewset
    """

    queryset = Property.objects.all()
    serializer_class = PropertySerializer

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action == 'destroy':
            permission_classes = [IsCreatorOrReadOnly]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    def update(self, request, *args, **kwargs):
        """
        Override the update method to prevent updating an existing property
        """

        return Response({"error": "Property cannot be modified once created."}, status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        """
        Override the update method to prevent partcially updating an existing property
        """
         
        return Response({"error": "Property cannot be modified once created."}, status=status.HTTP_403_FORBIDDEN)
    

class TaskPropertyViewSet(viewsets.ModelViewSet):
    """
    Task property viewset (task property controller)

    Only task owners are allowed to access this viewset except for safe methods 
    """

    queryset = TaskProperty.objects.all()
    serializer_class = TaskPropertySerializer
    permission_classes = [IsPropertyLinkedTaskOwnerOrReadOnly]


class UserPropertyViewSet(viewsets.ModelViewSet):
    """
    UserProperty viewset (user property controller)

    Safe methods: anyone is allowed
    POST request: any authenticated user with a profile of employee
    PUT, PATCH, DELETE request: only the user himself/herself is allowed to modify and delete his/her own 
    property status
    """

    queryset = UserProperty.objects.all()
    serializer_class = UserPropertySerializer

    def get_permissions(self):
        """
        Instantiates and returns a list of permissions for the view 
        """

        if self.action == 'create':
            permission_classes = [IsEmployee]
        else:
            permission_classes = [IsUserOrReadOnly]
        return [permission() for permission in permission_classes]


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    UserProfile viewset (user profile controller)

    Only the user himself/herself is allowed to access this viewset except for safe methods
    PUT, PATCH are diabled for this viewset
    """

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsUserOrReadOnly]
    
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
            return Response({"error": "Cannot delete UserProfile while the User exists."},
                            status=status.HTTP_400_BAD_REQUEST)

        # If the User does not exist, proceed with deletion
        return super().destroy(request, *args, **kwargs)


class UserBehaviorViewSet(viewsets.ModelViewSet):
    """
    UserBehavior viewset (user behavior controller)

    Only the user him/herself is allowed to access this viewset except for safe methods
    """

    queryset = UserBehavior.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsUserOrReadOnly]
