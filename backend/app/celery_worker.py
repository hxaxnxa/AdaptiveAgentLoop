from celery import Celery

# 1. Initialize Celery
# 'app.main' is the path to our FastAPI app (for context, though not strictly needed here)
# 'broker' tells Celery to use Redis on localhost port 6379
celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0" # Also use Redis to store task results
)

# 2. Point Celery to our tasks file (which we will create next)
celery_app.autodiscover_tasks(["app.tasks"])

# 3. Optional: Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)