from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User


class LoginForm(forms.Form):
    """Form for user authentication supporting username or email."""
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        }),
        required=True
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            # Check if user passed email instead of username
            user = authenticate(username=username, password=password)
            if user is None and '@' in username:
                try:
                    user_obj = User.objects.get(email__iexact=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is None:
                raise ValidationError("Invalid username/email or password.")
            if not user.is_active:
                raise ValidationError("This account is currently disabled.")

            self.user_cache = user
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)


class RegisterForm(forms.ModelForm):
    """Form for new user registration."""
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    full_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full Name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    PUBLIC_ROLE_CHOICES = [('analyst', 'Analyst'), ('viewer', 'Viewer')]
    role = forms.ChoiceField(
        choices=PUBLIC_ROLE_CHOICES,
        required=False,
        initial='analyst',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create Password'
        }),
        required=True
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        }),
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Passwords do not match.")

        # Ensure either first_name/last_name or full_name is present
        fn = (cleaned_data.get('first_name') or '').strip()
        ln = (cleaned_data.get('last_name') or '').strip()
        fullname = (cleaned_data.get('full_name') or '').strip()

        if not fn and not fullname:
            self.add_error('first_name', "Please enter your first name or full name.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])

        fn = (self.cleaned_data.get('first_name') or '').strip()
        ln = (self.cleaned_data.get('last_name') or '').strip()
        fullname = (self.cleaned_data.get('full_name') or '').strip()

        if fn or ln:
            user.first_name = fn
            user.last_name = ln
        elif fullname:
            if ' ' in fullname:
                user.first_name, user.last_name = fullname.split(' ', 1)
            else:
                user.first_name = fullname
                user.last_name = ''

        role = self.cleaned_data.get('role')
        # Security: Never allow self-registration as admin
        if role == 'admin':
            role = 'analyst'
        if role in dict(User.ROLE_CHOICES):
            user.role = role
        else:
            user.role = 'analyst'

        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Form for updating user profile details."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'organization', 'bio', 'avatar', 'email_notifications']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organization / Police Dept'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Short professional bio'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SettingsForm(forms.ModelForm):
    """Form for updating account and notification preferences."""
    class Meta:
        model = User
        fields = ['email', 'phone', 'organization', 'email_notifications']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
