from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField


class OptionForm(FlaskForm):
    outcome = SelectField(u"Limit outcomes",
                          render_kw={"id": "outcome_select"},
                          choices=[("", "DEFAULT"), ("WON", "WON"), ("LOST", "LOST")])
    pos = SelectField(u"Side to sort results to",
                      render_kw={"id": "pos_select"},
                      choices=[("", "DEFAULT"), ("RIGHT", "RIGHT"), ("LEFT", "LEFT")])
    submit = SubmitField("Save")
