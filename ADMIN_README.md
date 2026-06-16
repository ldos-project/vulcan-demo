# Admin Dashboard Setup

## Access

- **Admin Dashboard URL**: `http://your-domain:4000/admin/login`
- **Default Password**: `changeme123`

## Changing the Admin Password

Set the `ADMIN_PASSWORD` environment variable:

```bash
export ADMIN_PASSWORD="your-secure-password"
python3 app.py
```

Or set it in production deployment configuration.

## Features

### Edit Submissions
- Click the "Edit" button next to any submission
- Modify: submitter name, group name, heuristic name, description, and algorithm type
- Changes are saved immediately to the database

### Delete Submissions
- **Single delete**: Click the "Delete" button next to a submission
- **Bulk delete**: 
  1. Check the boxes next to submissions you want to delete
  2. Click "Delete Selected (N)" button at the top
  3. Confirm the deletion

### Security Notes
- Admin password is stored in environment variable (not in code)
- Session-based authentication using Flask sessions
- Admin endpoints are protected with `@require_admin` decorator
- Unauthorized API requests return 401 error

## Session Configuration

The app uses a secret key for session encryption. In production, set:

```bash
export SECRET_KEY="your-long-random-secret-key"
```

Generate a secure key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## API Endpoints

### Admin Authentication
- `GET /admin/login` - Show login page
- `POST /admin/login` - Submit password
- `POST /api/admin/logout` - Logout

### Admin Operations (requires authentication)
- `GET /admin` - Admin dashboard
- `PUT /api/admin/submission/<id>` - Update submission
- `DELETE /api/admin/submissions` - Delete multiple submissions (POST body: `{"ids": [1, 2, 3]}`)

## Logout

Click the "Logout" button in the top-right corner of the admin dashboard.
