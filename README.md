
# celery-sqlalchemy-kit 
  
## About  
This kit enables you to store periodic celery tasks in an SQLAlchemy compatible database. 
The schedules can be set as **crontabs** or **time-intervals**. 
Scheduled tasks in the database can be **set active or inactive** to control whether they should run.   
This kit also allows your celery workers to **run asynchronous tasks**.   
  
This package is under active development and used in production at cap-on.   

**NOTE**: This package was developed and tested with a PostgreSQL backend. 
Theoretically, any other SQLAlchemy compatible database, that supports JSON type, can be used. 
But this has not been tested yet.
  
  
## Getting Started  
### Requirements  
- python >= 3.10  
- celery >= 5.2.7, < 6 
- sqlalchemy >= 1.4.46, < 3
- psycopg2 >= 2.9.3 / mysql-connector / other connector depending on database (psycopg2>=2.9.10 needed for Python 3.13)
- redis >= 4.5.1, < 8 / other broker/backend for celery

Earlier versions should work as well, they just have not been tested yet.

### Compatibility matrix

These combinations have been verified:

| Python                | Celery | SQLAlchemy | Redis | Psycopg2          | Status                |
|:----------------------|:-------|:-----------|:------|:------------------|:----------------------|
| 3.10                  | 5.2.7  | 1.4.46     | 4.5.1 | 2.9.3             | ✅ successfully tested |
| 3.10                  | 5.5.3  | 2.0.44     | 7.0.1 | 2.9.3             | ✅ successfully tested |
| 3.11.14, <br/>3.12.12 | 5.5.3  | 2.0.44     | 7.0.1 | 2.9.3,<br/>2.9.10 | ✅ successfully tested |
| 3.13.19               | 5.5.3  | 2.0.44     | 7.0.1 | 2.9.10            | ✅ successfully tested |
  
### Installation  
You can install this package from PyPi:  
  
```bash  
pip install celery-sqlalchemy-kit
```  

## SQL Table 'routines'
Using this package will create a table that contains your scheduled celery tasks. 
The structure of table 'routines' is as follows:

| Column           | Type                        | Nullable  | 
|------------------|-----------------------------|-----------|
| id               | uuid                        | not null  |
| name             | character varying(50)       | not null  |
| task             | character varying(50)       | not null  |
| schedule         | json                        | not null  |
| last_run_at      | timestamp without time zone |           |
| total_run_count  | integer                     |           |
| active           | boolean                     | not null  |
| kwargs           | json                        |           |
| options          | json                        |           |

  
## Usage & Configuration 
To demonstrate how to use the features of this package, there are examples in the 'example'-directory. 
These are being explained in the following.  
  
### 1. Configuration
  
First you need to instantiate celery, as you would normally do. 
Have a look at the [celery documentation](https://docs.celeryq.dev/en/stable/#).  
If you define your tasks in another file, include the path to their file via `include`.  
```python  
celery = Celery(  
    "celery", 
    include=["celery-sqlalchemy-kit.example.custom_tasks"], 
    backend=your_result_backend, 
    broker=your_broker_url
)  
```  

To use this package you have to configure some variables of your celery instance like so:  
  
```python
celery.conf.update(  
    {  
        "scheduler_db_uri": scheduler_db_uri,  
        "scheduler_max_interval": scheduler_max_interval,  
        "scheduler_sync_every": scheduler_sync_every,  
        "celery_max_retry": celery_max_retry,  
        "celery_retry_delay": celery_retry_delay,  
        "create_table": True,  
  },  
)
```

| variable                 | explanation                                                                                                                              | default	         |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| `scheduler_db_uri`       | db uri used by scheduler (must be synchronous)                                                                                           | /                |
| `scheduler_max_interval` | maximum time to sleep between re-checking the schedule                                                                                   | 300 (seconds)    |
| `scheduler_sync_every`   | How often to sync the schedule                                                                                                           | 3 * 60 (seconds) |
| `celery_max_retry`       | How often to retry a task when it fails                                                                                                  | 3                |
| `celery_retry_delay`     | How long to wait before next retry of failed task is started                                                                             | 300 (seconds)    |
| `create_table`           | If set `True`, table 'routines' for scheduled tasks is created automatically with sqlalchemy. If you wish to use alembic, set to `False` | True             |

Make sure to use the correct `scheduler_db_uri` of your project allowing the `RoutineScheduler` to create a table named `routines` and save your scheduled tasks in it.
These variables are also available as environment variables in upper case (except for `create_table`).

### 2.1. Create scheduled tasks
To create tasks that run after your desired schedule, you have to inherit from class `SyncTask` like so:

```python  
class CeleryTestTask(SyncTask):  
    name = "celery test"  
    schedule = 15   
  
    def run(self, *args, **kwargs):  
        # do stuff
```  

The task that you want to be executed, has to be defined as the `run`method from your task class. Make sure to define a name for your task and set the variable `schedule`. For the schedule you have to options:

| schedule type   | explanation                                    | example	                                                | syntax in db	                                |
|-----------------|------------------------------------------------|---------------------------------------------------------|----------------------------------------------|
| time interval   | run your task every ... seconds                | schedule = 15                                           | {"timedelta": 15}                            |
| crontab         | define schedule as crontab, by creating a dict | schedule = {"minute": 0, "hour": 9, "day_of_month": 15} | {"minute": 0, "hour": 9, "day_of_month": 15} |

Now when you start your program, the scheduled tasks are added to your database in `routines` table and executed by a celery worker within the schedule you defined.

**NOTE**: In your database the schedules of tasks are saved as type JSON. 
Make sure to keep the correct syntax.


### 2.2. Create asynchronous scheduled tasks

This works the same way as with synchronous tasks, except that your custom tasks has to inherit from class `AsnycTask` and the task logic has to be implemented within the async method `execute`:

```python  
class CeleryTestTask(AsyncTask):  
    name = "celery test"  
    schedule = 15   
  
    async def execute(self, *args, **kwargs):  
        # do stuff

```  

## 3. Change schedule / (in-) activate tasks

If you wish to change the schedule of a task, just update the corresponding db entry. 
The next time the `RoutineScheduler` synchronizes, it will acknowledge the new schedule. 
Same thing with activating or inactivating tasks. 
To activate a task, set column `active` in your db to `t` (True). 
To inactivate a task, set column `active` in your db to `f` (False).  
A task that is inactive will not be executed as long as you change it to active again.


## 4. Source of truth for schedule
- New scheduled task in code, that is not in db: new db entry is created automatically
- Scheduled task in code as well as db: schedule in db is used to run task
- Tasks that are deleted in code will be removed from db after redeploy
- Inactive tasks in db will not be executed


## 5. Run celery worker and beat
To start celery worker:
```bash
$ celery -A celery_instance worker --loglevel=INFO
```

To start celery beat:
```bash
$ celery -A celery_instance beat --loglevel=INFO --scheduler=scheduler.RoutineScheduler
```

`celery_instance` is the file containing your celery instance. 
Use the correct path of your project.