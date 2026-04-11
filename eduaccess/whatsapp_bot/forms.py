from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class EduAccessUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required — used to reset your password if you forget it.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class EduAccessAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True}))
