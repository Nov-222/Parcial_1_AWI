from flask import jsonify, redirect, render_template, request, url_for

from .errors import AuthError


def _next_url():
    if request.query_string:
        return f"{request.path}?{request.query_string.decode()}"
    return request.path


def handle_auth_error(err: AuthError):
    """Every auth failure becomes JSON for /api, HTML for the Jinja pages."""
    if request.path.startswith("/api/"):
        return (
            jsonify(
                {
                    "success": False,
                    "error": err.status_code,
                    "code": err.error["code"],
                    "message": err.error["description"],
                }
            ),
            err.status_code,
        )

    if err.status_code == 401:
        return redirect(url_for("auth.login_form", next=_next_url()))

    return render_template("errors/403.html", message=err.error["description"]), 403
