from quart_wtf import QuartForm
from wtforms import SubmitField, SelectField


class OptionForm(QuartForm):
    outcome = SelectField(u"Limit outcomes",
                          render_kw={"id": "outcome_select"},
                          choices=[("", "DEFAULT"), ("WON", "WON"), ("LOST", "LOST")])
    pos = SelectField(u"Side to sort results to (prioritize P1 if a value is given for both sides )",
                      render_kw={"id": "pos_select"},
                      choices=[("", "DEFAULT"), ("RIGHT", "RIGHT"), ("LEFT", "LEFT")])
    submit = SubmitField("Save")
