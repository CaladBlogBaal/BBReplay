from flask_wtf import FlaskForm
from wtforms import SubmitField
from flask_wtf.file import FileRequired, FileAllowed, MultipleFileField


class UploadForm(FlaskForm):
    files = MultipleFileField("Upload File", validators=[FileRequired("Empty file was passed."),
                                                         FileAllowed(["dat"], ".dat files only!")])
    submit = SubmitField("Submit")
