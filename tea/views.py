import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Exists, OuterRef
from tea.models import Tea, FavoriteTea, TeaReview
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count, Exists, OuterRef, Value, BooleanField
from tea.forms import GeneralUserRegistrationForm, EmailAuthenticationForm, ReviewForm
from .utils import send_verification_email
from tea.models import User
from django.db import IntegrityError


def signup(request):
    """一般ユーザー登録"""
    if request.method == 'POST':
        form = GeneralUserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            nickname = form.cleaned_data.get('nickname', '')
            
            # メールアドレスが既に存在するかチェック
            existing_user = User.objects.filter(email=email).first()
            
            if existing_user:
                # 既存ユーザーが存在する場合の処理
                if existing_user.is_email_verified:
                    # すでに確認済みの場合 - セキュリティ上、新規登録と同じメッセージ
                    messages.success(
                        request, 
                        '登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。'
                    )
                    return redirect('signup_complete')
                else:
                    # 未確認の場合は情報を更新して確認メールを再送信
                    try:
                        existing_user.set_password(password)
                        existing_user.nickname = nickname
                        existing_user.email_verification_token = uuid.uuid4()  # 新しいトークンを生成
                        existing_user.save()
                        
                        send_verification_email(existing_user, request)
                        messages.success(
                            request, 
                            '登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。'
                        )
                        return redirect('signup_complete')
                    except Exception as e:
                        # メール送信失敗時も同じメッセージ
                        messages.success(
                            request, 
                            '登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。'
                        )
                        return redirect('signup_complete')
            else:
                # 新規ユーザーの場合
                try:
                    # 手動でユーザーを作成
                    user = User(
                        email=email,
                        nickname=nickname,
                        is_active=False,
                        is_email_verified=False,
                        email_verification_token=uuid.uuid4()
                    )
                    user.set_password(password)
                    user.save()
                    
                    # 確認メール送信
                    try:
                        send_verification_email(user, request)
                        messages.success(
                            request, 
                            '登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。'
                        )
                        return redirect('signup_complete')
                    except Exception as e:
                        # メール送信失敗時はユーザーを削除
                        user.delete()
                        messages.error(request, '登録処理中にエラーが発生しました。しばらくしてから再度お試しください。')
                        return render(request, 'accounts/signup.html', {'form': form})
                        
                except IntegrityError:
                    # 同時リクエストなどで重複が発生した場合
                    messages.success(
                        request, 
                        '登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。'
                    )
                    return redirect('signup_complete')
    else:
        form = GeneralUserRegistrationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def verify_email(request, token):
    """メールアドレス確認"""
    try:
        user = get_object_or_404(User, email_verification_token=token)
        
        # トークンの有効期限チェック
        if not user.is_verification_token_valid():
            messages.error(request, '確認リンクの有効期限が切れています。再度登録をお願いします。')
            return redirect('signup')
        
        # 既に確認済みの場合
        if user.is_email_verified:
            messages.info(request, '既にメールアドレスは確認済みです。')
            return redirect('signin')
        
        # メール確認完了
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=['is_email_verified', 'is_active'])
        
        messages.success(request, 'メールアドレスの確認が完了しました。ログインしてください。')
        return redirect('signin')
        
    except User.DoesNotExist:
        messages.error(request, '無効な確認リンクです。')
        return redirect('signup')


def resend_verification_email(request):
    """確認メール再送信"""
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, is_email_verified=False)
            send_verification_email(user, request)
            messages.success(request, '確認メールを再送信しました。')
        except User.DoesNotExist:
            messages.error(request, 'そのメールアドレスのユーザーが見つからないか、既に確認済みです。')
        
        return redirect('resend_verification')
    
    return render(request, 'accounts/resend_verification.html')


def signup_complete(request):
    """登録完了ページ"""
    return render(request, 'accounts/signup_complete.html')

