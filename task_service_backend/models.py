from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


default_name_length = 100

class Task(models.Model):
    """
    One of the main tables, stores all relevant information of a task object

    Primary key: default id

    Foreign key: assignee (user id, whose linked profile must be a 'employee'), many to one relationship between user and task. One user can 
    take many tasks while one task can only have one assignee (user). You can access all the tasks assigned to a user through
    user.assigned_tasks.all()

    When the assigned user is deleted or deactivated, assignee will be null and the task will be reassigned (in the case that
    the task is not completed)

    Foreign key: owner (user id, whose linked profile must be a 'employee'), many to one relationship between user and task. One user can own many tasks
    while one task can only have one owner. When the owner is deleted or deactivated, the tasks he/she has owned 
    will also be deleted 
    """

    name = models.CharField(max_length=default_name_length)
    description = models.TextField(blank=True)
    output = models.TextField(default="")

    class Status(models.TextChoices):
        NOT_STARTED = "Not started"
        IN_PROGRESS = "In progress"
        IN_REVIEW = "In review"
        DONE = "Done"

    status = models.CharField(max_length=15,
                              choices=Status.choices,
                              default=Status.NOT_STARTED)
   
    assignee = models.ForeignKey(User, default = None, null=True, on_delete=models.SET_NULL, related_name='assigned_tasks')

    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='owned_tasks')

    is_submitted = models.BooleanField(default=False)

    is_approved = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    # deletion_date = models.DateTimeField(default=None, null=True, blank=True)
    submitted_on = models.DateTimeField(default = None, null=True, blank=True)
    approved_on = models.DateTimeField(default = None, null=True, blank=True)

    # def soft_delete(self):
    #     self.deletion_date = timezone.now()
    #     self.save()

    def __str__(self):
        return self.name


# TODO maybe user can deactivate their account and reactivate, another option beyond deleting the account
    
# class User(AbstractUser):
#     pass    


class Property(models.Model):
    """
    A table to store the tag / property (such as cleaning, cooking, coding ...) of a task 
    """

    name = models.CharField(max_length=default_name_length)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_properties')

    def __str__(self):
        return self.name


class TaskProperty(models.Model):
    """
    A table to link the tag/property to the task object, it will have default id as primary key.

    Foreign key: property id, many to many relationship between task and property. One task can have 
    many properties and one property can be linked to many tasks. It is stored as 'property_id' in the table and stores
    the id (primary key) of Property table.
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name = 'task_properties')  # null=False is the default
    property = models.ForeignKey(Property, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.task.name} - {self.property.name}'


class UserProperty(models.Model):
    """
    A table to link the tag/property to the user object, it will have the default id as primary key.

    Foreign key: property id, many to many relationship between user and property. One user can have 
    many properties and one property can be linked to many users. It is stored as 'property_id' in the table and stores
    the id (primary key) of Property table.

    Foreign key: user id
    """

    is_interested = models.BooleanField(default=True) 

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name = 'user_properties')
    property = models.ForeignKey(Property, on_delete=models.CASCADE)

    def __str__(self):
        if self.is_interested:
            return f"{self.user.username} - {self.property.name} - 'interested'"
        else:
            return f"{self.user.username} - {self.property.name} - 'uninterested'"
    

class UserProfile(models.Model):
    """
    One to one relationship between user and profile, user must decide whether he/she wants to be
    a employer who can only publish tasks or a employee who can only take tasks to complete. Users
    aren't allowed to take dual profiles
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_employer = models.BooleanField(default=False)

    def __str__(self):
        if self.is_employer:
            return f"{self.user.username} - 'employer'"
        else:
            return f"{self.user.username} - 'employee'"


class UserBehavior(models.Model):
    """
    To track the users' behaviors for one task, they can like and dislike a task 
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_behaviors')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_behaviors')
    is_like = models.BooleanField()

    class Meta:
        # Ensures that each user-task pair is unique
        unique_together = ('user', 'task')  

    def __str__(self):
        return f"{self.user.username} - {'liked' if self.is_like else 'disliked'} - {self.task.name}"