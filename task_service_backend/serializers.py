from rest_framework import serializers
from .password import CustomPasswordValidator
from task_service_backend.models import *
from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import gettext as _
from collections import defaultdict


"""
    Data fields' non-nulless, data type are checked (error raises and return 'bad request' etc if there is an error) before data 
    goes to serializer --> in serializer we validation several customized restrictions (error raises if there is any) -> check in-
    tegrity in data (e.g. duplicated records if uniqueness is required) when saving the instance after performing the action in view 
    (raise error if there is any)

    Field restriction -> validation in serialziers
    Endpoint restriction (whether you can access it or not) -> view + permissions
"""


class TaskSerializer(serializers.ModelSerializer):

    owner_name = serializers.SerializerMethodField(source=None)  # Add source=None
    assignee_name = serializers.SerializerMethodField(source=None)  # Add source=None


    class Meta:
        model = Task
        fields = ['id', 'name', 'description', 'output', 'status', 'assignee',
                  'owner', 'is_submitted', 'is_approved', 'is_active', 
                  'created_on', 'updated_on', 'submitted_on', 'approved_on', 'owner_name', 'assignee_name']
        
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False, 'max_length': 80},
            'description': {'required': True, 'allow_blank': False, 'max_length': 500},
            'status': {'read_only': True},
            'owner': {'read_only': True},
            'is_active': {'read_only': True},
            'created_on': {'read_only': True},
            'updated_on': {'read_only': True},
            'submitted_on': {'read_only': True},
            'approved_on': {'read_only': True}
        }
    
    def get_owner_name(self, obj):
        return obj.owner.username if obj.owner else None  # Handle potential null owner

    def get_assignee_name(self, obj):
        return obj.assignee.username if obj.assignee else None  # Handle potential null assignee

    def validate(self, data):
        '''
        Customized field validation

        Users with employee profile can assign to an active and unassigned task
        Task assignee can only unassign themselves from the task
        Only task assignee can submit a task to review
        Only task owner can update a task detail and approve a task (after it has been put to review)
        '''

        request = self.context.get('request')

        # Check if the request is a PUT or PATCH request
        if request and request.method in ['PUT', 'PATCH']:
            user = self.context['request'].user
            user_profile = UserProfile.objects.get(user=user)
            task = self.instance
            errors = {}

            # ensure that read-only fields cannot be modified by the users
            for field in ['status', 'owner', 'is_active', 'created_on', 'updated_on', 'submitted_on', 'approved_on']:
                if field in data:
                    errors[field] = "Modification to this field is not allowed."

            for field in ['name', 'description', 'output']:
                if field in data:
                    if not user_profile.is_employer:
                        errors[field] = "Your do not have the permission to change this field."
                    elif task.owner != user:
                        errors[field] = "Only the owner of the task can change this field."
            
            if 'assignee' in data:
                new_assignee = data.get('assignee')

                # if the task being updated already has an assignee
                if task and task.assignee:
                    if task.assignee != user:
                        errors["assignee"] = "Only the current task assignee can change this field."
                    elif new_assignee is not None:
                        errors["assignee"] = "You can only unassign yourself from the task."
                
                else:
                    if user_profile.is_employer:
                        errors["assignee"] = "You do not have the permission to change the assignee."
                    else:
                        if new_assignee is not None and new_assignee != user:
                            errors["assignee"] = "You can only assign the task to yourself."
        
            if 'is_submitted' in data:
                if user_profile.is_employer:
                    errors["is_submitted"] = "You don't have the permission to change this field."
                else:
                    if task.status == Task.Status.NOT_STARTED:
                        errors["is_submitted"] = "Cannot submit before the task is started."
                    elif task.assignee != user:
                        errors["is_submitted"] = "Only the task assignee can change this field."
                    
            if 'is_approved' in data:
                if not user_profile.is_employer:
                    errors["is_approved"] = "You don't have the permission to change this field."
                else:
                    if task.status == Task.Status.NOT_STARTED or task.status == Task.Status.IN_PROGRESS:
                        errors["is_approved"] = "Cannot approve before the task is submitted."
                    elif task.owner!= user:
                        errors["is_approved"] = "Only the task owner can change this field."

            if errors:
                raise serializers.ValidationError(errors) 
            
        return data

    def update(self, instance, validated_data):
        '''
        Automated updates of read-only fields, forbid users from updating an inactive task
        '''

        if not instance.is_active:
            raise serializers.ValidationError("You cannot update an inactive task")
        
        for attr, value in validated_data.items():
            if attr == 'assignee':
                if value is None:
                    instance.status = Task.Status.NOT_STARTED
                else:
                    instance.status = Task.Status.IN_PROGRESS
                instance.assignee = value
        
            elif attr == 'is_submitted' and value:
                instance.status = Task.Status.IN_REVIEW
                instance.submitted_on = timezone.now()

            elif attr == 'is_approved' and value:
                instance.status = Task.Status.DONE
                instance.approved_on = timezone.now()
                instance.is_active = False

            else:
                setattr(instance, attr, value)

        instance.save()
        return instance


class TaskSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'name']  # Include only the ID and name fields


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'is_staff', 'is_superuser', 'is_active', 'last_login', 'date_joined']
        #  username is unique and required in the default model
        extra_kwargs = {
            'username': {'required': True, 'allow_blank': False},
            'password': {'write_only': True,'required': True, 'min_length': 8},
            'email': {'required': True, 'allow_blank': False}
        }
        
 
    def create(self, request):
        '''
        Create a user with password
        '''

        user = User.objects.create_user(
            username=request['username'],
            email=request['email'],
            first_name=request.get('first_name', ''),
            last_name=request.get('last_name', '')
        )
        user.set_password(request['password'])
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """
        """
    
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        
        instance.save()
        return instance

    def validate(self, data):
        """
        Customized validation logics for default django user model

        Required fields by django default: username, email, password
        Length limit by django default: username (150 char), 
        """

        request = self.context.get('request')
        errors = defaultdict(list)

        if request and request.method in ['POST', 'PUT', 'PATCH']:

            email = data.get('email')
            if email and User.objects.filter(email=email).exists():
                errors['email'].append('A user with the provided email already exists.')

            user_password = data.get('password', None)
       
            if user_password:

                if not any(char.isdigit() for char in user_password):
                    errors['password'].append('The password must contain at least one digit')
                

                if not any(char.isalpha() for char in user_password):
                    errors['password'].append('The password must contain at least one letter.')

                if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/`~' for char in user_password):
                    errors['password'].append('The password must contain at least one special character: !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
            
            # superuser can be created through "python manage.py createsuperuser"  but not through the api endpoint
            for field in ['is_staff', 'is_superuser']:
                if field in data:
                    if request.method == 'POST':
                        errors[field].append('Creation of staff and superuser is not allowed.')
                    else:
                        errors[field].append('Modification of the state of staff and superuser is not allowed')
        

                
        if errors:
            raise ValidationError(errors) 
        
        return data

        
    
class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'name', 'creator']

        extra_kwargs = {
        'creator': {'read_only': True}
        }


class TaskPropertySerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskProperty
        fields = ['id', 'task', 'property']
    
    def validate(self, data):
        """
        Validation logics in the creation, updates and partial updates of the task property object

        An authorized user trying to link a task to a property tag -> he/she must own the task 
        An authorized user trying to relink a task he/she owns to another property tag -> fine
        An authorized user trying to relink a property tag to another task, he/she must also own the task to which he/she 
        wants to link the property tag to 
        """

        request = self.context.get('request')

        if request and request.method in ['POST', 'PUT', 'PATCH']:
            request_user = self.context['request'].user
            task_instance = self.instance.task if self.instance else None
            new_task = data.get('task', task_instance)

            if task_instance and new_task != task_instance:
                if not new_task.owner == request_user:
                    raise serializers.ValidationError({"task": "You can only relink properties to tasks you own."})
            
            if new_task and not task_instance:
                if data['task'].owner != request_user:
                    raise serializers.ValidationError({"task": "You can only link properties to your own tasks."})

            return data


class UserPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProperty
        fields = ['id', 'is_interested', 'user', 'property']

    def validate(self, data):
        """
        Validation logics against the creation, update and partial update of the user property object

        As an authorized user, you can only link a property to yourself, you cannot created linkage for others
        As an authorized user, you cannot relink a property to someone else  
        """

        request = self.context.get('request')

        if request:
            if request.method == 'POST':
                request_user = self.context['request'].user

                if data['user'] and data['user'] != request_user:
                    raise serializers.ValidationError({"user": "You can only create linkage to a property for yourself."})
            
            elif request.method in ['PUT', 'PATCH']:
                new_user = data.get('user', None)
                if new_user and new_user!= self.instance.user:
                    raise serializers.ValidationError({"user": "You cannot link the property to someone else."})
                
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'is_employer']
    
    def validate(self, data):
        """
        Validation logics for the creation of a user profile

        As an authorized user, you can only have one profile that is prohibited from modifying once created. 
        """

        request = self.context.get('request')

        if request and request.method == 'POST':
            request_user = self.context['request'].user
            if data['user'] and data['user'] != request_user:
                raise serializers.ValidationError({"user": "You can only set profile for yourself."})

        return data
                

class UserBehaviorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBehavior
        fields = ['id', 'user', 'task', 'is_like']
    
    def validate(self, data):
        """
        Validation logics for the creation of a user bahavior

        As an authorized user, you can only have one profile that is prohibited from modifying once created. 
        """

        request = self.context.get('request')
        errors = {}
        original_user = self.instance.user if self.instance else None
        new_user = data.get('user', original_user)

        if request and request.method == 'POST':
            request_user = self.context['request'].user

            if new_user and new_user!= request_user:
                errors["user"] = "You can only set a behavior for yourself."
           
        elif request.method in ['PUT', 'PATCH']:
            if new_user and new_user!= self.instance.user:
                errors["user"] = "You cannot remap your behavior to someone else."
        
        if errors:
            raise serializers.ValidationError(errors)

        return data
