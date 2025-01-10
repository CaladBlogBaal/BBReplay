from quart_wtf import QuartForm
from wtforms import SubmitField
from flask_wtf.file import FileRequired, FileAllowed, MultipleFileField


class UploadForm(QuartForm):
    files = MultipleFileField("Upload File", validators=[FileRequired("Empty file was passed."),
                                                         FileAllowed(["dat"], ".dat files only!")])
    submit = SubmitField("Submit")
