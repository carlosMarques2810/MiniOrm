import pytest
from classes.fields import Field

def test_fields_success():
    integerField = Field(int, default=1)
    charField = Field(str, null=True)
    assert integerField.validate(10) == 10
    assert integerField.validate() == 1
    assert charField.validate("Carlos") == "Carlos"
    assert charField.validate() is None

def test_fields_failed():
    integerField = Field(int)
    charField = Field(str)
    
    with pytest.raises(ValueError):
        integerField.validate()
        charField.validate()