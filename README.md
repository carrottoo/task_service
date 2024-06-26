## Description
A task assignment system featured with personalized task recommendations


### Assignment 
Newly created tasks will be put to task pool and will assign weights representing importance based on task characteristics and each user's preference


### Development 

### Deployment
On Google Cloud 

#### To install all dependecies 
```
poetry install
```

#### To run locally in dev mode
```bash
export DJANGO_DEBUG=true
python manage.py runserver
```

#### To generate the static files
```bash
python manage.py collectstatic
```

#### To run tests
```bash
python manage.py test
```
**To see the test running details, run**
```bash
python manage.py test --verbosity=2
```