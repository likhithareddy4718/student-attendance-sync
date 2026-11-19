# student-attendance-sync
```
student-attendance-sync
├─ config
│  ├─ database.py
│  ├─ notifications.py
│  ├─ scheduler.py
│  ├─ test_config.py
│  └─ __init__.py
├─ create_admin.py
├─ flask_app.py
├─ integrations
│  ├─ sync_orchestrator.py
│  └─ __init__.py
├─ main.py
├─ models
│  ├─ school.py
│  ├─ sync_log.py
│  ├─ sync_schedule.py
│  └─ __init__.py
├─ pages
│  ├─ login.py
│  ├─ review_matches.py
│  ├─ student_parent_matching.py
│  └─ __init__.py
├─ Procfile
├─ README.md
├─ requirements.txt
├─ reset_admin.py
├─ routes
│  ├─ admin_routes.py
│  ├─ auth_routes.py
│  ├─ connections.py
│  ├─ flask_auth.py
│  ├─ schools.py
│  ├─ school_routes.py
│  └─ __init__.py
├─ screens
│  └─ dashboard.py
├─ services
│  ├─ absence_detector.py
│  ├─ api_connection_service.py
│  ├─ auth_service.py
│  ├─ credential_storage_service.py
│  ├─ csv_parser.py
│  ├─ deduplication.py
│  ├─ match_saver.py
│  ├─ message_formatter.py
│  ├─ notification_sender.py
│  ├─ notification_validator.py
│  └─ student_parent_matcher.py
├─ sync
│  ├─ attendance_converter.py
│  ├─ attendance_fetcher.py
│  ├─ attendance_storage.py
│  ├─ attendance_sync.py
│  └─ __init__.py
├─ templates
│  ├─ dashboard.html
│  ├─ flask_login.html
│  ├─ review_matches.html
│  ├─ school_connections.html
│  ├─ student_parent_matching.html
│  ├─ sync_activity_log.html
│  └─ sync_error_details.html
├─ tests
│  ├─ run_all_tests.py
│  ├─ test_attendance_sync.py
│  ├─ test_data_conversion.py
│  ├─ test_notifications.py
│  ├─ test_notifications_db.py
│  ├─ test_sync_logs.py
│  └─ test_sync_logs_db.py
├─ test_notification_flow.py
├─ test_sync.py
├─ utils
│  ├─ crypto.py
│  └─ security.py
└─ workers
   ├─ attendance_sync.py
   ├─ notification_trigger.py
   └─ __init__.py

```