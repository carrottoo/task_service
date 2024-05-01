from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class CustomPasswordValidator:
    """
    Validate whether the password contains at least one letter, one number, and one special character.
    """

    def __call__(self, password, user=None):
       
        errors = {}

        if len(password) < 8:
            errors.append(_('The password must be at least 8 characters long.'))
      
        if not any(char.isdigit() for char in password):
            errors.append(_('The password must contain at least one digit'))

        if not any(char.isalpha() for char in password):
            errors.append(_('The password must contain at least one letter.'))

        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/`~' for char in password):
            errors.append(_('The password must contain at least one special character: !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        
        if errors:
            raise ValidationError(errors) 

    def get_help_text(self):
        return _(
            "Your password must contain at least one letter, one number, and one special character."
        )
