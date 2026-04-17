from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.test_task.test_ping")
def test_ping() -> str:
    return "pong"
