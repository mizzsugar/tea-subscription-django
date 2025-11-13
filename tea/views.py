from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from tea.models import Tea
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from tea.forms import SignUpForm, SignInForm


def signup_view(request):
    """会員登録ビュー - 完全フラット"""
    # フォームを作成（POSTデータがあれば使用）
    form = SignUpForm(request.POST or None)
    
    # バリデーション成功時のみ保存処理
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, '会員登録が完了しました。')
        return redirect('home')
    
    # GET時やバリデーション失敗時はフォームを表示
    return render(request, 'accounts/signup.html', {'form': form})


def signin_view(request):
    """サインインビュー - 完全フラット"""
    form = SignInForm(request.POST or None)
    
    # バリデーション成功時のみ認証処理
    if form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        
        if user:
            login(request, user)
            messages.success(request, 'ログインしました。')
            return redirect(request.GET.get('next', 'home'))
        
        messages.error(request, 'ユーザー名またはパスワードが正しくありません。')
    
    return render(request, 'accounts/signin.html', {'form': form})


@login_required
def home_view(request):
    """ホーム画面（ログイン必須）"""
    return render(request, 'accounts/home.html')


def signout_view(request):
    """サインアウトビュー"""
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('signin')


def published_tea_list(request):
    now = timezone.now()
    teas = Tea.objects.filter(published_at__isnull=False, published_at__lt=now)
    return render(request, 'tea/published_tea_list.html', {'teas': teas})


def published_tea_detail(request, tea_id: int):
    now = timezone.now()
    tea = get_object_or_404(Tea, id=tea_id, published_at__isnull=False, published_at__lt=now)
    return render(request, 'tea/published_tea_detail.html', {'tea': tea})
