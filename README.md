## Description
A task assignment system featured with personalized task recommendations

### Models
1. **Task**

    Meta fields: id (primary key), (task) name, (task) description, (task) output, (task) status, assignee (foreign key)

    Mapping: one task is mapped to only one user while one user can be mapped to multiple tasks.


2. **User**

    Meta fields: id, username, password, email, first_name, last_name, is_staff, is_active, date_joined (from the default django User model), 

3. **Property** 

    describing what category the task can fall in 

    Meta fields: id, name

4. **Task property** 
 
    mapping tasks to different to properties
    
    Meta fields: id, task_id, property_id

5. **User property**

    mapping users to different properties

    Meta fields: id, user_id, property_id, is_interested



### Assignment 
Newly created tasks will be put to task pool and will assign weights representing importance based on task characteristics and each user's preference


### Development 

#### To install all dependecies 
```
poetry install
```

#### To run locally in dev mode
```bash
python manage.py runserver
```

#### To run tests
```bash
python manage.py test
```

**To see the test running details, run**
```bash
python manage.py test --verbosity=2
```