from django.contrib.auth.models import AbstractUser

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """カスタムユーザーマスタ"""
    nickname = models.CharField(max_length=30, blank=True, verbose_name="ニックネーム")

    def __str__(self):
        return self.nickname or self.username

    @property
    def favorites_count(self):
        return self.favorite_teas.count()


class Tea(models.Model):
    """お茶マスタ"""
    STEAM_TYPE_CHOICES = [
        ("light", "浅蒸し"),
        ("middle", "中蒸し"),
        ("deep", "深蒸し"),
    ]

    name = models.CharField(max_length=100, verbose_name="お茶名")
    
    steam_type = models.CharField(max_length=20, choices=STEAM_TYPE_CHOICES, verbose_name="蒸し度")
    origin = models.CharField(max_length=100, blank=True, verbose_name="産地")
    description = models.TextField(blank=True, verbose_name="説明")
    caffeine_free = models.BooleanField(default=False, verbose_name="カフェインレス")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="公開日時")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return self.name


class FavoriteTea(models.Model):
    """お気に入りテーブル（ユーザーとお茶の中間テーブル）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_teas")
    tea = models.ForeignKey(Tea, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    class Meta:
        unique_together = ("user", "tea")  # 同じお茶を重複登録できないように
        verbose_name = "お気に入り"
        verbose_name_plural = "お気に入り一覧"

    def __str__(self):
        return f"{self.user} → {self.tea}"


class TeaReview(models.Model):
    """お茶に対するレビュー"""
    RATING_CHOICES = [
        (1, "★☆☆☆☆"),
        (2, "★★☆☆☆"),
        (3, "★★★☆☆"),
        (4, "★★★★☆"),
        (5, "★★★★★"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tea_reviews")
    tea = models.ForeignKey(Tea, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(verbose_name="評価", choices=RATING_CHOICES)
    content = models.TextField(blank=True, verbose_name="レビュー内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    class Meta:
        unique_together = ("user", "tea")
        verbose_name = "レビュー"
        verbose_name_plural = "レビュー一覧"
    
    def __str__(self):
        return f"{self.user} のレビュー: {self.content[:20]}..."
    
    def get_star_display(self):
        """星表示を返す"""
        return "★" * self.rating + "☆" * (5 - self.rating)