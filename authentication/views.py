import logging
import uuid

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from authentication.forms import EmailAuthenticationForm, GeneralUserRegistrationForm
from model.models import User

from .utils import send_verification_email

logger = logging.getLogger(__name__)


def signup(request):
    """一般ユーザー登録"""
    if request.method == "POST":
        form = GeneralUserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password1")
            nickname = form.cleaned_data.get("nickname", "")

            # メールアドレスが既に存在するかチェック
            existing_user = User.objects.filter(email=email).first()

            if existing_user:
                # 既存ユーザーが存在する場合の処理
                if existing_user.is_email_verified:
                    # すでに確認済みの場合 - セキュリティ上、新規登録と同じメッセージ
                    messages.success(
                        request,
                        "登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
                    )
                    return redirect("signup_complete")
                else:
                    # 未確認の場合は情報を更新して確認メールを再送信
                    try:
                        existing_user.set_password(password)
                        existing_user.nickname = nickname
                        existing_user.email_verification_token = (
                            uuid.uuid4()
                        )  # 新しいトークンを生成
                        existing_user.save()

                        send_verification_email(existing_user, request)
                        messages.success(
                            request,
                            "登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
                        )
                        return redirect("signup_complete")
                    except Exception as e:
                        logger.info(e)
                        messages.success(
                            request,
                            "登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
                        )
                        return redirect("signup_complete")
            else:
                # 新規ユーザーの場合
                try:
                    # 手動でユーザーを作成
                    user = User(
                        email=email,
                        nickname=nickname,
                        is_active=False,
                        is_email_verified=False,
                        email_verification_token=uuid.uuid4(),
                    )
                    user.set_password(password)
                    user.save()

                    # 確認メール送信
                    try:
                        send_verification_email(user, request)
                        messages.success(
                            request,
                            "登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
                        )
                        return redirect("signup_complete")
                    except Exception as e:
                        logger.info(e)
                        user.delete()
                        messages.error(
                            request,
                            "登録処理中にエラーが発生しました。しばらくしてから再度お試しください。",
                        )
                        return render(
                            request, "authentication/signup.html", {"form": form}
                        )

                except IntegrityError:
                    # 同時リクエストなどで重複が発生した場合
                    messages.success(
                        request,
                        "登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
                    )
                    return redirect("signup_complete")
    else:
        form = GeneralUserRegistrationForm()

    return render(request, "authentication/signup.html", {"form": form})


def verify_email(request, token):
    """メールアドレス確認"""
    try:
        user = get_object_or_404(User, email_verification_token=token)

        # トークンの有効期限チェック
        if not user.is_verification_token_valid():
            messages.error(
                request, "確認リンクの有効期限が切れています。再度登録をお願いします。"
            )
            return redirect("signup")

        # 既に確認済みの場合
        if user.is_email_verified:
            messages.info(request, "既にメールアドレスは確認済みです。")
            return redirect("signin")

        # メール確認完了
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])

        messages.success(
            request, "メールアドレスの確認が完了しました。ログインしてください。"
        )
        return redirect("signin")

    except User.DoesNotExist:
        messages.error(request, "無効な確認リンクです。")
        return redirect("signup")


def resend_verification_email(request):
    """確認メール再送信"""
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email, is_email_verified=False)
            send_verification_email(user, request)
            messages.success(request, "確認メールを再送信しました。")
        except User.DoesNotExist:
            messages.error(
                request,
                "そのメールアドレスのユーザーが見つからないか、既に確認済みです。",
            )

        return redirect("resend_verification")

    return render(request, "authentication/resend_verification.html")


def signup_complete(request):
    """登録完了ページ"""
    return render(request, "authentication/signup_complete.html")


def signin(request):
    """メールアドレスでログイン"""
    if request.method == "POST":
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"ようこそ、{user.get_display_name()}さん!")
                next_url = request.GET.get("next") or request.POST.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect("/")
            else:
                messages.error(
                    request, "メールアドレスまたはパスワードが正しくありません。"
                )
        else:
            # メール未確認エラーの場合は特別なメッセージ
            if "email_not_verified" in str(form.errors):
                # メール再送信リンクを表示
                messages.error(
                    request,
                    "メールアドレスの確認が完了していません。"
                    '<a href="/authentication/resend-verification/">確認メールを再送信</a>',
                    extra_tags="safe",
                )
    else:
        form = EmailAuthenticationForm()

    return render(request, "authentication/signin.html", {"form": form})


@login_required
def home(request):
    """ホーム画面（ログイン必須）"""
    return render(request, "authentication/home.html")


def signout(request):
    """サインアウトビュー"""
    logout(request)
    messages.success(request, "ログアウトしました。")
    return redirect("signin")
