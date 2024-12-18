from flask import Blueprint, flash, render_template, request

from app.controllers import file_controller
from app.controllers.file_controller import CorruptedFile

from app.forms.upload import UploadForm
from app.utils.helpers import clear_cache_on_success

bp = Blueprint("page", __name__, url_prefix="/")


@bp.route("/stats")
async def stats():
    return render_template("stats.html")


@bp.route("/")
async def index():
    if request.args:
        # need to figure this out
        pass
    return render_template("index.html")


@bp.route("/upload", methods=["GET", "POST"])
async def upload():
    form = UploadForm()
    if form.validate_on_submit():
        for file in form.files.data:
            file = file
            data = file.read()
            try:
                replay = await file_controller.upload_file("1.dat", data)

                if replay:
                    clear_cache_on_success(replay, 201)
                    flash("Replay successfully uploaded!", "success")
                else:
                    flash("Replay already exists", "failure")

            except CorruptedFile:
                flash(f"Invalid replay data: data is too small/big or corrupted.")

    return render_template("upload.html", form=form)
