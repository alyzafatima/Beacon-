from django import forms
from .models import StatusPage, Monitor


from django import forms
from django.contrib.auth.models import User
from .models import Profile


class AccountForm(forms.ModelForm):

    timezone = forms.CharField(
        max_length=100
    )

    class Meta:

        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
            "timezone",
        ]

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user")

        super().__init__(*args, **kwargs)

        self.user = user

        self.fields["timezone"].initial = (
            user.profile.timezone
        )

    def save(self, commit=True):

        user = super().save(commit=commit)

        user.profile.timezone = self.cleaned_data["timezone"]
        user.profile.save()

        return user

class StatusPageForm(forms.ModelForm):

    class Meta:
        model = StatusPage
        fields = [
            "title",
            "slug",
            "monitors",
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "Beacon System Status"
            }),

            "slug": forms.TextInput(attrs={
                "placeholder": "beacon"
            }),

            "monitors": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user:
            self.fields["monitors"].queryset = Monitor.objects.filter(
                owner=user
            )