from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

# カスタムUserモデルを取得
User = get_user_model()


class SignUpForm(UserCreationForm):
    """会員登録用フォーム"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレス'
        })
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ユーザー名'
        })
    )
    password1 = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        })
    )
    password2 = forms.CharField(
        label='パスワード（確認）',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード（確認）'
        })
    )

    class Meta:
        model = User  # get_user_model()で取得したモデルを使用
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('このメールアドレスは既に登録されています。')
        return email


class SignInForm(forms.Form):
    """サインイン用フォーム"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ユーザー名'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        })
    )