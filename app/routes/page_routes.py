from flask import Blueprint, flash, render_template, request, jsonify

from app.controllers import file_controller

from app.forms.upload import UploadForm
from app.utils.helpers import clear_cache_on_success

bp = Blueprint("page", __name__, url_prefix="/")


@bp.route("/")
async def index():
    if request.args:
        # need to figure this out
        pass
    return render_template("index.html")


@bp.route("/upload", methods=["POST"])
async def upload():
    data = request.data
    response, status_code = await file_controller.upload_file("1.dat", data)
    clear_cache_on_success(response, status_code)
    if status_code == 404:
        return jsonify({"message": "could not create replay, already exists"}), status_code

    return response, status_code


@bp.route("/upload-files", methods=["GET", "POST"])
async def upload_form():
    form = UploadForm()
    if form.validate_on_submit():
        for file in form.files.data:
            file = file
            data = file.read()
            response, status_code = await file_controller.upload_file("1.dat", data)
            clear_cache_on_success(response, status_code)
            if status_code != 404:
                flash("Replay successfully uploaded!", "success")
            else:
                flash("Replay already exists", "failure")

    return render_template("upload.html", form=form)