def signin(request):
    """メールアドレスでログイン"""
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'ようこそ、{user.get_display_name()}さん!')
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('/')
            else:
                messages.error(request, 'メールアドレスまたはパスワードが正しくありません。')
        else:
            # メール未確認エラーの場合は特別なメッセージ
            if 'email_not_verified' in str(form.errors):
                # メール再送信リンクを表示
                messages.error(
                    request, 
                    'メールアドレスの確認が完了していません。'
                    '<a href="/accounts/resend-verification/">確認メールを再送信</a>',
                    extra_tags='safe'
                )
    else:
        form = EmailAuthenticationForm()
    
    return render(request, 'accounts/signin.html', {'form': form})


@login_required
def home(request):
    """ホーム画面（ログイン必須）"""
    return render(request, 'accounts/home.html')


def signout(request):
    """サインアウトビュー"""
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('signin')


def published_tea_list(request):
    now = timezone.now()
    teas = Tea.objects.filter(published_at__isnull=False, published_at__lt=now).\
        annotate(favorites_count=Count('favorited_by'))
    
    # ログイン中のユーザーがいいねしているかをアノテーション
    if request.user.is_authenticated:
        user_favorite = FavoriteTea.objects.filter(
            user=request.user,
            tea=OuterRef('pk')
        )
        teas = teas.annotate(is_favorited=Exists(user_favorite))
    else:
        # ログインしていない場合はすべてFalse
        teas = teas.annotate(
            is_favorited=Value(False, output_field=BooleanField())
        )
    
    return render(request, 'tea/published_tea_list.html', {'teas': teas})


def published_tea_detail(request, tea_id: int):
    """お茶詳細ページ"""
    now = timezone.now()

    # 1つのお茶だけにアノテーションを適用
    queryset = Tea.objects.filter(pk=tea_id, published_at__isnull=False, published_at__lt=now).\
        annotate(favorites_count=Count('favorited_by'))
    
    if request.user.is_authenticated:
        user_favorite = FavoriteTea.objects.filter(
            user=request.user,
            tea=OuterRef('pk')
        )
        queryset = queryset.annotate(is_favorited=Exists(user_favorite))
    else:
        queryset = queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField())
        )
    
    tea = get_object_or_404(queryset)

    # レビュー一覧を取得
    reviews = tea.reviews.select_related('user').all()
    
    # ユーザーが既にレビュー済みかチェック
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = TeaReview.objects.filter(
            tea=tea,
            user=request.user
        ).exists()

    # レビューフォーム
    review_form = None
    if request.user.is_authenticated and not user_has_reviewed:
        review_form = ReviewForm()

    return render(request, 'tea/published_tea_detail.html', {
        'tea': tea,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'review_form': review_form,
    })



@login_required
def add_favorite_tea(request, tea_id):
    """お気に入りに追加"""
    if request.method == 'POST':
        tea = get_object_or_404(Tea, pk=tea_id)
        
        # お気に入りを追加（既に存在する場合は何もしない）
        FavoriteTea.objects.get_or_create(user=request.user, tea=tea)
        
        # 更新後のいいね数を取得
        favorites_count = tea.favorited_by.count()
        
        return JsonResponse({
            'success': True,
            'is_favorited': True,
            'favorites_count': favorites_count,
            'add_url': reverse('add_favorite_tea', args=[tea_id]),
            'cancel_url': reverse('cancel_favorite_tea', args=[tea_id])
        })
    
    return JsonResponse({'success': False}, status=400)


@login_required
def cancel_favorite_tea(request, tea_id):
    """お気に入りを解除"""
    if request.method == 'POST':
        tea = get_object_or_404(Tea, pk=tea_id)
        
        # お気に入りを削除
        FavoriteTea.objects.filter(user=request.user, tea=tea).delete()
        
        # 更新後のいいね数を取得
        favorites_count = tea.favorited_by.count()
        
        return JsonResponse({
            'success': True,
            'is_favorited': False,
            'favorites_count': favorites_count,
            'add_url': reverse('add_favorite_tea', args=[tea_id]),
            'cancel_url': reverse('cancel_favorite_tea', args=[tea_id])
        })
    
    return JsonResponse({'success': False}, status=400)


@login_required
def add_review(request, tea_id):
    """お茶のレビューをする"""
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.tea_id = tea_id
        review.save()
        messages.success(request, 'レビューが送信されました。')
        return redirect('published_tea_detail', tea_id=tea_id)
