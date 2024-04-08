from rest_framework import serializers
from task_service_backend.models import *
from django.contrib.auth.models import User


class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = ['id', 'name', 'description', 'output', 'status', 'assignee', 
                  'owner',  'is_submitted', 'is_approved', 'is_active', 
                  'created_on', 'updated_on', 'submitted_on', 'approved_on']
        
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

            for field in ['name', 'description', 'output']:
                if field in data:
                    if not user_profile.is_employer:
                        raise serializers.ValidationError({field: "Your do not have the permission to change this field"})   
                    elif task.owner != user:
                        raise serializers.ValidationError({field: "Only the owner of the task can change this field"}) 
            

            if 'assignee' in data:
                new_assignee = data.get('assignee')

                # if the task being updated already has an assignee
                if task and task.assignee:
                    if task.assignee != user:
                        raise serializers.ValidationError({"assignee": "Only the current task assignee can change this field "})
                    elif new_assignee is not None:
                        raise serializers.ValidationError({"assignee": "You can only unassign yourself from the task."})
                
                else:
                    if user_profile.is_employer:
                        raise serializers.ValidationError({"assignee": "You do not have the permission to change the assignee"})
                    else:
                        if new_assignee is not None and new_assignee != user:
                            raise serializers.ValidationError({"assignee": "You can only assign the task to yourself"}) 

        
            if 'is_submitted' in data:
                if user_profile.is_employer:
                    raise serializers.ValidationError({"is_submitted": "You don't have the permission to change this field"})
                else:
                    if task.status == Task.Status.NOT_STARTED:
                        raise serializers.ValidationError({"is_submitted": "Cannot submit before the task is started"})
                    elif task.assignee != user:
                        raise serializers.ValidationError({"is_submitted": "Only the task assignee can change this field"})
                    
            if 'is_approved' in data:
                if not user_profile.is_employer:
                    raise serializers.ValidationError({"is_approved": "You don't have the permission to change this field"})
                else:
                    if task.status == Task.Status.NOT_STARTED or task.status == Task.Status.IN_PROGRESS:
                        raise serializers.ValidationError({"is_approved": "Cannot approve before the task is submitted"})
                    elif task.owner!= user:
                        raise serializers.ValidationError({"is_submitted": "Only the task owner can change this field"})
                    
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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        #  username is unique and required in the default model
        extra_kwargs = {
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


class UserPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProperty
        fields = ['id', 'is_interested', 'user', 'property']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'is_employer']

class UserBehaviorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBehavior
        fields = ['id', 'user', 'task', 'is_like']
