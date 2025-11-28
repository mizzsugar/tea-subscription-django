from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from model.models import TeaReview


# カスタムUserモデルを取得
User = get_user_model()


class GeneralUserRegistrationForm(forms.Form):
    """一般ユーザー登録フォーム（ModelFormを使わない）"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレス'
        }),
        label='メールアドレス'
    )
    
    nickname = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ニックネーム（任意）'
        }),
        label='ニックネーム'
    )
    
    password1 = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        }),
        help_text='8文字以上で、数字のみは使用できません。'
    )
    
    password2 = forms.CharField(
        label='パスワード（確認）',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード（確認）'
        }),
        help_text='確認のため、同じパスワードを入力してください。'
    )
    
    def clean_password1(self):
        """パスワードのバリデーション"""
        password1 = self.cleaned_data.get('password1')
        
        # Djangoのパスワードバリデーターを実行
        try:
            validate_password(password1)
        except ValidationError as e:
            raise ValidationError(e.messages)
        
        return password1
    
    def clean(self):
        """パスワード一致確認"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError({
                'password2': 'パスワードが一致しません。'
            })
        
        return cleaned_data


class EmailAuthenticationForm(AuthenticationForm):
    """メールアドレス認証フォーム"""
    
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'メールアドレス'}),
        label='メールアドレス'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'パスワード'}),
        label='パスワード'
    )
    
    def confirm_login_allowed(self, user):
        """ログイン可否の確認"""
        # まず親クラスのチェック(is_activeなど)
        super().confirm_login_allowed(user)
        
        # スーパーユーザーとスタッフはメール確認不要
        if user.is_superuser or user.is_staff:
            return
        
        # 一般ユーザーはメール確認必須
        if not user.is_email_verified:
            raise ValidationError(
                'メールアドレスの確認が完了していません。'
                '登録時に送信されたメール内のリンクをクリックしてください。',
                code='email_not_verified',
            )

class ReviewForm(forms.ModelForm):
    """レビューフォーム"""

    rating = forms.ChoiceField(
        choices=TeaReview.RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='評価',
        initial=3,
    )
    
    class Meta:
        model = TeaReview
        fields = ['rating', 'content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'レビューを入力してください'
            }),
        }
        labels = {
            'content': 'レビュー内容',
        }
